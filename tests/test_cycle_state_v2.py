from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from lwm.cycle_receipt import CycleReceiptV2, write_cycle_receipt
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


def test_v2_receipt_is_the_due_clock(tmp_path: Path) -> None:
    write_cycle_receipt(
        CycleReceiptV2(
            schema_version=2,
            cycle_id="cycle-v2",
            runtime_id="runtime-v2",
            started_at="2026-08-01T00:00:00+00:00",
            finished_at="2026-08-01T00:01:00+00:00",
            core_status="success",
            overall_status="success",
        ),
        tmp_path,
    )

    assert is_due(
        tmp_path,
        interval_seconds=43200,
        now=datetime.fromisoformat("2026-08-01T06:00:00+00:00").timestamp(),
    ) is False


def test_success_with_warnings_advances_the_due_clock(tmp_path: Path) -> None:
    write_cycle_receipt(
        CycleReceiptV2(
            schema_version=2,
            cycle_id="cycle-warning",
            runtime_id="runtime-v2",
            started_at="2026-08-01T00:00:00+00:00",
            finished_at="2026-08-01T00:01:00+00:00",
            core_status="success_with_warnings",
            overall_status="degraded",
        ),
        tmp_path,
    )

    assert is_due(
        tmp_path,
        interval_seconds=43200,
        now=datetime.fromisoformat("2026-08-01T06:00:00+00:00").timestamp(),
    ) is False


def test_supervisor_records_not_due_without_touching_full_cycle(tmp_path: Path) -> None:
    receipt = finish(begin("full", "due"), status="success")
    write_receipt(tmp_path, receipt)
    assert supervisor.run_supervisor(tmp_path) == 0
    assert read_receipt(tmp_path, "supervisor") is None
    assert read_receipt(tmp_path, "full")["receipt_id"] == receipt.receipt_id
