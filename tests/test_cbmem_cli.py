"""End-to-end CLI tests for ``lwm cbmem *`` — drives Typer's CliRunner.

We patch ``lwm.cli.lwm_cbmem`` (the alias) so no real subprocess is ever
spawned. The point of this file is to lock the user-visible contract:
exit codes, stderr hints, the ``is_indexed`` short-circuit, and the
mapping from subcommand name to module function.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from lwm import cbmem as cbmem_mod
from lwm.cli import app

runner = CliRunner()


def _make_cbmem_callable(return_value):
    """Return a plain callable that returns ``return_value`` regardless of args."""
    def _f(*args, **kwargs):
        return return_value
    return _f


@pytest.fixture
def stub_cbmem(monkeypatch: pytest.MonkeyPatch):
    """Replace the ``lwm_cbmem`` import inside ``lwm.cli`` with a
    SimpleNamespace holding plain callables for every public function. Using
    SimpleNamespace (not MagicMock) avoids auto-spec quirks where MagicMock
    would refuse to accept positional args that don't match the real
    function's signature.
    """
    ok = cbmem_mod.CbmemResult(ok=True, command=("x",), returncode=0, stdout="ok", stderr="")
    stub = SimpleNamespace(
        CbmemNotFoundError=cbmem_mod.CbmemNotFoundError,
        CbmemResult=cbmem_mod.CbmemResult,
        doctor=_make_cbmem_callable(ok),
        index_project=_make_cbmem_callable(ok),
        index_status=_make_cbmem_callable(ok),
        search=_make_cbmem_callable(ok),
        architecture=_make_cbmem_callable(ok),
        trace_path=_make_cbmem_callable(ok),
        detect_changes=_make_cbmem_callable(ok),
        dead_code=_make_cbmem_callable(ok),
        semantic_search=_make_cbmem_callable(ok),
        is_indexed=_make_cbmem_callable(True),
        render_doctor_report=_make_cbmem_callable("[cbmem doctor] OK"),
        render_index_report=_make_cbmem_callable("[cbmem index] indexed"),
        render_search_report=_make_cbmem_callable("[cbmem search] 'x':"),
        render_architecture_report=_make_cbmem_callable("arch"),
        render_trace_report=_make_cbmem_callable("trace"),
        render_changes_report=_make_cbmem_callable("changes"),
        render_dead_code_report=_make_cbmem_callable("dead"),
        render_query_report=_make_cbmem_callable("{}"),
    )
    monkeypatch.setattr("lwm.cli.lwm_cbmem", stub)
    return stub


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    p.mkdir()
    return p


# ---------- doctor ---------------------------------------------------------


def test_doctor_ok_exits_zero(stub_cbmem) -> None:
    r = runner.invoke(app, ["cbmem", "doctor"])
    assert r.exit_code == 0, r.output
    assert "[cbmem doctor] OK" in r.output


def test_doctor_missing_binary_exits_one_with_hint(
    stub_cbmem, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*a, **k):
        raise cbmem_mod.CbmemNotFoundError("nope")
    stub_cbmem.doctor = _raise
    r = runner.invoke(app, ["cbmem", "doctor"])
    assert r.exit_code == 1
    assert "nope" in r.output


# ---------- index ----------------------------------------------------------


def test_index_ok_passes_force_flag(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "index", str(project), "--force"])
    assert r.exit_code == 0, r.output


def test_index_missing_binary_exits_one(stub_cbmem, project: Path) -> None:
    def _raise(*a, **k):
        raise cbmem_mod.CbmemNotFoundError("nope")
    stub_cbmem.index_project = _raise
    r = runner.invoke(app, ["cbmem", "index", str(project)])
    assert r.exit_code == 1


def test_index_status_ok_runs(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "index-status", str(project)])
    assert r.exit_code == 0, r.output


# ---------- graph-dependent commands: is_indexed short-circuit -------------


@pytest.mark.parametrize(
    "sub, extra",
    [
        ("search",      ["foo"]),
        ("architecture", []),
        ("trace",       ["foo"]),
        ("changes",     []),
        ("dead",        []),
        ("query",       ["MATCH (n) RETURN n"]),
        ("semantic",    ["near-cache"]),
    ],
)
def test_graph_subcommand_exits_two_when_not_indexed(
    sub: str, extra: list[str], stub_cbmem, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_cbmem.is_indexed = lambda *a, **k: False
    r = runner.invoke(app, ["cbmem", sub, str(project), *extra])
    assert r.exit_code == 2, r.output
    assert ".codebase-memory/graph.db.zst" in r.output
    assert "lwm cbmem index" in r.output


# ---------- per-subcommand happy paths -------------------------------------


def test_search_ok_runs(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "search", str(project), "foo", "--limit", "5"])
    assert r.exit_code == 0, r.output


def test_architecture_ok_runs(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "architecture", str(project)])
    assert r.exit_code == 0, r.output


def test_trace_ok_passes_depth(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "trace", str(project), "foo", "--depth", "2"])
    assert r.exit_code == 0, r.output


def test_changes_ok_passes_base(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "changes", str(project), "--base", "main"])
    assert r.exit_code == 0, r.output


def test_dead_ok_runs(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "dead", str(project)])
    assert r.exit_code == 0, r.output


def test_query_ok_runs(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "query", str(project), "MATCH (n) RETURN n"])
    assert r.exit_code == 0, r.output


def test_query_empty_cypher_exits_two_with_hint(
    stub_cbmem: MagicMock, project: Path
) -> None:
    r = runner.invoke(app, ["cbmem", "query", str(project), ""])
    assert r.exit_code == 2, r.output
    assert "Cypher / search string must be non-empty" in r.output


def test_semantic_ok_passes_limit(stub_cbmem, project: Path) -> None:
    r = runner.invoke(app, ["cbmem", "semantic", str(project), "near-cache", "--limit", "3"])
    assert r.exit_code == 0, r.output
