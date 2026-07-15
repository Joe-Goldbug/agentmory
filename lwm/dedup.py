"""Event deduplication and the ``state/event-index.json`` ledger.

``dedup_key`` = sha1(``timestamp_date | tool | project_id | event_type |
task[:80] | sorted(verification)[:80]``). Re-submitting the same key
writes the new event to ``rejected/`` with ``reason=duplicate``.

For ``session_summary`` and ``session_start`` the same ``session_id``
within 24 hours collapses to a single kept event.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INDEX_FILENAME = "event-index.json"


@dataclass(frozen=True)
class DedupDecision:
    duplicate: bool
    key: str
    reason: str | None = None
    existing_event_id: str | None = None


def _safe_first80(value: Any) -> str:
    text = "" if value is None else str(value)
    return text[:80]


def dedup_key(event: dict[str, Any]) -> str:
    """Compute the deterministic dedup key for an event."""

    timestamp = str(event.get("timestamp") or "")
    date_part = timestamp[:10] or "unknown"
    task_part = _safe_first80(event.get("task"))
    verification_part = ",".join(
        sorted(_safe_first80(v) for v in event.get("verification") or [])
    )
    fields = [
        date_part,
        str(event.get("tool") or ""),
        str(event.get("project_id") or ""),
        str(event.get("event_type") or ""),
        task_part,
        verification_part,
    ]
    payload = "|".join(fields).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def index_path(root: Path) -> Path:
    return (root / "state" / INDEX_FILENAME).resolve()


def load_event_index(root: Path) -> dict[str, dict[str, Any]]:
    path = index_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def save_event_index(root: Path, index: dict[str, dict[str, Any]]) -> Path:
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def record_event(
    root: Path,
    event: dict[str, Any],
    *,
    bucket: str,
    file_path: str,
) -> None:
    """Append/overwrite the index entry for an event."""

    index = load_event_index(root)
    index[event["event_id"]] = {
        "key": dedup_key(event),
        "tool": event.get("tool"),
        "project_id": event.get("project_id"),
        "event_type": event.get("event_type"),
        "timestamp": event.get("timestamp"),
        "bucket": bucket,
        "file": file_path,
    }
    save_event_index(root, index)


def _session_key_exists(
    index: dict[str, dict[str, Any]],
    *,
    tool: str,
    session_id: str,
    event_type: str,
    project_id: str,
    incoming_ts: datetime,
) -> str | None:
    """Return existing event_id if another session event within 24h is indexed."""

    if event_type not in {"session_start", "session_summary"}:
        return None
    window = timedelta(hours=24)
    for event_id, entry in index.items():
        if entry.get("bucket") not in {"inbox", "processed"}:
            continue
        if entry.get("event_type") not in {"session_start", "session_summary"}:
            continue
        meta = entry
        if meta.get("tool") not in {None, tool}:
            continue
        if meta.get("project_id") != project_id:
            continue
        existing_ts = _parse_iso(str(meta.get("timestamp")))
        if existing_ts is None:
            continue
        if abs(existing_ts - incoming_ts) > window:
            continue
        return event_id
    return None


def evaluate(
    root: Path,
    event: dict[str, Any],
) -> DedupDecision:
    """Decide whether the given event is a duplicate of an existing one."""

    key = dedup_key(event)
    index = load_event_index(root)
    for event_id, entry in index.items():
        if entry.get("key") == key and event_id != event.get("event_id"):
            return DedupDecision(
                duplicate=True,
                key=key,
                reason="dedup_key",
                existing_event_id=event_id,
            )
    session_id = event.get("session_id")
    ts = _parse_iso(str(event.get("timestamp")))
    if session_id and ts is not None:
        existing = _session_key_exists(
            index,
            tool=str(event.get("tool") or ""),
            session_id=str(session_id),
            event_type=str(event.get("event_type") or ""),
            project_id=str(event.get("project_id") or ""),
            incoming_ts=ts,
        )
        if existing:
            return DedupDecision(
                duplicate=True,
                key=key,
                reason="session_window",
                existing_event_id=existing,
            )
    return DedupDecision(duplicate=False, key=key)


__all__ = [
    "DedupDecision",
    "INDEX_FILENAME",
    "dedup_key",
    "evaluate",
    "index_path",
    "load_event_index",
    "record_event",
    "save_event_index",
]
