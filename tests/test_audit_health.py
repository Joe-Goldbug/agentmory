"""Tests for the ``lwm audit`` + ``lwm hub health`` happy path.

Scope Lock:
- Solves: project memory pages with multi-line tags blocks get normalised
  to inline YAML by ``normalize_existing_pages``; project pages are no
  longer flagged as orphan; ``state/promotion-state.json`` is rewritten
  on every ``auto_promote_all`` call.
- Does not solve: launchd activation (covered separately).
- Acceptance: 4 tests, audit OK + health healthy + promote state observed.
"""

from __future__ import annotations

import json
from pathlib import Path

from lwm import audit, insights, promote
from lwm.events import make_event
from lwm.health import collect_and_write


def _write_block_tags(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "title: P\n"
        "type: project\n"
        "tags:\n  - project\n  - demo\n"
        "sources:\n  - raw/events/processed\n"
        "updated: 2026-07-11T00:00:00Z\n"
        "project_id: demo\n"
        "---\n\n# P\n\n## Status\n\n(no status yet)\n",
        encoding="utf-8",
    )


def test_normalize_existing_pages_rewrites_block_tags(tmp_path: Path) -> None:
    page = tmp_path / "wiki" / "projects" / "demo.md"
    _write_block_tags(page)

    from lwm.project_memory import normalize_existing_pages

    rewritten = normalize_existing_pages(tmp_path)
    assert rewritten == [page]
    text = page.read_text(encoding="utf-8")
    assert "tags: [project, demo]" in text
    # All section entries preserved.
    assert "## Status" in text


def test_audit_ok_after_normalize(tmp_path: Path) -> None:
    page = tmp_path / "wiki" / "projects" / "demo.md"
    _write_block_tags(page)

    from lwm.project_memory import normalize_existing_pages

    normalize_existing_pages(tmp_path)
    report = audit.run_audit(tmp_path, eval_suite=None, eval_mode="quick")
    assert report.schema_issues == 0


def test_health_is_healthy(tmp_path: Path) -> None:
    """After fixup + seeding the expected ``raw/events/processed`` source,
    the snapshot reports a healthy status."""

    page = tmp_path / "wiki" / "projects" / "demo.md"
    _write_block_tags(page)
    # Provide the source the page claims to live under.
    raw = tmp_path / "raw" / "events" / "processed" / "2026-07-11"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "x.json").write_text("{}", encoding="utf-8")
    from lwm.project_memory import normalize_existing_pages

    normalize_existing_pages(tmp_path)
    snapshot = collect_and_write(tmp_path)
    assert snapshot.status == "healthy"


def test_promotion_state_is_persisted(tmp_path: Path) -> None:
    payload = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="bugfix",
        task="promote me",
        verification=["smoke"],
        tags=["promote-tag"],
    )
    inbox = tmp_path / "raw" / "events" / "processed" / "2026-07-11"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{payload['event_id']}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    # promote auto path needs ≥2 projects. Seed a second one.
    payload_b = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-y",
        event_type="bugfix",
        task="promote me too",
        verification=["smoke"],
        tags=["promote-tag"],
    )
    (inbox / f"{payload_b['event_id']}.json").write_text(
        json.dumps(payload_b, ensure_ascii=False), encoding="utf-8"
    )

    events = insights.load_processed_events(tmp_path)
    candidates = insights.collect_candidates(events)
    decisions, _ = promote.auto_promote_all(tmp_path, candidates, events)
    state = promote.load_promotion_state(tmp_path)
    assert state["approved"] or state["rejected"]
    decisions_logged = state["approved"] + state["rejected"]
    assert len(decisions_logged) == len(decisions)
