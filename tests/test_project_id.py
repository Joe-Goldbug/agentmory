"""Project-id derivation tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lwm.project_id import (
    load_project_map,
    record_project,
    resolve_project_id,
    save_project_map,
)


def test_resolve_offline_path(tmp_path: Path) -> None:
    res = resolve_project_id(tmp_path)
    assert res.kind in {"local", "adhoc"}
    assert res.project_id.startswith(("local-", "adhoc-"))


def test_resolve_git_repo(tmp_path: Path) -> None:
    if not _git_available():
        pytest.skip("git not available")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "https://example.com/me/proj.git"],
        check=True,
    )
    res = resolve_project_id(tmp_path)
    assert res.kind == "git"
    assert res.project_id.startswith("git-")


def test_record_and_cache(tmp_path: Path) -> None:
    target = tmp_path / "wiki"
    target.mkdir()
    res = record_project(target, "/Users/me/projA")
    assert res.project_id.startswith(("local-", "adhoc-"))
    again = record_project(target, "/Users/me/projA")
    assert again.project_id == res.project_id
    cache = load_project_map(target)
    assert "/Users/me/projA" in cache
    save_project_map(target, cache)


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False
