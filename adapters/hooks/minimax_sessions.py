"""Observe MiniMax Code session metadata without reading conversation content."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from lwm import lifecycle


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def _sessions(database: Path) -> tuple[dict[str, object], ...]:
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT record_json FROM local_runtime_sessions"
            ).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return ()

    sessions: list[dict[str, object]] = []
    for row in rows:
        try:
            payload = json.loads(row[0]) if row and isinstance(row[0], str) else None
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            sessions.append(payload)
    return tuple(sessions)


def observe(root: Path, database: Path, seen: set[str]) -> None:
    if not database.is_file():
        return
    for item in _sessions(database):
        session_id = str(item.get("sessionId") or "")
        workspace = str(item.get("workspaceDir") or "")
        if not session_id or not workspace:
            continue
        start_key = f"start:{session_id}"
        if start_key not in seen:
            lifecycle.start(
                root,
                tool="minimax",
                project_path=workspace,
                session_id=session_id,
                source="watcher-observed",
            )
            seen.add(start_key)

        stop_key = f"stop:{session_id}"
        if item.get("status") == "finished" and stop_key not in seen:
            lifecycle.stop(
                root,
                tool="minimax",
                project_path=workspace,
                session_id=session_id,
                task="MiniMax Code local session observed finished",
                source="watcher-observed",
            )
            seen.add(stop_key)


def main() -> int:
    parser = argparse.ArgumentParser(prog="minimax-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--database",
        default=str(Path.home() / ".minimax" / "v2" / "sqlite" / "runtime-state.sqlite"),
    )
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    seen_path = root / "state" / "minimax-session-events.json"
    payload = _load_json(seen_path)
    seen = set(payload) if isinstance(payload, list) else set()
    observe(root, Path(args.database).expanduser(), seen)
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
