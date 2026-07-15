"""Inbox / processed / rejected / failed directory management.

Events arrive in ``<root>/raw/events/inbox/<YYYY-MM-DD>/<event_id>.json``.
Producers write via :func:`submit_event` (atomic temp + rename).
The processor moves them to ``processed/`` or ``rejected/`` or
``failed/`` via :func:`move_event`.

This module never deletes the original on a failed move; the caller
decides whether to retry or quarantine.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_BUCKETS: tuple[str, ...] = ("inbox", "processed", "rejected", "failed")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class InboxStatus:
    root: Path
    inbox: int
    processed: int
    rejected: int
    failed: int

    @property
    def total(self) -> int:
        return self.inbox + self.processed + self.rejected + self.failed

    def render(self) -> str:
        return (
            f"inbox={self.inbox} processed={self.processed} "
            f"rejected={self.rejected} failed={self.failed}"
        )


def events_root(root: Path) -> Path:
    return (root / "raw" / "events").resolve()


def _today_bucket() -> str:
    return datetime.now(tz=timezone.utc).astimezone().date().isoformat()


def bucket_dir(root: Path, bucket: str, *, day: str | None = None) -> Path:
    if bucket not in VALID_BUCKETS:
        raise ValueError(f"invalid bucket: {bucket}")
    day_value = day or _today_bucket()
    if not _DATE_RE.match(day_value):
        raise ValueError(f"invalid date: {day_value}")
    return events_root(root) / bucket / day_value


def ensure_bucket_dir(root: Path, bucket: str, *, day: str | None = None) -> Path:
    path = bucket_dir(root, bucket, day=day)
    path.mkdir(parents=True, exist_ok=True)
    return path


def submit_event(
    root: Path,
    payload: dict[str, Any],
    *,
    bucket: str = "inbox",
    day: str | None = None,
) -> Path:
    """Persist an event to ``<root>/raw/events/<bucket>/<day>/<event_id>.json``.

    Uses an atomic temp + rename so a half-written file never replaces
    a legitimate one. ``payload`` is mutated to ensure ``event_id`` and
    ``timestamp`` are populated.
    """

    if bucket not in VALID_BUCKETS:
        raise ValueError(f"invalid bucket: {bucket}")

    if not payload.get("event_id"):
        payload["event_id"] = str(uuid.uuid4())
    if not payload.get("timestamp"):
        payload["timestamp"] = (
            datetime.now(tz=timezone.utc).astimezone().isoformat(timespec="seconds")
        )

    target_dir = ensure_bucket_dir(root, bucket, day=day)
    target = target_dir / f"{payload['event_id']}.json"
    tmp_dir = Path(tempfile.gettempdir()) / f"lwm-inbox-{os.getpid()}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f".{target.name}.{os.getpid()}.tmp"
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return target


def _wiki_root(src: Path) -> Path:
    """Walk up from ``src`` until we find the directory that contains ``raw/events``."""

    p = src.resolve()
    while True:
        if (p / "raw" / "events").is_dir():
            return p
        if p.parent == p:
            return src.parents[max(0, len(src.parents) - 4)]
        p = p.parent


def move_event(src: Path, *, target_bucket: str, target_day: str | None = None) -> Path:
    """Move an event file from one location to another bucket."""

    if target_bucket not in VALID_BUCKETS:
        raise ValueError(f"invalid bucket: {target_bucket}")
    root = _wiki_root(src)
    target_dir = ensure_bucket_dir(root, target_bucket, day=target_day)
    target = target_dir / src.name
    if target.exists():
        suffix = f".{int(time.time() * 1000)}.replaced"
        target = target_dir / f"{src.stem}{suffix}{src.suffix}"
    shutil.move(str(src), str(target))
    return target


def list_events(root: Path, bucket: str, *, day: str | None = None) -> list[Path]:
    if bucket not in VALID_BUCKETS:
        raise ValueError(f"invalid bucket: {bucket}")
    if day:
        return sorted(p for p in bucket_dir(root, bucket, day=day).glob("*.json") if p.is_file())
    base = events_root(root) / bucket
    if not base.is_dir():
        return []
    out: list[Path] = []
    for day_dir in sorted(base.iterdir()):
        if not day_dir.is_dir() or not _DATE_RE.match(day_dir.name):
            continue
        out.extend(p for p in day_dir.glob("*.json") if p.is_file())
    return sorted(out)


def inbox_status(root: Path) -> InboxStatus:
    counts = {
        bucket: len(list_events(root, bucket)) for bucket in VALID_BUCKETS
    }
    return InboxStatus(
        root=events_root(root),
        inbox=counts["inbox"],
        processed=counts["processed"],
        rejected=counts["rejected"],
        failed=counts["failed"],
    )


__all__ = [
    "InboxStatus",
    "VALID_BUCKETS",
    "bucket_dir",
    "ensure_bucket_dir",
    "events_root",
    "inbox_status",
    "list_events",
    "move_event",
    "submit_event",
]
