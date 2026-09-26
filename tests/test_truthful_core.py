"""Truthful Core contract tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 2. Truthful Core
      -> Test Plan / 1. Contract And Unit Tests (Admission)

Asserted meaning, not file existence:

* commands, complete prompts, environment dumps, lifecycle receipts and watcher
  observations never reach durable project memory;
* every durable line is traceable to an event id, tool and evidence path;
* a rebuild is deterministic and byte-identical for unchanged input;
* event order does not change output;
* raw evidence is never mutated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lwm.project_memory import (
    MAX_ITEMS_PER_FIELD,
    MAX_ITEM_CHARS,
    MAX_TASK_CHARS,
    classify_event,
    load_processed_events,
    rebuild_project_pages,
)


PROJECT = "git-truthful-core"

NOISY_EVENTS: list[dict[str, object]] = [
    {
        "event_type": "workflow_observation",
        "task": "# AGENTS.md instructions\nYou are Codex, based on GPT-5.",
    },
    {
        "event_type": "workflow_observation",
        "task": "<environment_context>cwd=/tmp shell=zsh</environment_context>",
    },
    {"event_type": "workflow_observation", "task": "git status --short"},
    {"event_type": "session_start", "task": "Ather session started"},
    {"event_type": "session_summary", "task": "(no user text)"},
    {"event_type": "adapter_probe", "task": "probe codex"},
]

DURABLE_EVENTS: list[dict[str, object]] = [
    {
        "event_type": "decision",
        "task": "Lock the auxiliary evidence boundary",
        "decisions": ["Native tool instructions remain authoritative"],
        "verification": ["Lean Core design reviewed"],
    },
    {
        "event_type": "bugfix",
        "task": "Exclude archived review pages from active analysis",
        "changes": ["Ignore wiki path parts beginning with _archive"],
        "verification": ["analysis test reports zero duplicate slugs"],
    },
    {
        "event_type": "verification",
        "task": "Verify scheduled memory cycle",
        "verification": ["launchd exit code 0", "audit passed", "health healthy"],
    },
]


def _write_event(root: Path, event: dict[str, object], *, day: str = "2026-07-31") -> Path:
    payload = {
        "project_id": PROJECT,
        "tool": "codex",
        "timestamp": f"{day}T01:00:00+08:00",
        "privacy": "sanitized",
        "importance": "project",
        **event,
    }
    payload.setdefault("event_id", hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:36])
    target = root / "raw" / "events" / "processed" / day / f"{payload['event_id']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def _hash_tree(base: Path) -> dict[str, str]:
    return {
        path.relative_to(base).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*.json"))
    }


# --------------------------------------------------------------------------
# classify_event
# --------------------------------------------------------------------------


@pytest.mark.parametrize("event", NOISY_EVENTS)
def test_noisy_events_are_never_durable(event: dict[str, object]) -> None:
    admission = classify_event(event)
    assert admission.durability != "durable", admission
    assert admission.section is None


def test_instruction_and_environment_dumps_are_rejected() -> None:
    assert classify_event(NOISY_EVENTS[0]).durability == "rejected"
    assert classify_event(NOISY_EVENTS[1]).durability == "rejected"


def test_command_only_and_lifecycle_stay_operational() -> None:
    assert classify_event(NOISY_EVENTS[2]).durability == "operational"
    assert classify_event(NOISY_EVENTS[3]).durability == "operational"


def test_structured_work_is_durable_with_expected_section() -> None:
    sections = [classify_event(event).section for event in DURABLE_EVENTS]
    assert sections == ["decisions", "bugfixes", "verifications"]
    assert all(
        classify_event(event).durability == "durable" for event in DURABLE_EVENTS
    )


def test_project_status_requires_task_and_structured_field() -> None:
    assert classify_event({"event_type": "project_status", "task": "x"}).durability == (
        "operational"
    )
    admission = classify_event(
        {"event_type": "project_status", "task": "x", "changes": ["y"]}
    )
    assert (admission.durability, admission.section) == ("durable", "status")


def test_bugfix_without_verification_is_not_durable() -> None:
    admission = classify_event(
        {"event_type": "bugfix", "task": "t", "changes": ["c"]}
    )
    assert admission.durability == "operational"


def test_malformed_payloads_are_rejected_not_raised() -> None:
    assert classify_event(["not", "a", "dict"]).durability == "rejected"
    assert classify_event(None).durability == "rejected"


def test_malformed_nested_items_are_dropped() -> None:
    admission = classify_event(
        {"event_type": "decision", "task": "t", "decisions": [{"nested": "bad"}]}
    )
    assert admission.durability == "operational"


def test_secret_material_is_rejected() -> None:
    admission = classify_event(
        {
            "event_type": "decision",
            "task": "rotate key",
            "decisions": ["use sk-" + "A" * 32],
        }
    )
    assert admission.durability == "rejected"
    assert admission.reason == "secret_material"


# --------------------------------------------------------------------------
# rebuild_project_pages
# --------------------------------------------------------------------------


def test_rebuild_admits_only_durable_events(tmp_path: Path) -> None:
    for event in NOISY_EVENTS + DURABLE_EVENTS:
        _write_event(tmp_path, event)

    report = rebuild_project_pages(tmp_path)

    assert report.admitted_events == len(DURABLE_EVENTS)
    assert report.rejected_events == 2
    assert report.operational_events == 4
    assert report.pages_written == 1


def test_no_noise_string_reaches_the_project_page(tmp_path: Path) -> None:
    for event in NOISY_EVENTS + DURABLE_EVENTS:
        _write_event(tmp_path, event)
    rebuild_project_pages(tmp_path)

    page = (tmp_path / "wiki" / "projects" / f"{PROJECT}.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "AGENTS.md instructions",
        "You are Codex",
        "<environment_context>",
        "git status --short",
        "(no user text)",
    ):
        assert marker not in page, marker


def test_every_durable_line_is_traceable(tmp_path: Path) -> None:
    paths = [_write_event(tmp_path, event) for event in DURABLE_EVENTS]
    rebuild_project_pages(tmp_path)

    page = (tmp_path / "wiki" / "projects" / f"{PROJECT}.md").read_text(
        encoding="utf-8"
    )
    for path in paths:
        rel = path.relative_to(tmp_path).as_posix()
        assert rel in page, rel
        assert path.stem in page
    assert page.count("↳ codex · ") >= len(DURABLE_EVENTS)


def test_second_rebuild_is_byte_identical(tmp_path: Path) -> None:
    for event in DURABLE_EVENTS:
        _write_event(tmp_path, event)
    rebuild_project_pages(tmp_path)
    target = tmp_path / "wiki" / "projects" / f"{PROJECT}.md"
    first = target.read_bytes()

    second_report = rebuild_project_pages(tmp_path)

    assert target.read_bytes() == first
    assert second_report.pages_written == 0
    assert second_report.unchanged_paths


def test_event_order_does_not_change_output(tmp_path: Path, tmp_path_factory) -> None:
    other = tmp_path_factory.mktemp("reversed")
    for event in DURABLE_EVENTS:
        _write_event(tmp_path, event)
    for event in reversed(DURABLE_EVENTS):
        _write_event(other, event)

    rebuild_project_pages(tmp_path)
    rebuild_project_pages(other)

    name = f"{PROJECT}.md"
    assert (tmp_path / "wiki" / "projects" / name).read_text(encoding="utf-8") == (
        other / "wiki" / "projects" / name
    ).read_text(encoding="utf-8")


def test_polluted_page_is_replaced_from_clean_raw_events(tmp_path: Path) -> None:
    for event in DURABLE_EVENTS:
        _write_event(tmp_path, event)
    target = tmp_path / "wiki" / "projects" / f"{PROJECT}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\ntype: project\nproject_id: "
        + PROJECT
        + "\n---\n\n## Status\n\n- 2026-01-01 — <environment_context>leak</environment_context>\n",
        encoding="utf-8",
    )

    rebuild_project_pages(tmp_path)

    page = target.read_text(encoding="utf-8")
    assert "<environment_context>" not in page
    assert "Native tool instructions remain authoritative" in page


def test_rebuild_never_mutates_raw_evidence(tmp_path: Path) -> None:
    for event in NOISY_EVENTS + DURABLE_EVENTS:
        _write_event(tmp_path, event)
    base = tmp_path / "raw"
    before = _hash_tree(base)

    rebuild_project_pages(tmp_path)

    assert _hash_tree(base) == before


def test_dry_run_writes_nothing_but_reports_manifest(tmp_path: Path) -> None:
    for event in DURABLE_EVENTS:
        _write_event(tmp_path, event)

    report = rebuild_project_pages(tmp_path, dry_run=True)

    assert report.dry_run is True
    assert report.pages_written == 1
    assert report.written_paths == (f"wiki/projects/{PROJECT}.md",)
    assert not (tmp_path / "wiki" / "projects").exists()


def test_page_without_durable_events_is_reconciled_away(tmp_path: Path) -> None:
    _write_event(tmp_path, NOISY_EVENTS[3])
    stale = tmp_path / "wiki" / "projects" / f"{PROJECT}.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(
        f"---\ntype: project\nproject_id: {PROJECT}\n---\n\n## Status\n\n- x — y\n",
        encoding="utf-8",
    )

    report = rebuild_project_pages(tmp_path)

    assert report.pages_removed == 1
    assert not stale.exists()


def test_hand_written_page_is_never_removed(tmp_path: Path) -> None:
    hand = tmp_path / "wiki" / "projects" / "handwritten.md"
    hand.parent.mkdir(parents=True, exist_ok=True)
    hand.write_text("# notes kept by a human\n", encoding="utf-8")

    report = rebuild_project_pages(tmp_path)

    assert report.pages_removed == 0
    assert hand.exists()


def test_project_filter_scopes_the_rebuild(tmp_path: Path) -> None:
    _write_event(tmp_path, DURABLE_EVENTS[0])
    other = dict(DURABLE_EVENTS[1])
    path = _write_event(tmp_path, other)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["project_id"] = "git-other"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    report = rebuild_project_pages(tmp_path, project_id=PROJECT)

    assert report.written_paths == (f"wiki/projects/{PROJECT}.md",)
    assert not (tmp_path / "wiki" / "projects" / "git-other.md").exists()


def test_invalid_json_is_skipped_and_preserved(tmp_path: Path) -> None:
    _write_event(tmp_path, DURABLE_EVENTS[0])
    broken = tmp_path / "raw" / "events" / "processed" / "2026-07-31" / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    report = rebuild_project_pages(tmp_path)

    assert report.admitted_events == 1
    assert broken.read_text(encoding="utf-8") == "{not json"
    assert len(load_processed_events(tmp_path)) == 1


def test_durable_text_is_bounded(tmp_path: Path) -> None:
    _write_event(
        tmp_path,
        {
            "event_type": "decision",
            "task": "T" * (MAX_TASK_CHARS * 3),
            "decisions": ["D" * (MAX_ITEM_CHARS * 3)]
            + [f"extra-{i}" for i in range(MAX_ITEMS_PER_FIELD * 2)],
        },
    )

    rebuild_project_pages(tmp_path)

    page = (tmp_path / "wiki" / "projects" / f"{PROJECT}.md").read_text(
        encoding="utf-8"
    )
    assert "T" * (MAX_TASK_CHARS + 1) not in page
    assert "D" * (MAX_ITEM_CHARS + 1) not in page
    assert f"extra-{MAX_ITEMS_PER_FIELD * 2 - 1}" not in page
