"""Ingest pipeline + project memory + insight tests."""

from __future__ import annotations

import json
from pathlib import Path

from lwm import ingest
from lwm.events import make_event


def test_session_summary_creates_project_page(tmp_path: Path) -> None:
    for i in range(2):
        event = make_event(
            tool="claude-code",
            project_path=str(tmp_path),
            project_id=f"git-{i:04d}",
            event_type="session_summary",
            task=f"project-{i}",
        )
        inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8"
        )
    report = ingest.run(tmp_path, with_lock=False)
    assert report.processed_count == 2
    assert report.failed_count == 0
    # Truthful Core: session_summary is operational, never durable, so
    # no project page may appear from a pure session_summary ingest.
    pages = list((tmp_path / "wiki" / "projects").glob("*.md"))
    assert not pages


def test_durable_event_creates_project_page(tmp_path: Path) -> None:
    for i in range(2):
        event = make_event(
            tool="claude-code",
            project_path=str(tmp_path),
            project_id=f"git-{i:04d}",
            event_type="decision",
            task=f"ship project-{i}",
            decisions=[f"admit project {i}"],
            verification=["local review"],
        )
        inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8"
        )
    report = ingest.run(tmp_path, with_lock=False)
    assert report.processed_count == 2
    assert report.failed_count == 0
    pages = list((tmp_path / "wiki" / "projects").glob("*.md"))
    assert pages


def test_duplicate_event_rejected(tmp_path: Path) -> None:
    base = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-1",
        event_type="session_summary",
        task="dup-task",
    )
    inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{base['event_id']}.json").write_text(
        json.dumps(base, ensure_ascii=False), encoding="utf-8"
    )
    first = ingest.run(tmp_path, with_lock=False)
    assert first.processed_count == 1
    duplicate = dict(base)
    duplicate["event_id"] = "second-id"
    (inbox_dir / f"{duplicate['event_id']}.json").write_text(
        json.dumps(duplicate, ensure_ascii=False), encoding="utf-8"
    )
    second = ingest.run(tmp_path, with_lock=False)
    assert second.processed_count == 0
    assert second.rejected_count >= 1


def test_privacy_blocked_event_keeps_out_of_processed(tmp_path: Path) -> None:
    first = make_event(
        tool="shell",
        project_path="/Users/me/secrets/.env",
        project_id="local-x",
        event_type="workflow_observation",
        task="check",
    )
    inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{first['event_id']}.json").write_text(
        json.dumps(first, ensure_ascii=False), encoding="utf-8"
    )
    report = ingest.run(tmp_path, with_lock=False)
    assert report.processed_count == 0
    assert report.rejected_count == 1


def test_invalid_json_routes_to_rejected(tmp_path: Path) -> None:
    inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / "garbage.json").write_text("{not-json", encoding="utf-8")
    report = ingest.run(tmp_path, with_lock=False)
    assert report.processed_count == 0
    assert report.rejected_count == 1


def test_insight_candidate_generated_across_projects(tmp_path: Path) -> None:
    for pid in ("git-a", "git-b"):
        event = make_event(
            tool="claude-code",
            project_path=str(tmp_path),
            project_id=pid,
            event_type="workflow_observation",
            task=f"work in {pid}",
            tags=["deployment"],
            decisions=[f"chose {pid} method"],
            verification=["smoke-ok"],
        )
        inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8"
        )
    report = ingest.run(tmp_path, with_lock=False)
    assert report.processed_count == 2
    assert report.insights_written, "expected insight candidates written"
    promoted = (tmp_path / "wiki" / "global").glob("*.md")
    assert not any(promoted), "operational observations must not auto-promote"


def test_legacy_auto_promote_flag_cannot_write_global_memory(tmp_path: Path) -> None:
    for pid in ("git-a", "git-b"):
        event = make_event(
            tool="claude-code",
            project_path=str(tmp_path),
            project_id=pid,
            event_type="decision",
            task="reuse the reviewed loop",
            decisions=["reuse the reviewed loop"],
            verification=["local review"],
            tags=["deployment"],
        )
        inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8"
        )

    report = ingest.run(tmp_path, with_lock=False, auto_promote=True)

    assert report.promoted == ()
    assert report.insights_written
    assert not (tmp_path / "wiki" / "global").exists()
