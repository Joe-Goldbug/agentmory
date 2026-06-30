"""Create a new wiki directory tree (LLM Wiki INIT)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from lwiki.profiles import (
    DEFAULT_PROFILE,
    get_profile_spec,
    render_agents_md,
    render_index_md,
    render_purpose_md,
    render_overview_md,
)

# Default for AGENTS.md "Source Types" when `lwiki init` is run without `--sources`.
DEFAULT_SOURCE_TYPES = get_profile_spec(DEFAULT_PROFILE).source_focus

# Thin CLAUDE.md for Claude Code: imports AGENTS.md (see https://code.claude.com/docs/en/memory#agents-md).
CLAUDE_MD_STUB = """@AGENTS.md

## LLM Wiki (Claude Code)

Domain schema and conventions live in **AGENTS.md** (co-edited with the wiki). This file is fixed: edit `AGENTS.md` to change rules; keep the `@AGENTS.md` import so Claude Code loads the same content as other agents.
"""


def wiki_markers_exist(wiki_root: Path) -> bool:
    return (wiki_root / "wiki" / "index.md").is_file() and (wiki_root / "wiki" / "log.md").is_file()


def render_log_md(today: str, domain: str) -> str:
    return f"""# Wiki Log

Append-only. Format: `## [YYYY-MM-DD] <operation> | <title>`
Quick view: `grep "^## \\[" log.md | tail -10`

---

## [{today}] init | {domain}
"""


def render_eval_suite_template() -> str:
    return """# question | expected_slug
# Replace with your real workflow-memory and project questions.
workflow memory governance model | memory-governance
tool harvest automation workflow | tool-harvest
"""


def render_memory_policy_md(today: str) -> str:
    return f"""---
title: Memory Policy
type: concept
tags: [concept, memory, policy]
sources: []
updated: {today}
---

# Memory Policy

The global layer holds durable working style, communication preferences, and cross-project rules.

## Key Points

- Keep project-specific analysis out of the global layer.
- Promote only stable, reusable patterns.
- Treat the wiki as the source of truth for long-lived memory.

## See Also

- [[workflow-policy]]
- [[architecture-policy]]
- [[what-survives-promotion]]
"""


def render_workflow_policy_md(today: str) -> str:
    return f"""---
title: Workflow Policy
type: concept
tags: [concept, workflow, epev]
sources: []
updated: {today}
---

# Workflow Policy

The default workflow is explore, plan, execute, verify.

## Key Points

- Do not write first when the task still needs clarification.
- Make review and verification explicit steps.
- Keep high-impact changes small and test after each edit.

## See Also

- [[memory-policy]]
- [[architecture-policy]]
- [[tooling-policy]]
"""


def render_architecture_policy_md(today: str) -> str:
    return f"""---
title: Architecture Policy
type: concept
tags: [concept, architecture, hub]
sources: []
updated: {today}
---

# Architecture Policy

The wiki is the shared knowledge body; tools are readers and writers, not the final memory store.

## Key Points

- Use the wiki as the durable coordination layer.
- Keep raw inputs separate from curated pages.
- Prefer links and snapshots over implicit state.

## See Also

- [[project-memory]]
- [[claude-code]]
- [[obsidian]]
"""


def render_tooling_policy_md(today: str) -> str:
    return f"""---
title: Tooling Policy
type: concept
tags: [concept, tooling, claude-code, cursor, vscode, opencode]
sources: []
updated: {today}
---

# Tooling Policy

Claude Code, Codex, VSCode, Trae, Cursor, and OpenCode are execution surfaces that read the same wiki rules.

## Key Points

- Keep the rules centralized.
- Let tools read the same source of truth.
- Reuse the same memory shape across tools.

## See Also

- [[architecture-policy]]
- [[memory-policy]]
- [[claude-code]]
"""


def render_project_memory_md(today: str) -> str:
    return f"""---
title: Project Memory
type: entity
tags: [entity, memory, project]
sources: []
updated: {today}
---

# Project Memory

Project memory is the local place for bugs, implementation notes, and project-specific judgment.

## Key Points

- Keep project facts local.
- Promote only durable working rules.
- Do not let project noise overwrite the global layer.

## See Also

- [[memory-policy]]
- [[architecture-policy]]
"""


def render_legacy_source_vault_md(today: str) -> str:
    return f"""---
title: Legacy Source Vault
type: entity
tags: [entity, legacy, source, vault]
sources: []
updated: {today}
---

# Legacy Source Vault

This node represents older source material that has been migrated into the wiki.

## Key Points

- Historical material remains readable.
- Current rules live in llm-wiki.
- The vault is a source, not the active memory center.

## See Also

- [[memory-policy]]
- [[project-memory]]
- [[obsidian]]
"""


def render_obsidian_md(today: str) -> str:
    return f"""---
title: Obsidian
type: entity
tags: [entity, vault, notes]
sources: []
updated: {today}
---

# Obsidian

Obsidian is the historical note surface, now treated as a legacy source vault in this setup.

## See Also

- [[legacy-source-vault]]
- [[project-memory]]
"""


def render_claude_code_md(today: str) -> str:
    return f"""---
title: Claude Code
type: entity
tags: [entity, tool, claude-code, cli]
sources: []
updated: {today}
---

# Claude Code

Claude Code is one of the tool surfaces that reads the shared wiki rules and memory.

## See Also

- [[tooling-policy]]
- [[memory-governance]]
"""


def render_tool_harvest_md(today: str) -> str:
    return f"""---
title: Tool Harvest
type: entity
tags: [entity, harvest, automation]
sources: []
updated: {today}
---

# Tool Harvest

Canonical hub for recurring tool-memory harvest snapshots.

## Notes

- Use this as the stable wikilink target for `[[tool-harvest]]`.

## See Also

- [[memory-governance]]
- [[overview]]
"""


def render_promotion_insight_md(today: str) -> str:
    return f"""---
title: What Survives Promotion
type: insight
tags: [insight, promotion, memory]
sources: []
updated: {today}
---

# What Survives Promotion

Only stable working style, communication preferences, and AI rules should move into the global layer.

## See Also

- [[memory-policy]]
- [[project-memory]]
- [[obsidian]]
"""


def init_wiki_tree(
    wiki_root: Path,
    *,
    domain: str,
    source_types: str,
    force: bool,
    profile: str = DEFAULT_PROFILE,
) -> None:
    """
    Create wiki layout under wiki_root. Aligns with skills/llm-wiki INIT references.
    Raises FileExistsError if wiki exists and force is False.
    """
    wiki_root = wiki_root.resolve()
    if wiki_markers_exist(wiki_root) and not force:
        raise FileExistsError(
            f"Wiki already exists at {wiki_root} (found wiki/index.md and wiki/log.md). "
            "Use --force to overwrite."
        )

    today = date.today().isoformat()
    spec = get_profile_spec(profile)

    (wiki_root / "assets").mkdir(parents=True, exist_ok=True)
    (wiki_root / "raw").mkdir(parents=True, exist_ok=True)
    for _section_name, sub in spec.tree_sections:
        (wiki_root / "wiki" / sub).mkdir(parents=True, exist_ok=True)

    (wiki_root / "AGENTS.md").write_text(
        render_agents_md(domain, source_types, profile), encoding="utf-8"
    )
    (wiki_root / "CLAUDE.md").write_text(CLAUDE_MD_STUB, encoding="utf-8")
    (wiki_root / "wiki" / "index.md").write_text(
        render_index_md(domain, profile), encoding="utf-8"
    )
    (wiki_root / "wiki" / "log.md").write_text(render_log_md(today, domain), encoding="utf-8")
    (wiki_root / "wiki" / "purpose.md").write_text(
        render_purpose_md(domain, today, profile), encoding="utf-8"
    )
    (wiki_root / "wiki" / "overview.md").write_text(
        render_overview_md(domain, today, profile), encoding="utf-8"
    )
    (wiki_root / "wiki" / "concepts" / "memory-policy.md").write_text(
        render_memory_policy_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "concepts" / "workflow-policy.md").write_text(
        render_workflow_policy_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "concepts" / "architecture-policy.md").write_text(
        render_architecture_policy_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "concepts" / "tooling-policy.md").write_text(
        render_tooling_policy_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "entities" / "project-memory.md").write_text(
        render_project_memory_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "entities" / "legacy-source-vault.md").write_text(
        render_legacy_source_vault_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "entities" / "obsidian.md").write_text(
        render_obsidian_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "entities" / "claude-code.md").write_text(
        render_claude_code_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "entities" / "tool-harvest.md").write_text(
        render_tool_harvest_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "insights" / "what-survives-promotion.md").write_text(
        render_promotion_insight_md(today), encoding="utf-8"
    )
    (wiki_root / "wiki" / "eval-suite.txt").write_text(
        render_eval_suite_template(),
        encoding="utf-8",
    )
