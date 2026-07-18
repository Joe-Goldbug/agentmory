from __future__ import annotations

import json
from pathlib import Path

from lwm import memory_api
from lwm.project_id import record_project


def test_recall_returns_project_scoped_evidence_packet(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    project_id = record_project(tmp_path, project).project_id
    event_path = tmp_path / "raw" / "events" / "processed" / "2026-07-18"
    event_path.mkdir(parents=True)
    event = {
        "event_id": "event-1",
        "timestamp": "2026-07-18T12:00:00+08:00",
        "tool": "codex",
        "project_path": str(project),
        "project_id": project_id,
        "event_type": "decision",
        "importance": "project",
        "privacy": "sanitized",
        "task": "use B2 evidence recall",
        "decisions": ["use B2 evidence recall"],
        "verification": ["spec reviewed"],
    }
    (event_path / "event-1.json").write_text(json.dumps(event), encoding="utf-8")

    result = memory_api.recall(
        tmp_path,
        "为什么选择 B2 evidence recall？",
        project_path=str(project),
    )

    assert result["project_id"] == project_id
    assert result["scope"] == "project"
    assert result["packet"]["evidence"]
    assert result["hits"][0]["fact_id"] == "event-1"


def test_recall_without_project_is_explicitly_global_only(tmp_path: Path) -> None:
    result = memory_api.recall(tmp_path, "全局工作规则")
    assert result["scope"] == "global-only"
    assert any("global-only" in note.lower() or "could not" in note.lower() for note in result["notes"])
