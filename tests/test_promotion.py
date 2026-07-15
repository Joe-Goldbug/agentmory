"""Tests for promotion rules (acceptance: scratch → not global; ≥2 project → can)."""

from __future__ import annotations

import json
from pathlib import Path

from lwm import insights, promote
from lwm.events import make_event


def _seed_event(*, root: Path, pid: str, task: str, tag: str = "ops", temp: bool = False):
    event = make_event(
        tool="claude-code",
        project_path=str(root / pid),
        project_id=f"git-{pid}",
        event_type="bugfix",
        task=task,
        decisions=[f"fix {pid}"],
        verification=["smoke-ok"],
        tags=[tag],
        importance="scratch" if temp else "project",
    )
    inbox_dir = root / "raw" / "events" / "processed" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{event['event_id']}.json").write_text(
        json.dumps(event, ensure_ascii=False), encoding="utf-8"
    )


def test_scratch_rejected_from_global(tmp_path: Path) -> None:
    _seed_event(root=tmp_path, pid="aa", task="scratch-1", temp=True)
    candidates = insights.collect_candidates(insights.load_processed_events(tmp_path))
    decisions, leftovers = promote.auto_promote_all(
        tmp_path, candidates, insights.load_processed_events(tmp_path)
    )
    assert all(not d.approved for d in decisions)
    # leftover stays in candidate form
    assert leftovers == candidates


def test_two_projects_promote_to_global(tmp_path: Path) -> None:
    _seed_event(root=tmp_path, pid="aa", task="commit-1")
    _seed_event(root=tmp_path, pid="bb", task="commit-2")
    events = insights.load_processed_events(tmp_path)
    candidates = insights.collect_candidates(events)
    decisions, leftovers = promote.auto_promote_all(tmp_path, candidates, events)
    assert any(d.approved for d in decisions)
    global_pages = list((tmp_path / "wiki" / "global").glob("*.md"))
    assert global_pages


def test_temp_token_blocks_promotion(tmp_path: Path) -> None:
    for pid in ("alpha", "beta"):
        event = make_event(
            tool="claude-code",
            project_path=str(tmp_path / pid),
            project_id=f"git-{pid}",
            event_type="bugfix",
            task="tmp fix",
            decisions=["tmp keep around"],
            verification=["smoke-ok"],
            tags=["qa"],
        )
        inbox_dir = tmp_path / "raw" / "events" / "processed" / "2026-07-11"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event, ensure_ascii=False), encoding="utf-8"
        )
    events = insights.load_processed_events(tmp_path)
    candidates = insights.collect_candidates(events)
    decisions, _ = promote.auto_promote_all(tmp_path, candidates, events)
    # "tmp" token appears in body → no global page
    assert all(not d.approved for d in decisions)
    assert not list((tmp_path / "wiki" / "global").glob("*.md"))
