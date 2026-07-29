# LLM-WorkMem Lean Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce LLM-WorkMem to one canonical workflow, one current project-memory layer, and bounded source evidence while preserving verified cross-tool recall.

**Architecture:** Keep the existing file-based Retain/Recall/Reflect, event inbox, project pages, adapters, CBMEM bridge, supervisor, and health checks. Remove high-volume chat sources, make generated harvest/radar outputs stable, exclude operational snapshots from wiki compilation, and narrow AI exports to durable pages.

**Tech Stack:** Python 3, pytest, Ruff, Markdown/YAML frontmatter, macOS launchd, existing `lwm` CLI.

## Global Constraints

- Native IDE and shell instructions remain authoritative; LLM-WorkMem is auxiliary evidence.
- Do not add a database, vector store, resident LLM, new event schema, or second memory repository.
- Do not modify unrelated existing worktree changes in `.codebase-memory/` or `global/config/`.
- Do not delete native IDE files or shell configuration; only stop bulk-copying them into LLM-WorkMem.
- Preserve raw work events and current CBMEM fail-open behavior.
- Any cleanup must target known generated paths and be verified after regeneration.

### Task 1: Lock the lean source and output contracts with tests

**Files:**
- Modify: `tests/test_harvest_slimming.py`
- Modify: `tests/test_compile.py` if present, otherwise create `tests/test_compile.py`
- Modify: `tests/test_export.py` if present, otherwise create `tests/test_export.py`
- Modify: `tests/test_project_memory.py` if present, otherwise create `tests/test_project_memory.py`

**Interfaces:**
- Tests will cover `default_source_groups()`, `harvest_sources()`, `_compact_historical_harvest_pages()`, `compile_raw_sources()`, `write_analysis_report()`, `write_ai_exports()`, and project event filtering.

- [ ] Add failing tests proving full Claude history, Claude session-projects, and Copilot chat-session sources are absent from default harvest groups.
- [ ] Add failing tests proving harvest writes `wiki/insights/current-harvest.md` and analysis writes `wiki/insights/current-radar.md`.
- [ ] Add failing tests proving CBMEM and event raw trees do not create `wiki/summaries/source-*` pages.
- [ ] Add failing tests proving lifecycle-only events do not create or update durable project memory, while a verified decision still does.
- [ ] Add failing tests proving `llms.txt` excludes generated insights/review/summaries and contains canonical pages.
- [ ] Run each focused test file and confirm the failures are caused by the missing lean behavior.

### Task 2: Bound harvest inputs and generated pages

**Files:**
- Modify: `lwm/harvest.py`
- Modify: `lwm/cbmem_source.py`
- Modify: `lwm/analysis.py`
- Test: `tests/test_harvest_slimming.py` and the new focused tests from Task 1

**Interfaces:**
- `default_source_groups()` keeps rules, settings, memory, and adapter files but omits full chat/session archives.
- `harvest_sources()` writes changed source snapshots under the existing source tree without creating duplicate dated copies.
- `write_analysis_report()` returns `wiki/insights/current-radar.md`.

- [ ] Implement the smallest source filter that removes only full conversation/session archive inputs.
- [ ] Implement current snapshot output and idempotent unchanged-source behavior.
- [ ] Change CBMEM snapshots to current evidence paths and keep failures fail-open.
- [ ] Change harvest output to one stable `current-harvest.md` and remove stale generated harvest siblings during the controlled cleanup path.
- [ ] Change radar output to one stable `current-radar.md` and remove stale generated radar siblings during the controlled cleanup path.
- [ ] Run focused tests and then the harvest-related test group.

### Task 3: Stop operational data from becoming durable wiki summaries

**Files:**
- Modify: `lwm/compile.py`
- Modify: `lwm/analysis.py` only if generated-page filtering needs alignment
- Modify: `lwm/project_memory.py`
- Test: compile and project-memory tests

**Interfaces:**
- `compile_raw_sources()` ignores `raw/events/`, `raw/tool-snapshots/`, and `raw/cbmem-snapshots/`.
- Project memory accepts meaningful work events and ignores lifecycle-only events.

- [ ] Add the CBMEM prefix to compile exclusions.
- [ ] Add a bounded cleanup helper for known legacy `source-events-*` and `source-cbmem-*` generated summary pages.
- [ ] Keep explicit durable migration and hand-authored source summaries intact.
- [ ] Add the project-memory meaningful-event predicate and preserve event evidence in `raw/events/`.
- [ ] Run compile, ingest, project-memory, and audit tests.

### Task 4: Reduce context duplication and export noise

**Files:**
- Modify: `lwm/export.py`
- Modify: `lwm/adapters.py`
- Modify: `GLOBAL.md`
- Modify: `wiki/purpose.md`
- Modify: `wiki/overview.md`
- Regenerate: `adapters/*.md`, `adapters/*.mdc`, and shell adapter from the existing generator
- Test: adapter, context, export, and health tests

**Interfaces:**
- Generated adapters state that LLM-WorkMem supplies auxiliary evidence and must not override native tool instructions.
- `llms.txt` and `llms-full.txt` include canonical durable pages while excluding generated review, summary, and historical report noise.

- [ ] Replace the obsolete `.memory/STATE.md` contract in `GLOBAL.md` with the actual canonical sources.
- [ ] Rewrite `wiki/purpose.md` as the concise memory inclusion/exclusion policy.
- [ ] Rewrite `wiki/overview.md` as the current system synthesis while preserving harvest status updates.
- [ ] Update `_context_block()` and its generated adapter variants to the auxiliary-only wording.
- [ ] Narrow AI exports to purpose, overview, global, projects, concepts, entities, and current durable pages.
- [ ] Regenerate adapters and run context/adapter/export tests.

### Task 5: Controlled cleanup and runtime rebuild

**Files:**
- Delete only known generated files under `wiki/insights/`, legacy generated `wiki/summaries/`, and lifecycle-only `wiki/projects/` pages after source verification.
- Delete only tracked obsolete `*.before-wave-*` files listed by the audit.
- Modify: generated `llms.txt`, `llms-full.txt`, `llms.json`, `knowledge-digest.html`, and runtime mirrors through existing commands.

**Interfaces:**
- Cleanup must leave raw events, durable wiki pages, current project pages, current radar/harvest, and manually authored summaries.

- [ ] Produce a read-only cleanup manifest listing every candidate and its preservation source.
- [ ] Move or remove only candidates covered by the manifest; do not use broad recursive deletion.
- [ ] Run `lwm harvest` or the repository-supported refresh path to rebuild generated outputs and prune the runtime mirror.
- [ ] Verify no old dated harvest/radar pages, generated event/CBMEM summaries, or obsolete backup files remain in the active tree.

### Task 6: Full verification and write-back

**Files:**
- Modify: the current project memory page through the supported event/write-back path only
- Modify: `wiki/overview.md` through the supported harvest path only

- [ ] Run the full pytest suite.
- [ ] Run Ruff over the repository.
- [ ] Run schema/audit and strict health checks.
- [ ] Run a real `lwm hub context --tool codex --project ...` and confirm project scope plus canonical memory.
- [ ] Verify launchd remains loaded and the last harvest exit code is zero.
- [ ] Verify adapter files for Codex, Claude Code, OpenCode, VS Code, Kiro, Antigravity, Trae, Trae Solo, MiniMax, and shell contain the compact auxiliary pointer.
- [ ] Record the cleanup decision, exact size/page-count reduction, and verification evidence as one sanitized LLM-WorkMem event.
- [ ] Stage only files changed by this plan and report unrelated worktree changes untouched.

## Verification commands

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev lwm audit .
uv run --extra dev lwm hub health .
lwm hub context --tool codex --project "$PWD" "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
launchctl list | grep com.ethan.lwm.harvest
```
