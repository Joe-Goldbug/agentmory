"""Tests for ``lwm hub forget`` + ``lwm hub retention``.

Scope Lock:
- Solves: forget removes the file, drops the index entry, scrubs the
  matching bullet from the project page; retention deletes older than N
  days but never touches inbox.
- Does not solve: undo (by design).
- Acceptance: 5 tests cover the happy paths + safety branch.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from lwm import forget, ingest
from lwm.events import make_event
from lwm.memory_compiler import load_accepted_analysis_candidates
from lwm.stable_promotion import render_global_page
from lwm.structured_candidates import load_accepted


def _seed_event(root: Path, *, project_id: str = "git-x", tool: str = "shell", task: str = "forget me") -> dict:
    payload = make_event(
        tool=tool,
        project_path=str(root),
        project_id=project_id,
        event_type="decision",
        task=task,
        decisions=[task],
        verification=["local review"],
        tags=["forget-me"],
    )
    target = root / "raw" / "events" / "inbox" / "2026-07-11"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{payload['event_id']}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    ingest.run(root, with_lock=False)
    return payload


def test_forget_removes_file_index_and_bullet(tmp_path: Path) -> None:
    payload = _seed_event(tmp_path)
    page = tmp_path / "wiki" / "projects" / "git-x.md"
    assert page.is_file()
    text_before = page.read_text(encoding="utf-8")
    assert "forget me" in text_before

    result = forget.forget_event(tmp_path, payload["event_id"])
    assert result.deleted_files
    assert result.index_updated is True
    # Project page bullet entry for the event was removed.
    text_after = page.read_text(encoding="utf-8")
    assert "Last task: (no task recorded)" in text_after
    # The original bullet is a line like
    # ``- 2026-07-11T22:02:50+08:00 — forget me``; the header retains the
    # last-task summary. We assert the bullet line specifically is gone
    # by checking that no ``## Status`` content line mentions "forget me".
    in_status = [
        line
        for line in text_after.splitlines()
        if line.startswith("- ") and "forget me" in line
    ]
    assert in_status == []


def test_forget_cleans_project_page_bullet(tmp_path: Path) -> None:
    """End-to-end: write two events, forget one, page keeps the other.

    The two events must carry distinct timestamps or the page bullet
    becomes ambiguous (collisions exist when ``make_event`` is called in
    the same wall-clock second).
    """

    import time as _time

    a = make_event(
        tool="shell",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="decision",
        task="keep me",
        decisions=["keep me"],
        verification=["ok"],
        tags=["keep"],
    )
    _time.sleep(1.05)  # ensure unique timestamp down to the second.
    b = make_event(
        tool="shell",
        project_path=str(tmp_path),
        project_id="git-x",
        event_type="decision",
        task="drop me",
        decisions=["drop me"],
        verification=["ok"],
        tags=["drop"],
    )
    inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    for ev in (a, b):
        (inbox_dir / f"{ev['event_id']}.json").write_text(
            json.dumps(ev, ensure_ascii=False), encoding="utf-8"
        )
    ingest.run(tmp_path, with_lock=False)

    forget.forget_event(tmp_path, b["event_id"])

    text = (tmp_path / "wiki" / "projects" / "git-x.md").read_text(encoding="utf-8")
    assert "keep me" in text
    drop_lines = [
        line for line in text.splitlines()
        if line.startswith("- ") and "drop me" in line
    ]
    assert drop_lines == []


def test_forget_removes_processed_file_after_ingest(tmp_path: Path) -> None:
    payload = _seed_event(tmp_path, project_id="git-after")
    processed = tmp_path / "raw" / "events" / "processed" / "2026-07-11" / f"{payload['event_id']}.json"
    assert processed.is_file()
    result = forget.forget_event(tmp_path, payload["event_id"])
    assert any(p.name == f"{payload['event_id']}.json" for p in result.deleted_files)
    assert not processed.exists()


def test_forget_removes_accepted_and_derived_candidates(tmp_path: Path) -> None:
    payload = _seed_event(tmp_path)
    event_id = payload["event_id"]
    review_dir = tmp_path / "state" / "candidates"
    analysis_dir = tmp_path / "state" / "analysis" / "candidates"
    review_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    affected = review_dir / "affected.json"
    analysis = analysis_dir / "derived.json"
    unrelated = review_dir / "unrelated.json"
    affected.write_text(
        json.dumps({"state": "accepted", "evidence_ids": [event_id, "other"]}),
        encoding="utf-8",
    )
    analysis.write_text(
        json.dumps({"state": "accepted", "evidence_ids": ["other"], "counterevidence_ids": [event_id]}),
        encoding="utf-8",
    )
    unrelated.write_text(
        json.dumps({"state": "accepted", "evidence_ids": ["other"]}),
        encoding="utf-8",
    )
    assert len(load_accepted(tmp_path)) == 2
    assert len(load_accepted_analysis_candidates(tmp_path)) == 1

    result = forget.forget_event(tmp_path, event_id)

    assert set(result.invalidated_candidates) == {affected, analysis}
    assert affected.exists() and analysis.exists()
    assert json.loads(affected.read_text(encoding="utf-8"))["withdrawal_reason"] == "source_event_forgotten"
    assert json.loads(analysis.read_text(encoding="utf-8"))["state"] == "rejected"
    assert unrelated.exists()
    assert load_accepted(tmp_path) == [{"state": "accepted", "evidence_ids": ["other"]}]
    assert load_accepted_analysis_candidates(tmp_path) == []
    assert forget.forget_event(tmp_path, event_id).deleted_files == ()


def test_forget_withdraws_promoted_page_without_deleting_it(tmp_path: Path) -> None:
    from lwm.context import _approved_global_page

    payload = _seed_event(tmp_path)
    event_id = payload["event_id"]
    global_dir = tmp_path / "wiki" / "global"
    global_dir.mkdir(parents=True)
    affected = global_dir / "affected.md"
    unrelated = global_dir / "unrelated.md"
    for path, event_ids in ((affected, (event_id, "other")), (unrelated, ("other",))):
        path.write_text(
            render_global_page(
                claim="A source-backed claim",
                claim_key=path.stem,
                project_ids=("git-x",),
                event_ids=event_ids,
                evidence_paths=(),
                actor="human",
            ),
            encoding="utf-8",
        )
    assert _approved_global_page(affected, affected.read_text(encoding="utf-8"))

    with pytest.warns(UserWarning, match="pages requiring review"):
        result = forget.forget_event(tmp_path, event_id)

    assert affected.is_file() and unrelated.is_file()
    assert result.invalidated_pages == (affected,)
    assert affected in result.requires_review
    assert result.page_path in result.requires_review
    assert "status: source_withdrawn" in affected.read_text(encoding="utf-8")
    assert not _approved_global_page(affected, affected.read_text(encoding="utf-8"))
    assert _approved_global_page(unrelated, unrelated.read_text(encoding="utf-8"))


def test_forget_unknown_id_is_a_noop(tmp_path: Path) -> None:
    result = forget.forget_event(tmp_path, "00000000-no-such-event")
    assert result.deleted_files == ()
    assert result.index_updated is False


def test_forget_cleans_rejected_bucket(tmp_path: Path) -> None:
    """Events that ended up in ``rejected/`` should also be forgettable."""

    rejected = tmp_path / "raw" / "events" / "rejected" / "2026-07-11"
    rejected.mkdir(parents=True, exist_ok=True)
    event_id = "abc-rejected-001"
    (rejected / f"{event_id}.json").write_text(
        json.dumps(
            {
                "event_id": event_id,
                "timestamp": "2026-07-11T00:00:00+00:00",
                "tool": "shell",
                "project_path": "/x",
                "project_id": "git-x",
                "event_type": "workflow_observation",
                "importance": "scratch",
                "privacy": "redacted",
                "task": "redact me",
            }
        ),
        encoding="utf-8",
    )

    result = forget.forget_event(tmp_path, event_id)
    assert result.deleted_files and not (rejected / f"{event_id}.json").exists()


def test_retention_drops_old_processed_only(tmp_path: Path) -> None:
    """Retention must respect ``older_than_days`` and never touch inbox."""

    now = time.time()
    old = now - 100 * 86400
    fresh = now - 86400

    processed = tmp_path / "raw" / "events" / "processed" / "2026-07-11"
    processed.mkdir(parents=True, exist_ok=True)
    old_file = processed / "old.json"
    new_file = processed / "new.json"
    old_file.write_text("{}", encoding="utf-8")
    new_file.write_text("{}", encoding="utf-8")
    os.utime(old_file, (old, old))
    os.utime(new_file, (fresh, fresh))

    inbox_dir = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    old_inbox = inbox_dir / "old-inbox.json"
    old_inbox.write_text("{}", encoding="utf-8")
    os.utime(old_inbox, (old, old))

    removed = forget.apply_retention(
        tmp_path,
        bucket="processed",
        older_than_days=30,
        now_epoch=now,
    )
    assert old_file in removed and new_file not in removed
    assert old_inbox.exists(), "inbox must never be auto-pruned"
    # Inbox bucket is refused even if asked.
    inbox_removed = forget.apply_retention(
        tmp_path,
        bucket="inbox",
        older_than_days=30,
        now_epoch=now,
    )
    assert inbox_removed == ()


def test_retention_rejects_negative_days(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        forget.apply_retention(tmp_path, bucket="processed", older_than_days=-1)
