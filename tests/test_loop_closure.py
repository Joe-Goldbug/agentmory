from __future__ import annotations

import json
from pathlib import Path

from lwm.closure import check_closure
from lwm.cycle_state import begin, finish, write_receipt
from lwm.cycle_receipt import CycleReceiptV2, write_cycle_receipt
from lwm.loop_state import begin_loop, close_loop, record_evaluation, write_state


def _runtime_probe(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"
    python = runtime / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    module = runtime / "lib" / "python3.11" / "site-packages" / "lwm" / "__init__.py"
    python.write_text(
        "#!/bin/sh\n"
        f"printf '%s' {json.dumps(json.dumps({'module': str(module)}))}\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    return runtime


def test_closure_blocks_when_loop_is_not_verified(tmp_path: Path) -> None:
    state = close_loop(begin_loop("refresh"), exit_state="human_required", human_gate=True)
    write_state(tmp_path, state)
    report = check_closure(
        tmp_path,
        source_root=tmp_path,
        runtime_root=_runtime_probe(tmp_path),
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
        runtime_root=_runtime_probe(tmp_path),
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
        runtime_root=_runtime_probe(tmp_path),
        health_required=False,
        launchd_required=False,
    )
    assert report.status == "pass"


def test_closure_accepts_successful_v2_cycle_receipt(tmp_path: Path) -> None:
    (tmp_path / "lwm").mkdir()
    (tmp_path / "lwm" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# context\n", encoding="utf-8")
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
        runtime_root=_runtime_probe(tmp_path),
        health_required=False,
        launchd_required=False,
    )

    assert report.status == "pass"
    assert report.checks["receipt"] == "pass"


def test_closure_reports_degraded_checks_separately_from_blockers(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "lwm").mkdir()
    (tmp_path / "lwm" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# context\n", encoding="utf-8")
    write_cycle_receipt(
        CycleReceiptV2(
            schema_version=2,
            cycle_id="cycle-degraded",
            runtime_id="runtime-degraded",
            started_at="2026-08-01T00:00:00+00:00",
            finished_at="2026-08-01T00:01:00+00:00",
            core_status="success",
            overall_status="success",
        ),
        tmp_path,
    )
    state = begin_loop("refresh")
    state = record_evaluation(
        state,
        actual_observation="local evidence exists",
        actual_outcome="fresh",
        evidence=("llms.txt",),
        criteria_met=True,
        next_action="",
    )
    write_state(tmp_path, close_loop(state, exit_state="completed_verified", human_gate=False))
    monkeypatch.setattr("lwm.closure._launchd_check", lambda _label: "degraded")

    report = check_closure(
        tmp_path,
        source_root=tmp_path,
        runtime_root=_runtime_probe(tmp_path),
        health_required=False,
        launchd_required=True,
    )

    assert report.status == "degraded"
    assert report.failed_checks == ()
    assert report.degraded_checks == ("launchd",)
