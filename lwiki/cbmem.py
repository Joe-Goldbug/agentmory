"""codebase-memory integration for lwiki.

Wraps the ``codebase-memory-mcp`` CLI (DeusData/codebase-memory-mcp) so the
wiki can answer code-structure questions across any project directory the
user points it at. This is a thin shell-out layer with no extra runtime
dependencies — ``codebase-memory-mcp`` itself must be installed on PATH.

Install (one-time, on the user's machine):
    # macOS arm64 (Apple Silicon)
    curl -sSL -o /tmp/cbmem.tar.gz \\
      https://github.com/DeusData/codebase-memory-mcp/releases/download/v0.8.1/codebase-memory-mcp-darwin-arm64.tar.gz
    tar -xzf /tmp/cbmem.tar.gz -C ~/bin/
    rm /tmp/cbmem.tar.gz
    ln -sf ~/bin/codebase-memory-mcp ~/bin/cbmem
    chmod +x ~/bin/codebase-memory-mcp

    # Verify
    cbmem cli indexed '{}'   # returns 0 if binary works

Binary CLI contract (verified by inspecting the binary):
    Usage: codebase-memory-mcp cli [--progress] [--json] <tool_name> [json_args]

Where ``<tool_name>`` is one of:
    indexed, index_status, index_repository, search, search_code,
    search_graph, search_mode, search_prepare, trace_path, trace_call_path,
    get_architecture, detect_changes, dead_code, semantic_query, ...

The ``[json_args]`` is a JSON-encoded object passed as a single argv.

Usage from the wiki:
    lwiki cbmem doctor
    lwiki cbmem index <project-dir>
    lwiki cbmem search <project-dir> <symbol>
    lwiki cbmem architecture <project-dir>
    lwiki cbmem trace <project-dir> <symbol>
    lwiki cbmem dead <project-dir>
    lwiki cbmem graph <project-dir>
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Default binary lookup order: explicit env, then PATH. We accept either the
# long upstream name `codebase-memory-mcp` or the friendly `cbmem` symlink.
_DEFAULT_BINARIES = ("codebase-memory-mcp", "cbmem", "codebase-memory")


@dataclass(frozen=True)
class CbmemResult:
    """Result of a ``codebase-memory-mcp cli <tool>`` invocation."""

    ok: bool
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    def json(self) -> Any:
        """Parse stdout as JSON, or raise ValueError if not JSON."""
        if not self.stdout.strip():
            raise ValueError("cbmem returned empty stdout; cannot parse as JSON")
        return json.loads(self.stdout)


class CbmemNotFoundError(RuntimeError):
    """Raised when no ``codebase-memory-mcp`` binary is found on PATH."""


def resolve_binary() -> str:
    """Find the codebase-memory binary.

    Lookup order:
      1. ``LBM_CBMEM_BIN`` env var (explicit override).
      2. ``$LBM_BIN_DIR`` if set — only ``codebase-memory-mcp``.
      3. ``~/bin/`` — accept any of the default names.
      4. PATH — ``shutil.which`` for each candidate.

    Raises :class:`CbmemNotFoundError` if no binary is found.
    """
    override = os.environ.get("LBM_CBMEM_BIN")
    if override:
        if Path(override).is_file():
            return str(Path(override).resolve())
        raise CbmemNotFoundError(
            f"LBM_CBMEM_BIN points at {override!r} but no file exists there"
        )

    custom_dir = os.environ.get("LBM_BIN_DIR")
    if custom_dir:
        candidate = Path(custom_dir) / "codebase-memory-mcp"
        if candidate.is_file():
            return str(candidate.resolve())

    home_bin = Path.home() / "bin"
    for name in _DEFAULT_BINARIES:
        candidate = home_bin / name
        if candidate.is_file():
            return str(candidate.resolve())

    for name in _DEFAULT_BINARIES:
        found = shutil.which(name)
        if found:
            return found

    raise CbmemNotFoundError(
        "Could not find `codebase-memory-mcp` on PATH. "
        "Install it (see module docstring) or set LBM_CBMEM_BIN."
    )


def _run(
    binary: str,
    tool: str,
    args: dict[str, Any] | None,
    *,
    cwd: Path | None = None,
    timeout: float = 60.0,
    as_json: bool = True,
) -> CbmemResult:
    """Invoke ``codebase-memory-mcp cli [--json] <tool> [json_args]``.

    ``args`` is JSON-encoded and passed as a single argv item. ``as_json``
    toggles the ``--json`` flag on the binary, which makes it emit structured
    JSON instead of pretty text.
    """
    payload = json.dumps(args or {}, ensure_ascii=False)
    cmd: tuple[str, ...] = (binary, "cli")
    if as_json:
        cmd = (*cmd, "--json")
    cmd = (*cmd, tool, payload)

    try:
        proc = subprocess.run(  # noqa: S603 — controlled binary, controlled args
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CbmemNotFoundError(f"Binary {binary!r} disappeared mid-run") from exc
    except subprocess.TimeoutExpired as exc:
        def _as_str(value: object) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value)

        return CbmemResult(
            ok=False,
            command=cmd,
            returncode=124,
            stdout=_as_str(exc.stdout),
            stderr=_as_str(exc.stderr) + f"\n[cbmem] timeout after {timeout}s",
        )

    return CbmemResult(
        ok=proc.returncode == 0,
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def doctor(*, timeout: float = 15.0) -> CbmemResult:
    """Check binary health by asking for the indexed-status of a fake project.

    This works because ``indexed`` only needs a project path; we pass ``.``
    and check whether the binary responds at all.
    """
    binary = resolve_binary()
    return _run(binary, "indexed", {"path": "."}, timeout=timeout)


def index_project(
    project_dir: Path,
    *,
    force: bool = False,
    timeout: float = 900.0,
) -> CbmemResult:
    """Build or refresh the code graph for ``project_dir``."""
    binary = resolve_binary()
    project = project_dir.resolve()
    payload = {"path": str(project), "force": force}
    return _run(binary, "index_repository", payload, cwd=project, timeout=timeout)


def index_status(project_dir: Path, *, timeout: float = 15.0) -> CbmemResult:
    """Return the current indexing status of ``project_dir``."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary, "index_status", {"path": str(project)}, cwd=project, timeout=timeout
    )


def search(
    project_dir: Path,
    query: str,
    *,
    limit: int = 20,
    timeout: float = 30.0,
) -> CbmemResult:
    """Symbol/text search across the indexed graph."""
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary,
        "search",
        {"path": str(project), "query": query, "limit": limit},
        cwd=project,
        timeout=timeout,
    )


def architecture(project_dir: Path, *, timeout: float = 30.0) -> CbmemResult:
    """Architecture summary: languages, packages, entry points, routes."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary, "get_architecture", {"path": str(project)}, cwd=project, timeout=timeout
    )


def trace_path(
    project_dir: Path,
    symbol: str,
    *,
    depth: int = 3,
    timeout: float = 30.0,
) -> CbmemResult:
    """Follow call-graph edges out from ``symbol``."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary,
        "trace_path",
        {"path": str(project), "symbol": symbol, "depth": depth},
        cwd=project,
        timeout=timeout,
    )


def detect_changes(
    project_dir: Path,
    *,
    base: str = "HEAD",
    timeout: float = 60.0,
) -> CbmemResult:
    """Map a git diff to affected symbols."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary,
        "detect_changes",
        {"path": str(project), "base": base},
        cwd=project,
        timeout=timeout,
    )


def dead_code(project_dir: Path, *, timeout: float = 60.0) -> CbmemResult:
    """List symbols with no incoming callers."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary, "dead_code", {"path": str(project)}, cwd=project, timeout=timeout
    )


def semantic_search(
    project_dir: Path,
    query: str,
    *,
    limit: int = 10,
    timeout: float = 30.0,
) -> CbmemResult:
    """Vector search over indexed symbols."""
    binary = resolve_binary()
    project = project_dir.resolve()
    return _run(
        binary,
        "semantic_query",
        {"path": str(project), "query": query, "limit": limit},
        cwd=project,
        timeout=timeout,
    )


def graph_db_path(project_dir: Path) -> Path:
    """Return the on-disk location of the project's code graph artifact."""
    return (project_dir.resolve() / ".codebase-memory" / "graph.db.zst")


def is_indexed(project_dir: Path) -> bool:
    """True iff ``project_dir`` already has a code graph on disk."""
    return graph_db_path(project_dir).is_file()


# --- Pretty printers used by the CLI layer -----------------------------------


def render_doctor_report(result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem doctor] FAIL (exit {result.returncode})\n{result.stderr.strip()}"
        )
    return f"[cbmem doctor] OK\n{result.stdout.strip() or 'binary responded'}"


def render_index_report(project_dir: Path, result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem index] FAIL on {project_dir} (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    artifact = graph_db_path(project_dir)
    lines = [f"[cbmem index] indexed {project_dir}"]
    if artifact.is_file():
        size_mb = artifact.stat().st_size / (1024 * 1024)
        lines.append(f"  artifact: {artifact} ({size_mb:.1f} MB)")
    if result.stdout.strip():
        lines.append(f"  output: {result.stdout.strip()[:200]}")
    return "\n".join(lines)


def render_search_report(query: str, result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem search] FAIL for {query!r} (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    if not result.stdout.strip():
        return f"[cbmem search] no matches for {query!r}"
    return f"[cbmem search] {query!r}:\n{result.stdout.rstrip()[:500]}"


def render_architecture_report(result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem architecture] FAIL (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.rstrip()[:2000] or "(no output)"


def render_trace_report(symbol: str, result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem trace] FAIL for {symbol!r} (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.rstrip()[:1000] or f"(no callers/callees for {symbol!r})"


def render_changes_report(result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem detect-changes] FAIL (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.rstrip() or "(no changes detected)"


def render_dead_code_report(result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem dead-code] FAIL (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.rstrip() or "(no dead code found)"


def render_query_report(result: CbmemResult) -> str:
    if not result.ok:
        return (
            f"[cbmem query] FAIL (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    out = result.stdout.rstrip()
    if not out:
        return "(empty result set)"
    # Pretty-print JSON if it parses, else return raw.
    try:
        return json.dumps(json.loads(out), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return out


__all__ = [
    "CbmemNotFoundError",
    "CbmemResult",
    "resolve_binary",
    "doctor",
    "index_project",
    "index_status",
    "search",
    "architecture",
    "trace_path",
    "detect_changes",
    "dead_code",
    "semantic_search",
    "graph_db_path",
    "is_indexed",
    "render_doctor_report",
    "render_index_report",
    "render_search_report",
    "render_architecture_report",
    "render_trace_report",
    "render_changes_report",
    "render_dead_code_report",
    "render_query_report",
]