"""Local desktop-style dashboard and lightweight wiki server."""

from __future__ import annotations

import html
import re
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import quote, unquote

from lwm.analysis import WikiAnalysis, WikiPage, analyze_wiki, collect_wiki_pages

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class DashboardContext:
    root: Path
    analysis: WikiAnalysis
    pages: tuple[WikiPage, ...]
    purpose: str
    overview: str
    log_tail: tuple[str, ...]
    slug_map: dict[str, WikiPage]


def _strip_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    return text[match.end() :]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _tail_lines(text: str, limit: int = 12) -> tuple[str, ...]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return tuple(lines[-limit:])


def _summary_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("> "):
            return stripped[2:].strip()
        return stripped
    return ""


def _page_body(path: Path) -> str:
    return _strip_frontmatter(_read_text(path)).strip()


def _purpose_excerpt(root: Path) -> str:
    for candidate in (root / "wiki" / "purpose.md", root / "AGENTS.md"):
        text = _page_body(candidate)
        if text:
            return text
    return "No purpose page yet."


def _overview_excerpt(root: Path) -> str:
    text = _page_body(root / "wiki" / "overview.md")
    return text or "No overview yet."


def _static_page_filename(rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    if rel.endswith(".md"):
        rel = rel[:-3]
    rel = rel.replace("/", "__")
    return f"{rel}.html"


def _log_tail(root: Path) -> tuple[str, ...]:
    text = _read_text(root / "wiki" / "log.md")
    if not text:
        return ()
    return _tail_lines(text)


def load_dashboard_context(root: Path) -> DashboardContext:
    root = root.resolve()
    pages = collect_wiki_pages(root)
    analysis = analyze_wiki(root)
    slug_map: dict[str, WikiPage] = {}
    for page in pages:
        if page.slug not in slug_map:
            slug_map[page.slug] = page
        else:
            slug_map[page.slug] = None  # type: ignore[assignment]
    slug_map = {slug: page for slug, page in slug_map.items() if page is not None}
    return DashboardContext(
        root=root,
        analysis=analysis,
        pages=pages,
        purpose=_purpose_excerpt(root),
        overview=_overview_excerpt(root),
        log_tail=_log_tail(root),
        slug_map=slug_map,
    )


def _escape_and_linkify(
    text: str,
    link_href: Callable[[str], str | None],
) -> str:
    parts: list[str] = []
    last = 0
    for match in WIKILINK_RE.finditer(text):
        parts.append(html.escape(text[last : match.start()]))
        target = match.group(1).strip()
        label = (match.group(2) or target).strip()
        href = link_href(target)
        if href:
            parts.append(f'<a class="wikilink" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
        else:
            parts.append(f'<span class="wikilink missing">{html.escape(label)}</span>')
        last = match.end()
    parts.append(html.escape(text[last:]))
    return "".join(parts)


def render_markdown_html(
    text: str,
    *,
    link_href: Callable[[str], str | None],
) -> str:
    body = _strip_frontmatter(text)
    lines = body.splitlines()
    html_parts: list[str] = []
    paragraph: list[str] = []
    list_mode: str | None = None
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html_parts.append(f"<p>{' '.join(paragraph)}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_mode
        if list_mode == "ul":
            html_parts.append("</ul>")
        elif list_mode == "ol":
            html_parts.append("</ol>")
        list_mode = None

    def open_list(kind: str) -> None:
        nonlocal list_mode
        if list_mode != kind:
            close_list()
            html_parts.append("<ul>" if kind == "ul" else "<ol>")
            list_mode = kind

    def render_inline(raw: str) -> str:
        return _escape_and_linkify(raw, link_href)

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                html_parts.append(
                    "<pre><code"
                    + (f' class="language-{html.escape(code_lang)}"' if code_lang else "")
                    + ">"
                    + html.escape("\n".join(code_lines))
                    + "</code></pre>"
                )
                code_lines = []
                in_code = False
                code_lang = ""
            else:
                flush_paragraph()
                close_list()
                in_code = True
                code_lang = stripped[3:].strip()
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            level = len(heading_match.group(1))
            html_parts.append(f"<h{level}>{render_inline(heading_match.group(2))}</h{level}>")
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            flush_paragraph()
            open_list("ul")
            html_parts.append(f"<li>{render_inline(bullet_match.group(1))}</li>")
            continue

        ordered_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered_match:
            flush_paragraph()
            open_list("ol")
            html_parts.append(f"<li>{render_inline(ordered_match.group(1))}</li>")
            continue

        quote_match = re.match(r"^>\s?(.*)$", stripped)
        if quote_match:
            flush_paragraph()
            close_list()
            html_parts.append(f"<blockquote>{render_inline(quote_match.group(1))}</blockquote>")
            continue

        flush_paragraph()
        close_list()
        paragraph.append(render_inline(stripped))

    flush_paragraph()
    close_list()
    if in_code:
        html_parts.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")

    return "\n".join(html_parts)


def _dashboard_actions(analysis: WikiAnalysis) -> tuple[str, ...]:
    actions: list[str] = []
    if analysis.broken_links:
        actions.append("Repair broken links.")
    if analysis.missing_sources:
        actions.append("Repair source traceability.")
    if analysis.orphan_pages:
        actions.append("Connect or archive orphan pages.")
    if analysis.duplicate_slugs:
        actions.append("Resolve duplicate slugs before adding more content.")
    if not actions:
        actions.append("Workspace is structurally healthy. Ingest the next batch.")
    return tuple(actions)


def _page_href(root: Path, rel_path: str, *, live: bool, export_dir: Path | None = None) -> str:
    if live:
        return f"/page/{quote(rel_path, safe='')}"
    if export_dir is not None:
        return f"{export_dir.name}/{_static_page_filename(rel_path)}"
    return (root / rel_path).resolve().as_uri()


def _page_type_counts(pages: tuple[WikiPage, ...]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for page in pages:
        counts[page.page_type] = counts.get(page.page_type, 0) + 1
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _render_cards(analysis: WikiAnalysis) -> str:
    cards = [
        ("Pages", str(len(analysis.pages))),
        ("Hubs", str(len(analysis.hub_pages))),
        ("Orphans", str(len(analysis.orphan_pages))),
        ("Broken links", str(len(analysis.broken_links))),
        ("Missing sources", str(len(analysis.missing_sources))),
        ("Components", str(len(analysis.connected_components))),
    ]
    return "".join(
        f'<article class="stat-card"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></article>'
        for label, value in cards
    )


def _render_issue_list(title: str, items: tuple[str, ...]) -> str:
    if not items:
        return f'<section class="panel"><h2>{html.escape(title)}</h2><p class="muted">None.</p></section>'
    return (
        f'<section class="panel"><h2>{html.escape(title)}</h2><ul class="issue-list">'
        + "".join(f"<li>{html.escape(item)}</li>" for item in items)
        + "</ul></section>"
    )


def render_dashboard_html(
    context: DashboardContext,
    *,
    live: bool = False,
    export_dir: Path | None = None,
) -> str:
    analysis = context.analysis
    actions = _dashboard_actions(analysis)
    page_rows: list[str] = []
    for page in context.pages:
        inbound = analysis.inbound_counts.get(page.rel_path, 0)
        outbound = analysis.page_outbound_counts.get(page.rel_path, 0)
        href = _page_href(context.root, page.rel_path, live=live, export_dir=export_dir)
        page_rows.append(
            "<tr "
            f'data-search="{html.escape(" ".join([page.title, page.rel_path, page.page_type, " ".join(page.tags)]).lower(), quote=True)}">'
            f'<td><a href="{html.escape(href, quote=True)}">{html.escape(page.title)}</a></td>'
            f"<td>{html.escape(page.page_type)}</td>"
            f"<td>{inbound}</td>"
            f"<td>{outbound}</td>"
            f"<td>{len(page.sources)}</td>"
            f"<td>{html.escape(page.rel_path)}</td>"
            "</tr>"
        )

    components = analysis.connected_components[:8]
    component_html = (
        "<ol class=\"component-list\">"
        + "".join(
            "<li>"
            + ", ".join(
                f'<a href="{html.escape(_page_href(context.root, item, live=live, export_dir=export_dir), quote=True)}">{html.escape(Path(item).stem)}</a>'
                for item in component
            )
            + "</li>"
            for component in components
        )
        + "</ol>"
        if components
        else '<p class="muted">None.</p>'
    )

    hubs_html = (
        "<ul class=\"link-list\">"
        + "".join(
            f'<li><a href="{html.escape(_page_href(context.root, rel_path, live=live, export_dir=export_dir), quote=True)}">{html.escape(Path(rel_path).stem)}</a>'
            f"<span>{inbound} inbound · {outbound} outbound</span></li>"
            for rel_path, inbound, outbound in analysis.hub_pages
        )
        + "</ul>"
        if analysis.hub_pages
        else '<p class="muted">None.</p>'
    )

    orphans_html = (
        "<ul class=\"link-list\">"
        + "".join(
            f'<li><a href="{html.escape(_page_href(context.root, rel_path, live=live, export_dir=export_dir), quote=True)}">{html.escape(Path(rel_path).stem)}</a></li>'
            for rel_path in analysis.orphan_pages
        )
        + "</ul>"
        if analysis.orphan_pages
        else '<p class="muted">None.</p>'
    )

    log_html = (
        "<ul class=\"log-list\">"
        + "".join(f"<li>{html.escape(line)}</li>" for line in context.log_tail)
        + "</ul>"
        if context.log_tail
        else '<p class="muted">No log entries yet.</p>'
    )

    type_rows = "".join(
        f"<tr><td>{html.escape(page_type)}</td><td>{count}</td></tr>"
        for page_type, count in _page_type_counts(context.pages)
    )

    issue_lines = [
        f"{len(analysis.broken_links)} broken links",
        f"{len(analysis.missing_sources)} missing sources",
        f"{len(analysis.orphan_pages)} orphans",
        f"{len(analysis.duplicate_slugs)} duplicate slugs",
    ]

    rows_html = "".join(page_rows) if page_rows else '<tr><td colspan="6" class="empty">No pages yet.</td></tr>'

    page_count = len(analysis.pages)
    updated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LLM-WorkMem Desktop</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fc;
      --panel: #ffffff;
      --panel-2: #f1f5fb;
      --text: #101828;
      --muted: #667085;
      --border: #d9e2ef;
      --accent: #2457d6;
      --accent-2: #0f766e;
      --warn: #9a3412;
      --shadow: 0 18px 40px rgba(16, 24, 40, 0.08);
      --radius: 10px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #f8fbff 0%, var(--bg) 22%);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto auto 1fr;
    }}
    header {{
      padding: 22px 28px 12px;
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 20px;
    }}
    h1 {{
      margin: 0;
      font-size: 24px;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    .subhead {{
      margin-top: 8px;
      color: var(--muted);
      max-width: 78ch;
    }}
    .meta {{
      display: grid;
      gap: 4px;
      justify-items: end;
      color: var(--muted);
      text-align: right;
      font-size: 12px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      padding: 0 28px 16px;
    }}
    .stat-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 14px 16px;
      display: grid;
      gap: 8px;
      min-height: 88px;
    }}
    .stat-card span {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .stat-card strong {{
      font-size: 28px;
      line-height: 1;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.1fr 1.9fr 1.15fr;
      gap: 14px;
      padding: 0 28px 28px;
      align-items: start;
    }}
    .stack {{
      display: grid;
      gap: 14px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 16px;
    }}
    .panel h2 {{
      margin: 0 0 10px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #344054;
    }}
    .panel h3 {{
      margin: 18px 0 8px;
      font-size: 13px;
      color: #344054;
    }}
    .muted {{ color: var(--muted); }}
    .purpose {{
      display: grid;
      gap: 10px;
    }}
    .purpose-body {{
      display: grid;
      gap: 10px;
      padding: 10px 12px;
      border-left: 3px solid var(--accent);
      background: #f5f8ff;
      border-radius: 8px;
      color: #1d2939;
    }}
    .issue-list, .link-list, .log-list, .component-list {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }}
    .link-list li {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }}
    .link-list span {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #edf2f7;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--panel-2);
      color: #344054;
      font-weight: 600;
    }}
    tr:hover td {{
      background: #f8fafc;
    }}
    .searchbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .searchbar input {{
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }}
    .section-grid {{
      display: grid;
      gap: 14px;
    }}
    .page-preview {{
      display: grid;
      gap: 8px;
      font-size: 13px;
      color: #344054;
    }}
    .page-preview .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 8px;
      border-radius: 999px;
      background: #eef4ff;
      color: #1d4ed8;
      font-size: 12px;
      white-space: nowrap;
    }}
    .warning {{
      color: var(--warn);
      font-weight: 600;
    }}
    .empty {{
      color: var(--muted);
      text-align: center;
      padding: 20px 12px;
    }}
    .wikilink.missing {{
      color: #b42318;
    }}
    .footer-note {{
      padding: 0 28px 24px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 1180px) {{
      .stats, .layout {{ grid-template-columns: 1fr 1fr; }}
      .layout {{ grid-template-columns: 1fr; }}
      header {{ align-items: start; flex-direction: column; }}
      .meta {{ justify-items: start; text-align: left; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>LLM-WorkMem Desktop</h1>
        <div class="subhead">{html.escape(context.root.name)} · {html.escape(_summary_line(context.purpose) if context.purpose else "No purpose yet.")}</div>
      </div>
      <div class="meta">
        <div>{html.escape(updated)}</div>
        <div>{page_count} pages · {len(analysis.connected_components)} components</div>
      </div>
    </header>

    <section class="stats">
      {_render_cards(analysis)}
    </section>

    <main class="layout">
      <section class="stack">
        <article class="panel purpose">
          <h2>Purpose</h2>
          <div class="purpose-body">{render_markdown_html(context.purpose, link_href=lambda target: _page_href(context.root, f"wiki/{target}.md", live=live, export_dir=export_dir))}</div>
        </article>
        <article class="panel">
          <h2>Next Actions</h2>
          <ul class="issue-list">
            {''.join(f'<li>{html.escape(action)}</li>' for action in actions)}
          </ul>
        </article>
        <article class="panel">
          <h2>Page Types</h2>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Type</th><th>Pages</th></tr></thead>
              <tbody>{type_rows or '<tr><td colspan="2" class="empty">No pages yet.</td></tr>'}</tbody>
            </table>
          </div>
        </article>
        <article class="panel">
          <h2>Log Tail</h2>
          {log_html}
        </article>
      </section>

      <section class="section-grid">
        <article class="panel">
          <h2>Knowledge Body</h2>
          <div class="page-preview">
            <div class="muted">{html.escape(_summary_line(context.overview) if context.overview else "")}</div>
            <div class="chip-row">
              <span class="chip">root: {html.escape(context.root.name)}</span>
              <span class="chip">pages: {page_count}</span>
              <span class="chip">issues: {len(analysis.broken_links) + len(analysis.missing_sources) + len(analysis.duplicate_slugs)}</span>
            </div>
            <p>{html.escape("Use the table below to search pages, jump into markdown, and inspect structure.")}</p>
          </div>
        </article>

        <article class="panel">
          <h2>Pages</h2>
          <div class="searchbar">
            <input id="page-filter" type="search" placeholder="Filter pages, types, tags, paths..." />
          </div>
          <div class="table-wrap">
            <table id="pages-table">
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Type</th>
                  <th>In</th>
                  <th>Out</th>
                  <th>Src</th>
                  <th>Path</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section class="stack">
        <article class="panel">
          <h2>Hubs</h2>
          {hubs_html}
        </article>
        <article class="panel">
          <h2>Orphans</h2>
          {orphans_html}
        </article>
        <article class="panel">
          <h2>Connected Components</h2>
          {component_html}
        </article>
        <article class="panel">
          <h2>Issues</h2>
          <ul class="issue-list">
            {''.join(f'<li>{html.escape(line)}</li>' for line in issue_lines)}
          </ul>
        </article>
      </section>
    </main>

    <div class="footer-note">
      Desktop mode is local-first. Use <code>lwm dashboard</code> for a snapshot or <code>lwm serve</code> for a live workspace.
    </div>
  </div>

  <script>
    const input = document.getElementById('page-filter');
    const rows = Array.from(document.querySelectorAll('#pages-table tbody tr'));
    input.addEventListener('input', () => {{
      const q = input.value.trim().toLowerCase();
      rows.forEach((row) => {{
        const hay = row.getAttribute('data-search') || '';
        row.style.display = hay.includes(q) ? '' : 'none';
      }});
    }});
  </script>
</body>
</html>
"""


def write_dashboard_html(root: Path, out_path: Path | None = None) -> Path:
    root = root.resolve()
    context = load_dashboard_context(root)
    target = out_path or (root / "knowledge-digest.html")
    export_dir = target.with_name(f"{target.stem}.pages")
    export_dir.mkdir(parents=True, exist_ok=True)
    for page in context.pages:
        page_export = export_dir / _static_page_filename(page.rel_path)
        page_export.write_text(
            render_page_html(
                root,
                page.path,
                live=False,
                export_dir=export_dir,
                dashboard_href=f"../{target.name}",
            ),
            encoding="utf-8",
        )
    html_text = render_dashboard_html(context, live=False, export_dir=export_dir)
    target.write_text(html_text, encoding="utf-8")
    return target


def _resolve_page(root: Path, pages: tuple[WikiPage, ...], rel_or_slug: str) -> Path | None:
    root = root.resolve()
    candidate = (root / rel_or_slug).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        candidate = None
    if candidate and candidate.is_file():
        return candidate

    slug_matches = [page for page in pages if page.slug == rel_or_slug.lower()]
    if len(slug_matches) == 1:
        return slug_matches[0].path

    rel_matches = [page for page in pages if page.rel_path == rel_or_slug]
    if len(rel_matches) == 1:
        return rel_matches[0].path

    return None


def _page_title(path: Path) -> str:
    text = _read_text(path)
    match = re.search(r"^#\s+(.+)$", _strip_frontmatter(text), re.MULTILINE)
    if match:
        return match.group(1).strip()
    return path.stem


def render_page_html(
    root: Path,
    page: Path,
    *,
    live: bool = True,
    export_dir: Path | None = None,
    dashboard_href: str = "/",
) -> str:
    root = root.resolve()
    context = load_dashboard_context(root)
    raw = _read_text(page)
    title = _page_title(page)
    page_page = next((item for item in context.pages if item.path == page), None)
    if page_page is None:
        resolved_page = page.resolve()
        page_page = next((item for item in context.pages if item.path.resolve() == resolved_page), None)
    if page_page is None:
        try:
            rel_path = page.relative_to(root).as_posix()
        except ValueError:
            parts = page.parts
            if "wiki" in parts:
                rel_path = Path(*parts[parts.index("wiki") :]).as_posix()
            else:
                rel_path = page.name
        page_page = WikiPage(
            path=page,
            rel_path=rel_path,
            slug=page.stem.lower(),
            title=title,
            page_type=page.parent.name,
            sources=(),
            outbound_links=(),
            tags=(),
        )

    def href_for(target: str) -> str | None:
        slug = target.lower()
        match = context.slug_map.get(slug)
        if match is not None:
            return _page_href(root, match.rel_path, live=live, export_dir=export_dir)
        rel = (root / target).resolve()
        try:
            rel.relative_to(root)
        except ValueError:
            return None
        if rel.is_file():
            return _page_href(root, rel.relative_to(root).as_posix(), live=live, export_dir=export_dir)
        return None

    rendered_body = render_markdown_html(raw, link_href=href_for)
    refresh_link = '<a href="/_refresh">Refresh</a>' if live else ""
    sources_html = (
        "<ul class=\"link-list\">"
        + "".join(
            f"<li>{html.escape(source)}</li>"
            for source in (page_page.sources if page_page else ())
        )
        + "</ul>"
        if page_page and page_page.sources
        else '<p class="muted">No sources recorded.</p>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} · LLM-WorkMem</title>
  <style>
    body {{
      margin: 0;
      font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
      color: #101828;
      background: #f6f8fc;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 28px;
      display: grid;
      gap: 16px;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #d9e2ef;
      border-radius: 10px;
      box-shadow: 0 18px 40px rgba(16, 24, 40, 0.08);
      padding: 16px;
    }}
    .meta {{
      color: #667085;
      font-size: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta span {{
      background: #eef4ff;
      color: #1d4ed8;
      border-radius: 999px;
      padding: 4px 8px;
    }}
    .muted {{ color: #667085; }}
    .wikilink.missing {{ color: #b42318; }}
    .body h1, .body h2, .body h3 {{ margin-top: 1.2em; }}
    .body p, .body ul, .body ol, .body blockquote {{ margin: 0.8em 0; }}
    .body blockquote {{
      margin-left: 0;
      padding: 10px 12px;
      border-left: 3px solid #2457d6;
      background: #f5f8ff;
      border-radius: 8px;
    }}
    .body pre {{
      padding: 14px;
      overflow: auto;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 8px;
    }}
    a {{ color: #2457d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .topnav {{ display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; }}
  </style>
</head>
<body>
    <main>
      <div class="topnav">
        <a href="{html.escape(dashboard_href, quote=True)}">Dashboard</a>
        {refresh_link}
        <span class="muted">{html.escape(page_page.rel_path)}</span>
      </div>
    <section class="panel">
      <h1>{html.escape(title)}</h1>
      <div class="meta">
        <span>type: {html.escape(page_page.page_type)}</span>
        <span>sources: {len(page_page.sources)}</span>
        <span>inbound: {context.analysis.inbound_counts.get(page_page.rel_path, 0)}</span>
        <span>outbound: {len(page_page.outbound_links)}</span>
      </div>
      {sources_html}
    </section>
    <article class="panel body">
      {rendered_body or '<p class="muted">Empty page.</p>'}
    </article>
  </main>
</body>
</html>
"""


def serve_wiki(
    root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
) -> None:
    root = root.resolve()

    class WikiHandler(BaseHTTPRequestHandler):
        server_version = "lwm/desktop"

        def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_text(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index.html", "/dashboard"}:
                self._send_html(render_dashboard_html(load_dashboard_context(root), live=True))
                return
            if self.path == "/_refresh":
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/")
                self.end_headers()
                return
            if self.path.startswith("/page/"):
                rel = unquote(self.path[len("/page/") :])
                context = load_dashboard_context(root)
                resolved = _resolve_page(root, context.pages, rel)
                if resolved is None:
                    self._send_text(f"Page not found: {rel}", status=HTTPStatus.NOT_FOUND)
                    return
                self._send_html(render_page_html(root, resolved, live=True))
                return
            if self.path.startswith("/raw/"):
                rel = unquote(self.path[len("/raw/") :])
                resolved = (root / rel).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    self._send_text("Not allowed", status=HTTPStatus.FORBIDDEN)
                    return
                if not resolved.is_file():
                    self._send_text("Not found", status=HTTPStatus.NOT_FOUND)
                    return
                self._send_text(_read_text(resolved))
                return
            self._send_text("Not found", status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), WikiHandler)
    url = f"http://{host}:{port}/"
    print(f"Serving LLM-WorkMem desktop workspace at {url}")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
