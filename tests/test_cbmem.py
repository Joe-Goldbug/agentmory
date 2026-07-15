"""Unit tests for ``lwm.cbmem`` — argv shape and error paths, no real binary."""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lwm import cbmem


# ---------- resolve_binary -------------------------------------------------


def test_resolve_binary_honors_lbm_cbmem_env(stub_cbmem_binary: Path) -> None:
    assert cbmem.resolve_binary() == str(stub_cbmem_binary.resolve())


def test_resolve_binary_raises_when_env_points_to_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LBM_CBMEM_BIN", str(tmp_path / "does-not-exist"))
    with pytest.raises(cbmem.CbmemNotFoundError):
        cbmem.resolve_binary()


def test_resolve_binary_falls_back_to_lbm_bin_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "tools"
    bin_dir.mkdir()
    target = bin_dir / "codebase-memory-mcp"
    target.write_text("#!/bin/sh\n")
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("LBM_BIN_DIR", str(bin_dir))
    monkeypatch.delenv("LBM_CBMEM_BIN", raising=False)
    assert cbmem.resolve_binary() == str(target.resolve())


def test_resolve_binary_falls_back_to_home_bin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home_bin = tmp_path / "bin"
    home_bin.mkdir()
    target = home_bin / "codebase-memory-mcp"
    target.write_text("#!/bin/sh\n")
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    monkeypatch.delenv("LBM_CBMEM_BIN", raising=False)
    monkeypatch.delenv("LBM_BIN_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cbmem.resolve_binary() == str(target.resolve())


def test_resolve_binary_resolves_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import stat as _st
    home_bin = tmp_path / "bin"
    home_bin.mkdir()
    real = home_bin / "codebase-memory-mcp"
    real.write_text("#!/bin/sh\n")
    real.chmod(real.stat().st_mode | _st.S_IEXEC)
    link = home_bin / "cbmem"
    link.symlink_to(real)
    monkeypatch.delenv("LBM_CBMEM_BIN", raising=False)
    monkeypatch.delenv("LBM_BIN_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cbmem.resolve_binary() == str(real.resolve())


def test_resolve_binary_raises_when_nothing_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LBM_CBMEM_BIN", raising=False)
    monkeypatch.delenv("LBM_BIN_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    with pytest.raises(cbmem.CbmemNotFoundError) as exc:
        cbmem.resolve_binary()
    assert "Could not find" in str(exc.value)


# ---------- _run argv shape ------------------------------------------------


def _ok_proc(stdout: str = "{}", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = 0
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_run_uses_cli_json_wrapper(stub_cbmem_binary: Path) -> None:
    with patch("lwm.cbmem.subprocess.run", return_value=_ok_proc()) as pr:
        cbmem._run(str(stub_cbmem_binary), "indexed", {"path": "."})  # noqa: SLF001
    cmd = pr.call_args.args[0]
    assert cmd[:3] == (str(stub_cbmem_binary), "cli", "--json")
    assert cmd[3] == "indexed"
    assert json.loads(cmd[4]) == {"path": "."}


def test_run_as_json_false_omits_flag(stub_cbmem_binary: Path) -> None:
    with patch("lwm.cbmem.subprocess.run", return_value=_ok_proc()) as pr:
        cbmem._run(str(stub_cbmem_binary), "indexed", {"path": "."}, as_json=False)  # noqa: SLF001
    cmd = pr.call_args.args[0]
    assert cmd == (str(stub_cbmem_binary), "cli", "indexed", '{"path": "."}')


def test_run_timeout_returns_normalised_result(stub_cbmem_binary: Path) -> None:
    exc = subprocess.TimeoutExpired(cmd=["x"], timeout=0.1, output=b"partial", stderr=b"oops")
    with patch("lwm.cbmem.subprocess.run", side_effect=exc):
        r = cbmem._run(str(stub_cbmem_binary), "search", {"path": ".", "query": "x"})  # noqa: SLF001
    assert r.ok is False
    assert r.returncode == 124
    assert "partial" in r.stdout
    assert "oops" in r.stderr


# ---------- per-function argv contract --------------------------------------


@pytest.fixture
def patched_run():
    captured = []

    def _runner(cmd, **kwargs):
        captured.append((cmd, kwargs))
        return _ok_proc(stdout='{"ok": true}')

    with patch("lwm.cbmem.subprocess.run", side_effect=_runner) as pr:
        yield pr, captured


def test_doctor_calls_version(stub_cbmem_binary: Path, patched_run) -> None:
    pr, calls = patched_run
    cbmem.doctor()
    cmd = calls[0][0]
    assert cmd[1:] == ("--version",)


def test_index_project_uses_index_repository_tool(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.index_project(tmp_path, force=True)
    cmd = calls[0][0]
    assert cmd[3] == "index_repository"
    payload = json.loads(cmd[4])
    assert payload["repo_path"] == str(tmp_path.resolve())
    assert payload["persistence"] is True
    assert payload["force"] is True
    assert calls[0][1]["cwd"] == str(tmp_path.resolve())


def test_index_status_passes_path_only(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.index_status(tmp_path)
    cmd = calls[0][0]
    assert cmd[3] == "index_status"
    assert json.loads(cmd[4]) == {"project": str(tmp_path.resolve())}


def test_search_rejects_empty_query(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        cbmem.search(tmp_path, "")


def test_search_passes_query_and_limit(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.search(tmp_path, "foo", limit=7)
    cmd = calls[0][0]
    assert cmd[3] == "search_graph"
    payload = json.loads(cmd[4])
    assert payload == {"project": str(tmp_path.resolve()), "query": "foo", "limit": 7}


def test_architecture_uses_get_architecture_tool(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.architecture(tmp_path)
    cmd = calls[0][0]
    assert cmd[3] == "get_architecture"
    assert json.loads(cmd[4]) == {"project": str(tmp_path.resolve())}


def test_trace_path_passes_symbol_and_depth(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.trace_path(tmp_path, "run_query", depth=2)
    cmd = calls[0][0]
    assert cmd[3] == "trace_path"
    assert json.loads(cmd[4]) == {
        "project": str(tmp_path.resolve()),
        "symbol": "run_query",
        "depth": 2,
    }


def test_detect_changes_default_base_is_head(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.detect_changes(tmp_path)
    cmd = calls[0][0]
    assert cmd[3] == "detect_changes"
    assert json.loads(cmd[4])["base"] == "HEAD"


def test_detect_changes_custom_base(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.detect_changes(tmp_path, base="main")
    assert json.loads(calls[0][0][4])["base"] == "main"


def test_dead_code_uses_dead_code_tool(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.dead_code(tmp_path)
    cmd = calls[0][0]
    assert cmd[3] == "dead_code"
    assert json.loads(cmd[4]) == {"project": str(tmp_path.resolve())}


def test_semantic_search_uses_semantic_query_tool(
    tmp_path: Path, stub_cbmem_binary: Path, patched_run
) -> None:
    pr, calls = patched_run
    cbmem.semantic_search(tmp_path, "near-cache", limit=4)
    cmd = calls[0][0]
    assert cmd[3] == "search_graph"
    assert json.loads(cmd[4]) == {
        "project": str(tmp_path.resolve()),
        "semantic_query": ["near-cache"],
        "limit": 4,
    }


# ---------- helpers: is_indexed, graph_db_path, CbmemResult.json ----------


def test_graph_db_path_uses_dot_codebase_memory_dir(tmp_path: Path) -> None:
    p = cbmem.graph_db_path(tmp_path)
    assert p == tmp_path.resolve() / ".codebase-memory" / "graph.db.zst"


def test_is_indexed_false_when_artifact_missing(tmp_path: Path) -> None:
    assert cbmem.is_indexed(tmp_path) is False


def test_is_indexed_true_when_artifact_present(tmp_path: Path) -> None:
    artifact = tmp_path / ".codebase-memory" / "graph.db.zst"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x00")
    assert cbmem.is_indexed(tmp_path) is True


def test_cbmem_result_json_parses_stdout() -> None:
    r = cbmem.CbmemResult(ok=True, command=("x",), returncode=0, stdout='{"a": 1}', stderr="")
    assert r.json() == {"a": 1}


def test_cbmem_result_json_raises_on_empty_stdout() -> None:
    r = cbmem.CbmemResult(ok=False, command=("x",), returncode=1, stdout="", stderr="")
    with pytest.raises(ValueError):
        r.json()


def test_cbmem_result_json_raises_on_invalid_json() -> None:
    r = cbmem.CbmemResult(ok=False, command=("x",), returncode=1, stdout="not json", stderr="")
    with pytest.raises(ValueError):
        r.json()


# ---------- render_*_report pretty-printers -------------------------------


def _result(ok: bool, stdout: str = "", stderr: str = "", rc: int = 0) -> cbmem.CbmemResult:
    return cbmem.CbmemResult(ok=ok, command=("x",), returncode=rc, stdout=stdout, stderr=stderr)


def test_render_doctor_ok_includes_stdout() -> None:
    out = cbmem.render_doctor_report(_result(True, stdout="version 0.8.1"))
    assert "[cbmem doctor] OK" in out
    assert "version 0.8.1" in out


def test_render_doctor_fail_includes_stderr() -> None:
    out = cbmem.render_doctor_report(_result(False, stderr="boom", rc=1))
    assert "FAIL (exit 1)" in out
    assert "boom" in out


def test_render_index_ok_includes_artifact_size(tmp_path: Path) -> None:
    artifact = tmp_path / ".codebase-memory" / "graph.db.zst"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x00" * (3 * 1024 * 1024))
    out = cbmem.render_index_report(tmp_path, _result(True))
    assert "indexed" in out
    assert "3.0 MB" in out


def test_render_index_fail_mentions_dir_and_stderr(tmp_path: Path) -> None:
    out = cbmem.render_index_report(tmp_path, _result(False, stderr="lock held", rc=2))
    assert "FAIL" in out
    assert "lock held" in out


def test_render_search_no_match_returns_explicit_message() -> None:
    out = cbmem.render_search_report("missing", _result(True, stdout=""))
    assert "no matches" in out


def test_render_search_ok_includes_query_and_stdout() -> None:
    out = cbmem.render_search_report("foo", _result(True, stdout="hit-1\nhit-2"))
    assert "'foo'" in out
    assert "hit-1" in out
    assert "hit-2" in out


def test_render_search_truncates_long_output() -> None:
    big = "x" * 5000
    out = cbmem.render_search_report("q", _result(True, stdout=big))
    assert len(out) < 1000


def test_render_architecture_pretty_prints_json() -> None:
    out = cbmem.render_architecture_report(_result(True, stdout='{"a": 1, "b": [1,2]}'))
    assert '"a": 1' in out
    assert '"b": [' in out


def test_render_architecture_empty_returns_marker() -> None:
    assert cbmem.render_architecture_report(_result(True, stdout="")) == "(no output)"


def test_render_trace_no_callers_returns_marker() -> None:
    out = cbmem.render_trace_report("foo", _result(True, stdout=""))
    assert "no callers/callees" in out


def test_render_changes_no_changes_returns_marker() -> None:
    out = cbmem.render_changes_report(_result(True, stdout=""))
    assert "no changes" in out


def test_render_dead_code_no_dead_returns_marker() -> None:
    out = cbmem.render_dead_code_report(_result(True, stdout=""))
    assert "no dead code" in out


def test_render_query_pretty_prints_json() -> None:
    out = cbmem.render_query_report(_result(True, stdout='{"nodes": [{"id": 1}]}'))
    assert '"nodes"' in out
    assert '"id": 1' in out


def test_render_query_empty_returns_marker() -> None:
    assert cbmem.render_query_report(_result(True, stdout="")) == "(empty result set)"


def test_render_query_non_json_returns_raw() -> None:
    out = cbmem.render_query_report(_result(True, stdout="raw text"))
    assert "raw text" in out
