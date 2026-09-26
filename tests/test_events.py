"""Test the central hub event schema + validation."""

from __future__ import annotations



from lwm.events import (
    ALLOWED_EVENT_TYPES,
    EVENT_SCHEMA_VERSION,
    make_event,
    truncate_event_text,
    validate_event,
)


def _minimal_event(**overrides):
    payload = make_event(
        tool="claude-code",
        project_path="/tmp/proj",
        project_id="git-abc",
        event_type="session_summary",
        task="test",
    )
    payload.update(overrides)
    return payload


def test_make_event_minimal() -> None:
    event = _minimal_event()
    assert event["tool"] == "claude-code"
    assert event["event_type"] == "session_summary"
    assert event["schema_version"] == EVENT_SCHEMA_VERSION
    assert "event_id" in event and len(event["event_id"]) >= 32
    assert "timestamp" in event


def test_v2_event_carries_task_and_handoff_links() -> None:
    event = make_event(
        tool="codex",
        project_path="/tmp/proj",
        project_id="git-abc",
        event_type="session_summary",
        task_id="task-1",
        handoff_id="handoff-1",
        operation_id="write-1",
        source_receipt_id="receipt-1",
        risks=["needs review"],
    )

    report = validate_event(event)
    assert report.ok
    assert event["risks"] == ["needs review"]
    assert event["task_id"] == "task-1"
    assert event["handoff_id"] == "handoff-1"


def test_v2_event_rejects_invalid_identity_fields() -> None:
    event = _minimal_event(schema_version=3, task_id=123)
    report = validate_event(event)

    assert not report.ok
    paths = {issue.path for issue in report.issues}
    assert "$.schema_version" in paths
    assert "$.task_id" in paths


def test_validate_event_missing_required_keys() -> None:
    report = validate_event({"tool": "x"})
    assert not report.ok
    paths = {issue.path for issue in report.issues}
    assert "$.event_id" in paths
    assert "$.project_path" in paths


def test_validate_event_unknown_event_type() -> None:
    event = _minimal_event()
    event["event_type"] = "definitely-not-real"
    report = validate_event(event)
    assert not report.ok
    assert any("event_type" in issue.path for issue in report.issues)


def test_validate_event_unknown_importance() -> None:
    event = _minimal_event()
    event["importance"] = "scratch-ish"
    report = validate_event(event)
    assert not report.ok


def test_validate_event_timestamp_format() -> None:
    event = _minimal_event()
    event["timestamp"] = "yesterday"
    report = validate_event(event)
    assert not report.ok


def test_validate_event_confidence_range() -> None:
    event = _minimal_event(confidence=2.0)
    report = validate_event(event)
    assert not report.ok


def test_validate_event_optional_lists_must_be_string_list() -> None:
    event = _minimal_event()
    event["decisions"] = [1, 2, 3]
    report = validate_event(event)
    assert not report.ok


def test_known_event_types_present() -> None:
    expected = {
        "session_start",
        "session_summary",
        "decision",
        "bugfix",
        "verification",
        "project_status",
        "workflow_observation",
        "insight_candidate",
    }
    assert expected <= ALLOWED_EVENT_TYPES


def test_truncate_event_text_handles_unicode() -> None:
    short, truncated = truncate_event_text("hi", limit_bytes=16)
    assert short == "hi"
    assert truncated is False
    long_text = "😀" * 10_000
    out, truncated = truncate_event_text(long_text)
    assert truncated is True
    assert isinstance(out, str)


def test_validate_event_top_level_must_be_dict() -> None:
    report = validate_event([1, 2, 3])
    assert not report.ok
    report = validate_event("string-not-dict")
    assert not report.ok


def test_make_event_confidence_is_float() -> None:
    event = make_event(
        tool="x",
        project_path="/p",
        project_id="git-x",
        event_type="verification",
        confidence=0,
    )
    assert event["confidence"] == 0.0
    assert isinstance(event["confidence"], float)
