from __future__ import annotations

import json
from pathlib import Path

from lwm.capabilities import record, summary
from lwm.health import collect
from lwm.memory_api import reflect_project, retain


def test_capability_requires_read_and_write_receipts(tmp_path: Path) -> None:
    assert summary(tmp_path)["codex"]["bidirectional"] is False
    (tmp_path / "read.json").write_text("read evidence\n", encoding="utf-8")
    (tmp_path / "write.json").write_text("write evidence\n", encoding="utf-8")
    record(tmp_path, tool="codex", direction="read", source="native-hook", evidence_path="read.json", operation_id="read-1")
    assert summary(tmp_path)["codex"]["bidirectional"] is False
    record(tmp_path, tool="codex", direction="write", source="native-hook", evidence_path="write.json", operation_id="write-1")
    assert summary(tmp_path)["codex"]["bidirectional"] is True


def test_health_distinguishes_duplicate_from_privacy(tmp_path: Path) -> None:
    rejected = tmp_path / "raw" / "events" / "rejected" / "2026-07-18"
    rejected.mkdir(parents=True)
    (rejected / "a.json").write_text("{}", encoding="utf-8")
    (rejected / "a.json.reason").write_text("duplicate:dedup_key\n", encoding="utf-8")
    (rejected / "b.json").write_text("{}", encoding="utf-8")
    (rejected / "b.json.reason").write_text("privacy: secret\n", encoding="utf-8")
    snapshot = collect(tmp_path)
    assert snapshot.quality["rejection_breakdown"] == {"duplicate": 1, "privacy_blocked": 1}
    assert snapshot.quality["privacy_rejection_rate"] == 0.5


def test_retain_and_reflect_leave_project_evidence(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = retain(tmp_path, tool="shell", project_path=str(project), task="completed task")
    assert Path(result["path"]).is_file()
    processed = tmp_path / "raw" / "events" / "processed" / "2026-07-18"
    processed.mkdir(parents=True)
    event = result["event"]
    (processed / f"{event['event_id']}.json").write_text(json.dumps(event), encoding="utf-8")
    state = reflect_project(tmp_path, result["project_id"])
    assert state.is_file()
    assert "completed task" in state.read_text(encoding="utf-8")
