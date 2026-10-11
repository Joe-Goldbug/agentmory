from __future__ import annotations

import json
from pathlib import Path

import pytest

from lwm.project_memory import (
    append_event,
    prune_empty_pages,
    rebuild_project_pages,
    reconcile_forgotten_event,
)


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
        empty.read_text(encoding="utf-8")
        .replace("Last task: (no task recorded)", "Last task: keep adapter source")
        .replace("session_start", "decision"),
        encoding="utf-8",
    )

    removed = prune_empty_pages(tmp_path)

    assert removed == [empty]
    assert not empty.exists()
    assert durable.exists()


def test_reconcile_forgotten_source_preserves_human_notes(tmp_path: Path) -> None:
    base = tmp_path / "raw" / "events" / "processed" / "2026-07-31"
    base.mkdir(parents=True)
    for event_id, task, timestamp in (
        ("keep", "keep this decision", "2026-07-30T10:00:00+00:00"),
        ("forget", "forget this decision", "2026-07-31T10:00:00+00:00"),
    ):
        (base / f"{event_id}.json").write_text(
            json.dumps(
                {
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "tool": "codex",
                    "project_id": "git-demo",
                    "event_type": "decision",
                    "task": task,
                    "decisions": [task],
                }
            ),
            encoding="utf-8",
        )
    rebuild_project_pages(tmp_path)
    page = tmp_path / "wiki" / "projects" / "git-demo.md"
    page.write_text(
        page.read_text(encoding="utf-8") + "\n## Human Notes\n\nKeep my manual note.\n",
        encoding="utf-8",
    )
    (base / "forget.json").unlink()

    assert reconcile_forgotten_event(tmp_path, "git-demo", "forget")

    text = page.read_text(encoding="utf-8")
    assert "forget this decision" not in text
    assert "Last task: keep this decision" in text
    assert "keep this decision" in text
    assert "## Human Notes\n\nKeep my manual note.\n" in text


def test_reconcile_last_source_keeps_page_without_stale_summary(tmp_path: Path) -> None:
    event = {
        "event_id": "forget",
        "timestamp": "2026-07-31T10:00:00+00:00",
        "tool": "codex",
        "project_id": "git-demo",
        "event_type": "decision",
        "task": "forget this decision",
        "decisions": ["forget this decision"],
    }
    base = tmp_path / "raw" / "events" / "processed" / "2026-07-31"
    base.mkdir(parents=True)
    source = base / "forget.json"
    source.write_text(json.dumps(event), encoding="utf-8")
    rebuild_project_pages(tmp_path)
    source.unlink()

    assert reconcile_forgotten_event(tmp_path, "git-demo", "forget")

    page = tmp_path / "wiki" / "projects" / "git-demo.md"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "forget this decision" not in text
    assert "Last task: (no task recorded)" in text
    assert "Last event: n/a @ n/a" in text


def _repair_event(**overrides):
    return {
        "event_id": "photodos-validation",
        "timestamp": "2026-09-27T01:19:03+08:00",
        "tool": "antigravity",
        "project_id": "git-photodos",
        "event_type": "bugfix",
        "task": "Audit code, decouple Ch3 dual vs solo inversion and harden mobile touch",
        "changes": [f"Change {i}: " + "rendering details " * 20 for i in range(5)],
        "verification": [
            "Node.js syntax check passed across all HTML files",
            "SHA-256 hash match confirmed across 5 files",
            "git push origin main succeeded",
        ],
        "risks": ["Real-device touch behavior remains unverified"],
        **overrides,
    }


def _processed_event(root, event):
    source = root / "raw/events/processed/2026-09-27" / f"{event['event_id']}.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(event), encoding="utf-8")
    return source


@pytest.mark.parametrize("incremental", [False, True])
def test_photodos_validation_survives_long_changes(tmp_path, incremental):
    event = _repair_event()
    source = _processed_event(tmp_path, event)
    raw_before = source.read_bytes()
    if incremental:
        page = append_event(tmp_path, event)
    else:
        rebuild_project_pages(tmp_path)
        page = tmp_path / "wiki/projects/git-photodos.md"
    text = page.read_text(encoding="utf-8")
    verifications = text.split("## Verifications", 1)[1].split("## Open Questions", 1)[0]
    assert event["task"] in text
    assert "Change 0:" in text and "Change 4:" in text
    for check in event["verification"]:
        assert check in verifications
    assert event["risks"][0] in text
    assert source.relative_to(tmp_path).as_posix() in text
    assert source.read_bytes() == raw_before


def test_append_is_byte_idempotent_and_preserves_existing_provenance(tmp_path):
    first = _repair_event(event_type="decision", decisions=["Keep one canonical source"])
    _processed_event(tmp_path, first)
    rebuild_project_pages(tmp_path)
    page = tmp_path / "wiki/projects/git-photodos.md"
    original = page.read_bytes()
    append_event(tmp_path, first)
    assert page.read_bytes() == original
    second = _repair_event(
        event_id="new-decision",
        event_type="decision",
        decisions=["Use bounded source-backed summaries"],
    )
    _processed_event(tmp_path, second)
    append_event(tmp_path, second)
    once = page.read_bytes()
    append_event(tmp_path, second)
    assert page.read_bytes() == once
    text = page.read_text(encoding="utf-8")
    decisions = text.split("## Decisions", 1)[1].split("## Bugfixes", 1)[0]
    assert decisions.count("Keep one canonical source") == 1
    assert decisions.count("Use bounded source-backed summaries") == 1
    assert "antigravity · photodos-validation · raw/events/processed/" in decisions


def test_append_without_tool_or_source_still_retains_event_identity(tmp_path):
    event = _repair_event(tool="")
    page = append_event(tmp_path, event)
    before = page.read_bytes()
    append_event(tmp_path, event)
    assert page.read_bytes() == before
    assert "photodos-validation" in page.read_text(encoding="utf-8")


def test_append_migrates_source_backed_legacy_bullets_without_losing_notes(tmp_path):
    event = _repair_event(event_type="decision", decisions=["Keep one canonical source"])
    source = _processed_event(tmp_path, event)
    page = tmp_path / "wiki/projects/git-photodos.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ntype: project\nproject_id: git-photodos\n---\n"
        "## Decisions\n\n"
        "- 2026-09-27T01:19:03+08:00 — Keep one canonical source\n"
        "- 2026-09-26T00:00:00Z — Historical manual decision\n"
        "\n## Human Notes\n\nKeep my manual note.\n",
        encoding="utf-8",
    )
    append_event(tmp_path, event)
    text = page.read_text(encoding="utf-8")
    assert text.count("Keep one canonical source") == 1
    assert "Historical manual decision" in text
    assert "Keep my manual note." in text
    assert source.relative_to(tmp_path).as_posix() in text
    once = page.read_bytes()
    append_event(tmp_path, event)
    assert page.read_bytes() == once


def test_append_questions_are_bounded_idempotent_and_source_backed(tmp_path):
    event = _repair_event(event_type="project_status", open_questions=["Confirm device touch"])
    source = _processed_event(tmp_path, event)
    page = append_event(tmp_path, event)
    append_event(tmp_path, event)
    questions = page.read_text(encoding="utf-8").split("## Open Questions", 1)[1]
    assert questions.count("Confirm device touch") == 1
    assert event["event_id"] in questions
    assert source.relative_to(tmp_path).as_posix() in questions


def test_replay_preserves_provenance_when_raw_source_is_unavailable(tmp_path):
    event = _repair_event()
    source = _processed_event(tmp_path, event)
    rebuild_project_pages(tmp_path)
    page = tmp_path / "wiki/projects/git-photodos.md"
    before = page.read_bytes()
    source.unlink()
    append_event(tmp_path, event)
    assert page.read_bytes() == before


def test_legacy_truncated_bugfix_is_migrated_with_actual_verification(tmp_path):
    event = _repair_event()
    source = _processed_event(tmp_path, event)
    # Literal old renderer contract: the combined text was truncated at 480.
    old = (
        event["task"]
        + " — changes: "
        + "; ".join(change[:240] for change in event["changes"])
        + " — verified: "
        + "; ".join(event["verification"])
    )[:480]
    page = tmp_path / "wiki/projects/git-photodos.md"
    page.parent.mkdir(parents=True)
    page.write_text("## Bugfixes\n\n- " + event["timestamp"] + " — " + old + "\n", encoding="utf-8")
    append_event(
        tmp_path,
        _repair_event(
            event_id="new",
            event_type="decision",
            decisions=["Keep verified evidence"],
            changes=[],
            verification=[],
            risks=[],
        ),
    )
    text = page.read_text(encoding="utf-8")
    assert text.count("Change 0:") == 1
    assert source.relative_to(tmp_path).as_posix() in text
    verifications = text.split("## Verifications", 1)[1].split("## Open Questions", 1)[0]
    for check in event["verification"]:
        assert check in verifications


def test_long_verification_items_each_keep_a_compact_slot(tmp_path):
    event = _repair_event(verification=[f"Check {i}: " + "proof " * 100 for i in range(8)])
    page = append_event(tmp_path, event)
    verifications = page.read_text(encoding="utf-8").split("## Verifications", 1)[1]
    for i in range(8):
        assert f"Check {i}:" in verifications


def test_append_migrates_truncated_bullet_with_existing_provenance(tmp_path):
    event = _repair_event()
    source = _processed_event(tmp_path, event)
    old = (
        event["task"]
        + " — changes: "
        + "; ".join(change[:240] for change in event["changes"])
        + " — verified: "
        + "; ".join(event["verification"])
    )[:480]
    page = tmp_path / "wiki/projects/git-photodos.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "## Bugfixes\n\n- " + event["timestamp"] + " — " + old + "\n"
        f"  ↳ antigravity · {event['event_id']} · {source.relative_to(tmp_path).as_posix()}\n",
        encoding="utf-8",
    )
    append_event(
        tmp_path,
        _repair_event(
            event_id="new",
            event_type="decision",
            decisions=["Keep verified evidence"],
            changes=[],
            verification=[],
            risks=[],
        ),
    )
    text = page.read_text(encoding="utf-8")
    verifications = text.split("## Verifications", 1)[1].split("## Open Questions", 1)[0]
    for check in event["verification"]:
        assert check in verifications
    assert source.relative_to(tmp_path).as_posix() in verifications


def test_same_event_id_cannot_overwrite_the_recorded_decision(tmp_path):
    event = _repair_event(
        event_type="decision",
        decisions=["Recorded decision"],
        changes=[],
        verification=[],
        risks=[],
    )
    page = append_event(tmp_path, event)
    original = page.read_bytes()
    append_event(tmp_path, {**event, "decisions": ["Altered replay"]})
    assert page.read_bytes() == original
