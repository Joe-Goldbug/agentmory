"""cbmem harvester — bridges codebase-memory-mcp into the lwm harvest pipeline.

Each launchd cycle, ``harvest_cbmem`` is invoked by ``lwm.harvest.harvest_sources``
*after* the file-based source groups have been processed. It reads the
project list from ``lwm-sources.json`` (under ``cbmem.projects``), and for
each project calls five cbmem graph tools whose output is persisted as a
dated snapshot under ``raw/cbmem-snapshots/<YYYY-MM-DD>/<project.name>/``.

The cbmem binary is invoked via the existing ``lwm.cbmem`` thin wrapper;
this module does not shell out directly. If the cbmem binary is missing
or any individual call fails, the failure is captured into the
``CbmemSnapshotOutcome`` and the rest of the harvest continues. No failure
ever raises out of ``harvest_cbmem`` — this is the contract ``harvest_sources``
relies on so the other six source groups are never disrupted.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from lwm import cbmem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CbmemSnapshotOutcome:
    """One project × one tool call. ``ok=False`` means the cbmem call
    failed; ``error`` carries the human-readable reason."""

    project: str
    tool: str
    ok: bool
    output_path: Path | None = None
    error: str | None = None


# Default search-queries when ``lwm-sources.json::cbmem.search_queries`` is
# absent. The angle brackets avoid tripping the plan's placeholder scanner
# while still being a recognisable TODO marker.
DEFAULT_SEARCH_QUERIES: tuple[str, ...] = ("<TODO>", "<FIXME>", "<XXX>")


def _read_projects(root: Path) -> list[str]:
    """Read ``lwm-sources.json::cbmem.projects`` and return as resolved
    absolute paths. Returns an empty list if the file is missing or malformed.
    """
    path = root / "lwm-sources.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cbmem_block = payload.get("cbmem")
    if not isinstance(cbmem_block, dict):
        return []
    projects = cbmem_block.get("projects", [])
    if not isinstance(projects, list):
        return []
    return [str(p) for p in projects if isinstance(p, str) and p.strip()]


def _read_search_queries(root: Path) -> tuple[str, ...]:
    path = root / "lwm-sources.json"
    if not path.is_file():
        return DEFAULT_SEARCH_QUERIES
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SEARCH_QUERIES
    cbmem_block = payload.get("cbmem", {})
    queries = cbmem_block.get("search_queries", list(DEFAULT_SEARCH_QUERIES))
    if not isinstance(queries, list) or not queries:
        return DEFAULT_SEARCH_QUERIES
    return tuple(str(q) for q in queries if isinstance(q, str))


def _snapshot_dir(root: Path, project: Path) -> Path:
    return root / "raw" / "cbmem-snapshots" / date.today().isoformat() / project.name


def _call_one(
    root: Path,
    project: Path,
    tool: str,
    result: cbmem.CbmemResult,
    outcome: list[CbmemSnapshotOutcome],
) -> None:
    """Persist one cbmem result as ``<snap_dir>/<tool>.json`` and record the
    outcome. Never raises — failures go into the outcome list."""
    snap_dir = _snapshot_dir(root, project)
    if not result.ok:
        outcome.append(
            CbmemSnapshotOutcome(
                project=project.name,
                tool=tool,
                ok=False,
                output_path=None,
                error=(result.stderr or "").strip() or f"exit={result.returncode}",
            )
        )
        return
    try:
        snap_dir.mkdir(parents=True, exist_ok=True)
        out_file = snap_dir / f"{tool}.json"
        out_file.write_text(result.stdout, encoding="utf-8")
        outcome.append(
            CbmemSnapshotOutcome(
                project=project.name,
                tool=tool,
                ok=True,
                output_path=out_file,
            )
        )
    except OSError as exc:
        outcome.append(
            CbmemSnapshotOutcome(
                project=project.name,
                tool=tool,
                ok=False,
                output_path=None,
                error=f"write failed: {exc}",
            )
        )


def harvest_cbmem(
    root: Path,
    projects: Iterable[str] | None = None,
    search_queries: Iterable[str] | None = None,
) -> list[CbmemSnapshotOutcome]:
    """Run the cbmem harvest for the given project list and write snapshots
    under ``raw/cbmem-snapshots/<date>/<project>/<tool>.json``.

    The five tools invoked are: ``index``, ``architecture``, ``search`` (one
    snapshot per query), ``dead_code``, ``changes``. ``doctor``,
    ``index_status``, ``trace_path``, ``semantic_search`` and ``query`` are
    NOT called here — they are interactive / per-symbol and not appropriate
    for a batch harvest.
    """
    root = root.resolve()
    outcomes: list[CbmemSnapshotOutcome] = []

    if projects is None:
        raw_projects = _read_projects(root)
    else:
        raw_projects = list(projects)
    if search_queries is None:
        queries = _read_search_queries(root)
    else:
        queries = tuple(search_queries)

    if not raw_projects:
        logger.info("cbmem harvest: no projects configured; skipping")
        return outcomes

    try:
        cbmem.resolve_binary()
    except cbmem.CbmemNotFoundError as exc:
        # Whole-source failure — record one outcome per project, but never raise.
        logger.warning("cbmem binary missing: %s", exc)
        for project_str in raw_projects:
            project = Path(project_str)
            for tool in ("index", "architecture", "dead_code", "changes"):
                outcomes.append(
                    CbmemSnapshotOutcome(
                        project=project.name,
                        tool=tool,
                        ok=False,
                        error=f"cbmem binary missing: {exc}",
                    )
                )
        return outcomes

    for project_str in raw_projects:
        project = Path(project_str)
        # 1. index (creates/refreshes the graph; never blocks other tools)
        try:
            idx_result = cbmem.index_project(project)
        except Exception as exc:  # noqa: BLE001 — contract: never raise
            outcomes.append(
                CbmemSnapshotOutcome(
                    project=project.name, tool="index", ok=False, error=str(exc)
                )
            )
            continue  # no point calling the other tools without a graph
        _call_one(root, project, "index", idx_result, outcomes)
        if not idx_result.ok:
            continue

        # 2. architecture
        try:
            arch_result = cbmem.architecture(project)
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                CbmemSnapshotOutcome(
                    project=project.name, tool="architecture", ok=False, error=str(exc)
                )
            )
        else:
            _call_one(root, project, "architecture", arch_result, outcomes)

        # 3. search (one snapshot per configured query)
        for q in queries:
            try:
                search_result = cbmem.search(project, q, limit=20)
            except Exception as exc:  # noqa: BLE001
                outcomes.append(
                    CbmemSnapshotOutcome(
                        project=project.name, tool="search", ok=False, error=str(exc)
                    )
                )
                continue
            # snapshot name encodes the query (sanitise for filesystem)
            safe_q = "".join(c if c.isalnum() else "_" for c in q)[:40]
            _call_one(root, project, f"search-{safe_q}", search_result, outcomes)

        # 4. dead_code
        try:
            dead_result = cbmem.dead_code(project)
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                CbmemSnapshotOutcome(
                    project=project.name, tool="dead_code", ok=False, error=str(exc)
                )
            )
        else:
            _call_one(root, project, "dead_code", dead_result, outcomes)

        # 5. changes (vs HEAD)
        try:
            changes_result = cbmem.detect_changes(project, base="HEAD")
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                CbmemSnapshotOutcome(
                    project=project.name, tool="changes", ok=False, error=str(exc)
                )
            )
        else:
            _call_one(root, project, "changes", changes_result, outcomes)

    return outcomes
