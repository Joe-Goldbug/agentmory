"""Stable-claim-key promotion tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 6. Workflow and relationship consolidation
"""

from __future__ import annotations

import json
from pathlib import Path

from lwm.stable_promotion import (
    BLOCKED_PROMOTION_TAGS,
    evaluate_promotion,
    normalize_claim,
    persist_promotion,
    render_global_page,
    stable_claim_key,
)


def _event(project_id: str, *, decisions: list[str] | None = None,
           verifications: list[str] | None = None,
           tags: list[str] | None = None,
           event_id: str = "e1") -> dict:
    return {
        "project_id": project_id,
        "event_type": "decision",
        "task": "Reuse the same daily memory refresh loop",
        "decisions": decisions or ["Reuse the same daily memory refresh loop"],
        "verification": verifications or [],
        "tags": tags or ["stable-claim"],
        "event_id": event_id,
    }


def test_normalize_claim_lowercases_and_collapses() -> None:
    assert normalize_claim("  Hello   World!  ") == "hello world"


def test_stable_claim_key_is_hash_based() -> None:
    a = stable_claim_key("Reuse the same loop")
    b = stable_claim_key("Reuse the SAME loop.")
    c = stable_claim_key("Different claim")
    assert a == b
    assert a != c


def test_blocked_tags_excluded_from_supporting_events() -> None:
    events = [
        _event("p1", tags=["lifecycle"]),
        _event("p1", tags=["session"]),
        _event("p1", tags=["adapter"]),
        _event("p1", tags=["workflow_observation"]),
        _event("p1", tags=["shell"]),
        _event("p1"),
    ]
    candidate = evaluate_promotion(
        Path("/tmp/lwm-promote-test"),
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    # Only the last event (no blocked tag) supports the claim; the rest are
    # blocked by their lifecycle/session/adapter/shell/workflow_observation
    # tags.
    assert len(candidate.event_ids) == 1
    # And it's still just one project, so promotion is gated.
    assert not candidate.promoted
    assert "insufficient_projects:1" in candidate.reasons


def test_promotion_requires_two_distinct_projects(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v"], event_id="e1"),
        _event("p1", verifications=["v"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    assert not candidate.promoted
    assert "insufficient_projects:1" in candidate.reasons


def test_promotion_requires_two_verified_projects(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v"], event_id="e1"),
        _event("p2", event_id="e2"),  # no verification
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    assert not candidate.promoted
    assert "insufficient_verified_projects:1" in candidate.reasons


def test_promotion_succeeds_with_two_verified_projects(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v1"], event_id="e1"),
        _event("p2", verifications=["v2"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    assert candidate.promoted
    assert candidate.target_path is not None
    assert candidate.claim_key.startswith("claim-")
    persisted = persist_promotion(candidate)
    assert persisted == candidate.target_path
    text = persisted.read_text(encoding="utf-8")
    assert "type: principle" in text
    assert "claim_key: " in text
    assert "p1" in text and "p2" in text
    audit = tmp_path / "wiki" / "promotion-audit.jsonl"
    assert audit.is_file()
    line = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert line["action"] == "promoted"
    assert line["event_ids"] == ["e1", "e2"]
    assert line["rollback"]["backup_path"] is None


def test_project_count_changes_update_same_page(tmp_path: Path) -> None:
    first = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=[_event("p1", verifications=["v"], event_id="e1")],
    )
    second = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=[
            _event("p1", verifications=["v"], event_id="e1"),
            _event("p2", verifications=["v"], event_id="e2"),
            _event("p3", verifications=["v"], event_id="e3"),
            _event("p4", verifications=["v"], event_id="e4"),
        ],
    )
    assert first.claim_key == second.claim_key
    assert first.target_path == second.target_path
    assert second.promoted


def test_39_40_41_recurring_pages_are_replaced() -> None:
    claim = "Reuse the same daily memory refresh loop"
    keys = {stable_claim_key(claim) for _ in range(3)}
    assert len(keys) == 1


def test_forbidden_pattern_blocks_promotion(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v"], event_id="e1"),
        _event("p2", verifications=["v"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path, claim="This causes latency in ingest", events=events
    )
    assert not candidate.promoted
    assert any("forbidden_pattern" in r for r in candidate.reasons)


def test_secret_in_claim_blocks_promotion(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v"], event_id="e1"),
        _event("p2", verifications=["v"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path, claim="rotate sk-" + "A" * 32, events=events
    )
    assert not candidate.promoted
    assert "secret_in_claim" in candidate.reasons


def test_audit_record_carries_actor_and_claim_key(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v"], event_id="e1"),
        _event("p2", verifications=["v"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    persist_promotion(candidate, actor="automated-supervisor")
    audit = tmp_path / "wiki" / "promotion-audit.jsonl"
    line = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
    assert line["actor"] == "automated-supervisor"
    assert line["claim_key"].startswith("claim-")


def test_blocked_promotion_tags_constant_matches_spec() -> None:
    # Spec §3.4 BLOCKED_PROMOTION_TAGS = {lifecycle, session, adapter,
    # workflow_observation, shell}
    assert BLOCKED_PROMOTION_TAGS == {
        "lifecycle",
        "session",
        "adapter",
        "workflow_observation",
        "shell",
    }


def test_render_global_page_contains_provenance(tmp_path: Path) -> None:
    text = render_global_page(
        claim="Reuse the same daily memory refresh loop",
        claim_key="claim-reuse-the-same-daily-mem-abc123def456",
        project_ids=("p1", "p2"),
        event_ids=("e1", "e2"),
        evidence_paths=("raw/events/processed/2026-07-31/e1.json",),
        actor="human",
    )
    for marker in (
        "type: principle",
        "status: approved",
        "claim_key: claim-reuse-the-same-daily-mem-abc123def456",
        "actor: human",
        "raw/events/processed/2026-07-31/e1.json",
    ):
        assert marker in text, marker


def test_explicit_evidence_ids_allow_a_validated_paraphrase(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v1"], event_id="e1"),
        _event("p2", verifications=["v2"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="The daily refresh loop is reused across projects",
        events=events,
        evidence_ids=("e1", "e2"),
    )

    assert candidate.promoted
    persisted = persist_promotion(candidate, page_type="pattern")
    assert persisted is not None
    assert "type: pattern" in persisted.read_text(encoding="utf-8")


def test_replacing_a_global_page_creates_a_rollback_backup(tmp_path: Path) -> None:
    events = [
        _event("p1", verifications=["v1"], event_id="e1"),
        _event("p2", verifications=["v2"], event_id="e2"),
    ]
    candidate = evaluate_promotion(
        tmp_path,
        claim="Reuse the same daily memory refresh loop",
        events=events,
    )
    persist_promotion(candidate)
    persist_promotion(candidate)

    backups = list((tmp_path / "wiki" / "global" / ".promotion-backups").glob("*.md"))
    assert backups
