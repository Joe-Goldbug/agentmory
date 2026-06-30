---
name: llm-wiki
description: "Use this skill whenever work is wiki- or knowledge-base-shaped—especially if the user says wiki, knowledge base, vault notes, or raw/ in this project. Trigger on words such as `ingest wiki`, `add to wiki`, `init wiki`, or `lint wiki`, updating or revising wiki pages, and on domain-specific questions that should be answered from the wiki (what we know about X, compare A and B, gaps, contradictions)—not off-wiki trivia. Do not use for generic chat, unrelated code or tooling, or file operations with no wiki intent."
metadata:
  author: hsuanguo
  version: "1.0"
---

# LLM Wiki

An LLM wiki that evolves with you. Based on [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## How to work

Use two phases: **(1) gather context**, **(2) map the request into steps**—each step is one operation with a dedicated reference file. Read that reference *before* executing the step.

### 1. Gather context

Infer **intent** from the user’s message (bootstrap, ingest, answer from the wiki, revise pages, lint, etc.) and **state** from the vault:

- Whether a wiki already exists at the target root (`wiki/index.md` and `wiki/log.md`).
- If it exists: skim `wiki/index.md`, tail `wiki/log.md`, and inspect `raw/` when ingest, drift, or new sources matter.
- If uncertain about what a wiki structure looks like, ALWAYS run **`lwiki structure`** to get the information.

### 2. Map intention to one or more steps

Decompose the request into an **ordered list of steps**. Each step = a single primary operation. **Open the matching reference for every step** you will run; do not rely on memory alone.

| Operation | Typical trigger | Reference |
|-----------|-----------------|-----------|
| **INIT** | No wiki yet; user wants a new knowledge base | [references/init.md](references/init.md) |
| **INGEST** | New or changed files in `raw/`, pasted content, or URL to add | [references/ingest.md](references/ingest.md) |
| **QUERY** | Question that should be answered **from wiki pages**, not general knowledge | [references/query.md](references/query.md) |
| **UPDATE** | User wants edits, corrections, or merges on existing pages | [references/update.md](references/update.md) |
| **ANALYZE** | Deterministic graph inspection for hubs, orphans, broken links, and missing sources | [references/analyze.md](references/analyze.md) |
| **COMPILE** | Deterministically compile `raw/` into `wiki/summaries/` pages with source hashes | [references/compile.md](references/compile.md) |
| **SCHEMA** | Validate frontmatter keys and page type constraints | [references/schema.md](references/schema.md) |
| **REVIEW** | Build review queue items from graph/schema issues | [references/review.md](references/review.md) |
| **EVAL** | Run reproducible question suites against wiki query behavior | [references/eval.md](references/eval.md) |
| **AUDIT** | Run unified quality gate (analyze+schema+review+optional eval) | [references/audit.md](references/audit.md) |
| **LINT** | “Lint”, health check, gaps, inconsistencies, optional raw vs `files.log` drift | [references/lint.md](references/lint.md) |
| **HARVEST** | Automatically snapshot tool memory sources into raw/ and refresh wiki summaries | [references/harvest.md](references/harvest.md) |
| **WATCH** | Detect source drift, refresh if needed, and audit the current state | [references/watch.md](references/watch.md) |
| **EXPORT** | Write AI-consumable exports (`llms.txt`, `llms-full.txt`, `llms.json`) | [references/export.md](references/export.md) |
| **SCHEDULE** | Generate a launchd bundle that runs harvest on a schedule | [references/schedule.md](references/schedule.md) |

One message can imply several steps (e.g. INGEST then LINT). Order them sensibly—often INIT first if missing, then INGEST / UPDATE / QUERY, and LINT when checking health after substantive changes.

### Routing hint

```
wiki/index.md + wiki/log.md present at wiki root?
├─ No → INIT → references/init.md
├─ Yes →
│   ├─ New/changed raw/, or paste/URL to capture? → INGEST → references/ingest.md
│   ├─ Domain question grounded in the wiki? → QUERY → references/query.md
│   ├─ "analyze" / graph health / hubs / orphans / broken links? → ANALYZE → references/analyze.md
│   ├─ "compile" / raw to summaries / source hash pages? → COMPILE → references/compile.md
│   ├─ "schema" / frontmatter constraints / page type checks? → SCHEMA → references/schema.md
│   ├─ "review" / quality queue / unresolved items? → REVIEW → references/review.md
│   ├─ "eval" / benchmark / reproducible query checks? → EVAL → references/eval.md
│   ├─ "audit" / quality gate / release check? → AUDIT → references/audit.md
   │   ├─ "harvest" / tool memory snapshots / automation refresh? → HARVEST → references/harvest.md
   │   ├─ "watch" / source drift / auto-refresh if changed? → WATCH → references/watch.md
   │   ├─ "export" / llms.txt / machine-readable exports? → EXPORT → references/export.md
   │   ├─ "schedule" / recurring harvest / launchd bundle? → SCHEDULE → references/schedule.md
│   ├─ "lint" / health check / find gaps? → LINT → references/lint.md
│   ├─ Revise or correct existing pages? → UPDATE → references/update.md
│   └─ Paste or URL only? → save under raw/, then INGEST → references/ingest.md
```

## Wiki Structure

**Authoritative layout** is whatever **`lwiki structure`** prints. Run that command and treat the output as the single source of truth for INIT and whenever you need to understand the wiki structure; do not invent alternate directory trees or maintain a parallel diagram in prose.

At a glance: `<wiki-root>/` has **`AGENTS.md`** (editable domain schema), **`CLAUDE.md`** (thin file that imports `@AGENTS.md` for [Claude Code](https://code.claude.com/docs/en/memory#agents-md)), `assets/`, `raw/` (including auto-managed `files.log`), and `wiki/` with `index.md`, `log.md`, `overview.md`, plus the profile-specific content directories printed by `lwiki structure`.
The desktop-oriented snapshot adds `purpose.md` at `wiki/` root and can be generated with `lwiki dashboard`; the live browser workspace is available via `lwiki serve`. Tool memory snapshots can be refreshed with `lwiki harvest`, and recurring automation bundles can be generated with `lwiki schedule`.

## Tooling (required)

All structural operations use the **`lwiki`** CLI. Never hand-edit `files.log` or create dirs manually.

| Action | Command (wiki root as cwd unless noted) |
|--------|------------------------------------------|
| Show canonical tree | `lwiki structure` |
| Bootstrap files + dirs | `lwiki init <wiki-root> --domain "..." --sources "..." [--profile personal]` |
| Refresh `raw/files.log` | `lwiki raw sync` (or `lwiki checkout`) |
| Report drift (no write) | `lwiki raw status` |
| Inspect graph health | `lwiki analyze <wiki-root> [--write]` |
| Compile raw sources | `lwiki compile <wiki-root>` |
| Validate schema | `lwiki schema <wiki-root>` |
| Build review queue | `lwiki review <wiki-root> [--write]` |
| Run eval suite | `lwiki eval <suite-file> [--root . --mode standard]` |
| Run unified audit | `lwiki audit <wiki-root> [--eval-suite wiki/eval-suite.txt]` |
| Snapshot tool memories | `lwiki harvest <wiki-root>` |
| Generate scheduled harvest bundle | `lwiki schedule <wiki-root>` |

## Page Conventions

Page templates are in `templates/` — read the relevant template before creating a new page:
- [templates/summary.md](templates/summary.md) — source summaries
- [templates/concept.md](templates/concept.md) — concept pages
- [templates/entity.md](templates/entity.md) — entity pages
- [templates/insight.md](templates/insight.md) — insights (point-in-time snapshots, NOT cascade-updated)
- [templates/index.md](templates/index.md) — index table format
- [templates/project.md](templates/project.md) — project pages for the personal profile
- [templates/decision.md](templates/decision.md) — recorded decisions
- [templates/pattern.md](templates/pattern.md) — reusable patterns
- [templates/conflict.md](templates/conflict.md) — tensions and contradictions
- [templates/question.md](templates/question.md) — open questions
- [templates/principle.md](templates/principle.md) — validated principles
- [templates/preference.md](templates/preference.md) — personal preferences or judgment tendencies

Common rules:
- Use `[[wikilinks]]` with plain filenames — no paths (e.g., `[[rag]]` not `[[concepts/rag]]`)
- Start every page with a 1-2 sentence summary
- Every page ends with a `## See Also` section for cross-references
- Slugs: lowercase, hyphen-separated (e.g., `attention-mechanism.md`)
- Raw files: no date prefix in filename; dates tracked via frontmatter

## Key Rules

1. **LLM writes wiki; human curates sources and asks questions**
2. **raw/ is immutable** — never modify
3. **Log and index only on wiki/ file changes** — no-op queries don't write anything
4. **Ask only when uncertain** — proceed autonomously; escalate when facts are ambiguous, sources conflict, or a change would alter meaning
5. **Pages are not bound to raw files** — LLM determines relevance across the entire wiki
6. **Backlink audit on every ingest** — scan all pages for missing links to new content
7. **Insights are snapshots** — not cascade-updated; add reverse links in See Also (Obsidian backlinks invisible to LLM)
8. **Schema co-evolves** — suggest AGENTS.md changes; user confirms; log records
9. **Use lwiki CLI** for INIT, structure, and raw/files.log — see Tooling

## Tips for Users

Surface these to the user when relevant (e.g., during INIT, first ingest, or when they ask for help):

- Use `lwiki dashboard` to inspect hub pages, orphans, and the latest snapshots.
- Use `lwiki serve` for a live browser workspace.
- Use `lwiki harvest` when you want the wiki to refresh from Codex / Claude Code / VSCode working memory sources.
- Use `lwiki watch` when you want to detect source drift and refresh only when working inputs changed.
- Use `lwiki export` when another agent needs `llms.txt`, `llms-full.txt`, or JSON manifests.
- From the second source onward, pay attention to cross-source connections.
