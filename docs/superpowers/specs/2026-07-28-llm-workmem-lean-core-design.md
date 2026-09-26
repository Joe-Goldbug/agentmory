# LLM-WorkMem Lean Core

- Date: 2026-07-28
- Status: approved for implementation
- Scope: remove repeated workflow instructions, generated memory noise, and redundant snapshots while preserving cross-tool evidence recall.

## Goal

Keep LLM-WorkMem as one small, source-backed auxiliary memory center for local IDEs and shell. It must retain verified project decisions, changes, verification results, risks, and open loops without collecting full conversations or creating repeated daily pages.

## Design Precedence

This Lean Core document is the current architecture boundary. The V2 control
plane document dated 2026-07-18 is historical rationale only. It may
contribute non-conflicting privacy, identity, provenance, retention, and
verification requirements, but its second control-plane authority,
`projects/<id>/STATE.md` hierarchy, and any conflicting source-of-truth rule
are superseded. New implementation work must follow Lean Core, the approved
goal-completion requirements, and their derived HLD/LLD rather than reviving
the historical V2 hierarchy.

## Non-goals

- No second database, vector store, resident LLM, or new memory service.
- No new event fields or new memory hierarchy.
- No replacement of Codex, Claude Code, OpenCode, VS Code, Kiro, Trae, Antigravity, or MiniMax native instructions and memory.
- No deletion of raw work events that are still within the existing retention policy.

## Canonical workflow sources

1. Native tool instructions remain authoritative.
2. `GLOBAL.md` is the single cross-tool workflow contract.
3. `wiki/purpose.md` is the single memory inclusion and exclusion policy.
4. `wiki/overview.md` is the current synthesis and automation status.
5. `wiki/projects/<project_id>.md` is the single project memory page.
6. `raw/events/` is append-only operational evidence; lifecycle receipts do not become durable project knowledge by themselves.
7. Generated adapters contain only a compact pointer to the above sources and the auxiliary-only authority boundary.

Historical design documents remain under `docs/` but are excluded from normal context and AI exports.

## Lean runtime policy

- Do not snapshot full Claude history, Claude session-project directories, or VS Code Copilot chat sessions.
- Continue recording sanitized lifecycle and meaningful work events through the existing adapters.
- Store current tool source snapshots only when content changes; do not create a dated copy for unchanged content.
- Keep CBMEM as current/on-demand code evidence. Do not compile dated CBMEM snapshots into wiki summary pages.
- Generate one stable current harvest page and one stable current radar page; remove stale generated siblings after preserving their durable project/event evidence.
- Compile only explicit durable source files. Legacy event summaries and CBMEM summaries are excluded and removed from the live wiki.
- Keep empty lifecycle-only project pages out of the durable project-memory layer.

## Active memory shape

```text
wiki/
  purpose.md
  overview.md
  global/          audited cross-project rules
  projects/        one page per project with meaningful work
  concepts/        small reusable concepts
  entities/        current tool/project entities
  insights/
    current-harvest.md
    current-radar.md
  review/          candidates awaiting review
summaries/         only durable, explicitly compiled source summaries
raw/
  events/          sanitized work evidence
  tool-snapshots/  current changed source evidence
  cbmem-snapshots/ current code evidence
```

## Cleanup safety

- Before removing generated pages, verify the source event, current project page, or durable wiki page exists.
- Do not touch unrelated user modifications in the worktree.
- Do not delete native IDE memory, shell configuration, or source files; only stop copying them wholesale into LLM-WorkMem.
- Rebuild `llms.txt`, `llms-full.txt`, `llms.json`, dashboard exports, and runtime mirrors after cleanup.

## Acceptance criteria

- A harvest cycle no longer creates duplicate dated harvest/radar pages for unchanged state.
- Full chat/session archives are not copied by default.
- `wiki/summaries` contains no generated event or CBMEM summary pages.
- `llms.txt` is compact and points to canonical pages only.
- Context still resolves project memory and recent verified activity.
- Existing event ingest, recall, CBMEM fail-open behavior, health, supervisor, and adapter tests remain green.
- Full pytest, Ruff, audit, health, and a real `lwm hub context` run pass after implementation.
