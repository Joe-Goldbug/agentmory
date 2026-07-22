"""Inbox + dedup + lockfile tests."""

from __future__ import annotations

import json
import time
from pathlib import Path


from lwm import inbox
from lwm import dedup
from lwm import lockfile
from lwm.events import make_event


def test_submit_and_move(tmp_path: Path) -> None:
    event = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="workflow_observation",
        task="hello",
    )
    target = inbox.submit_event(tmp_path, event)
    assert target.exists()
    status = inbox.inbox_status(tmp_path)
    assert status.inbox == 1

    moved = inbox.move_event(target, target_bucket="processed")
    assert moved.exists()
    status = inbox.inbox_status(tmp_path)
    assert status.inbox == 0
    assert status.processed == 1


def test_submit_uses_same_directory_for_atomic_replace(tmp_path: Path, monkeypatch) -> None:
    event = make_event(
        tool="trae",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="workflow_observation",
        task="sandbox-safe write",
    )
    replacements: list[tuple[Path, Path]] = []
    real_replace = inbox.os.replace

    def capture_replace(source: str | Path, target: str | Path) -> None:
        replacements.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(inbox.os, "replace", capture_replace)

    target = inbox.submit_event(tmp_path, event)

    assert replacements == [(replacements[0][0], target)]
    assert replacements[0][0].parent == target.parent
    assert not replacements[0][0].exists()


def test_dedup_evaluates_duplicate(tmp_path: Path) -> None:
    event = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="session_summary",
        task="task-A",
    )
    inbox.submit_event(tmp_path, event)
    dedup.record_event(tmp_path, event, bucket="inbox", file_path="dummy.json")
    duplicate = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="session_summary",
        task="task-A",
        event_id="second-id",
    )
    decision = dedup.evaluate(tmp_path, duplicate)
    assert decision.duplicate is True


def test_dedup_session_window(tmp_path: Path) -> None:
    first = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="session_summary",
        task="start",
        session_id="abc",
    )
    dedup.record_event(tmp_path, first, bucket="processed", file_path="a.json")
    second = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="session_start",
        task="restart",
        session_id="abc",
    )
    decision = dedup.evaluate(tmp_path, second)
    assert decision.duplicate is True


def test_lockfile_acquire_release(tmp_path: Path) -> None:
    result = lockfile.try_acquire(tmp_path)
    assert result.acquired is True
    again = lockfile.try_acquire(tmp_path)
    assert again.acquired is False
    assert lockfile.release(tmp_path) is True
    third = lockfile.try_acquire(tmp_path)
    assert third.acquired is True


def test_lockfile_stale_recovery(tmp_path: Path) -> None:
    lockfile_path = lockfile.lock_path(tmp_path)
    lockfile_path.parent.mkdir(parents=True, exist_ok=True)
    long_ago = time.time() - 9999
    lockfile_path.write_text(
        json.dumps({"pid": 1, "acquired_at": long_ago, "stale_after": 60}),
        encoding="utf-8",
    )
    result = lockfile.try_acquire(tmp_path, stale_after=60)
    assert result.acquired is True


def test_inbox_status_zero_on_empty(tmp_path: Path) -> None:
    status = inbox.inbox_status(tmp_path)
    assert status.inbox == 0
    assert status.processed == 0
