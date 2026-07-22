"""Observe TRAE and TRAE Solo local session indexes without reading messages."""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from lwm import lifecycle


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def _workspace(path: Path) -> str | None:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return None
    folder = payload.get("folder")
    if not isinstance(folder, str) or not folder:
        workspace = payload.get("workspace")
        if not isinstance(workspace, str) or not workspace:
            return None
        parsed_workspace = urlparse(workspace)
        workspace_path = Path(
            unquote(parsed_workspace.path)
            if parsed_workspace.scheme == "file"
            else workspace
        )
        workspace_payload = _load_json(workspace_path)
        folders = (
            workspace_payload.get("folders")
            if isinstance(workspace_payload, dict)
            else None
        )
        first = folders[0] if isinstance(folders, list) and folders else None
        folder = first.get("path") if isinstance(first, dict) else None
        if isinstance(folder, str) and folder and not Path(folder).is_absolute():
            folder = str((workspace_path.parent / folder).resolve())
    if not isinstance(folder, str) or not folder:
        return None
    parsed = urlparse(folder)
    return unquote(parsed.path) if parsed.scheme == "file" else folder


def _session_ids(database: Path) -> tuple[str, ...]:
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT value FROM ItemTable WHERE key = ?",
                ("icube_session_agent_map",),
            ).fetchone()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return ()
    try:
        payload = json.loads(row[0]) if row and isinstance(row[0], str) else None
    except json.JSONDecodeError:
        return ()
    return tuple(str(key) for key in payload) if isinstance(payload, dict) else ()


def observe(
    root: Path,
    storage: Path,
    tool: str,
    seen: set[str],
    *,
    settle_seconds: float,
) -> None:
    if not storage.is_dir():
        return
    cutoff = time.time() - settle_seconds
    for workspace_dir in storage.iterdir():
        workspace = _workspace(workspace_dir / "workspace.json")
        database = workspace_dir / "state.vscdb"
        if not workspace or not database.is_file():
            continue
        try:
            settled = database.stat().st_mtime <= cutoff
        except OSError:
            settled = False
        for session_id in _session_ids(database):
            start_key = f"{tool}:start:{workspace_dir.name}:{session_id}"
            if start_key not in seen:
                lifecycle.start(
                    root,
                    tool=tool,
                    project_path=workspace,
                    session_id=session_id,
                    source="watcher-observed",
                )
                seen.add(start_key)
            stop_key = f"{tool}:stop:{workspace_dir.name}:{session_id}"
            if settled and stop_key not in seen:
                lifecycle.stop(
                    root,
                    tool=tool,
                    project_path=workspace,
                    session_id=session_id,
                    task=f"{tool} local session observed idle",
                    source="watcher-observed",
                )
                seen.add(stop_key)


def main() -> int:
    parser = argparse.ArgumentParser(prog="trae-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument("--settle-seconds", type=float, default=30.0)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    seen_path = root / "state" / "trae-session-events.json"
    payload = _load_json(seen_path)
    seen = set(payload) if isinstance(payload, list) else set()
    base = Path.home() / "Library" / "Application Support"
    for tool, app_dir in (("trae", "Trae"), ("trae-solo", "TRAE SOLO")):
        observe(
            root,
            base / app_dir / "User" / "workspaceStorage",
            tool,
            seen,
            settle_seconds=args.settle_seconds,
        )
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
