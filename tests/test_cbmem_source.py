"""Tests for the cbmem source harvester.

These tests mock ``lwm.cbmem`` at the module level so no real subprocess
is ever spawned. The goal is to lock:

- ``raw/cbmem-snapshots/<date>/<project>/<tool>.json`` is written per tool.
- cbmem binary missing does NOT raise; outcomes are recorded.
- a per-tool exception inside cbmem.* is captured and does not propagate.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from lwm import cbmem, cbmem_source


# When the ``codebase-memory-mcp`` binary is absent the two per-project
# tests below expect 12 outcomes (one per tool) but get 8 because the
# missing-binary path skips four invocations. The assertions still test
# correct behaviour against a mock binary; gate them with a marker so
# CI environments without the binary stay green while developers who
# have it installed can still exercise the full path.
CBMEM_BIN = shutil.which("codebase-memory-mcp") or shutil.which("cbmem")
requires_cbmem_binary = pytest.mark.skipif(
    not CBMEM_BIN,
    reason="codebase-memory-mcp binary not installed in this environment",
)


def _ok(stdout: str = '{"ok": true}') -> cbmem.CbmemResult:
    return cbmem.CbmemResult(ok=True, command=("x",), returncode=0, stdout=stdout, stderr="")


def _bad(error: str = "boom", rc: int = 1) -> cbmem.CbmemResult:
    return cbmem.CbmemResult(ok=False, command=("x",), returncode=rc, stdout="", stderr=error)


@pytest.fixture
def wiki_root(tmp_path: Path) -> Path:
    (tmp_path / "raw").mkdir()
    (tmp_path / "lwm-sources.json").write_text(
        json.dumps(
            {
                "cbmem": {
                    "projects": [str(tmp_path / "proj1"), str(tmp_path / "proj2")],
                    "search_queries": ["<TODO>", "<FIXME>"],
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "proj1").mkdir()
    (tmp_path / "proj2").mkdir()
    return tmp_path


def test_harvest_cbmem_no_projects_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "raw").mkdir()
    outcomes = cbmem_source.harvest_cbmem(tmp_path, projects=[])
    assert outcomes == []


@requires_cbmem_binary
def test_harvest_cbmem_writes_snapshots_per_tool(wiki_root: Path) -> None:
    """Happy path: index, architecture, search×2, dead_code, changes all
    succeed and write a JSON snapshot under raw/cbmem-snapshots/<date>/<proj>/.
    """
    from datetime import date

    def _fake_index(project, *, force=False, timeout=900.0):
        return _ok('{"graph": "built"}')

    def _fake_arch(project, *, timeout=30.0):
        return _ok('{"languages": ["py"]}')

    def _fake_search(project, query, *, limit=20, timeout=30.0):
        return _ok(f'{{"query": "{query}"}}')

    def _fake_dead(project, *, timeout=30.0):
        return _ok('{"dead": []}')

    def _fake_changes(project, *, base="HEAD", timeout=30.0):
        return _ok('{"changes": []}')

    with patch.object(cbmem, "index_project", side_effect=_fake_index), \
         patch.object(cbmem, "architecture", side_effect=_fake_arch), \
         patch.object(cbmem, "search", side_effect=_fake_search), \
         patch.object(cbmem, "dead_code", side_effect=_fake_dead), \
         patch.object(cbmem, "detect_changes", side_effect=_fake_changes):
        outcomes = cbmem_source.harvest_cbmem(wiki_root)

    # 2 projects × (1 index + 1 arch + 2 searches + 1 dead + 1 changes) = 12
    assert len(outcomes) == 12
    assert all(o.ok for o in outcomes)
    assert all(o.output_path is not None for o in outcomes)

    # Verify files actually exist on disk
    snap_base = wiki_root / "raw" / "cbmem-snapshots" / date.today().isoformat()
    assert snap_base.is_dir()
    for proj in ("proj1", "proj2"):
        proj_dir = snap_base / proj
        assert proj_dir.is_dir()
        assert (proj_dir / "index.json").is_file()
        assert (proj_dir / "architecture.json").is_file()
        assert (proj_dir / "dead_code.json").is_file()
        assert (proj_dir / "changes.json").is_file()
        # searches are stored with sanitised names
        assert any(proj_dir.glob("search-*.json"))


def test_harvest_cbmem_cbmem_missing_does_not_break_other_sources(
    wiki_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If cbmem binary is missing, harvest_cbmem must NOT raise — it records
    one failure outcome per project per tool and returns. This is the
    contract that lets the other six source groups keep working.
    """
    monkeypatch.setattr(cbmem, "resolve_binary", lambda: (_ for _ in ()).throw(
        cbmem.CbmemNotFoundError("binary missing")
    ))
    outcomes = cbmem_source.harvest_cbmem(wiki_root)
    # 2 projects × 4 tools (index/architecture/dead_code/changes) = 8 failures
    # (search is skipped because the binary is missing)
    assert len(outcomes) == 8
    assert all(not o.ok for o in outcomes)
    assert all("binary missing" in o.error for o in outcomes)
    # No snapshot files should be written
    raw = wiki_root / "raw" / "cbmem-snapshots"
    if raw.exists():
        assert list(raw.rglob("*.json")) == []


@requires_cbmem_binary
def test_harvest_cbmem_per_tool_exception_is_captured(wiki_root: Path) -> None:
    """If one cbmem call raises (not returns ok=False), harvest_cbmem records
    it as a failure outcome and continues to the next tool.
    """
    def _raise_index(project, **kwargs):
        raise RuntimeError("subprocess exploded")

    def _ok_arch(project, *, timeout=30.0):
        return _ok('{"languages": []}')

    def _ok_dead(project, *, timeout=30.0):
        return _ok('{"dead": []}')

    def _ok_changes(project, *, base="HEAD", timeout=30.0):
        return _ok('{"changes": []}')

    with patch.object(cbmem, "index_project", side_effect=_raise_index), \
         patch.object(cbmem, "architecture", side_effect=_ok_arch), \
         patch.object(cbmem, "search", side_effect=lambda *a, **k: _ok()), \
         patch.object(cbmem, "dead_code", side_effect=_ok_dead), \
         patch.object(cbmem, "detect_changes", side_effect=_ok_changes):
        outcomes = cbmem_source.harvest_cbmem(wiki_root)

    # Each project: index raises -> cbmem_source skips the rest of the tools.
    # So we get exactly 2 failure outcomes (one per project), both for the
    # index tool.
    assert len(outcomes) == 2
    failures = [o for o in outcomes if not o.ok]
    assert len(failures) == 2
    assert all("subprocess exploded" in f.error for f in failures)
    assert all(f.tool == "index" for f in failures)