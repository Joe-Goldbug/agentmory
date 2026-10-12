"""Observe local VS Code/Copilot boundaries and bounded completed-turn results.

The watcher remains the fallback for hosts that have not fired a native
integration. The packaged VS Code-compatible companion is the native bridge
path. This adapter never persists raw prompts or reasoning, and labels
receipts ``watcher-observed`` so
capability probing cannot mistake observation for a native callback.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from lwm import lifecycle
from adapters.hooks._common import host_results


def _workspace_path(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("git_root: ") or line.startswith("cwd: "):
                return line.split(": ", 1)[1].strip()
    except OSError:
        return None
    return None


def _workspace_storage_path(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    folder = payload.get("folder") if isinstance(payload, dict) else None
    if not isinstance(folder, str) or not folder:
        return None
    parsed = urlparse(folder)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return folder


def _jsonl_events(path: Path) -> list[dict]:
    events: list[dict] = []
    try:
        with path.open("rb") as stream:
            size = stream.seek(0, 2)
            stream.seek(max(0, size - 262144))
            data = stream.read(262144)
        lines = data.splitlines()
        if size > 262144:
            lines = lines[1:]
    except OSError:
        return events
    for line in lines[-160:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _observe_cli_sessions(root: Path, sessions: Path, seen: set[str]) -> None:
    if not sessions.is_dir():
        return
    for session in sessions.iterdir():
        workspace = _workspace_path(session / "workspace.yaml")
        events = session / "events.jsonl"
        if not workspace or not events.is_file():
            continue
        history = _jsonl_events(events)
        for event in history:
            _observe_boundary(root, workspace, session.name, event, seen, f"cli:{session}")
        _observe_results(root, workspace, session.name, history, seen, f"cli:{session}")


def _observe_results(root: Path, workspace: str, session_id: str,
                     events: list[dict], seen: set[str], prefix: str) -> None:
    rows = []
    for event in events[-160:]:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        kind = event.get("type")
        if kind == "user.message":
            rows = []
        elif kind == "assistant.message":
            rows.append({"role": "assistant", "content": data.get("content")})
        elif kind == "tool.execution_complete":
            result = data.get("result")
            output = result.get("content") if isinstance(result, dict) else result
            if output:
                rows.append({"role": "tool", "content": [{"type": "tool_result",
                    "content": output, "is_error": data.get("success") is False}]})
        elif kind == "assistant.turn_end":
            key = f"result:{prefix}:{event.get('id')}"
            if not event.get("id") or key in seen:
                continue
            summary = host_results({"transcript": rows}, host="vscode")
            if summary is not None:
                task_id = f"vscode:{session_id}:{event['id']}"
                lifecycle.stop(root, tool="vscode", project_path=workspace, session_id=session_id,
                    source="watcher-observed", task_id=task_id, handoff_summary={**summary, "task_id": task_id},
                    source_timestamp=event.get("timestamp") if isinstance(event.get("timestamp"),str) else None)
                seen.add(key)


def _observe_workspace_storage(
    root: Path, storage: Path, seen: set[str], *, settle_seconds: float
) -> None:
    if not storage.is_dir():
        return
    cutoff = time.time() - settle_seconds
    for workspace_dir in storage.iterdir():
        workspace = _workspace_storage_path(workspace_dir / "workspace.json")
        transcripts = workspace_dir / "GitHub.copilot-chat" / "transcripts"
        if not workspace or not transcripts.is_dir():
            continue
        for transcript in transcripts.glob("*.jsonl"):
            events = _jsonl_events(transcript)
            session_id = transcript.stem
            started = False
            for event in events:
                kind = str(event.get("type") or "")
                if kind == "session.start":
                    started = True
                _observe_boundary(
                    root, workspace, session_id, event, seen, f"transcript:{transcript}"
                )
            _observe_results(root, workspace, session_id, events, seen, f"transcript:{transcript}")
            if started:
                try:
                    stat = transcript.stat()
                except OSError:
                    continue
                # VS Code's transcript format has no idle event. A settled
                # transcript is the strongest local observation available.
                idle_key = f"transcript-idle:{transcript}:{stat.st_mtime_ns}"
                if stat.st_mtime <= cutoff and idle_key not in seen:
                    lifecycle.stop(
                        root,
                        tool="vscode",
                        project_path=workspace,
                        session_id=session_id,
                        task="VS Code Copilot transcript observed idle",
                        source="watcher-observed",
                    )
                    seen.add(idle_key)


def _observe_boundary(
    root: Path,
    workspace: str,
    fallback_session_id: str,
    event: dict,
    seen: set[str],
    key_prefix: str,
) -> None:
    event_id = str(event.get("id") or "")
    kind = str(event.get("type") or "")
    seen_key = f"{key_prefix}:{event_id}"
    if not event_id or seen_key in seen:
        return
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    session_id = str(data.get("sessionId") or fallback_session_id)
    if kind == "session.start":
        lifecycle.start(
            root, tool="vscode", project_path=workspace,
            session_id=session_id, source="watcher-observed"
        )
    elif kind == "session.idle":
        lifecycle.stop(
            root, tool="vscode", project_path=workspace,
            session_id=session_id, source="watcher-observed"
        )
    else:
        return
    seen.add(seen_key)


def main() -> int:
    parser = argparse.ArgumentParser(prog="vscode-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument("--sessions", default=str(Path.home() / ".copilot" / "session-state"))
    parser.add_argument(
        "--workspace-storage",
        default=str(
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "workspaceStorage"
        ),
    )
    parser.add_argument("--settle-seconds", type=float, default=30.0)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    sessions = Path(args.sessions).expanduser()
    seen_path = root / "state" / "vscode-session-events.json"
    try:
        seen = set(json.loads(seen_path.read_text(encoding="utf-8"))) if seen_path.is_file() else set()
    except (OSError, json.JSONDecodeError):
        seen = set()
    _observe_cli_sessions(root, sessions, seen)
    _observe_workspace_storage(
        root,
        Path(args.workspace_storage).expanduser(),
        seen,
        settle_seconds=args.settle_seconds,
    )
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
