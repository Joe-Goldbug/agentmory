"""Lightweight wiki graph analysis and report generation."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class WikiPage:
    path: Path
    rel_path: str
    slug: str
    title: str
    page_type: str
    sources: tuple[str, ...]
    outbound_links: tuple[str, ...]
    tags: tuple[str, ...]
    updated: str = ""
    # Stability fields (Looped World Model ρ(Ā)<1): optional, fallback in scoring
    # last_used_at: ISO date string of most recent successful query hit (frontmatter `last_used_at`)
    # use_count: total times this page has been a query hit (frontmatter `use_count`)
    last_used_at: str = ""
    use_count: int = 0


@dataclass(frozen=True)
class WikiAnalysis:
    root: Path
    pages: tuple[WikiPage, ...]
    inbound_counts: dict[str, int]
    page_outbound_counts: dict[str, int]
    broken_links: tuple[tuple[str, str], ...]
    duplicate_slugs: tuple[tuple[str, tuple[str, ...]], ...]
    missing_sources: tuple[tuple[str, str], ...]
    orphan_pages: tuple[str, ...]
    hub_pages: tuple[tuple[str, int, int], ...]
    connected_components: tuple[tuple[str, ...], ...]
    errors: tuple[str, ...]


def _split_csv_list(value: str) -> tuple[str, ...]:
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return ()
    return tuple(part.strip().strip("'\"") for part in text.split(",") if part.strip())


def _parse_int(value: str) -> int:
    """Parse a frontmatter integer; return 0 on empty/invalid (spectral-stable fallback)."""
    text = value.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    rest = text[match.end() :]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, rest


def _normalize_link(value: str) -> str:
    link = value.strip()
    link = link.split("|", 1)[0]
    link = link.split("#", 1)[0]
    link = link.rsplit("/", 1)[-1]
    if link.endswith(".md"):
        link = link[:-3]
    return link.lower()


def _slug_for_path(path: Path) -> str:
    return path.stem.lower()


def _is_ignored_page(path: Path) -> bool:
    if path.name in {"log.md"}:
        return True
    # Legacy releases compiled raw/events JSON into summary pages. Keep those
    # files as historical evidence, but exclude them from the live wiki graph.
    return path.parent.name == "summaries" and path.name.startswith("source-events-")


def collect_wiki_pages(root: Path) -> tuple[WikiPage, ...]:
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        return ()

    pages: list[WikiPage] = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if _is_ignored_page(path):
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(text)
        slug = _slug_for_path(path)
        links = tuple(_normalize_link(match.group(1)) for match in LINK_RE.finditer(body))
        sources = _split_csv_list(frontmatter.get("sources", ""))
        tags = _split_csv_list(frontmatter.get("tags", ""))
        title = frontmatter.get("title") or _title_from_body(body) or path.stem
        page_type = frontmatter.get("type", path.parent.name)
        pages.append(
            WikiPage(
                path=path,
                rel_path=path.relative_to(root).as_posix(),
                slug=slug,
                title=title,
                page_type=page_type,
                sources=sources,
                outbound_links=links,
                tags=tags,
                updated=frontmatter.get("updated", ""),
                last_used_at=frontmatter.get("last_used_at", ""),
                use_count=_parse_int(frontmatter.get("use_count", "0")),
            )
        )
    return tuple(pages)


def _title_from_body(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _build_slug_map(pages: Iterable[WikiPage]) -> dict[str, tuple[WikiPage, ...]]:
    buckets: dict[str, list[WikiPage]] = defaultdict(list)
    for page in pages:
        buckets[page.slug].append(page)
    return {slug: tuple(items) for slug, items in buckets.items()}


def analyze_wiki(root: Path) -> WikiAnalysis:
    pages = collect_wiki_pages(root)
    slug_map = _build_slug_map(pages)
    duplicate_slugs = tuple(
        (slug, tuple(page.rel_path for page in items))
        for slug, items in sorted(slug_map.items())
        if len(items) > 1
    )

    inbound_counts: Counter[str] = Counter()
    broken_links: list[tuple[str, str]] = []
    errors: list[str] = []

    for page in pages:
        for link in page.outbound_links:
            # Legacy event-summary links may remain in generated index/radar
            # pages. Event JSON is operational data, not a wiki graph node.
            if link.startswith("source-events-"):
                continue
            targets = slug_map.get(link)
            if not targets:
                broken_links.append((page.rel_path, link))
                continue
            if len(targets) > 1:
                errors.append(f"Ambiguous link [[{link}]] referenced by {page.rel_path}")
                continue
            inbound_counts[targets[0].rel_path] += 1

    missing_sources: list[tuple[str, str]] = []
    raw_dir = root / "raw"
    for page in pages:
        for source in page.sources:
            source_path = root / source if source.startswith("raw/") else raw_dir / source
            if not source_path.exists():
                missing_sources.append((page.rel_path, source))

    ignored_orphans = {"wiki/index.md", "wiki/overview.md"}
    # Auto-generated project memory pages legitimately live without being
    # linked from other wiki pages; only the inherited index / overview are
    # considered structural orphans by the same rules.
    ignored_orphans.update(
        {p.rel_path for p in pages if p.page_type == "project"}
    )
    ignored_orphans.update(
        {
            p.rel_path
            for p in pages
            if p.page_type == "principle"
            and p.rel_path.startswith("wiki/global/recurring-tag-")
        }
    )
    orphan_pages = tuple(
        sorted(
            page.rel_path
            for page in pages
            if page.rel_path not in ignored_orphans
            and inbound_counts.get(page.rel_path, 0) == 0
            and page.page_type not in {"overview", "insight", "review", "project"}
        )
    )

    page_outbound_counts = {page.rel_path: len(page.outbound_links) for page in pages}
    hub_pages = tuple(
        sorted(
            (
                (
                    page.rel_path,
                    inbound_counts.get(page.rel_path, 0),
                    page_outbound_counts.get(page.rel_path, 0),
                )
                for page in pages
            ),
            key=lambda item: (-item[1], -item[2], item[0]),
        )
    )

    connected_components = _connected_components(pages, slug_map)
    errors.extend(f"Broken link [[{link}]] in {source}" for source, link in broken_links)
    errors.extend(f"Missing source {source!r} referenced by {page}" for page, source in missing_sources)
    errors.extend(
        f"Duplicate slug {slug!r} found in {', '.join(paths)}"
        for slug, paths in duplicate_slugs
    )

    return WikiAnalysis(
        root=root,
        pages=pages,
        inbound_counts=dict(inbound_counts),
        page_outbound_counts=page_outbound_counts,
        broken_links=tuple(sorted(broken_links)),
        duplicate_slugs=duplicate_slugs,
        missing_sources=tuple(sorted(missing_sources)),
        orphan_pages=orphan_pages,
        hub_pages=hub_pages,
        connected_components=connected_components,
        errors=tuple(errors),
    )


def _connected_components(
    pages: tuple[WikiPage, ...], slug_map: dict[str, tuple[WikiPage, ...]]
) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, set[str]] = {page.rel_path: set() for page in pages}
    for page in pages:
        for link in page.outbound_links:
            targets = slug_map.get(link)
            if len(targets or ()) != 1:
                continue
            target = targets[0].rel_path
            adjacency[page.rel_path].add(target)
            adjacency[target].add(page.rel_path)

    seen: set[str] = set()
    components: list[tuple[str, ...]] = []
    for start in sorted(adjacency):
        if start in seen:
            continue
        stack = [start]
        component: list[str] = []
        seen.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for nxt in sorted(adjacency[node]):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(tuple(sorted(component)))
    components.sort(key=lambda comp: (-len(comp), comp))
    return tuple(components)


def render_analysis_report(analysis: WikiAnalysis) -> str:
    lines: list[str] = []
    lines.append(f"# Wiki Analysis — {analysis.root.name}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Pages: {len(analysis.pages)}")
    lines.append(f"- Broken links: {len(analysis.broken_links)}")
    lines.append(f"- Missing sources: {len(analysis.missing_sources)}")
    lines.append(f"- Duplicate slugs: {len(analysis.duplicate_slugs)}")
    lines.append(f"- Orphans: {len(analysis.orphan_pages)}")
    lines.append("")

    lines.append("## Hubs")
    if analysis.hub_pages:
        lines.append("| Page | Inbound | Outbound |")
        lines.append("|------|---------|----------|")
        for rel_path, inbound, outbound in analysis.hub_pages:
            lines.append(f"| [[{Path(rel_path).stem}]] | {inbound} | {outbound} |")
    else:
        lines.append("*No pages found.*")
    lines.append("")

    lines.append("## Orphans")
    if analysis.orphan_pages:
        for rel_path in analysis.orphan_pages:
            lines.append(f"- [[{Path(rel_path).stem}]]")
    else:
        lines.append("*None.*")
    lines.append("")

    lines.append("## Broken Links")
    if analysis.broken_links:
        for page, link in analysis.broken_links:
            lines.append(f"- {page}: `{link}`")
    else:
        lines.append("*None.*")
    lines.append("")

    lines.append("## Missing Sources")
    if analysis.missing_sources:
        for page, source in analysis.missing_sources:
            lines.append(f"- {page}: {source}")
    else:
        lines.append("*None.*")
    lines.append("")

    lines.append("## Duplicate Slugs")
    if analysis.duplicate_slugs:
        for slug, paths in analysis.duplicate_slugs:
            lines.append(f"- {slug}: {', '.join(paths)}")
    else:
        lines.append("*None.*")
    lines.append("")

    lines.append("## Connected Components")
    if analysis.connected_components:
        for index, component in enumerate(analysis.connected_components[:10], start=1):
            pretty = ", ".join(f"[[{Path(item).stem}]]" for item in component)
            lines.append(f"{index}. {pretty}")
    else:
        lines.append("*None.*")
    lines.append("")

    return "\n".join(lines)


def write_analysis_report(root: Path, analysis: WikiAnalysis) -> Path:
    insights_dir = root / "wiki" / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    out_path = insights_dir / f"knowledge-radar-{date.today().isoformat()}.md"
    page = f"""---
title: Knowledge Radar
type: insight
tags: [insight, analysis, radar]
cited: []
sources: []
updated: {date.today().isoformat()}
---

{render_analysis_report(analysis)}
"""
    out_path.write_text(page, encoding="utf-8")
    return out_path
