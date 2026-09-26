"""Review queue generation from wiki analysis and schema checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lwm.analysis import analyze_wiki
from lwm.schema import validate_schema


@dataclass(frozen=True)
class ReviewReport:
    root: Path
    items: tuple[str, ...]


def build_review_report(root: Path) -> ReviewReport:
    root = root.resolve()
    analysis = analyze_wiki(root)
    schema = validate_schema(root)
    items: set[str] = set()

    for source, link in analysis.broken_links:
        items.add(f"broken-link | {source} -> [[{link}]]")
    for gap in analysis.source_gaps:
        # Keep the stable ``missing-source`` prefix for compatible consumers,
        # while making the repair boundary explicit to humans and tooling.
        items.add(
            f"missing-source | scope={gap.scope} | {gap.page} -> {gap.source}"
            f" (resolved: {gap.resolved_path})"
        )
    for page in analysis.orphan_pages:
        items.add(f"orphan-page | {page}")
    for slug, paths in analysis.duplicate_slugs:
        items.add(f"duplicate-slug | {slug} -> {', '.join(paths)}")
    for issue in schema.issues:
        items.add(f"schema-issue | {issue.rel_path} -> {issue.message}")

    return ReviewReport(root=root, items=tuple(sorted(items)))


def render_review_report(report: ReviewReport) -> str:
    lines = [
        f"# Review Queue — {report.root.name}",
        "",
        f"- Items: {len(report.items)}",
        "",
    ]
    if not report.items:
        lines.append("No review items.")
        return "\n".join(lines)

    lines.append("## Queue")
    for item in report.items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def write_review_page(root: Path, report: ReviewReport) -> Path:
    today = date.today().isoformat()
    out = root / "wiki" / "review" / f"review-queue-{today}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    body = f"""---
title: Review Queue {today}
type: review
tags: [review, queue, quality]
sources: []
updated: {today}
---

{render_review_report(report)}

## See Also

- [[overview]]
- [[memory-governance]]
"""
    out.write_text(body, encoding="utf-8")
    return out
