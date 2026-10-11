from pathlib import Path

from lwm.dedup import evaluate, record_event


def _event(tool: str, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "tool": tool,
        "project_id": "project-1",
        "session_id": "same-session-name",
        "event_type": "session_summary",
        "task": f"{tool} task",
        "timestamp": "2026-07-13T00:00:00+08:00",
        "verification": [],
    }


def test_session_dedup_is_scoped_to_tool(tmp_path: Path) -> None:
    claude = _event("claude-code", "claude-event")
    opencode = _event("opencode", "opencode-event")
    record_event(tmp_path, claude, bucket="processed", file_path="claude.json")

    assert not evaluate(tmp_path, opencode).duplicate


def test_same_tool_session_is_still_deduplicated(tmp_path: Path) -> None:
    first = _event("opencode", "first")
    second = _event("opencode", "second")
    record_event(tmp_path, first, bucket="processed", file_path="first.json")

    assert evaluate(tmp_path, second).duplicate


def test_distinct_sessions_and_turns_are_not_collapsed(tmp_path: Path) -> None:
    first = _event("opencode", "first")
    record_event(tmp_path, first, bucket="processed", file_path="first.json")
    assert not evaluate(tmp_path, {**first, "event_id": "second", "session_id": "different"}).duplicate
    assert not evaluate(tmp_path, {**first, "event_id": "third", "task_id": "second-turn"}).duplicate


def test_full_result_and_changes_participate_in_identity(tmp_path: Path) -> None:
    first = {**_event("opencode", "first"), "event_type": "verification",
             "verification": ["x" * 100 + "FAIL"]}
    record_event(tmp_path, first, bucket="processed", file_path="first.json")
    assert not evaluate(tmp_path, {**first, "event_id": "second", "verification": ["x" * 100 + "PASS"]}).duplicate
    assert not evaluate(tmp_path, {**first, "event_id": "third", "changes": ["Actual change"]}).duplicate
