from __future__ import annotations

import json
from pathlib import Path

import pytest

from lwm.structured_candidates import (
    build_relationship_candidates,
    build_workflow_candidates,
    generate_candidates,
    load_accepted,
    review_candidate,
    save_candidate,
    seed_analysis_candidates,
)
from lwm.memory_compiler import load_candidate


def _events() -> list[dict]:
    return [
        {
            "event_id": f"e-{index}",
            "event_type": "verification",
            "tool": "codex",
            "project_id": f"p-{index % 2}",
            "task": "run verification",
            "changes": ["patch source"],
            "verification": ["pytest passed"],
            "tags": ["verification-loop"],
        }
        for index in range(3)
    ]


def _write_sources(root: Path, events: list[dict]) -> None:
    base = root / "raw" / "events" / "processed" / "2026-07-31"
    base.mkdir(parents=True, exist_ok=True)
    for event in events:
        (base / f"{event['event_id']}.json").write_text(json.dumps(event), encoding="utf-8")


def test_workflow_candidate_contains_a_reviewable_chain() -> None:
    candidate = build_workflow_candidates(_events())[0]
    assert candidate.trigger
    assert candidate.steps
    assert candidate.verification == ("pytest passed",)
    assert len(candidate.evidence_ids) == 3
    assert candidate.state == "pending_review"


def test_relationship_candidate_requires_multiple_projects() -> None:
    candidate = build_relationship_candidates(_events())[0]
    assert "verification-loop" in candidate.relationship
    assert "p-0" in candidate.context and "p-1" in candidate.context


def test_operational_observations_and_tags_do_not_create_candidates() -> None:
    events = [
        {
            "event_id": f"observation-{index}",
            "event_type": "workflow_observation",
            "tool": "codex",
            "project_id": f"p-{index % 2}",
            "task": "same command",
            "tags": ["repeated-tag"],
        }
        for index in range(4)
    ]

    assert build_workflow_candidates(events) == []
    assert build_relationship_candidates(events) == []


def test_only_accepted_candidates_are_recalled(tmp_path: Path) -> None:
    candidate = build_workflow_candidates(_events())[0]
    save_candidate(tmp_path, candidate)
    _write_sources(tmp_path, _events())
    assert load_accepted(tmp_path) == []
    review_candidate(tmp_path, candidate.candidate_id, decision="accept")
    assert load_accepted(tmp_path)[0]["candidate_id"] == candidate.candidate_id


def test_reaccept_fails_when_any_source_was_forgotten(tmp_path: Path) -> None:
    candidate = build_workflow_candidates(_events())[0]
    path = save_candidate(tmp_path, candidate)
    _write_sources(tmp_path, _events())
    review_candidate(tmp_path, candidate.candidate_id, decision="accept")
    review_candidate(tmp_path, candidate.candidate_id, decision="reject")
    before = path.read_bytes()
    (tmp_path / "raw" / "events" / "processed" / "2026-07-31" / "e-1.json").unlink()

    with pytest.raises(ValueError, match="source events must all exist"):
        review_candidate(tmp_path, candidate.candidate_id, decision="accept")

    assert path.read_bytes() == before
    assert load_accepted(tmp_path) == []


def test_generation_does_not_overwrite_reviewed_candidate(tmp_path: Path) -> None:
    candidate = build_workflow_candidates(_events())[0]
    path = save_candidate(tmp_path, candidate)
    review_candidate(
        tmp_path,
        candidate.candidate_id,
        decision="correct",
        correction="Use the verified release checklist, not the generic task wording.",
    )
    before = path.read_bytes()

    generate_candidates(tmp_path, _events())

    assert path.read_bytes() == before
    payload = path.read_text(encoding="utf-8")
    assert '"state": "corrected"' in payload
    assert "verified release checklist" in payload


def test_generation_reuses_one_shot_evidence_for_both_candidate_kinds(tmp_path: Path) -> None:
    paths = generate_candidates(tmp_path, iter(_events()))

    assert len(paths) == 2
    assert any('"kind": "workflow"' in path.read_text(encoding="utf-8") for path in paths)
    assert any('"kind": "relationship"' in path.read_text(encoding="utf-8") for path in paths)


def test_analysis_seed_bridge_creates_compiler_candidates(tmp_path: Path) -> None:
    paths = seed_analysis_candidates(tmp_path, _events())

    assert len(paths) == 2
    candidates = [load_candidate(tmp_path, path.stem) for path in paths]
    assert {candidate.kind for candidate in candidates if candidate} == {
        "workflow",
        "relationship",
    }
    workflow = next(candidate for candidate in candidates if candidate and candidate.kind == "workflow")
    assert workflow.state == "pending_analysis"
    assert set(workflow.evidence_ids) == {"e-0", "e-1", "e-2"}
    assert set(workflow.scope) == {"p-0", "p-1"}


def test_rejected_review_candidate_is_not_seeded_for_analysis(tmp_path: Path) -> None:
    candidate = build_workflow_candidates(_events())[0]
    save_candidate(tmp_path, candidate)
    review_candidate(tmp_path, candidate.candidate_id, decision="reject")

    paths = seed_analysis_candidates(tmp_path, _events())

    assert all(path.stem != candidate.candidate_id for path in paths)
    assert load_candidate(tmp_path, candidate.candidate_id) is None
