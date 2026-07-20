from __future__ import annotations

from pathlib import Path

from lwm.loop_state import begin_loop, close_loop, read_last, record_evaluation, write_state


def test_loop_round_trip_records_prediction_evidence_and_verified_completion(tmp_path: Path) -> None:
    state = begin_loop(
        "scheduled memory refresh",
        constraints=("one bounded cycle",),
        success_criteria=("audit passes", "health passes"),
        expected_observation="fresh source and runtime inputs",
        expected_outcome="updated export with a successful audit",
    )
    state = record_evaluation(
        state,
        actual_observation="audit=ok; health=healthy",
        actual_outcome="export updated",
        evidence=("state/last-cycle.json", "state/health.json"),
        criteria_met=True,
        next_action="",
    )
    state = close_loop(state, exit_state="completed_verified", human_gate=False)
    write_state(tmp_path, state)

    loaded = read_last(tmp_path)
    assert loaded is not None
    assert loaded.exit_state == "completed_verified"
    assert loaded.expected_outcome == "updated export with a successful audit"
    assert loaded.evidence == ("state/last-cycle.json", "state/health.json")


def test_loop_evaluation_cannot_close_as_verified_when_criteria_fail() -> None:
    state = begin_loop("refresh", success_criteria=("audit passes",))
    state = record_evaluation(
        state,
        actual_observation="audit=failed",
        actual_outcome="no verified export",
        evidence=("state/last-cycle.json",),
        criteria_met=False,
        next_action="repair audit failure",
    )
    closed = close_loop(state, exit_state="completed_verified", human_gate=False)
    assert closed.exit_state == "continue"
    assert closed.next_action == "repair audit failure"


def test_loop_can_close_as_human_required_or_blocked() -> None:
    state = begin_loop("decide ambiguous scope")
    assert close_loop(state, exit_state="human_required", human_gate=True).human_gate is True
    assert close_loop(state, exit_state="blocked", human_gate=False).exit_state == "blocked"
