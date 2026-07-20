from __future__ import annotations

from pathlib import Path

from lwm import supervisor
from lwm.cycle_state import begin, finish, read_receipt, write_receipt
from lwm.health import collect
from lwm.loop_state import read_active


def test_not_due_supervisor_preserves_last_full_evidence_and_records_loop(tmp_path: Path) -> None:
    previous = finish(begin("full", "due"), status="success")
    write_receipt(tmp_path, previous)

    assert supervisor.run_supervisor(tmp_path) == 0
    state = read_active(tmp_path)
    assert state is not None
    assert state.exit_state == "continue"
    assert state.next_action == "wait for the next due window"
    assert read_receipt(tmp_path)["receipt_id"] == previous.receipt_id
    assert (tmp_path / "state" / "health.json").is_file()


def test_health_reports_loop_exit_for_an_empty_root(tmp_path: Path) -> None:
    snapshot = collect(tmp_path, strict=True)
    assert snapshot.cycle["loop_exit_state"] in {None, "continue", "human_required", "blocked"}
