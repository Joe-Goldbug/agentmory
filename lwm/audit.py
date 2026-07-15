"""Unified audit runner for wiki health checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lwm.analysis import analyze_wiki
from lwm.eval import run_eval
from lwm.review import build_review_report
from lwm.schema import validate_schema


@dataclass(frozen=True)
class AuditReport:
    root: Path
    analysis_errors: int
    schema_issues: int
    review_items: int
    eval_pass: int
    eval_total: int
    cbmem_indexed: int = 0
    cbmem_projects_total: int = 0

    @property
    def sections(self) -> tuple["AuditSection", ...]:
        """Read-only summary view used by :mod:`lwm.health`."""

        return (
            AuditSection(name="analyze", issues=self.analysis_errors),
            AuditSection(name="schema", issues=self.schema_issues),
            AuditSection(name="review", issues=self.review_items),
        )

    @property
    def ok(self) -> bool:
        eval_ok = self.eval_total == 0 or self.eval_pass == self.eval_total
        return (
            self.analysis_errors == 0
            and self.schema_issues == 0
            and self.review_items == 0
            and eval_ok
        )


@dataclass(frozen=True)
class AuditSection:
    name: str
    issues: int


def _check_cbmem_indexed(root: Path) -> tuple[int, int]:
    """Return (indexed_count, projects_total). Reads ``lwm-sources.json::cbmem.projects``
    and counts how many of those paths have a ``.codebase-memory/graph.db.zst`` artifact.

    Audit is a status report — never raises. Returns ``(0, 0)`` if the
    config file is missing or malformed.
    """
    path = root / "lwm-sources.json"
    if not path.is_file():
        return (0, 0)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return (0, 0)
    cbmem_block = payload.get("cbmem")
    if not isinstance(cbmem_block, dict):
        return (0, 0)
    projects = cbmem_block.get("projects", [])
    if not isinstance(projects, list):
        return (0, 0)
    indexed = 0
    for p in projects:
        if not isinstance(p, str) or not p.strip():
            continue
        artifact = Path(p) / ".codebase-memory" / "graph.db.zst"
        if artifact.is_file():
            indexed += 1
    return (indexed, len([p for p in projects if isinstance(p, str) and p.strip()]))


def run_audit(root: Path, *, eval_suite: Path | None = None, eval_mode: str = "standard") -> AuditReport:
    root = root.resolve()
    analysis = analyze_wiki(root)
    schema = validate_schema(root)
    review = build_review_report(root)

    eval_pass = 0
    eval_total = 0
    if eval_suite is not None and eval_suite.is_file():
        eval_report = run_eval(root, eval_suite, mode=eval_mode, limit=3)
        eval_pass = eval_report.pass_count
        eval_total = eval_report.total

    cbmem_indexed, cbmem_total = _check_cbmem_indexed(root)

    return AuditReport(
        root=root,
        analysis_errors=len(analysis.errors),
        schema_issues=len(schema.issues),
        review_items=len(review.items),
        eval_pass=eval_pass,
        eval_total=eval_total,
        cbmem_indexed=cbmem_indexed,
        cbmem_projects_total=cbmem_total,
    )


def render_audit_report(report: AuditReport) -> str:
    lines = [
        f"# Audit Report — {report.root.name}",
        "",
        f"- Analyze errors: {report.analysis_errors}",
        f"- Schema issues: {report.schema_issues}",
        f"- Review queue items: {report.review_items}",
        f"- Eval: {report.eval_pass}/{report.eval_total}" if report.eval_total else "- Eval: skipped",
        f"- CBMEM: {report.cbmem_indexed}/{report.cbmem_projects_total} projects indexed",
        "",
        f"Status: {'OK' if report.ok else 'FAILED'}",
    ]
    return "\n".join(lines)
