"""Codex exporter: turn ``~/.codex/sessions/*.jsonl`` into central events.

Codex (the CLI) writes per-session transcripts under
``~/.codex/sessions/`` with one JSON object per line. This adapter runs
on a timer (LaunchAgent or watch trigger) and emits a
``workflow_observation`` event per session that captures the user
prompt and the last assistant reply. It mirrors the level-3 model used
by the shell adapter: explicit, audited, deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from lwm import lifecycle


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _message(entry: dict[str, Any]) -> dict[str, Any]:
    if entry.get("type") == "response_item" and isinstance(entry.get("payload"), dict):
        payload = entry["payload"]
        return payload if payload.get("type") == "message" else {}
    message = entry.get("message")
    return message if isinstance(message, dict) else {}


def _entry_text(entry: dict[str, Any]) -> str:
    msg = _message(entry)
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "input_text", "output_text"}:
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool:{block.get('name', '?')}]")
        return "\n".join(p for p in parts if p)
    return ""


def _summarize_session(path: Path) -> dict[str, Any]:
    entries = _read_jsonl(path)
    if not entries:
        return {}
    messages = [(entry, _message(entry)) for entry in entries]
    user_prompts = [entry for entry, message in messages if message.get("role") == "user"]
    assistant_msgs = [
        entry for entry, message in messages if message.get("role") == "assistant"
    ]
    metadata = next(
        (
            entry.get("payload")
            for entry in entries
            if entry.get("type") == "session_meta" and isinstance(entry.get("payload"), dict)
        ),
        {},
    )
    first_prompt = _entry_text(user_prompts[0]) if user_prompts else ""
    last_reply = _entry_text(assistant_msgs[-1]) if assistant_msgs else ""
    return {
        "first_prompt": first_prompt[:400],
        "last_reply": last_reply[:400],
        "tool_calls": sum(
            1
            for e in entries
            for blk in ((e.get("message") or {}).get("content") or [])
            if isinstance(blk, dict) and blk.get("type") == "tool_use"
        ),
        "entry_count": len(entries),
        "project_path": str(metadata.get("cwd") or ""),
        "session_id": str(metadata.get("id") or path.stem),
    }


def emit_session(
    root: Path,
    session_path: Path,
    *,
    settle_seconds: float = 30.0,
    seen: set[str] | None = None,
) -> int:
    summary = _summarize_session(session_path)
    if not summary:
        return 0
    project_path = summary["project_path"]
    if not project_path:
        return 0
    session_id = summary["session_id"]
    seen = seen if seen is not None else set()
    start_key = f"start:{session_id}"
    if start_key not in seen:
        lifecycle.start(
            root,
            tool="codex",
            project_path=project_path,
            session_id=session_id,
            source="watcher-observed",
        )
        seen.add(start_key)
    try:
        stat = session_path.stat()
    except OSError:
        return 0
    event_key = f"summary:{session_id}:{stat.st_mtime_ns}"
    event = {
        "tool": "codex",
        "project_path": project_path,
        "session_id": session_id,
        "event_type": "workflow_observation",
        "task": summary["first_prompt"] or "(no user prompt)",
        "verification": [],
        "decisions": [],
        "changes": [],
        "importance": "project",
        "privacy": "sanitized",
        "source": {"kind": "file-watch", "path": str(session_path)},
        "tags": ["codex", "session-summary"],
    }
    try:
        from adapters.hooks._common import emit

        result = emit(root, event) if event_key not in seen else 0
        seen.add(event_key)
        settled = stat.st_mtime <= time.time() - settle_seconds
        stop_key = f"stop:{session_id}"
        if settled and stop_key not in seen:
            lifecycle.stop(
                root,
                tool="codex",
                project_path=project_path,
                session_id=session_id,
                task="Codex local session observed idle",
                source="watcher-observed",
            )
            seen.add(stop_key)
        return result
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"codex adapter failed: {exc}\n")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="codex-export")
    parser.add_argument("--root", required=True, help="Wiki/WorkMem root.")
    parser.add_argument(
        "--sessions",
        default=os.environ.get("CODEX_SESSIONS_DIR", str(Path.home() / ".codex" / "sessions")),
        help="Directory containing Codex session JSONL files.",
    )
    parser.add_argument("--settle-seconds", type=float, default=30.0)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    sessions = Path(args.sessions).expanduser()
    if not sessions.is_dir():
        print(f"no sessions dir: {sessions}", file=sys.stderr)
        return 0
    seen_path = root / "state" / "codex-session-events.json"
    try:
        payload = json.loads(seen_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = []
    seen = set(payload) if isinstance(payload, list) else set()
    rc = 0
    for session in sorted(sessions.glob("**/*.jsonl")):
        rc |= emit_session(
            root,
            session,
            settle_seconds=args.settle_seconds,
            seen=seen,
        )
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
