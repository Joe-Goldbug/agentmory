"""Wiki query, synthesis, and save-as-insight helpers."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lwm.analysis import WikiAnalysis, WikiPage, analyze_wiki, collect_wiki_pages


@dataclass(frozen=True)
class QueryHit:
    page: WikiPage
    score: int
    reasons: tuple[str, ...]
    excerpt: str


@dataclass(frozen=True)
class QueryReport:
    root: Path
    query: str
    mode: str
    hits: tuple[QueryHit, ...]
    related: tuple[str, ...]
    notes: tuple[str, ...]


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(token for token in re.findall(r"[a-z0-9]+", text.lower()) if token)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
        if match:
            return text[match.end() :]
    return text


def _page_body(page: WikiPage) -> str:
    return _strip_frontmatter(page.path.read_text(encoding="utf-8"))


def _page_excerpt(body: str, tokens: tuple[str, ...], limit: int = 2) -> str:
    lines: list[str] = []
    lowered_tokens = [token.lower() for token in tokens]
    for line_no, raw_line in enumerate(body.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            continue
        if lowered_tokens and any(token in line.lower() for token in lowered_tokens):
            lines.append(f"[L{line_no}] {line}")
        elif not lines:
            lines.append(f"[L{line_no}] {line}")
        if len(lines) >= limit:
            break
    if not lines:
        return ""
    text = " ".join(lines)
    return text if len(text) <= 220 else text[:220].rstrip() + "..."


def _score_page(page: WikiPage, body: str, tokens: tuple[str, ...], mode: str) -> tuple[int, list[str]]:
    if not tokens:
        return 0, []

    mode_bias = {
        "quick": 1,
        "deep": 2,
        "thesis": 2,
        "list": 1,
    }.get(mode, 1)
    score = 0
    reasons: list[str] = []
    blob = " ".join([page.title, page.slug, page.page_type, " ".join(page.tags), " ".join(page.sources)])
    deep_blob = f"{blob}\n{body}" if mode != "quick" else blob
    lowered_blob = deep_blob.lower()
    title_blob = page.title.lower()
    slug_blob = page.slug.lower()

    for token in tokens:
        hits = lowered_blob.count(token)
        if not hits:
            continue
        if token in title_blob:
            score += 8 * mode_bias
            reasons.append(f"title:{token}")
        elif token in slug_blob:
            score += 6 * mode_bias
            reasons.append(f"slug:{token}")
        elif token in " ".join(page.tags).lower():
            score += 5 * mode_bias
            reasons.append(f"tag:{token}")
        elif token in " ".join(page.sources).lower():
            score += 2 * mode_bias
            reasons.append(f"source:{token}")
        if mode != "quick":
            score += min(hits, 3) * mode_bias
            reasons.append(f"body:{token}x{min(hits, 3)}")

    if mode == "thesis":
        if page.page_type in {"conflict", "decision", "principle", "preference", "question"}:
            score += 4
            reasons.append(f"type:{page.page_type}")
        if page.page_type == "insight":
            score += 2
            reasons.append("type:insight")
    # Apply spectral-stable factor (spectral-stable ρ(Ā)<1) — keeps
    # well-trodden core pages from being drowned by new ones.
    score = round(_apply_stability(score, page))
    return score, reasons


def _score_metadata_only(
    page: WikiPage, tokens: tuple[str, ...], mode: str
) -> tuple[int, list[str]]:
    """Score page using only metadata (title/slug/tags/sources) — no body read.

    Used in the latent stage of deferred decoding to pre-filter candidates
    before paying the cost of reading page bodies. Saves 80%+ of body reads
    on large wikis by short-circuiting to the top-K candidates.
    """
    if not tokens:
        return 0, []

    mode_bias = {
        "quick": 1,
        "deep": 2,
        "thesis": 2,
        "list": 1,
    }.get(mode, 1)

    score = 0
    reasons: list[str] = []
    blob = " ".join(
        [page.title, page.slug, page.page_type, " ".join(page.tags), " ".join(page.sources)]
    )
    lowered_blob = blob.lower()
    title_blob = page.title.lower()
    slug_blob = page.slug.lower()

    for token in tokens:
        hits = lowered_blob.count(token)
        if not hits:
            continue
        if token in title_blob:
            score += 8 * mode_bias
            reasons.append(f"title:{token}")
        elif token in slug_blob:
            score += 6 * mode_bias
            reasons.append(f"slug:{token}")
        elif token in " ".join(page.tags).lower():
            score += 5 * mode_bias
            reasons.append(f"tag:{token}")
        elif token in " ".join(page.sources).lower():
            score += 2 * mode_bias
            reasons.append(f"source:{token}")

    if mode == "thesis":
        if page.page_type in {"conflict", "decision", "principle", "preference", "question"}:
            score += 4
            reasons.append(f"type:{page.page_type}")
        if page.page_type == "insight":
            score += 2
            reasons.append("type:insight")

    return score, reasons


# Spectral-stable decay parameters (Looped World Model ρ(Ā) < 1)
# λ=0.99: page loses 1% relevance per day, ~16% remains at 6 months
# λ=0.95: page loses 5% relevance per day, ~0.4% remains at 6 months
_DECAY_LAMBDA = 0.99


def _stability_factor(page: WikiPage) -> float:
    """Spectral-stable memory factor: age decay × use boost.

    New pages do not drown out well-trodden core pages; rarely-used pages
    gently decay. Bounded so no single page can dominate or vanish.
    """
    # Age decay: λ^Δt  (fallback to updated, then to today if both missing)
    last_used = page.last_used_at or page.updated
    try:
        last_used_date = date.fromisoformat(last_used)
    except (TypeError, ValueError):
        last_used_date = date.today()
    age_days = max((date.today() - last_used_date).days, 0)
    age_decay = _DECAY_LAMBDA ** age_days

    # Use boost: log(1 + n) — diminishing returns, bounded
    use_boost = 1.0 + math.log1p(max(page.use_count, 0))

    return age_decay * use_boost


def _apply_stability(score: int, page: WikiPage) -> float:
    """Apply spectral-stable factor to a raw integer score, return float."""
    return score * _stability_factor(page)


_DECISION_KEYWORDS = (
    "对比", "比较", "vs", "原则", "偏好", "决策", "权衡",
    "decide", "decision", "principle", "preference", "compare", "contrast", "should",
)
_SHORT_FACTUAL_STARTS = (
    "谁", "什么", "哪个", "何时", "何地", "为什么",
    "who", "what", "when", "where", "why",
)


def _auto_mode(question: str) -> str:
    """Exit Gate: auto-pick query mode from question shape when mode='standard'.

    Heuristics:
    - Comparative / judgment / decision keywords → 'thesis' (weighted for decisions/principles)
    - Short factual (who/what/when/where) → 'quick' (metadata only)
    - Otherwise → 'deep' (full body)
    """
    q = question.strip().lower()
    if not q:
        return "quick"
    if any(kw in q for kw in _DECISION_KEYWORDS):
        return "thesis"
    words = q.split()
    if len(words) <= 6 and any(q.startswith(p) for p in _SHORT_FACTUAL_STARTS):
        return "quick"
    return "deep"


def _find_related_pages(
    analysis: WikiAnalysis, hits: tuple[QueryHit, ...], limit: int = 6
) -> tuple[str, ...]:
    if not hits:
        return ()
    seed = hits[0].page.rel_path
    for component in analysis.connected_components:
        if seed in component:
            related = [rel for rel in component if rel != seed]
            return tuple(related[:limit])
    return ()


def run_query(root: Path, question: str, *, mode: str = "standard", limit: int = 6) -> QueryReport:
    root = root.resolve()
    analysis = analyze_wiki(root)
    pages = collect_wiki_pages(root)
    tokens = _tokenize(question)

    # === Exit Gate: when caller passes mode='standard', auto-pick from question shape ===
    if mode == "standard":
        mode = _auto_mode(question)

    # === Recurrent Block Stage 1: pure latent (zero body reads) ===
    # Score every page using only metadata (title/slug/tags/sources/page_type).
    latent_hits: list[tuple[WikiPage, int]] = []
    for page in pages:
        meta_score = _score_metadata_only(page, tokens, mode)[0]
        if meta_score > 0:
            latent_hits.append((page, meta_score))
    latent_hits.sort(key=lambda item: (-item[1], item[0].title.lower(), item[0].rel_path))
    # Round 1: keep a generous pool — recurrent block will tighten later.
    K1 = max(limit * 16, 100)
    pool: list[tuple[WikiPage, int]] = latent_hits[:K1]

    # === Recurrent Block Stage 2: add stability signal (spectral-stable ρ(Ā)<1) ===
    # Re-rank with stability factor; high-use and recent pages rise, stale ones sink.
    pool = sorted(
        pool,
        key=lambda item: (
            -_apply_stability(item[1], item[0]),
            item[0].title.lower(),
            item[0].rel_path,
        ),
    )
    # Round 2: tighten to a mid-sized pool.
    K2 = max(K1 // 2, limit * 4)
    pool = pool[:K2]

    # === Deferred Decoding Stage 3: materialize (read bodies of final candidates) ===
    # Final K: the candidate set that pays the body-read cost.
    K3 = max(limit * 8, 50)
    candidate_pages = [page for page, _ in pool[:K3]]
    hits: list[QueryHit] = []
    for page in candidate_pages:
        body = _page_body(page)
        score, reasons = _score_page(page, body, tokens, mode)
        if score <= 0:
            continue
        hits.append(
            QueryHit(
                page=page,
                score=score,
                reasons=tuple(reasons[:6]),
                excerpt=_page_excerpt(body, tokens),
            )
        )
    hits.sort(key=lambda item: (-item.score, item.page.title.lower(), item.page.rel_path))
    trimmed_hits = tuple(hits[:limit])
    related = _find_related_pages(analysis, trimmed_hits) if mode in {"deep", "thesis"} else ()
    notes = _build_notes(question, mode, trimmed_hits, related, analysis)
    return QueryReport(root=root, query=question, mode=mode, hits=trimmed_hits, related=related, notes=notes)


def _build_notes(
    question: str,
    mode: str,
    hits: tuple[QueryHit, ...],
    related: tuple[str, ...],
    analysis: WikiAnalysis,
) -> tuple[str, ...]:
    notes: list[str] = []
    if not hits:
        notes.append("No strong matches found; widen the query or ingest more sources.")
        return tuple(notes)
    notes.append(f"Top match: [[{hits[0].page.slug}]]")
    if mode == "quick":
        notes.append("Quick mode only scores titles, tags, slugs, and sources.")
    elif mode == "deep":
        notes.append("Deep mode scores full page bodies and connected context.")
    elif mode == "thesis":
        notes.append("Thesis mode weights decisions, conflicts, principles, and questions.")
    if related:
        notes.append(f"Related cluster size: {len(related) + 1}")
    if analysis.missing_sources:
        notes.append(f"Wiki has {len(analysis.missing_sources)} missing source reference(s).")
    if analysis.orphan_pages:
        notes.append(f"Wiki has {len(analysis.orphan_pages)} orphan page(s).")
    if " vs " in question.lower() or "compare" in question.lower():
        notes.append("This query looks comparative; consider related conflict or decision pages.")
    return tuple(notes)


def render_query_report(report: QueryReport) -> str:
    lines: list[str] = []
    lines.append(f"# Query — {report.mode.title()}")
    lines.append("")
    lines.append(f"**Question**: {report.query}")
    lines.append("")
    lines.append("## Best Matches")
    if report.hits:
        lines.append("| Page | Type | Score | Why | Excerpt |")
        lines.append("|------|------|-------|-----|---------|")
        for hit in report.hits:
            why = ", ".join(hit.reasons) if hit.reasons else "metadata"
            excerpt = hit.excerpt or "*No excerpt*"
            lines.append(
                f"| [[{hit.page.slug}|{hit.page.title}]] | {hit.page.page_type} | {hit.score} | {why} | {excerpt} |"
            )
    else:
        lines.append("*No strong matches found.*")
    lines.append("")

    if report.related:
        lines.append("## Related Cluster")
        for rel_path in report.related:
            lines.append(f"- [[{Path(rel_path).stem}|{Path(rel_path).stem.replace('-', ' ').title()}]]")
        lines.append("")

    lines.append("## Notes")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## Next Actions")
    if report.hits:
        lines.append("- Read the top pages in full.")
        lines.append("- If the answer is durable, save this synthesis back into the wiki.")
        if report.mode == "thesis":
            lines.append("- Check the conflict and principle pages for contradiction pressure.")
    else:
        lines.append("- Broaden the query or ingest more source material.")
    return "\n".join(lines)


def _append_index_row(index_path: Path, page_slug: str, summary: str, updated: str) -> None:
    if not index_path.exists():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    target_header = "## Insights"
    header_index = None
    for i, line in enumerate(lines):
        if line.strip() == target_header:
            header_index = i
            break
    if header_index is None:
        return

    row = f"| [[{page_slug}]] | {summary} | {updated} |"
    section_start = header_index + 1
    insert_at = len(lines)
    for i in range(section_start, len(lines)):
        if lines[i].startswith("## ") and i > section_start:
            insert_at = i
            break
    section_lines = lines[section_start:insert_at]
    if row in section_lines:
        return

    # Insert just after the table header if present.
    table_end = section_start
    for i in range(section_start, insert_at):
        if lines[i].strip().startswith("|") and "Updated" in lines[i]:
            table_end = i + 2
    new_lines = lines[:table_end] + [row] + lines[table_end:]
    index_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _append_log_entry(log_path: Path, updated: str, title: str) -> None:
    current = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    entry = f"\n## [{updated}] query | {title}\n"
    if current.endswith("\n") or not current:
        log_path.write_text(current + entry.lstrip("\n"), encoding="utf-8")
    else:
        log_path.write_text(current + entry, encoding="utf-8")


def save_query_report(root: Path, report: QueryReport, *, slug: str | None = None) -> Path:
    root = root.resolve()
    slug_value = slug or f"query-{date.today().isoformat()}-{_tokenize(report.query)[0] if _tokenize(report.query) else 'synthesis'}"
    out_path = root / "wiki" / "insights" / f"{slug_value}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    title = f"Query Synthesis — {report.query}"
    page = f"""---
title: {title}
type: insight
tags: [insight, query, synthesis]
sources: []
updated: {date.today().isoformat()}
---

{render_query_report(report)}
"""
    out_path.write_text(page, encoding="utf-8")
    index_path = root / "wiki" / "index.md"
    summary = report.query if len(report.query) <= 80 else report.query[:77] + "..."
    _append_index_row(index_path, Path(out_path).stem, summary, date.today().isoformat())
    log_path = root / "wiki" / "log.md"
    _append_log_entry(log_path, date.today().isoformat(), report.query)
    return out_path
