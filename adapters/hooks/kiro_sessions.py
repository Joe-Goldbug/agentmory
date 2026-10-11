"""Observe Kiro boundaries and bounded results without persisting raw chat."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from lwm import lifecycle
from adapters.hooks._common import host_results


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def observe(root: Path, sessions_root: Path, seen: set[str], *, settle_seconds: float) -> None:
    if not sessions_root.is_dir():
        return
    cutoff = time.time() - settle_seconds
    for index_path in sessions_root.glob("*/sessions.json"):
        payload = _load_json(index_path)
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            session_id = str(item.get("sessionId") or "")
            workspace = str(item.get("workspaceDirectory") or "")
            if not session_id or not workspace:
                continue
            start_key = f"start:{index_path.parent.name}:{session_id}"
            if start_key not in seen:
                lifecycle.start(
                    root,
                    tool="kiro",
                    project_path=workspace,
                    session_id=session_id,
                    source="watcher-observed",
                )
                seen.add(start_key)

            session_path = index_path.parent / f"{session_id}.json"
            try:
                settled = session_path.is_file() and session_path.stat().st_mtime <= cutoff
            except OSError:
                settled = False
            stop_key = f"stop:{index_path.parent.name}:{session_id}:{session_path.stat().st_mtime_ns}" if settled else ""
            if settled and stop_key not in seen:
                summary = None
                if session_path.stat().st_size <= 2_000_000:
                    session = _load_json(session_path)
                    if isinstance(session, dict):
                        session_workspace = session.get("workspaceDirectory") or session.get("workspacePath")
                        if session_workspace and Path(str(session_workspace)).resolve() != Path(workspace).resolve():
                            continue
                        history = session.get("history")
                        if isinstance(history, list):
                            summary = host_results({"transcript": history[-160:]}, host="kiro")
                lifecycle.stop(
                    root,
                    tool="kiro",
                    project_path=workspace,
                    session_id=session_id,
                    task="Kiro local session observed idle",
                    source="watcher-observed",
                    task_id=str((summary or {}).get("task_id") or "") or None,
                    handoff_summary=summary,
                    source_timestamp=datetime.fromtimestamp(session_path.stat().st_mtime, timezone.utc).isoformat(),
                )
                seen.add(stop_key)


def main() -> int:
    parser = argparse.ArgumentParser(prog="kiro-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--sessions-root",
        default=str(
            Path.home()
            / "Library"
            / "Application Support"
            / "Kiro"
            / "User"
            / "globalStorage"
            / "kiro.kiroagent"
            / "workspace-sessions"
        ),
    )
    parser.add_argument("--settle-seconds", type=float, default=30.0)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    seen_path = root / "state" / "kiro-session-events.json"
    payload = _load_json(seen_path)
    seen = set(payload) if isinstance(payload, list) else set()
    observe(
        root,
        Path(args.sessions_root).expanduser(),
        seen,
        settle_seconds=args.settle_seconds,
    )
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
