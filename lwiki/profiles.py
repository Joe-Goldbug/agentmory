"""Wiki profile definitions and renderers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileSpec:
    """A wiki profile describes the tree layout and starter schema."""

    name: str
    tree_sections: tuple[tuple[str, str], ...]
    knowledge_model: tuple[str, ...]
    source_focus: str
    purpose_title: str
    index_title: str
    overview_title: str
    overview_prompt: str


DEFAULT_PROFILE = "default"
PERSONAL_PROFILE = "personal"


PROFILE_SPECS: dict[str, ProfileSpec] = {
    DEFAULT_PROFILE: ProfileSpec(
        name=DEFAULT_PROFILE,
        tree_sections=(
            ("Summaries", "summaries"),
            ("Concepts", "concepts"),
            ("Entities", "entities"),
            ("Insights", "insights"),
        ),
        knowledge_model=(
            "source summaries",
            "concept pages",
            "entity pages",
            "point-in-time insights",
        ),
        source_focus="articles, URLs, papers",
        purpose_title="Wiki Purpose",
        index_title="Wiki Index",
        overview_title="Overview",
        overview_prompt="Evolving synthesis across all sources.",
    ),
    PERSONAL_PROFILE: ProfileSpec(
        name=PERSONAL_PROFILE,
        tree_sections=(
            ("Inbox", "inbox"),
            ("Projects", "projects"),
            ("Inventory", "inventory"),
            ("Datasets", "datasets"),
            ("Archive", "archive"),
            ("Review", "review"),
            ("Summaries", "summaries"),
            ("Concepts", "concepts"),
            ("Decisions", "decisions"),
            ("Patterns", "patterns"),
            ("Conflicts", "conflicts"),
            ("Questions", "questions"),
            ("Principles", "principles"),
            ("Preferences", "preferences"),
            ("Entities", "entities"),
            ("Insights", "insights"),
        ),
        knowledge_model=(
            "inbox triage",
            "project pages",
            "inventory records",
            "dataset manifests",
            "archived context",
            "review queue items",
            "source summaries",
            "concept pages",
            "decision records",
            "reusable patterns",
            "conflict notes",
            "open questions",
            "principles",
            "preferences / judgment patterns",
            "entity pages",
            "point-in-time insights",
        ),
        source_focus="project docs, consultations, conversations, notes, ideas, papers",
        purpose_title="Knowledge Body Purpose",
        index_title="Knowledge Body Index",
        overview_title="Knowledge Body Overview",
        overview_prompt="A living synthesis of your projects, thinking patterns, decisions, conflicts, and reusable principles.",
    ),
}


def get_profile_spec(profile: str) -> ProfileSpec:
    try:
        return PROFILE_SPECS[profile]
    except KeyError as exc:  # pragma: no cover - defensive guard
        valid = ", ".join(sorted(PROFILE_SPECS))
        raise ValueError(f"Unknown profile {profile!r}. Valid profiles: {valid}") from exc


def profile_choices() -> tuple[str, ...]:
    return tuple(sorted(PROFILE_SPECS))


def _render_table(section_name: str) -> str:
    return f"""## {section_name}

| Page | Summary | Updated |
|------|---------|---------|
"""


def render_index_md(domain: str, profile: str) -> str:
    spec = get_profile_spec(profile)
    sections = "\n".join(_render_table(section_name) for section_name, _ in spec.tree_sections)
    return f"""# {spec.index_title} — {domain}

{sections}
"""


def render_purpose_md(domain: str, today: str, profile: str) -> str:
    spec = get_profile_spec(profile)
    if profile == PERSONAL_PROFILE:
        body = """- What am I trying to remember across projects?
- Which decisions, patterns, and conflicts should survive context switches?
- Which signals are important enough to promote into durable structure?
- Which sources should the LLM treat as authoritative for my working style?
"""
    else:
        body = """- What is this wiki for?
- What questions should it answer repeatedly?
- Which source domains belong here?
- What should the LLM preserve when it compiles new knowledge?
"""
    return f"""---
title: Purpose
type: purpose
tags: [purpose, scope]
sources: []
updated: {today}
---

# {spec.purpose_title}

> {spec.overview_prompt}

## Why this wiki exists

{body}

## Guardrails

- Keep the raw sources immutable.
- Promote only stable, reusable, high-signal structure.
- Separate temporary observations from durable principles.
- Use the purpose page to steer ingest, query, and review.

## See Also

- [[index]]
- [[overview]]
"""


def render_overview_md(domain: str, today: str, profile: str) -> str:
    spec = get_profile_spec(profile)
    return f"""---
title: Overview
type: overview
tags: [overview, synthesis]
sources: []
updated: {today}
---

# {domain} — {spec.overview_title}

> {spec.overview_prompt} Updated on each ingest or review.

## Current Understanding

*No sources ingested yet.*

## Open Questions

*Add questions here as they arise.*

## Key Concepts / Projects

*Populated as pages are created.*
"""


def render_agents_md(domain: str, source_types: str, profile: str) -> str:
    spec = get_profile_spec(profile)
    model_lines = "\n".join(f"- {item}" for item in spec.knowledge_model)
    return f"""# {domain} Wiki Schema

## Domain
{domain}

## Source Types
{source_types}

## Knowledge Model
{model_lines}

## Conventions
- All wiki pages use YAML frontmatter with: title, type, tags, sources, updated
- Cross-references use [[wikilinks]] with plain filenames
- raw/ is immutable — never modify source documents
- log.md is append-only
- Pages should preserve source traceability, confidence, and status where useful
- This schema co-evolves with use — suggest changes when conventions need updating
"""


def render_profile_tree(profile: str) -> str:
    spec = get_profile_spec(profile)
    lines = [
        "<wiki-root>/",
        "├── AGENTS.md              # Domain schema (editable; shared with non-Claude agents)",
        "├── CLAUDE.md              # Imports @AGENTS.md for Claude Code (keep thin; fixed stub from lwiki init)",
        "├── assets/                # Attachments (images, PDFs) — self-contained",
        "├── raw/                   # Immutable source documents (LLM reads, never modifies)",
        "│   ├── files.log          # Auto-generated file tracking (name + sha256)",
        "│   └── ...",
        "└── wiki/",
        "    ├── index.md           # Content catalog — every page with link + one-line summary",
        "    ├── log.md             # Append-only chronological operation log",
        "    ├── purpose.md         # Why this wiki exists and what it should preserve",
        "    ├── overview.md        # High-level evolving synthesis across all sources",
    ]
    for section_name, dir_name in spec.tree_sections:
        lines.append(f"    ├── {dir_name}/{' ' * (19 - len(dir_name))}# {section_name} pages")
    return "\n".join(lines)


def render_structure_text(profile: str) -> str:
    """Full text for `lwiki structure` (tree + required commands)."""
    spec = get_profile_spec(profile)
    return f"""{render_profile_tree(profile)}
Commands (install the `lwiki` CLI if missing):
  lwiki init <wiki-root> --domain \"...\" --sources \"...\" --profile {spec.name}   create this layout + initial raw/files.log
  lwiki raw sync                                                                    from wiki root: refresh raw/files.log
  lwiki raw status                                                                  from wiki root: report drift (no write)
  lwiki analyze <wiki-root> [--write]                                                inspect backlinks, hubs, orphans, broken links
  lwiki compile <wiki-root>                                                         compile raw sources into deterministic summary pages
  lwiki schema <wiki-root>                                                          validate controlled schema keys and page types
  lwiki review <wiki-root> [--write]                                                generate deterministic review queue from health issues
  lwiki eval <suite-file> [--root . --mode standard]                                run reproducible query eval cases (question | expected_slug)
  lwiki audit <wiki-root> [--eval-suite wiki/eval-suite.txt]                        run analyze+schema+review and optional eval as one gate
  lwiki query <question> [--root . --mode quick|standard|deep|thesis|list]          query the wiki and optionally save an insight
  lwiki dashboard <wiki-root> [--out knowledge-digest.html] [--open]                write a desktop-style HTML dashboard
  lwiki serve <wiki-root> [--host 127.0.0.1 --port 8765 --open]                     run a local desktop-like web workspace
  lwiki harvest <wiki-root>                                                          snapshot tool memories into raw/ and refresh wiki
  lwiki watch <wiki-root> [--eval-suite wiki/eval-suite.txt]                        detect source drift, refresh if changed, and audit
  lwiki export <wiki-root>                                                           write llms.txt, llms-full.txt, and llms.json exports
  lwiki schedule <wiki-root>                                                         generate a launchd bundle for recurring watch+audit runs
"""
