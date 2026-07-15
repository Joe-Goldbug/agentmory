"""Regression: ``lwm context`` must find the project page even when the
caller passed a literal ``project_id`` that disagrees with the one git
would derive.  Tests pin the new ``project-map`` bridge behaviour.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lwm import context, ingest, project_id
from lwm.events import make_event


def _git_init(path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    # Make sure resolve_project_id takes the git path → git-<sha> branch.
    subprocess.run(
        ["git", "-C", str(path), "remote", "add", "origin",
         f"https://example.com/{path.name}.git"],
        check=True,
    )


def test_caller_id_wins_and_is_persisted(tmp_path: Path) -> None:
    """Caller passes a literal project_id → ingest must bridge it into project-map."""

    _git_init(tmp_path)
    payload = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-lwm-stable",
        event_type="session_summary",
        task="id bridge",
    )
    inbox = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{payload['event_id']}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    ingest.run(tmp_path, with_lock=False)

    cache = project_id.load_project_map(tmp_path)
    assert cache[str(tmp_path.resolve())] == "git-lwm-stable"


def test_context_finds_project_page_with_caller_id(tmp_path: Path) -> None:
    """After ingest, ``context`` should look up the cached id and find the page."""

    _git_init(tmp_path)
    payload = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-lwm-stable",
        event_type="session_summary",
        task="id bridge test 2",
    )
    inbox = tmp_path / "raw" / "events" / "inbox" / "2026-07-11"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{payload['event_id']}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    ingest.run(tmp_path, with_lock=False)

    report = context.build(
        tmp_path,
        tool="claude-code",
        project_path=str(tmp_path),
        format="markdown",
    )
    assert "git-lwm-stable" in report.markdown
    # The legacy "no project memory yet" message must not appear.
    assert "no project memory yet" not in report.markdown
