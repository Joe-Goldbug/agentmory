"""15-minute supervisor with a separately enforced 12-hour full cycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lwm import inbox
from lwm.cycle_state import begin, finish, is_due, write_receipt


FULL_INTERVAL_SECONDS = 43200


def _reason_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in (inbox.events_root(root) / "rejected").rglob("*.json.reason"):
        try:
            reason = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        key = "privacy_blocked" if reason.startswith("privacy:") else "duplicate" if reason.startswith("duplicate:") else "invalid"
        counts[key] = counts.get(key, 0) + 1
    return counts


def run_supervisor(root: Path, *, interval_seconds: int = FULL_INTERVAL_SECONDS, force: bool = False) -> int:
    """Leave a supervisor receipt and run a full cycle only when due."""

    root = root.resolve()
    supervisor = begin("supervisor", "scheduled")
    if not force and not is_due(root, interval_seconds=interval_seconds):
        write_receipt(root, finish(supervisor, status="success", reason="not_due"))
        return 0

    write_receipt(root, finish(supervisor, status="success", reason="full_cycle_due"))
    full = begin("full", "due")
    write_receipt(root, full)
    before = inbox.inbox_status(root)
    before_reasons = _reason_counts(root)
    try:
        from lwm.runner import run_cycle

        code = run_cycle(root)
    except Exception as exc:  # noqa: BLE001
        write_receipt(root, finish(full, status="failed", error=str(exc)))
        return 1
    status = "success" if code == 0 else "failed"
    after = inbox.inbox_status(root)
    after_reasons = _reason_counts(root)
    def delta(key: str) -> int:
        return max(getattr(after, key) - getattr(before, key), 0)
    counts: dict[str, Any] = {
        "processed": delta("processed"),
        "accepted": delta("processed"),
        "duplicate": max(after_reasons.get("duplicate", 0) - before_reasons.get("duplicate", 0), 0),
        "privacy_blocked": max(after_reasons.get("privacy_blocked", 0) - before_reasons.get("privacy_blocked", 0), 0),
        "invalid": max(after_reasons.get("invalid", 0) - before_reasons.get("invalid", 0), 0),
        "failed": delta("failed"),
    }
    write_receipt(root, finish(full, status=status, error=None if code == 0 else f"exit {code}", **counts))
    from lwm.health import collect_and_write

    collect_and_write(root, strict=True)
    return code


__all__ = ["FULL_INTERVAL_SECONDS", "run_supervisor"]
