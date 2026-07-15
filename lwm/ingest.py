"""Orchestrator: read inbox, sanitize, dedupe, project-route, persist.

Exposed via ``lwm ingest``. Designed to be safe under repeated
invocations (LaunchAgent + IDE hook triggered ingest):

* Each event is processed independently; one failure does not abort.
* Outcomes are summed into an :class:`IngestReport`.
* Idempotent: re-running on a fully drained inbox is a no-op.

The pipeline:

1. Acquire the ingest lock.
2. Walk every ``raw/events/inbox/<date>/*.json``.
3. For each event:

   a. Validate schema.
   b. Run :func:`lwm.privacy.sanitize_event`.
   c. Resolve ``project_id`` if missing.
   d. Compute :func:`lwm.dedup.dedup_key` and reject duplicates.
   e. Apply event to :mod:`lwm.project_memory` (project page).
   f. Move the file to ``processed/`` / ``rejected/`` / ``failed/``.

4. After all events: re-scan ``processed/`` for cross-project insight
   candidates and (optionally) auto-promote to global.
5. Run conflict detection.
6. Persist ``state/event-index.json`` updates.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lwm import conflict, dedup, inbox, insights, lockfile, privacy, project_id, project_memory
from lwm.events import validate_event
from lwm.inbox import _wiki_root as _event_wiki_root

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestReport:
    root: Path
    processed: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]  # (event_id, reason)
    failed: tuple[tuple[str, str], ...]  # (event_id, reason)
    insights_written: tuple[Path, ...]
    conflicts_written: tuple[Path, ...]
    promoted: tuple[str, ...]
    skipped: int

    @property
    def ok(self) -> bool:
        return not self.failed

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def processed_count(self) -> int:
        return len(self.processed)

    def render(self) -> str:
        lines = [
            f"ingest ok={self.ok}",
            f"processed={self.processed_count} rejected={self.rejected_count} failed={self.failed_count}",
        ]
        if self.insights_written:
            lines.append(
                f"insights: {', '.join(str(p.relative_to(self.root)) for p in self.insights_written)}"
            )
        if self.conflicts_written:
            lines.append(
                f"conflicts: {', '.join(str(p.relative_to(self.root)) for p in self.conflicts_written)}"
            )
        if self.promoted:
            lines.append(f"promoted: {', '.join(self.promoted)}")
        return "\n".join(lines)


def _move_to(src: Path, *, bucket: str) -> Path:
    target = inbox.move_event(src, target_bucket=bucket)
    return target


def _safe_load(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("ingest: cannot read %s: %s", path, exc)
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _save_event_copy(target_dir: Path, event_id: str, payload: dict[str, Any]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{event_id}.json"
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out


def _reject(src: Path, *, reason: str) -> Path:
    payload = _safe_load(src) or {}
    event_id = str(payload.get("event_id") or src.stem)
    out = _save_event_copy(_event_wiki_root(src) / "raw" / "events" / "rejected" / src.parent.name, event_id, payload)
    try:
        src.unlink()
    except FileNotFoundError:
        pass
    target_meta = out.with_suffix(out.suffix + ".reason")
    target_meta.write_text(reason + "\n", encoding="utf-8")
    return out


def _process_one(root: Path, src: Path) -> tuple[str, str | None, dict[str, Any] | None]:
    payload = _safe_load(src)
    if payload is None:
        _reject(src, reason="invalid-json")
        return src.stem, "invalid-json", None

    validation = validate_event(payload)
    if not validation.ok:
        msg = "; ".join(i.render() for i in validation.issues)
        _reject(src, reason=msg)
        return src.stem, msg, None

    sanitized, issues, blocked = privacy.sanitize_event(payload)
    if blocked:
        _reject(src, reason=f"privacy: {' | '.join(i.reason for i in issues)}")
        return src.stem, "privacy", sanitized

    project_id.ensure_project_id(root, sanitized)

    decision = dedup.evaluate(root, sanitized)
    if decision.duplicate:
        _reject(
            src,
            reason=f"duplicate:{decision.reason or 'dedup_key'} (existing={decision.existing_event_id})",
        )
        return src.stem, "duplicate", sanitized

    project_memory.append_event(root, sanitized)

    return src.stem, None, sanitized


def _finalize_event_file(
    src: Path,
    sanitized: dict[str, Any],
    *,
    bucket: str,
) -> Path | None:
    event_id = str(sanitized["event_id"])
    target_dir = _event_wiki_root(src) / "raw" / "events" / bucket / src.parent.name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{event_id}.json"
    target.write_text(
        json.dumps(sanitized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        src.unlink()
    except FileNotFoundError:
        pass
    return target


def run(
    root: Path,
    *,
    with_lock: bool = True,
    auto_promote: bool = True,
) -> IngestReport:
    """Process every event currently in the inbox."""

    root = root.resolve()
    if with_lock:
        try:
            with lockfile.ingest_lock(root):
                return _run_unlocked(root, auto_promote=auto_promote)
        except lockfile.LockBusyError as exc:
            logger.warning("ingest skipped: %s", exc)
            return IngestReport(
                root=root,
                processed=(),
                rejected=(),
                failed=(),
                insights_written=(),
                conflicts_written=(),
                promoted=(),
                skipped=1,
            )
    return _run_unlocked(root, auto_promote=auto_promote)


def _run_unlocked(root: Path, *, auto_promote: bool) -> IngestReport:
    inbox_dir = inbox.events_root(root) / "inbox"
    processed: list[str] = []
    rejected: list[tuple[str, str]] = []
    failed: list[tuple[str, str]] = []
    if inbox_dir.is_dir():
        for day_dir in sorted(inbox_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            for src in sorted(day_dir.glob("*.json")):
                try:
                    _handle_one(root, src, processed, rejected, failed)
                except Exception as exc:  # never abort the loop
                    logger.exception("ingest: unexpected failure for %s", src)
                    failed.append((src.stem, f"exception: {exc}"))

    insights_written: list[Path] = []
    conflicts_written: list[Path] = []
    promoted: list[str] = []
    try:
        candidates = insights.collect_candidates(insights.load_processed_events(root))
        if candidates:
            insights_written.extend(insights.write_candidates(root, candidates))
        if auto_promote:
            from lwm import promote as promote_mod

            events_all = insights.load_processed_events(root)
            decisions, leftovers = promote_mod.auto_promote_all(
                root, candidates, events_all
            )
            for decision in decisions:
                if decision.approved and decision.target_path is not None:
                    promoted.append(str(decision.target_path))
            if leftovers:
                rejected_paths = insights.write_candidates(root, leftovers)
                insights_written.extend(rejected_paths)
        events_all = insights.load_processed_events(root)
        detected = conflict.detect_conflicts(events_all)
        if detected:
            path = conflict.write_conflict_page(root, detected)
            if path is not None:
                conflicts_written.append(path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("post-processing failed: %s", exc)

    return IngestReport(
        root=root,
        processed=tuple(processed),
        rejected=tuple(rejected),
        failed=tuple(failed),
        insights_written=tuple(insights_written),
        conflicts_written=tuple(conflicts_written),
        promoted=tuple(promoted),
        skipped=0,
    )


def _handle_one(
    root: Path,
    src: Path,
    processed: list[str],
    rejected: list[tuple[str, str]],
    failed: list[tuple[str, str]],
) -> None:
    event_id, error, sanitized = _process_one(root, src)
    if error is not None:
        rejected.append((event_id, error))
        return
    if sanitized is None:
        rejected.append((event_id, "rejected"))
        return
    try:
        new_path = _finalize_event_file(src, sanitized, bucket="processed")
    except Exception as exc:  # noqa: BLE001
        logger.exception("move failed for %s: %s", src, exc)
        failed_dir = src.parents[2] / "failed" / src.parent.name
        failed_path = _save_event_copy(failed_dir, event_id, sanitized)
        try:
            src.unlink()
        except FileNotFoundError:
            pass
        failed.append((event_id, f"write_failed:{exc} -> {failed_path}"))
        return

    dedup.record_event(
        root,
        sanitized,
        bucket="processed",
        file_path=str(new_path),
    )
    processed.append(event_id)


__all__ = ["IngestReport", "run"]
