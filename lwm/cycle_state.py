"""Durable evidence for supervisor and full-harvest cycles."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class CycleReceipt:
    receipt_id: str
    kind: str
    started_at: str
    finished_at: str | None
    status: str
    reason: str
    processed: int = 0
    accepted: int = 0
    duplicate: int = 0
    privacy_blocked: int = 0
    invalid: int = 0
    failed: int = 0
    error: str | None = None


def state_dir(root: Path) -> Path:
    path = root / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def receipt_path(root: Path, kind: str = "full") -> Path:
    filename = "last-cycle.json" if kind == "full" else f"last-{kind}.json"
    return state_dir(root) / filename


def write_receipt(root: Path, receipt: CycleReceipt) -> Path:
    target = receipt_path(root, receipt.kind)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(receipt), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def read_receipt(root: Path, kind: str = "full") -> dict[str, Any] | None:
    path = receipt_path(root, kind)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def begin(kind: str, reason: str) -> CycleReceipt:
    return CycleReceipt(str(uuid.uuid4()), kind, _now(), None, "running", reason)


def finish(receipt: CycleReceipt, *, status: str, **counts: int | str | None) -> CycleReceipt:
    values = asdict(receipt)
    values.update(counts)
    values["finished_at"] = _now()
    values["status"] = status
    return CycleReceipt(**values)


def is_due(root: Path, interval_seconds: int = 43200, now: float | None = None) -> bool:
    current = time.time() if now is None else now
    # v2 is the authoritative full-cycle clock. Keep the v1 fallback so old
    # installations can finish their migration without losing scheduling.
    from lwm.cycle_receipt import load_last_attempt, load_latest

    latest = load_latest(root)
    attempt = load_last_attempt(root)
    candidates = [
        receipt
        for receipt in (latest, attempt)
        if isinstance(receipt, dict) and receipt.get("schema_version") == 2
    ]
    v2 = max(candidates, key=lambda receipt: str(receipt.get("finished_at") or ""), default=None)
    if v2 and v2.get("schema_version") == 2:
        if v2.get("core_status") not in {"success", "success_with_warnings"}:
            return True
        finished = str(v2.get("finished_at") or "")
        try:
            parsed = datetime.fromisoformat(finished.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return True
        return current - parsed >= interval_seconds

    receipt = read_receipt(root)
    if not receipt or receipt.get("status") != "success":
        return True
    finished = str(receipt.get("finished_at") or "")
    try:
        parsed = datetime.fromisoformat(finished).timestamp()
    except ValueError:
        return True
    return current - parsed >= interval_seconds
