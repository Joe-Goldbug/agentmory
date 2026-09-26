"""Observe local VS Code Copilot session metadata without reading prompts.

The watcher remains the fallback for hosts that have not fired a native
integration. The packaged VS Code-compatible companion is the native bridge
path; until the host fires it, this adapter uses only session headers/event
types, never message content, and labels receipts ``watcher-observed`` so
capability probing cannot mistake observation for a native callback.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from lwm import lifecycle


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
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return events
    for line in lines:
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
        for event in _jsonl_events(events):
            _observe_boundary(root, workspace, session.name, event, seen, f"cli:{session}")


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
