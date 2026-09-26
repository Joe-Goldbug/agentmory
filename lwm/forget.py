"""Selective forgetting of stored events.

The hub follows the user's preference for **explicit control of memory**:
any time a user wants to remove a stored event, ``lwm forget <event_id>``
deletes the underlying file, the event-index ledger entry, and removes
the matching bullet from its project memory page. The CLI exposes a
``--dry-run`` flag so the operation is reviewable first.
"""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

from lwm import dedup, inbox


@dataclass(frozen=True)
class ForgetResult:
    event_id: str
    deleted_files: tuple[Path, ...]
    index_updated: bool
    page_updated: bool
    page_path: Path | None
    invalidated_pages: tuple[Path, ...] = ()
    invalidated_candidates: tuple[Path, ...] = ()
    requires_review: tuple[Path, ...] = ()


def _load_index(root: Path) -> dict[str, dict]:
    return dedup.load_event_index(root)


def _save_index(root: Path, index: dict[str, dict]) -> None:
    dedup.save_event_index(root, index)


def _find_event_file(root: Path, event_id: str) -> Path | None:
    """Locate the canonical event file under any bucket subdirectory."""

    for bucket in ("inbox", "processed", "rejected", "failed"):
        for day_dir in (root / "raw" / "events" / bucket).iterdir() if (root / "raw" / "events" / bucket).is_dir() else []:
            if not day_dir.is_dir():
                continue
            candidate = day_dir / f"{event_id}.json"
            if candidate.is_file():
                return candidate
    return None


def _remove_bullet_from_project_page(
    path: Path,
    event_id: str,
    *,
    index_info: dict | None = None,
    raw_payload: dict | None = None,
) -> bool:
    """Strip the line that carries this event's contribution to the page.

    Matching strategy (in priority order):
    1. Bullet line whose trailing annotation includes the event_id hash.
    2. Bullet line whose timestamp prefix equals the event's ISO 8601
       timestamp (from ``index_info``) and whose body matches the event's
       task / verification text.
    3. Bullet line whose body contains ``event_id`` (legacy fallback).
    """

    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    iso_seconds = None  # ISO without ms / tz offset for comparison.
    if index_info and index_info.get("timestamp"):
        full = str(index_info["timestamp"])
        # Normalize: split on ms, drop tz offset (e.g. +08:00).
        iso_seconds = full.split(".")[0]
        if "+" in iso_seconds:
            iso_seconds = iso_seconds.split("+")[0]
        if iso_seconds.endswith("Z"):
            iso_seconds = iso_seconds[:-1]
    bullet_text_hint = None
    if raw_payload is not None:
        task = raw_payload.get("task")
        if isinstance(task, str) and task:
            bullet_text_hint = task

    candidate_event_ids = {event_id}
    if len(event_id) >= 8:
        candidate_event_ids.add(event_id[:8])

    kept: list[str] = []
    removed = False
    for line in lines:
        if not line.startswith("- "):
            kept.append(line)
            continue

        parts = line[2:].split(" — ", 1)
        if len(parts) != 2:
            kept.append(line)
            continue
        ts_part, body = parts[0].strip(), parts[1]

        if any(eid in line for eid in candidate_event_ids):
            removed = True
            continue
        # Compare normalised (no tz offset, no fractional second) so that
        # the bullet prefix ``2026-07-11T22:04:45+08:00`` matches the
        # event's stored ``timestamp`` regardless of timezone.
        line_ts_normalised = ts_part.split("+")[0].rstrip("Z")
        if iso_seconds and line_ts_normalised == iso_seconds:
            if bullet_text_hint is None or bullet_text_hint in body:
                removed = True
                continue
        kept.append(line)
    if removed:
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return removed


def _invalidate_derived_candidates(root: Path, event_id: str) -> tuple[Path, ...]:
    """Withdraw candidates whose evidence or counterevidence uses this event."""

    invalidated: list[Path] = []
    for directory in (root / "state" / "candidates", root / "state" / "analysis" / "candidates"):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(payload, dict):
                continue
            if any(
                isinstance(payload.get(key), list) and event_id in payload[key]
                for key in ("evidence_ids", "counterevidence_ids")
            ):
                if payload.get("state") != "rejected" or payload.get("withdrawal_reason") != "source_event_forgotten":
                    payload["state"] = "rejected"
                    payload["withdrawal_reason"] = "source_event_forgotten"
                    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    invalidated.append(path)
    return tuple(invalidated)


def _invalidate_promoted_pages(root: Path, event_id: str) -> tuple[Path, ...]:
    """Withdraw generated global pages backed by the forgotten event."""

    base = root / "wiki" / "global"
    if not base.is_dir():
        return ()
    invalidated: list[Path] = []
    for path in base.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        parts = text.split("---", 2)
        if len(parts) != 3 or not re.search(r"^claim_key:[ \t]*\S+", parts[1], re.MULTILINE):
            continue
        match = re.search(r"^event_ids:[ \t]*\[([^\]]*)\][ \t]*$", parts[1], re.MULTILINE)
        if match is None or event_id not in {value.strip() for value in match.group(1).split(",")}:
            continue
        frontmatter, changed = re.subn(
            r"^status:[ \t]*approved[ \t]*$", "status: source_withdrawn", parts[1], count=1, flags=re.MULTILINE
        )
        if changed:
            path.write_text(f"---{frontmatter}---{parts[2]}", encoding="utf-8")
            invalidated.append(path)
    return tuple(invalidated)


def forget_event(root: Path, event_id: str) -> ForgetResult:
    root = root.resolve()

    deleted: list[Path] = []

    # Remove the file itself under every bucket.
    target = _find_event_file(root, event_id)
    raw_payload = None
    if target is not None:
        try:
            raw_payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        target.unlink()
        deleted.append(target)

    # Drop the index entry.
    index = _load_index(root)
    info = index.pop(event_id, None)
    if index is not None and info is not None:
        _save_index(root, index)

    invalidated_candidates = _invalidate_derived_candidates(root, event_id)
    invalidated_pages = _invalidate_promoted_pages(root, event_id)

    page_updated = False
    page_path: Path | None = None
    requires_review: list[Path] = list(invalidated_pages)
    if info and info.get("project_id"):
        from lwm import project_memory

        page_path = project_memory.project_page_path(root, str(info["project_id"]))
        reconciled = project_memory.reconcile_forgotten_event(
            root, str(info["project_id"]), event_id
        )
        legacy_cleaned = _remove_bullet_from_project_page(
            page_path,
            event_id,
            index_info=info,
            raw_payload=raw_payload,
        )
        page_updated = reconciled or legacy_cleaned
        if page_path.is_file():
            requires_review.append(page_path)
    if requires_review:
        warnings.warn(
            "forgotten source may remain in pages requiring review: "
            + ", ".join(str(path) for path in requires_review),
            stacklevel=2,
        )

    return ForgetResult(
        event_id=event_id,
        deleted_files=tuple(deleted),
        index_updated=info is not None,
        page_updated=page_updated,
        page_path=page_path,
        invalidated_pages=invalidated_pages,
        invalidated_candidates=invalidated_candidates,
        requires_review=tuple(requires_review),
    )


def apply_retention(
    root: Path,
    *,
    bucket: str,
    older_than_days: int,
    now_epoch: float | None = None,
) -> tuple[Path, ...]:
    """Delete event JSON files older than ``older_than_days`` from one bucket.

    Returns the list of files removed. ``now_epoch`` exists so tests can
    pin time without monkeypatching the OS clock. A retention=0 deletes
    every file (kept as a safety hatch but the CLI defaults to a sane
    30 to prevent accidental wipes).
    """

    import time

    if bucket not in inbox.VALID_BUCKETS:
        raise ValueError(f"invalid bucket: {bucket}")
    if older_than_days < 0:
        raise ValueError("older_than_days must be >= 0")
    if bucket == "inbox":
        # Never auto-delete pending events; preserve safety.
        return ()

    base = root / "raw" / "events" / bucket
    if not base.is_dir():
        return ()

    threshold = time.time() - older_than_days * 86400
    if now_epoch is not None:
        threshold = now_epoch - older_than_days * 86400

    removed: list[Path] = []
    for day_dir in sorted(base.iterdir()):
        if not day_dir.is_dir():
            continue
        for path in sorted(day_dir.glob("*.json")):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime < threshold:
                try:
                    path.unlink()
                    removed.append(path)
                except OSError:
                    continue
    return tuple(removed)


__all__ = ["ForgetResult", "apply_retention", "forget_event"]
