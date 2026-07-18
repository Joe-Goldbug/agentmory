from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from lwm.recall import build_recall_packet, plan_question
from lwm.project_id import ProjectIdResolution


FIXED_NOW = datetime.fromisoformat("2026-07-19T12:00:00+08:00")


def _map_project(root: Path, project_path: Path, project_id: str) -> None:
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "project-map.json").write_text(
        json.dumps({str(project_path.resolve()): project_id}), encoding="utf-8"
    )


def _seed_event(
    root: Path,
    project_path: Path,
    *,
    project_id: str,
    event_id: str,
    task: str,
    event_type: str = "decision",
    verification: list[str] | None = None,
    fact_key: str | None = None,
    timestamp: str = "2026-07-18T12:00:00+08:00",
) -> None:
    event = {
        "schema_version": 2,
        "event_id": event_id,
        "timestamp": timestamp,
        "tool": "shell",
        "project_path": str(project_path),
        "project_id": project_id,
        "event_type": event_type,
        "importance": "project",
        "privacy": "sanitized",
        "task": task,
        "decisions": [task] if event_type == "decision" else [],
        "changes": [],
        "verification": verification or [],
        "open_questions": [],
    }
    if fact_key:
        event["fact_key"] = fact_key
    path = root / "raw" / "events" / "processed" / "2026-07-18"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{event_id}.json").write_text(json.dumps(event), encoding="utf-8")


def test_plan_detects_current_timeline_and_verification() -> None:
    plan = plan_question("当前项目上周什么时候完成验证？", now=FIXED_NOW)
    assert plan.dimensions == ("current_state", "timeline", "verification", "project")
    assert plan.time_window == ("2026-07-12", "2026-07-18")


def test_packet_does_not_return_another_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()
    monkeypatch.setattr(
        "lwm.recall.record_project",
        lambda root, path: ProjectIdResolution("git-a", "local", toplevel=str(path)),
    )
    _seed_event(
        tmp_path,
        project_a,
        project_id="git-a",
        event_id="event-a",
        task="B2 decision for project A",
        verification=["design reviewed"],
    )
    _seed_event(
        tmp_path,
        project_b,
        project_id="git-b",
        event_id="event-b",
        task="unrelated project B decision",
    )
    packet = build_recall_packet(
        tmp_path,
        "B2 decision",
        project_path=str(project_a),
        now=FIXED_NOW,
    )
    assert packet.project_id == "git-a"
    assert packet.evidence
    assert all(item.project_id == "git-a" for item in packet.evidence)
    assert all("project B" not in item.statement for item in packet.evidence)


def test_packet_marks_missing_verification_as_partial(tmp_path: Path) -> None:
    project_a = tmp_path / "project-a"
    project_a.mkdir()
    _seed_event(
        tmp_path,
        project_a,
        project_id="git-a",
        event_id="event-a",
        task="planned only",
    )
    packet = build_recall_packet(
        tmp_path,
        "是否完成验证？",
        project_path=str(project_a),
        now=FIXED_NOW,
    )
    assert packet.coverage in {"partial", "insufficient"}
    assert "explicit verification" in packet.missing


def test_packet_surfaces_conflicting_current_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_a = tmp_path / "project-a"
    project_a.mkdir()
    monkeypatch.setattr(
        "lwm.recall.record_project",
        lambda root, path: ProjectIdResolution("git-a", "local", toplevel=str(path)),
    )
    _seed_event(
        tmp_path,
        project_a,
        project_id="git-a",
        event_id="event-left",
        task="scheduler is healthy",
        fact_key="scheduler-status",
    )
    _seed_event(
        tmp_path,
        project_a,
        project_id="git-a",
        event_id="event-right",
        task="scheduler is unhealthy",
        fact_key="scheduler-status",
    )
    packet = build_recall_packet(
        tmp_path,
        "scheduler 状态冲突",
        project_path=str(project_a),
        now=FIXED_NOW,
        mode="deep",
    )
    assert packet.conflicts
    assert packet.coverage == "complete"
