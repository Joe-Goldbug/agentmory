from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lwm.cycle_state import CycleReceipt, begin, finish, is_due, read_receipt, write_receipt
from lwm import supervisor


def test_cycle_receipt_round_trip_and_due_state(tmp_path: Path) -> None:
    receipt = finish(begin("full", "due"), status="success", accepted=3, duplicate=2)
    write_receipt(tmp_path, receipt)

    loaded = read_receipt(tmp_path)
    assert loaded is not None
    assert loaded["status"] == "success"
    assert loaded["accepted"] == 3
    assert is_due(tmp_path, interval_seconds=43200, now=datetime.now(timezone.utc).timestamp()) is False


def test_missing_or_failed_receipt_is_due(tmp_path: Path) -> None:
    assert is_due(tmp_path, interval_seconds=43200) is True
    receipt = finish(begin("full", "due"), status="failed", error="boom")
    write_receipt(tmp_path, receipt)
    assert is_due(tmp_path, interval_seconds=43200) is True


def test_receipt_shape_is_stable() -> None:
    receipt = CycleReceipt("id", "supervisor", "now", None, "running", "not_due")
    assert receipt.kind == "supervisor"


def test_supervisor_records_not_due_without_touching_full_cycle(tmp_path: Path) -> None:
    receipt = finish(begin("full", "due"), status="success")
    write_receipt(tmp_path, receipt)
    assert supervisor.run_supervisor(tmp_path) == 0
    assert read_receipt(tmp_path, "supervisor")["reason"] == "not_due"
    assert read_receipt(tmp_path, "full")["receipt_id"] == receipt.receipt_id
