"""Observe Antigravity conversation metadata without reading message content."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from lwm import lifecycle


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def _workspace_uri(summary: dict) -> str | None:
    uris = summary.get("WorkspaceURIs")
    if not isinstance(uris, list) or not uris or not isinstance(uris[0], str):
        return None
    parsed = urlparse(uris[0])
    return unquote(parsed.path) if parsed.scheme == "file" else uris[0]


def _is_settled(value: object, settle_seconds: float) -> bool:
    if not isinstance(value, str):
        return False
    try:
        updated = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return updated <= datetime.now(timezone.utc) - timedelta(seconds=settle_seconds)


def observe(root: Path, metadata_path: Path, seen: set[str], *, settle_seconds: float) -> None:
    payload = _load_json(metadata_path)
    conversations = payload.get("conversations") if isinstance(payload, dict) else None
    if not isinstance(conversations, dict):
        return
    for fallback_id, item in conversations.items():
        if not isinstance(item, dict):
            continue
        summary = item.get("summary")
        if not isinstance(summary, dict):
            continue
        session_id = str(summary.get("ID") or fallback_id)
        workspace = _workspace_uri(summary)
        if not session_id or not workspace:
            continue
        start_key = f"start:{session_id}"
        if start_key not in seen:
            lifecycle.start(
                root,
                tool="antigravity",
                project_path=workspace,
                session_id=session_id,
                source="watcher-observed",
            )
            seen.add(start_key)
        stop_key = f"stop:{session_id}"
        if _is_settled(summary.get("UpdatedAt"), settle_seconds) and stop_key not in seen:
            lifecycle.stop(
                root,
                tool="antigravity",
                project_path=workspace,
                session_id=session_id,
                task="Antigravity local conversation observed idle",
                source="watcher-observed",
            )
            seen.add(stop_key)


def main() -> int:
    parser = argparse.ArgumentParser(prog="antigravity-sessions")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--metadata",
        default=str(Path.home() / ".gemini" / "antigravity-cli" / "cache" / "conversation_metadata.json"),
    )
    parser.add_argument("--settle-seconds", type=float, default=30.0)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    seen_path = root / "state" / "antigravity-session-events.json"
    payload = _load_json(seen_path)
    seen = set(payload) if isinstance(payload, list) else set()
    observe(
        root,
        Path(args.metadata).expanduser(),
        seen,
        settle_seconds=args.settle_seconds,
    )
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
