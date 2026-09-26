# llm-workmem

<p align="center">
  <img src="assets/logo.svg" alt="llm-workmem" width="480" /><br />
  <sub>LLM-powered personal knowledge base</sub>
</p>

An LLM-WorkMem that evolves with you. Based on [Karpathy's LLM-WorkMem](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

[Chinese](README.zh-CN.md)

This repo ships two things:

| What | Path | Purpose |
|------|------|---------|
| **Skill** | `skills/llm-workmem/` | Agent skill (OpenCode, Claude Code / Cursor / Copilot) — INIT, INGEST, QUERY, UPDATE, LINT |
| **CLI** | `lwm/` | Python CLI — scaffold wiki trees and track `raw/` drift |

For a more opinionated personal knowledge body, use `lwm init --profile personal` and `lwm analyze` to inspect hubs, orphans, broken links, and missing sources. Use `lwm query` for quick/deep/thesis synthesis, `lwm dashboard` for a desktop-style snapshot, `lwm serve` for the live local workspace, `lwm harvest` to snapshot tool memories into the wiki, `lwm watch` to refresh only when source drift changes, `lwm export` to write `llms.txt`/`llms-full.txt`/`llms.json`, `lwm adapters`/`lwm attach` to let IDEs and shells consume the wiki, and `lwm schedule` to generate a recurring launchd bundle.

## Evidence Recall B2

`lwm hub recall` returns a project-scoped evidence packet instead of only page hits:

```bash
lwm hub recall "What was verified in this project recently?" \
  --project "/path/to/project" \
  "/path/to/LLM-WorkMem"
```

The packet includes the project identity, retrieval plan, evidence sources, current/historical/conflicted state, missing dimensions, and a `coverage` result. `compact` is the default; use `--mode deep --format markdown` when a deeper audit is needed. If a project cannot be resolved, the result is explicitly `global-only` rather than being presented as project memory.

This layer organizes evidence for IDEs and shells; it does not generate their final answer. Reads remain available when receipts or CBMEM are unavailable, while the degraded state is surfaced in warnings and health checks.

## Unified Local Tool Interface

The local hub can collect bounded evidence from IDEs, CLI agents, and the
interactive shell, then return project context and handoffs to those tools.
It remains an auxiliary evidence layer: each tool's native instructions,
skills, planning, execution, and verification stay authoritative.

Set the data root once, then run the installation steps locally:

```bash
export LWM_ROOT="/path/to/LLM-WorkMem"
lwm install-global "$LWM_ROOT" --dry-run
lwm install-global "$LWM_ROOT"
lwm hub install-ide-hooks "$LWM_ROOT"
lwm hub install-shell-hook "$LWM_ROOT"
```

Check what is installed and what has real evidence before relying on a tool:

```bash
lwm hub tools probe --root "$LWM_ROOT" --json
lwm hub coverage --root "$LWM_ROOT" --json
```

At session start, a tool can request bounded project context. At completion,
it can write only structured work evidence and an optional handoff:

```bash
lwm hub context --tool codex --project "$PWD" "$LWM_ROOT"
lwm hub lifecycle stop --tool codex --project "$PWD" \
  --task-id "$LWM_TASK_ID" \
  --handoff-json '{"task_id":"...","objective":"...","changes":[],"verifications":[],"risks":[],"open_questions":[],"next_action":"..."}' \
  --root "$LWM_ROOT"
```

`watcher-observed` means the local file or session boundary was observed;
only a qualifying native hook receipt can be reported as verified tool
integration. Use `lwm hub tools probe` and `lwm hub coverage` rather than
assuming that a generated instruction file proves bidirectional support.

## Quick Start

You can do the manual installation without needing `uv` or `act-cli`.
However, it will be quicker to sync with this repo if you use the manifest file.

### 1. Requirements

- `uv` is installed, get it from [here](https://docs.astral.sh/uv/getting-started/installation/) if it is not.
- Install `act-cli` with:

```bash
uv tool install https://github.com/hsuanguo/act-cli.git
```

### 2. Create an `act.toml`

Add an `act.toml` to your wiki root:

```toml
[project]
name = "my-wiki"
description = "My LLM-WorkMem"

[skills]
llm-workmem = "hsuanguo/llm-workmem/skills/llm-workmem"

[dependencies.tools.uv]
lwm = "git+https://github.com/hsuanguo/llm-workmem.git"
```

### 3. Sync

Just do:

```bash
act
```

This installs the `llm-workmem` agent skill and the `lwm` CLI tool.

## Manual Setup

Install the CLI:

```bash
pip install .
# or with uv:
uv tool install .
```

Copy the skill into your wiki:

```bash
cp -r skills/llm-workmem /path/to/project/.claude/skills/
```

## Skill

The `skills/llm-workmem/` directory is a self-contained agent skill with:

- **`SKILL.md`** — main instructions (gather context, route to operation, execute)
- **`references/`** — per-operation playbooks: `init.md`, `ingest.md`, `query.md`, `update.md`, `lint.md`, `harvest.md`, `watch.md`, `export.md`, `schedule.md`
- **`templates/`** — starter page templates: `index.md`, `concept.md`, `entity.md`, `insight.md`, `summary.md`

Works with any agent that reads `SKILL.md` from `.claude/skills/` or similar conventions.

`.claude/skills/` is supported by most AI agents (OpenCode, Cursor, etc.). If your agent does not support this location, move it to the path your agent expects.

## Usage

This wiki skill is markdown-first and works with any frontend that can read the generated wiki pages. The typical workflow can be described as below.

<p align="center">
  <img src="assets/flow.svg" alt="wiki-flow" width="600" /><br />
</p>

### 1. Create a New Wiki (INIT)

Tell Agent:

```
Init a wiki at wiki/greek-history for Greek history
```

AI Agent will:
- Run `lwm init` to create the directory structure
- Generate `AGENTS.md` (domain schema), `CLAUDE.md`, and starter wiki files
- Create empty `raw/`, `assets/`, and wiki subdirectories

**Result:**
```
wiki/greek-history/
├── AGENTS.md           # Your domain schema
├── CLAUDE.md           # Auto-imports AGENTS.md
├── assets/
├── raw/
│   └── files.log
└── wiki/
    ├── index.md
    ├── log.md
    ├── purpose.md
    ├── overview.md
    ├── summaries/
    ├── concepts/
    ├── entities/
    └── insights/
```

### 2. Add Sources (INGEST)

#### Option A: Files

Move source files (PDF, Markdown, etc.) into `wiki/greek-history/raw/`

Then tell AI:
```
Ingest all new sources in raw/
```

#### Option B: Paste content directly

```
Add this to the wiki:
<paste article text or URL>
```

#### What happens during ingest

AI will:
1. Read each source in full
2. Create or update pages in `summaries/`, `concepts/`, `entities/`
3. Run a backlink audit — add `[[wikilinks]]` across existing pages
4. Scan the entire wiki for pages affected by the new information (cascade update)
5. Update `index.md`, `overview.md`, and `log.md`
6. Sync `raw/files.log` via `lwm raw sync`

**Note:** AI Agent proceeds autonomously. It only asks you when something is genuinely unclear (ambiguous facts, conflicting sources it can't resolve).

### 3. Ask Questions (QUERY)

```
What do we know about the Peloponnesian War?
```

```
Compare Athenian and Spartan military strategies across all sources
```

```
What are the unresolved questions about the fall of Mycenaean civilization?
```

AI answers strictly from wiki content, citing pages with `[[wikilinks]]`. After answering, it may:
- **Offer to save** the analysis as an insight page (if the answer has standalone value)
- **Report issues** found in existing pages (outdated info, contradictions) and ask if you want to fix them

### 4. Update Pages (UPDATE)

#### User-triggered (you ask for changes)

```
Update concepts/democracy.md — the latest source says X
```

```
Fix the contradiction between concepts/oligarchy.md and concepts/democracy.md
```

Agent shows a diff for each page and waits for your confirmation before writing.

#### LLM-triggered (during ingest)

When new sources affect existing pages, AI Agent updates them automatically if the change is straightforward. It asks you only for uncertain or meaning-altering changes.

### 5. Health Check (LINT)

```
Lint the wiki
```

AI checks for:

| Category | Auto-fixed? | Examples |
|----------|-------------|---------|
| **Deterministic** | Yes | Broken links, missing frontmatter, index inconsistencies |
| **Heuristic** | No — reports only | Contradictions, stale claims, orphan pages, missing cross-references, stale insights |

Writes a lint report to `insights/lint-<date>.md` and offers fixes for heuristic issues.

### 6. Check for New Sources (Drift Detection)

```
Any new files in raw/?
```

Or run directly:

```bash
lwm raw status    # report only
lwm raw sync      # update files.log
```

## Daily Workflow

| You do | AI does |
|--------|-------------|
| Clip articles → drop in `raw/` | Ingest, summarize, cross-reference |
| Ask questions | Answer from wiki, offer to save insights |
| Say "lint" occasionally | Health check, fix issues, suggest gaps |
| Review and guide | Everything else |

## Multi-Wiki Setup

You can have multiple wikis under one vault:

```
vault/wiki/
├── greek-history/   # One knowledge base
├── health/          # Another
└── reading/         # Another
```

Each wiki is fully independent with its own `AGENTS.md` schema. Agent loads the right schema automatically based on which directory you're working in.

## Tips

- **Obsidian Web Clipper** is the fastest way to get articles into `raw/`
- **Graph view** in Obsidian shows wiki structure — hubs, orphans, clusters
- **Dataview** plugin lets you query pages by type, tags, or date
- You never write wiki pages yourself — AI handles all the maintenance
- `lwm dashboard` gives you a desktop-style HTML view of the wiki
- `lwm query` searches and synthesizes from wiki pages
- `lwm serve` turns the repo into a live local workspace you can browse
- `lwm harvest` snapshots tool-memory sources and refreshes the wiki
- `lwm watch` refreshes only when source drift changes, then audits the result
- `lwm export` writes agent-consumable `llms.txt`, `llms-full.txt`, and `llms.json`
- `lwm schedule` writes a launchd bundle for recurring watch + audit runs

### Loop Engineering control state

Scheduled work runs as one bounded loop: observe, define, decompose, execute,
evaluate, and update. Each loop stores its expected result, actual evidence,
next action, and exit state in `state/active-loop.json` or
`state/last-loop.json`. `completed_verified` requires external evidence; a
configured adapter or launchd plist alone is not completion proof.

Run `lwm hub closure <root>` to inspect the closure gate. It checks loop state,
evidence, source/runtime readability, exports, receipts, strict health, and
launchd. Missing proof is reported as `degraded` or `blocked`.

## Codebase Memory (`lwm cbmem`)

`lwm cbmem` wraps [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) so the wiki can answer code-structure questions about any project directory. The wrapper is in `lwm/cbmem.py`; the decision record is in [wiki/insights/integrations-2026-06-30.md](wiki/insights/integrations-2026-06-30.md); the cheatsheet is in [wiki/summaries/lwm-cbmem-cheatsheet.md](wiki/summaries/lwm-cbmem-cheatsheet.md).

One-time install (downloads ~270 MB into `~/bin/`):

```bash
bash automation/install-cbmem.sh
lwm cbmem doctor
```

Subcommands: `doctor`, `index`, `index-status`, `search`, `architecture`, `trace`, `changes`, `dead`, `query`, `semantic`. See `lwm cbmem --help` for the full list.

> **Note on the macOS sandbox.** Some agent sandboxes (notably Claude Code's Bash) SIGKILL the 270 MB binary with exit 137. Run `lwm cbmem *` from a real terminal, not from inside the sandbox. See [wiki/insights/integrations-2026-06-30.md](wiki/insights/integrations-2026-06-30.md) Decision 1 for the full rationale.

## License

[MIT](LICENSE)
