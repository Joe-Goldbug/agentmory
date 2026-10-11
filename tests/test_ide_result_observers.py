"""Bounded native caches are evidence, never native callback proof."""
import json
from pathlib import Path

from adapters.hooks import kiro_sessions, vscode_sessions


def work_events(root: Path):
    return [event for path in (root / "raw/events/inbox").glob("*/*.json")
            if "structured-summary" in (event := json.loads(path.read_text())).get("tags", [])]


def test_kiro_results_are_bounded_observed_and_idempotent(tmp_path):
    sessions = tmp_path / "sessions/p"
    sessions.mkdir(parents=True)
    (sessions / "sessions.json").write_text(json.dumps([
        {"sessionId": "s", "workspaceDirectory": str(tmp_path)}]))
    path = sessions / "s.json"
    body = {"workspaceDirectory": str(tmp_path), "history": [
        {"message": {"role": "user", "content": "private user prompt"}},
        {"message": {"role": "assistant", "content": "<think>private reasoning</think>Tests still pending"}}]}
    path.write_text(json.dumps(body))
    seen = set()
    kiro_sessions.observe(tmp_path, sessions.parent, seen, settle_seconds=0)
    kiro_sessions.observe(tmp_path, sessions.parent, seen, settle_seconds=0)
    events = work_events(tmp_path)
    assert len(events) == 1
    text = json.dumps(events)
    assert "Tests still pending" in text
    assert "private user prompt" not in text and "private reasoning" not in text
    assert events[0]["source"]["kind"] == "watcher-observed"
    body["history"] += [{"message": {"role": "user", "content": "new request"}},
                        {"message": {"role": "assistant", "content": "Actual test failed"}}]
    path.write_text(json.dumps(body))
    kiro_sessions.observe(tmp_path, sessions.parent, seen, settle_seconds=0)
    assert len(work_events(tmp_path)) == 2


def test_copilot_completed_turn_records_results_not_reasoning_or_requests(tmp_path):
    events = [
        {"id": "u1", "type": "user.message", "data": {"content": "private request"}},
        {"id": "a1", "type": "assistant.message", "data": {"content": "Checked actual config", "reasoningText": "private thought"}},
        {"id": "t1", "type": "tool.execution_complete", "data": {"success": False, "result": {"content": "FAIL actual test"}}},
        {"id": "e1", "type": "assistant.turn_end", "timestamp": "2026-07-22T15:00:00+00:00", "data": {}},
    ]
    seen = set()
    for _ in range(2):
        vscode_sessions._observe_results(tmp_path, str(tmp_path), "s", events, seen, "file")
    captured = work_events(tmp_path)
    assert len(captured) == 1
    text = json.dumps(captured)
    assert "FAIL actual test" in text and "Checked actual config" in text
    assert "private request" not in text and "private thought" not in text
    assert captured[0]["source"]["kind"] == "watcher-observed"
    assert captured[0]["timestamp"] == "2026-07-22T15:00:00+00:00"
    assert captured[0]["source"]["timestamp_basis"] == "native_cache"
    events += [{"id": "u2", "type": "user.message", "data": {"content": "another request"}},
               {"id": "a2", "type": "assistant.message", "data": {"content": "Second turn result"}},
               {"id": "e2", "type": "assistant.turn_end", "data": {}}]
    vscode_sessions._observe_results(tmp_path, str(tmp_path), "s", events, seen, "file")
    assert len(work_events(tmp_path)) == 2
