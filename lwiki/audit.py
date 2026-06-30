"""Unified audit runner for wiki health checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lwiki.analysis import analyze_wiki
from lwiki.eval import run_eval
from lwiki.review import build_review_report
from lwiki.schema import validate_schema


@dataclass(frozen=True)
class AuditReport:
    root: Path
    analysis_errors: int
    schema_issues: int
    review_items: int
    eval_pass: int
    eval_total: int

    @property
    def ok(self) -> bool:
        eval_ok = self.eval_total == 0 or self.eval_pass == self.eval_total
        return (
            self.analysis_errors == 0
            and self.schema_issues == 0
            and self.review_items == 0
            and eval_ok
        )


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

    return AuditReport(
        root=root,
        analysis_errors=len(analysis.errors),
        schema_issues=len(schema.issues),
        review_items=len(review.items),
        eval_pass=eval_pass,
        eval_total=eval_total,
    )


def render_audit_report(report: AuditReport) -> str:
    lines = [
        f"# Audit Report — {report.root.name}",
        "",
        f"- Analyze errors: {report.analysis_errors}",
        f"- Schema issues: {report.schema_issues}",
        f"- Review queue items: {report.review_items}",
        f"- Eval: {report.eval_pass}/{report.eval_total}" if report.eval_total else "- Eval: skipped",
        "",
        f"Status: {'OK' if report.ok else 'FAILED'}",
    ]
    return "\n".join(lines)
