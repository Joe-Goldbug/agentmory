"""Deterministic raw-to-summary compilation helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lwm.raw_tracker import scan_directory


IGNORED_PREFIXES = (
    "tool-snapshots/",
    "cbmem-snapshots/",
    # Event JSON is operational queue data. It is consumed by lwm ingest and
    # must never become one generic wiki summary page per event.
    "events/",
)


@dataclass(frozen=True)
class CompileItem:
    raw_rel: str
    page_slug: str
    page_path: Path
    changed: bool


@dataclass(frozen=True)
class CompileReport:
    root: Path
    compiled: tuple[CompileItem, ...]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def _summary_slug(raw_rel: str) -> str:
    base = raw_rel.rsplit(".", 1)[0]
    return f"source-{_slugify(base.replace('/', '-'))}"


def _source_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_excerpt(text: str, limit: int = 10) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if len(line) > 160:
            line = line[:160].rstrip() + "..."
        lines.append((line_no, line))
        if len(lines) >= limit:
            break
    return lines


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _render_summary_page(
    raw_rel: str, source_sha: str, excerpt: list[tuple[int, str]], today: str
) -> str:
    title = f"Source Summary — {raw_rel}"
    bullets = (
        "\n".join(f"- [L{line_no}] {line}" for line_no, line in excerpt)
        if excerpt
        else "- _No readable excerpt available._"
    )
    return f"""---
title: {title}
type: summary
tags: [summary, source, compiled]
sources: [raw/{raw_rel}]
source_sha256: {source_sha}
updated: {today}
---

# {title}

> Auto-compiled summary from raw source `raw/{raw_rel}`.

## Source Info

- **Raw file:** `raw/{raw_rel}`
- **SHA256:** `{source_sha}`

## Key Takeaways

{bullets}

## See Also

- [[overview]]
- [[index]]
"""


def _existing_source_sha(page_path: Path) -> str:
    if not page_path.is_file():
        return ""
    text = page_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("source_sha256:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def _append_index_row(index_path: Path, slug: str, summary: str, updated: str) -> None:
    if not index_path.exists():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    header = "## Summaries"
    header_index = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            header_index = i
            break
    if header_index is None:
        return
    row = f"| [[{slug}]] | {summary} | {updated} |"
    section_start = header_index + 1
    insert_at = len(lines)
    for i in range(section_start, len(lines)):
        if lines[i].startswith("## ") and i > section_start:
            insert_at = i
            break
    if row in lines[section_start:insert_at]:
        return
    table_insert = section_start
    for i in range(section_start, insert_at):
        if lines[i].strip().startswith("|") and "Updated" in lines[i]:
            table_insert = i + 2
            break
    new_lines = lines[:table_insert] + [row] + lines[table_insert:]
    index_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _append_log_entry(log_path: Path, today: str, count: int) -> None:
    entry = f"\n## [{today}] compile | raw-to-summary\nPages compiled: {count}\n"
    current = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if current.endswith("\n") or not current:
        log_path.write_text(current + entry.lstrip("\n"), encoding="utf-8")
    else:
        log_path.write_text(current + entry, encoding="utf-8")


def _prune_operational_index_rows(index_path: Path) -> None:
    """Remove index rows for raw operational trees no longer compiled."""

    if not index_path.is_file():
        return
    text = index_path.read_text(encoding="utf-8")
    blocked = (
        "Compiled from raw/events/",
        "Compiled from raw/tool-snapshots/",
        "Compiled from raw/cbmem-snapshots/",
    )
    lines = [line for line in text.splitlines() if not any(token in line for token in blocked)]
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def compile_raw_sources(root: Path) -> CompileReport:
    root = root.resolve()
    raw_dir = root / "raw"
    today = date.today().isoformat()
    tracked = scan_directory(raw_dir)
    compiled: list[CompileItem] = []

    for raw_rel in sorted(tracked.keys()):
        if raw_rel == "files.log":
            continue
        if any(raw_rel.startswith(prefix) for prefix in IGNORED_PREFIXES):
            continue
        source_path = raw_dir / raw_rel
        slug = _summary_slug(raw_rel)
        page_path = root / "wiki" / "summaries" / f"{slug}.md"
        sha = _source_sha(source_path)
        existing_sha = _existing_source_sha(page_path)
        changed = sha != existing_sha
        if changed:
            excerpt = _extract_excerpt(_read_text(source_path))
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(
                _render_summary_page(raw_rel, sha, excerpt, today),
                encoding="utf-8",
            )
            _append_index_row(
                root / "wiki" / "index.md",
                slug,
                f"Compiled from raw/{raw_rel}",
                today,
            )
        compiled.append(
            CompileItem(
                raw_rel=raw_rel,
                page_slug=slug,
                page_path=page_path,
                changed=changed,
            )
        )

    index_path = root / "wiki" / "index.md"
    _prune_operational_index_rows(index_path)
    _append_log_entry(root / "wiki" / "log.md", today, len(compiled))
    return CompileReport(root=root, compiled=tuple(compiled))


def render_compile_report(report: CompileReport) -> str:
    changed = [item for item in report.compiled if item.changed]
    lines = [
        f"# Compile Report — {report.root.name}",
        "",
        f"- Raw files considered: {len(report.compiled)}",
        f"- Pages changed: {len(changed)}",
        "",
    ]
    if not report.compiled:
        lines.append("No raw sources found to compile.")
        return "\n".join(lines)
    lines.append("## Items")
    for item in report.compiled:
        status = "updated" if item.changed else "unchanged"
        lines.append(f"- {status} | raw/{item.raw_rel} -> wiki/summaries/{item.page_slug}.md")
    return "\n".join(lines)
