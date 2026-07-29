"""AI-consumable exports for the wiki."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lwm.analysis import WikiPage, collect_wiki_pages


@dataclass(frozen=True)
class ExportReport:
    root: Path
    llms_txt: Path
    llms_full_txt: Path
    llms_json: Path
    pages: int


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
        if match:
            return text[match.end() :]
    return text


def _summary_line(text: str) -> str:
    body = _strip_frontmatter(text)
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        return line if len(line) <= 160 else line[:157].rstrip() + "..."
    return ""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _page_block(root: Path, page_path: Path, page: WikiPage) -> str:
    text = _read_text(page_path)
    rel = page_path.relative_to(root).as_posix()
    summary = _summary_line(text)
    return f"""===== {rel} =====
Title: {page.title}
Type: {page.page_type}
Tags: {", ".join(page.tags)}
Sources: {", ".join(page.sources)}
Summary: {summary}

{text.rstrip()}
"""


def write_ai_exports(root: Path) -> ExportReport:
    root = root.resolve()
    pages = tuple(
        page
        for page in collect_wiki_pages(root)
        if not any(
            part in {"insights", "review", "summaries"}
            for part in page.path.relative_to(root / "wiki").parts
        )
    )
    llms_txt_path = root / "llms.txt"
    llms_full_path = root / "llms-full.txt"
    llms_json_path = root / "llms.json"
    today = date.today().isoformat()

    page_rows = []
    full_blocks = []
    manifest_pages = []
    for page in pages:
        text = _read_text(page.path)
        summary = _summary_line(text)
        page_rows.append(
            f"- {page.rel_path} | {page.title} | {page.page_type} | {summary or 'No summary available.'}"
        )
        full_blocks.append(_page_block(root, page.path, page))
        manifest_pages.append(
            {
                "rel_path": page.rel_path,
                "slug": page.slug,
                "title": page.title,
                "type": page.page_type,
                "tags": list(page.tags),
                "sources": list(page.sources),
                "outbound_links": list(page.outbound_links),
            }
        )

    purpose_path = root / "wiki" / "purpose.md"
    overview_path = root / "wiki" / "overview.md"
    purpose = _read_text(purpose_path) if purpose_path.is_file() else ""
    overview = _read_text(overview_path) if overview_path.is_file() else ""

    llms_txt = f"""# LLM-WorkMem Export — {root.name}

Generated: {today}

## Purpose

{_summary_line(purpose) if purpose else "No purpose page found."}

## Overview

{_summary_line(overview) if overview else "No overview page found."}

## Pages

{chr(10).join(page_rows) if page_rows else "- No wiki pages found."}
"""

    llms_full = "\n\n".join(full_blocks) if full_blocks else "# No wiki pages found."

    manifest = {
        "root": str(root),
        "generated_at": today,
        "page_count": len(manifest_pages),
        "pages": manifest_pages,
    }

    llms_txt_path.write_text(llms_txt.rstrip() + "\n", encoding="utf-8")
    llms_full_path.write_text(llms_full.rstrip() + "\n", encoding="utf-8")
    llms_json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return ExportReport(
        root=root,
        llms_txt=llms_txt_path,
        llms_full_txt=llms_full_path,
        llms_json=llms_json_path,
        pages=len(manifest_pages),
    )


def render_export_report(report: ExportReport) -> str:
    lines = [
        f"# Export Report — {report.root.name}",
        "",
        f"- Pages exported: {report.pages}",
        f"- `llms.txt`: {report.llms_txt}",
        f"- `llms-full.txt`: {report.llms_full_txt}",
        f"- `llms.json`: {report.llms_json}",
    ]
    return "\n".join(lines)
