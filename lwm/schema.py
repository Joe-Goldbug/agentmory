"""Controlled schema checks for wiki pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lwm.analysis import collect_wiki_pages


REQUIRED_KEYS: tuple[str, ...] = (
    "title",
    "type",
    "tags",
    "sources",
    "updated",
)

ALLOWED_TYPES: frozenset[str] = frozenset(
    {
        "purpose",
        "overview",
        "summary",
        "concept",
        "entity",
        "insight",
        "project",
        "decision",
        "pattern",
        "conflict",
        "question",
        "principle",
        "preference",
        "review",
        "unified-memory",
    }
)

SCHEMA_EXEMPT_PAGES: frozenset[str] = frozenset(
    {
        "wiki/index.md",
        "wiki/log.md",
    }
)


@dataclass(frozen=True)
class SchemaIssue:
    rel_path: str
    message: str


@dataclass(frozen=True)
class SchemaReport:
    root: Path
    checked_pages: int
    issues: tuple[SchemaIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def _frontmatter_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return ""
    return text[4:end]


def _has_key(frontmatter: str, key: str) -> bool:
    prefix = f"{key}:"
    for line in frontmatter.splitlines():
        if line.strip().startswith(prefix):
            return True
    return False


def validate_schema(root: Path) -> SchemaReport:
    root = root.resolve()
    pages = collect_wiki_pages(root)
    issues: list[SchemaIssue] = []
    for page in pages:
        if page.rel_path in SCHEMA_EXEMPT_PAGES:
            continue
        fm = _frontmatter_text(page.path)
        if not fm:
            issues.append(SchemaIssue(page.rel_path, "Missing YAML frontmatter."))
            continue
        for key in REQUIRED_KEYS:
            if not _has_key(fm, key):
                issues.append(SchemaIssue(page.rel_path, f"Missing frontmatter key: {key}"))
        if page.page_type not in ALLOWED_TYPES:
            issues.append(
                SchemaIssue(
                    page.rel_path,
                    f"Unknown page type: {page.page_type} (allowed: {', '.join(sorted(ALLOWED_TYPES))})",
                )
            )
        if not page.tags:
            issues.append(SchemaIssue(page.rel_path, "Empty tags list."))
    return SchemaReport(root=root, checked_pages=len(pages), issues=tuple(issues))


def render_schema_report(report: SchemaReport) -> str:
    lines = [
        f"# Schema Check — {report.root.name}",
        "",
        f"- Checked pages: {report.checked_pages}",
        f"- Issues: {len(report.issues)}",
        "",
    ]
    if not report.issues:
        lines.append("Schema OK.")
        return "\n".join(lines)

    lines.append("## Issues")
    for issue in report.issues:
        lines.append(f"- {issue.rel_path}: {issue.message}")
    return "\n".join(lines)
