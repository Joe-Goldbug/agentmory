"""Tests for branch-isolated handoff concurrency and CAS fork safety."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from lwm.handoff import (
    HandoffConflictError,
    HandoffPacket,
    close_handoff,
    create_handoff,
    create_handoff_from_summary,
    load_active,
)

PROJECT = "concurrent-git-handoff"


def test_handoff_version_increments_with_cas(tmp_path: Path) -> None:
    first = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="first objective",
        current_state="in-progress",
        source_tool="claude-code",
    )
    assert first.version == 1
    assert first.git_branch == ""

    second = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="second objective",
        current_state="done",
        source_tool="codex",
        supersedes=first.handoff_id,
    )
    assert second.version == 2
    assert second.supersedes == first.handoff_id


def test_cas_conflict_creates_audit_fork_and_raises(tmp_path: Path) -> None:
    first = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="base state",
        current_state="ready",
        source_tool="claude-code",
    )
    # Agent A advances to second
    second = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="agent A commit",
        current_state="verified",
        source_tool="codex",
        supersedes=first.handoff_id,
    )

    # Agent B was working concurrently and still thinks active is first
    with pytest.raises(HandoffConflictError) as exc_info:
        create_handoff(
            tmp_path,
            project_id=PROJECT,
            task_id="t1",
            objective="agent B concurrent commit",
            current_state="testing",
            source_tool="cursor",
            supersedes=first.handoff_id,
        )

    err = exc_info.value
    assert err.active_id == second.handoff_id
    assert err.fork_path is not None
    assert err.fork_path.is_file()

    fork_data = json.loads(err.fork_path.read_text(encoding="utf-8"))
    assert fork_data["conflict_status"] == "fork_supersedes_mismatch"
    assert fork_data["source_tool"] == "cursor"
    assert fork_data["objective"] == "agent B concurrent commit"

    # Active pointer is uncorrupted and still points to second
    active = load_active(tmp_path, project_id=PROJECT)
    assert active is not None
    assert active.handoff_id == second.handoff_id


def test_cas_conflict_allow_fork_returns_packet(tmp_path: Path) -> None:
    first = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="base state",
        current_state="ready",
        source_tool="claude-code",
    )
    create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="advance",
        current_state="done",
        source_tool="codex",
        supersedes=first.handoff_id,
    )

    fork = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="forked branch work",
        current_state="stale",
        source_tool="cursor",
        supersedes=first.handoff_id,
        allow_fork=True,
    )
    assert fork.conflict_status == "fork_supersedes_mismatch"
    fork_file = tmp_path / "state" / "handoffs" / f"fork-{fork.handoff_id}.json"
    assert fork_file.is_file()


def test_git_branch_isolation(tmp_path: Path) -> None:
    main_packet = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t1",
        objective="main branch work",
        current_state="in-progress",
        source_tool="claude-code",
        git_branch="main",
        head_commit="abc1234",
    )

    feat_packet = create_handoff(
        tmp_path,
        project_id=PROJECT,
        task_id="t2",
        objective="feature branch work",
        current_state="experiment",
        source_tool="codex",
        git_branch="feat/auth",
        head_commit="def5678",
    )

    active_main = load_active(tmp_path, project_id=PROJECT, branch="main")
    assert active_main is not None
    assert active_main.handoff_id == main_packet.handoff_id
    assert active_main.git_branch == "main"

    active_feat = load_active(tmp_path, project_id=PROJECT, branch="feat/auth")
    assert active_feat is not None
    assert active_feat.handoff_id == feat_packet.handoff_id
    assert active_feat.git_branch == "feat/auth"

    # Closing feat cleans up feat branch active pointer
    close_handoff(tmp_path, handoff_id=feat_packet.handoff_id)
    assert load_active(tmp_path, project_id=PROJECT, branch="feat/auth", fallback_to_project=False) is None
    # Main branch active pointer remains completely intact
    assert load_active(tmp_path, project_id=PROJECT, branch="main").handoff_id == main_packet.handoff_id
