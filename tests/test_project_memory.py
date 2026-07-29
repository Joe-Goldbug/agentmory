from __future__ import annotations

from pathlib import Path

from lwm.project_memory import append_event, prune_empty_pages


def test_lifecycle_only_event_does_not_create_project_page(tmp_path: Path) -> None:
    event = {
        "event_id": "session-start",
        "timestamp": "2026-07-28T10:00:00+08:00",
        "tool": "codex",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-demo",
        "event_type": "session_start",
        "importance": "scratch",
        "privacy": "sanitized",
        "tags": ["codex", "lifecycle"],
    }

    append_event(tmp_path, event)

    assert not (tmp_path / "wiki" / "projects" / "git-demo.md").exists()


def test_placeholder_session_summary_does_not_create_project_page(tmp_path: Path) -> None:
    event = {
        "event_id": "session-summary-placeholder",
        "timestamp": "2026-07-28T10:00:00+08:00",
        "tool": "claude-code",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-placeholder",
        "event_type": "session_summary",
        "task": "(no user text)",
        "importance": "project",
        "privacy": "sanitized",
        "tags": ["claude-code", "lifecycle"],
    }

    append_event(tmp_path, event)

    assert not (tmp_path / "wiki" / "projects" / "git-placeholder.md").exists()


def test_lifecycle_observation_does_not_create_project_page(tmp_path: Path) -> None:
    event = {
        "event_id": "session-summary-observed-idle",
        "timestamp": "2026-07-28T10:00:00+08:00",
        "tool": "vscode",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-observed-idle",
        "event_type": "session_summary",
        "task": "VS Code Copilot transcript observed idle",
        "importance": "project",
        "privacy": "sanitized",
        "tags": ["vscode", "lifecycle"],
    }

    append_event(tmp_path, event)

    assert not (tmp_path / "wiki" / "projects" / "git-observed-idle.md").exists()


def test_verified_decision_still_creates_project_page(tmp_path: Path) -> None:
    event = {
        "event_id": "decision-1",
        "timestamp": "2026-07-28T10:00:00+08:00",
        "tool": "codex",
        "project_path": str(tmp_path / "project"),
        "project_id": "git-demo",
        "event_type": "decision",
        "importance": "project",
        "privacy": "sanitized",
        "task": "Choose the stable adapter source",
        "decisions": ["Keep one canonical adapter generator"],
        "verification": ["adapter tests pass"],
    }

    page = append_event(tmp_path, event)

    assert page.is_file()
    assert "Keep one canonical adapter generator" in page.read_text(encoding="utf-8")


def test_prune_empty_lifecycle_page_keeps_durable_page(tmp_path: Path) -> None:
    projects = tmp_path / "wiki" / "projects"
    projects.mkdir(parents=True)
    empty = projects / "git-empty.md"
    empty.write_text(
        """---\ntitle: Project git-empty\ntype: project\n---\n\n# Project git-empty\n\nLast task: (no task recorded)\nLast event: session_start @ 2026-07-28T10:00:00+08:00\n\n## Status\n\n- 2026-07-28T10:00:00+08:00 — session_start\n\n## Decisions\n\n(no decisions yet)\n\n## Bugfixes\n\n(no bugfixes yet)\n\n## Verifications\n\n(no verifications yet)\n\n## Open Questions\n\n(no open_questions yet)\n""",
        encoding="utf-8",
    )
    durable = projects / "git-durable.md"
    durable.write_text(
        empty.read_text(encoding="utf-8").replace(
            "Last task: (no task recorded)", "Last task: keep adapter source"
        ).replace("session_start", "decision"),
        encoding="utf-8",
    )

    removed = prune_empty_pages(tmp_path)

    assert removed == [empty]
    assert not empty.exists()
    assert durable.exists()
