from lwm.evidence import (
    arbitrate_state,
    build_evidence_item,
    deduplicate_evidence,
)


def test_current_fact_supersedes_historical_fact() -> None:
    old = build_evidence_item(
        {
            "fact_id": "old",
            "fact_key": "scheduler",
            "statement": "old",
            "valid_to": "2026-07-18T00:00:00+08:00",
        }
    )
    new = build_evidence_item(
        {
            "fact_id": "new",
            "fact_key": "scheduler",
            "statement": "new",
            "verification": ["ok"],
            "supersedes": "old",
        }
    )
    ledger = arbitrate_state([old, new])
    assert {item.fact_id: item.state for item in ledger} == {
        "old": "historical",
        "new": "current",
    }


def test_conflicting_current_facts_are_not_silently_selected() -> None:
    left = build_evidence_item(
        {"fact_id": "left", "fact_key": "status", "statement": "A"}
    )
    right = build_evidence_item(
        {"fact_id": "right", "fact_key": "status", "statement": "B"}
    )
    ledger = arbitrate_state([left, right])
    assert {item.state for item in ledger} == {"conflicted"}


def test_duplicate_evidence_is_removed_by_fact_id_and_dedup_key() -> None:
    first = build_evidence_item({"fact_id": "same", "statement": "fact"})
    second = build_evidence_item({"fact_id": "same", "statement": "fact"})
    assert len(deduplicate_evidence([first, second])) == 1


def test_event_details_are_source_backed_in_one_statement() -> None:
    item = build_evidence_item(
        {
            "event_id": "event-1",
            "project_id": "git-a",
            "event_type": "decision",
            "task": "choose recall design",
            "decisions": ["use evidence ledger"],
            "verification": ["design reviewed"],
        }
    )
    assert item.source_event_ids == ("event-1",)
    assert "choose recall design" in item.statement
    assert "use evidence ledger" in item.statement
    assert item.state == "current"
