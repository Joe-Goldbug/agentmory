"""Handoff contract tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Architecture And Interfaces / 3. Event And Handoff Contracts
      -> Implementation Changes / 4. Handoff and unified task identity

Asserted meaning:

* exactly one active handoff per project, identified by ``handoff_id``;
* ``supersedes`` is mandatory: a stale write that names a different prior
  handoff is rejected;
* a closed handoff stays in storage but loses the active pointer;
* ack appends to ``verifications`` without re-pointing the active file when
  the target is no longer active.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lwm.handoff import (
    HandoffPacket,
    ack_handoff,
    append_handoff_evidence,
    close_handoff,
    create_handoff,
    create_handoff_from_summary,
    list_handoffs,
    load_active,
    render_handoff_markdown,
)


PROJECT = "git-handoff"


def _seed(root: Path, **overrides: object) -> HandoffPacket:
    payload = {
        "project_id": PROJECT,
        "task_id": "task-1",
        "objective": "ship the boundary",
        "current_state": "drafting",
        "source_tool": "claude-code",
        "decisions": ["use stable claim key"],
        "next_action": "run pytest",
        "evidence_ids": ["evt-1", "evt-2"],
    }
    payload.update(overrides)
    return create_handoff(root, **payload)  # type: ignore[arg-type]


def test_create_writes_active_pointer_and_file(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    assert (tmp_path / "state" / "handoffs" / f"{packet.handoff_id}.json").is_file()
    active = load_active(tmp_path, project_id=PROJECT)
    assert active is not None
    assert active.handoff_id == packet.handoff_id
    assert active.schema_version == 2


def test_structured_summary_creates_bounded_handoff_with_event_evidence(
    tmp_path: Path,
) -> None:
    packet = create_handoff_from_summary(
        tmp_path,
        project_id=PROJECT,
        source_tool="claude-code",
        task_id="task-structured",
        evidence_id="event-1",
        summary={
            "objective": "finish the interface",
            "current_state": "implementation verified",
            "decisions": ["keep native instructions authoritative"],
            "changes": ["added bounded stop handoff"],
            "verifications": ["focused tests pass"],
            "risks": ["real adapter evidence is still pending"],
            "next_action": "run the full suite",
            "evidence_ids": ["receipt-1"],
            "raw_prompt": "must never be persisted",
        },
    )

    assert packet.task_id == "task-structured"
    assert packet.evidence_ids == ("event-1", "receipt-1")
    assert "must never be persisted" not in json.dumps(packet.to_dict())


def test_structured_summary_supersedes_same_task_but_rejects_other_task(
    tmp_path: Path,
) -> None:
    first = create_handoff_from_summary(
        tmp_path,
        project_id=PROJECT,
        source_tool="codex",
        task_id="task-1",
        evidence_id="event-1",
        summary={"objective": "first"},
    )
    second = create_handoff_from_summary(
        tmp_path,
        project_id=PROJECT,
        source_tool="claude-code",
        task_id="task-1",
        evidence_id="event-2",
        summary={"objective": "updated"},
    )

    assert second.supersedes == first.handoff_id
    with pytest.raises(ValueError, match="different task"):
        create_handoff_from_summary(
            tmp_path,
            project_id=PROJECT,
            source_tool="codex",
            task_id="task-2",
            evidence_id="event-3",
            summary={"objective": "stale task"},
        )


def test_structured_summary_rejects_unbounded_string_lists(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="decisions must be a list"):
        create_handoff_from_summary(
            tmp_path,
            project_id=PROJECT,
            source_tool="codex",
            task_id="task-1",
            evidence_id="event-1",
            summary={"decisions": "not a list"},
        )


def test_append_handoff_evidence_updates_active_packet(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    updated = append_handoff_evidence(
        tmp_path,
        handoff_id=packet.handoff_id,
        evidence_ids=("event-3", packet.evidence_ids[0]),
    )

    assert updated.evidence_ids == ("evt-1", "evt-2", "event-3")
    assert load_active(tmp_path, project_id=PROJECT).evidence_ids == updated.evidence_ids


def test_each_project_has_at_most_one_active_handoff(tmp_path: Path) -> None:
    first = _seed(tmp_path)
    second = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="task-2",
        objective="next phase",
        current_state="drafting v2",
        source_tool="codex",
        supersedes=first.handoff_id,
    )
    assert second.handoff_id != first.handoff_id
    assert second.supersedes == first.handoff_id
    active = load_active(tmp_path, project_id=PROJECT)
    assert active is not None
    assert active.handoff_id == second.handoff_id
    assert first.handoff_id in {p.handoff_id for p in list_handoffs(tmp_path)}


def test_stale_supersedes_is_rejected(tmp_path: Path) -> None:
    first = _seed(tmp_path)
    _seed(tmp_path, supersedes=first.handoff_id)  # second active handoff
    with pytest.raises(ValueError):
        create_handoff(
            tmp_path,
            project_id=PROJECT,
            task_id="task-3",
            objective="stale write",
            current_state="x",
            source_tool="codex",
            supersedes=first.handoff_id,  # no longer active
        )


def test_active_handoff_requires_explicit_compare_and_swap(tmp_path: Path) -> None:
    first = _seed(tmp_path)
    with pytest.raises(ValueError, match="supersedes"):
        create_handoff(
            tmp_path,
            project_id=PROJECT,
            task_id="task-2",
            objective="implicit overwrite",
            current_state="x",
            source_tool="codex",
        )
    assert load_active(tmp_path, project_id=PROJECT).handoff_id == first.handoff_id


def test_list_handoffs_does_not_duplicate_active_pointer(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    assert [item.handoff_id for item in list_handoffs(tmp_path)] == [packet.handoff_id]


def test_first_handoff_may_omit_supersedes(tmp_path: Path) -> None:
    packet = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t",
        objective="o",
        current_state="c",
        source_tool="claude-code",
    )
    assert packet.supersedes is None


def test_ack_appends_verification(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    acked = ack_handoff(
        tmp_path, handoff_id=packet.handoff_id, target_tool="codex"
    )
    assert any(item.startswith("ack:codex@") for item in acked.verifications)


def test_ack_on_unknown_handoff_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ack_handoff(tmp_path, handoff_id="missing", target_tool="codex")


def test_close_clears_active_pointer_but_keeps_file(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    closed = close_handoff(tmp_path, handoff_id=packet.handoff_id)
    assert closed.closed_at
    assert load_active(tmp_path, project_id=PROJECT) is None
    storage = tmp_path / "state" / "handoffs" / f"{packet.handoff_id}.json"
    assert storage.is_file()


def test_handoff_isolated_per_project(tmp_path: Path) -> None:
    _seed(tmp_path, project_id="git-a")
    _seed(tmp_path, project_id="git-b")
    assert load_active(tmp_path, project_id="git-a") is not None
    assert load_active(tmp_path, project_id="git-b") is not None
    assert load_active(tmp_path, project_id="git-c") is None


def test_render_handoff_markdown_includes_sections(tmp_path: Path) -> None:
    packet = _seed(
        tmp_path,
        risks=("sneakernet latency",),
        open_questions=("how to keep evidence hash stable",),
    )
    text = render_handoff_markdown(packet)
    for header in (
        "Decisions",
        "Open questions",
        "Risks",
        "Evidence IDs",
        "Next action",
        "evt-1",
        "use stable claim key",
    ):
        assert header in text, header


def test_packet_round_trip_through_disk(tmp_path: Path) -> None:
    packet = _seed(tmp_path)
    storage = tmp_path / "state" / "handoffs" / f"{packet.handoff_id}.json"
    payload = json.loads(storage.read_text(encoding="utf-8"))
    restored = HandoffPacket.from_dict(payload)
    assert restored == packet


def test_invalid_payloads_are_normalized_not_crashed(tmp_path: Path) -> None:
    payload = {
        "handoff_id": "  ",  # whitespace-only
        "project_id": PROJECT,
        "task_id": "t",
        "objective": "o",
        "current_state": "c",
    }
    packet = HandoffPacket.from_dict(payload)
    # Whitespace is replaced with a fresh uuid; everything else sticks.
    assert packet.handoff_id.strip() != ""
    assert packet.project_id == PROJECT
