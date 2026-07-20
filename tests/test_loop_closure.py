from __future__ import annotations

from pathlib import Path

from lwm.closure import check_closure
from lwm.cycle_state import begin, finish, write_receipt
from lwm.loop_state import begin_loop, close_loop, record_evaluation, write_state


def test_closure_blocks_when_loop_is_not_verified(tmp_path: Path) -> None:
    state = close_loop(begin_loop("refresh"), exit_state="human_required", human_gate=True)
    write_state(tmp_path, state)
    report = check_closure(
        tmp_path,
        source_root=tmp_path,
        runtime_root=tmp_path,
        health_required=False,
        launchd_required=False,
    )
    assert report.status == "blocked"
    assert "loop" in report.failed_checks


def test_closure_accepts_verified_loop_with_local_evidence(tmp_path: Path) -> None:
    (tmp_path / "lwm").mkdir()
    (tmp_path / "lwm" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# context\n", encoding="utf-8")
    write_receipt(tmp_path, finish(begin("full", "due"), status="success"))
    state = begin_loop("refresh", success_criteria=("evidence exists",))
    state = record_evaluation(
        state,
        actual_observation="local evidence exists",
        actual_outcome="fresh",
        evidence=("llms.txt",),
        criteria_met=True,
        next_action="",
    )
    write_state(tmp_path, close_loop(state, exit_state="completed_verified", human_gate=False))
    report = check_closure(
        tmp_path,
        source_root=tmp_path,
        runtime_root=tmp_path,
        health_required=False,
        launchd_required=False,
    )
    assert report.status == "pass"


def test_closure_accepts_successful_not_due_wait_state(tmp_path: Path) -> None:
    (tmp_path / "lwm").mkdir()
    (tmp_path / "lwm" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# context\n", encoding="utf-8")
    write_receipt(tmp_path, finish(begin("full", "due"), status="success"))
    state = begin_loop("refresh")
    state = record_evaluation(
        state,
        actual_observation="full cycle not due",
        actual_outcome="previous full-cycle evidence remains current",
        evidence=("state/last-cycle.json",),
        criteria_met=True,
        next_action="wait for the next due window",
    )
    write_state(tmp_path, close_loop(state, exit_state="continue", human_gate=False))
    report = check_closure(
        tmp_path,
        source_root=tmp_path,
        runtime_root=tmp_path,
        health_required=False,
        launchd_required=False,
    )
    assert report.status == "pass"
