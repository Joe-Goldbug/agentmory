"""Time-aware evidence lifecycle regression tests."""

from lwm.evidence import arbitrate_state, build_evidence_item


def test_future_valid_to_stays_current() -> None:
    item = build_evidence_item(
        {"fact_id": "future", "statement": "still valid", "valid_to": "2099-01-01T00:00:00+08:00"}
    )

    assert item.state == "current"
    assert arbitrate_state([item])[0].state == "current"


def test_past_valid_to_is_historical() -> None:
    item = build_evidence_item(
        {"fact_id": "past", "statement": "expired", "valid_to": "2000-01-01T00:00:00Z"}
    )

    assert item.state == "historical"
    assert arbitrate_state([item])[0].state == "historical"
