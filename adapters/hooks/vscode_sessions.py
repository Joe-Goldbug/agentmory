"""Observe local VS Code Copilot session metadata without reading prompts.

VS Code exposes no lifecycle hook for this integration.  The watcher uses only
the local session header and event type, never message content, and labels its
receipts ``watcher-observed`` so capability probing cannot mistake it for a
native callback.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lwm import lifecycle


def _workspace_path(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("git_root: ") or line.startswith("cwd: "):
                return line.split(": ", 1)[1].strip()
    except OSError:
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(prog="vscode-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument("--sessions", default=str(Path.home() / ".copilot" / "session-state"))
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    sessions = Path(args.sessions).expanduser()
    if not sessions.is_dir():
        return 0
    seen_path = root / "state" / "vscode-session-events.json"
    try:
        seen = set(json.loads(seen_path.read_text(encoding="utf-8"))) if seen_path.is_file() else set()
    except (OSError, json.JSONDecodeError):
        seen = set()
    for session in sessions.iterdir():
        workspace = _workspace_path(session / "workspace.yaml")
        events = session / "events.jsonl"
        if not workspace or not events.is_file():
            continue
        for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_id = str(event.get("id") or "")
            kind = str(event.get("type") or "")
            if not event_id or event_id in seen:
                continue
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            session_id = str(data.get("sessionId") or session.name)
            if kind == "session.start":
                lifecycle.start(root, tool="vscode", project_path=workspace, session_id=session_id, source="watcher-observed")
            elif kind == "session.idle":
                lifecycle.stop(root, tool="vscode", project_path=workspace, session_id=session_id, source="watcher-observed")
            else:
                continue
            seen.add(event_id)
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
