"""Tests for the decision supersede state engine."""

from __future__ import annotations

from pathlib import Path
from lwm.project_memory import (
    ProjectMemoryEntry,
    _filter_active_decisions,
    append_event,
    render_project_page,
)


def test_filter_active_decisions_by_explicit_event_id() -> None:
    d1 = ProjectMemoryEntry(
        section="decisions",
        text="Use HTTP Basic Auth for agent endpoints",
        timestamp="2026-07-28T10:00:00Z",
        event_id="dec-1",
        tool="codex",
    )
    d2 = ProjectMemoryEntry(
        section="decisions",
        text="Switch to Ed25519 signature authentication",
        timestamp="2026-07-28T11:00:00Z",
        event_id="dec-2",
        tool="claude-code",
        supersedes="dec-1",
    )

    active = _filter_active_decisions([d1, d2])
    assert len(active) == 1
    assert active[0].event_id == "dec-2"
    assert active[0].text == "Switch to Ed25519 signature authentication"


def test_filter_active_decisions_by_tag_in_text() -> None:
    d1 = ProjectMemoryEntry(
        section="decisions",
        text="Store temporary state in redis",
        timestamp="2026-07-28T10:00:00Z",
        event_id="dec-1",
        tool="codex",
    )
    d2 = ProjectMemoryEntry(
        section="decisions",
        text="Migrate to local SQLite [supersedes: Store temporary state in redis]",
        timestamp="2026-07-28T11:00:00Z",
        event_id="dec-2",
        tool="claude-code",
    )
    d_unrelated = ProjectMemoryEntry(
        section="decisions",
        text="Always validate JSON schemas strictly",
        timestamp="2026-07-28T10:30:00Z",
        event_id="dec-3",
        tool="codex",
    )

    active = _filter_active_decisions([d1, d_unrelated, d2])
    active_ids = [e.event_id for e in active]
    assert "dec-1" not in active_ids
    assert "dec-2" in active_ids
    assert "dec-3" in active_ids


def test_decision_chain_supersedes_leaves_only_latest() -> None:
    d1 = ProjectMemoryEntry(
        section="decisions",
        text="V1 Architecture",
        timestamp="2026-07-28T09:00:00Z",
        event_id="v1",
    )
    d2 = ProjectMemoryEntry(
        section="decisions",
        text="V2 Architecture [supersedes: V1 Architecture]",
        timestamp="2026-07-28T10:00:00Z",
        event_id="v2",
    )
    d3 = ProjectMemoryEntry(
        section="decisions",
        text="V3 Architecture [replaces: V2 Architecture]",
        timestamp="2026-07-28T11:00:00Z",
        event_id="v3",
    )

    active = _filter_active_decisions([d1, d2, d3])
    assert len(active) == 1
    assert active[0].event_id == "v3"


def test_append_event_supersedes_omits_obsolete_decision_from_rendered_page(
    tmp_path: Path,
) -> None:
    event1 = {
        "event_id": "event-decision-old",
        "timestamp": "2026-07-28T10:00:00+08:00",
        "tool": "codex",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-supersede-demo",
        "event_type": "decision",
        "importance": "project",
        "privacy": "sanitized",
        "task": "Initial auth choice",
        "decisions": ["Use basic token string in header"],
        "verification": ["unit tests pass"],
    }
    append_event(tmp_path, event1)

    page1 = (tmp_path / "wiki" / "projects" / "git-supersede-demo.md").read_text(
        encoding="utf-8"
    )
    assert "Use basic token string in header" in page1

    event2 = {
        "event_id": "event-decision-new",
        "timestamp": "2026-07-28T12:00:00+08:00",
        "tool": "claude-code",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-supersede-demo",
        "event_type": "decision",
        "importance": "project",
        "privacy": "sanitized",
        "task": "Upgrade auth to wallet signature",
        "decisions": ["Upgrade auth to wallet signature"],
        "supersedes": "event-decision-old",
        "verification": ["crypto tests pass"],
    }
    append_event(tmp_path, event2)

    page2 = (tmp_path / "wiki" / "projects" / "git-supersede-demo.md").read_text(
        encoding="utf-8"
    )
    assert "Upgrade auth to wallet signature" in page2
    assert "Use basic token string in header" not in page2
