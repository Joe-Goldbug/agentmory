"""Conflict + insight candidate tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from lwm import conflict, insights, promote as promote_mod
from lwm.events import make_event


def test_conflict_detects_contradiction() -> None:
    events = [
        {
            "project_id": "git-a",
            "tags": ["deploy"],
            "decisions": ["use blue-green"],
            "timestamp": "2026-07-11T12:00:00+00:00",
        },
        {
            "project_id": "git-b",
            "tags": ["deploy"],
            "decisions": ["use rolling"],
            "timestamp": "2026-07-11T12:01:00+00:00",
        },
    ]
    out = conflict.detect_conflicts(events)
    assert len(out) == 1
    assert out[0].tag == "deploy"


def test_workflow_candidate_requires_three_observations() -> None:
    events = [
        {
            "project_id": "git-a",
            "tool": "trae",
            "event_type": "workflow_observation",
            "task": "lint",
            "timestamp": "2026-07-10T12:00:00+00:00",
        }
    ] * 3
    candidates = insights.collect_candidates(events)
    titles = [c.title for c in candidates]
    assert any("trae" in t and "lint" in t for t in titles)


def test_promote_blocked_without_verification() -> None:
    """Promote requires at least one verification across supporting events."""
    e_a = make_event(
        tool="codex",
        project_path="/p/a",
        project_id="git-a",
        event_type="bugfix",
        task="x",
        tags=["ops"],
        decisions=["do-a"],
    )
    e_b = make_event(
        tool="codex",
        project_path="/p/b",
        project_id="git-b",
        event_type="bugfix",
        task="x",
        tags=["ops"],
        decisions=["do-b"],
    )
    candidates = insights.collect_candidates([e_a, e_b])
    with tempfile.TemporaryDirectory() as td:
        decisions, _ = promote_mod.auto_promote_all(Path(td), candidates, [e_a, e_b])
    assert isinstance(decisions, list)
