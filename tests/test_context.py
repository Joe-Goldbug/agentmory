"""`lwm context` tests (acceptance: markdown + json output, all priority sections)."""

from __future__ import annotations

import json
from pathlib import Path

from lwm import context as lwm_context
from lwm import ingest
from lwm.events import make_event


def _seed_event(root: Path, project_path: Path, **overrides):
    event = make_event(
        tool="claude-code",
        project_path=str(project_path),
        project_id="git-demo",
        event_type="session_summary",
        task="bootstrap",
        verification=["smoke-ok"],
        decisions=["ship-it"],
    )
    event.update(overrides)
    inbox_dir = root / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{event['event_id']}.json").write_text(
        json.dumps(event, ensure_ascii=False), encoding="utf-8"
    )


def test_context_markdown_sections(tmp_path: Path) -> None:
    project_path = tmp_path / "proj"
    project_path.mkdir()
    _seed_event(tmp_path, project_path)
    ingest.run(tmp_path, with_lock=False)

    report = lwm_context.build(
        tmp_path,
        tool="claude-code",
        project_path=str(project_path),
        format="markdown",
        limit=4,
    )
    assert "Global Memory" in report.markdown
    assert "Project Memory" in report.markdown
    assert "Scope: project" in report.markdown
    assert "bootstrap" in report.markdown


def test_context_json_mode(tmp_path: Path) -> None:
    project_path = tmp_path / "proj"
    project_path.mkdir()
    report = lwm_context.build(
        tmp_path,
        tool="codex",
        project_path=str(project_path),
        format="json",
    )
    data = json.loads(report.markdown)
    assert data["tool"] == "codex"
    assert "global_rules" in data
    assert "recent_activity" in data
