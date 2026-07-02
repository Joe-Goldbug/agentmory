# CBMEM — Code-Graph Queries

Use this reference when the user asks about a **project's code structure**: where a symbol is defined, who calls it, what a diff actually changes, what code is dead, or what the architecture looks like at a glance. CBMEM is `lwm cbmem *`; it wraps `DeusData/codebase-memory-mcp` (v0.8.1).

## When to use

- "What calls `run_query` in `<dir>`?"
- "Where is `MemoryPolicy` defined?"
- "Show me the architecture of `<dir>`."
- "What symbols did commit `abc123` touch?"
- "Is there dead code in `<dir>`?"

## When NOT to use

- The user is asking about a wiki page → use [query.md](query.md).
- The user wants to edit a project → use [update.md](update.md) on the wiki, or just edit the project directly.
- The 270 MB binary is not installed → tell the user to run `bash automation/install-cbmem.sh` first.

## Subcommands (10 total)

| User intent | Subcommand |
|---|---|
| Is the binary there? | `lwm cbmem doctor` |
| Build the graph for a project | `lwm cbmem index <dir>` |
| How far along is the index? | `lwm cbmem index-status <dir>` |
| Where is symbol X? | `lwm cbmem search <dir> X` |
| Project overview | `lwm cbmem architecture <dir>` |
| Call graph for symbol X | `lwm cbmem trace <dir> X` |
| What did a diff touch? | `lwm cbmem changes <dir> [--base REF]` |
| Dead code candidates | `lwm cbmem dead <dir>` |
| Ad-hoc graph search | `lwm cbmem query <dir> "<cypher-like string>"` |
| Semantic search | `lwm cbmem semantic <dir> "<phrase>"` |

Every subcommand except `doctor`, `index`, and `index-status` requires the project to be indexed. The wrapper checks `is_indexed(<dir>)` (i.e. `<dir>/.codebase-memory/graph.db.zst` exists) and exits with code 2 and a "run `lwm cbmem index <dir>` first" hint if not.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | Binary not found, or the call returned a non-zero exit code |
| 2 | Project is not yet indexed, or input was empty |

## Edge cases

- **macOS sandbox SIGKILLs the binary with exit 137.** Run from a real terminal. If you (the agent) are inside Claude Code's Bash sandbox, surface a clear "this needs to be run from a real shell" message to the user.
- **The binary returns text in `query` mode and JSON in `--json` mode.** The wrapper always asks for `--json`; if the binary's `--json` flag ever changes name, fix it in `lwm/cbmem.py:_run`, not in this reference.
- **Long output is truncated** to 500–2000 chars in the pretty-printer. If the user wants the full payload, call `cbmem.<tool>(...)` from Python and read `result.stdout`.
- **`lwm cbmem query ""`** (empty Cypher) exits with code 2 and a clear stderr message — never a stack trace.

## How cbmem fits into lwm's automation

cbmem is **not** a manual tool. Every launchd cycle (every 12 hours), `lwm watch` calls `harvest_cbmem(root)` which reads `lwm-sources.json::cbmem.projects` and writes dated snapshots under `raw/cbmem-snapshots/<YYYY-MM-DD>/<project>/`. So cbmem output lands in the wiki's raw pipeline automatically — no agent action required once you've listed a project in the config.

To add a project to the auto-harvest, edit `lwm-sources.json`:

```json
{
  "cbmem": {
    "projects": ["/Users/you/projects/foo", "/Users/you/projects/bar"],
    "search_queries": ["<TODO>", "<FIXME>", "<XXX>"]
  }
}
```

The audit step (`lwm audit <dir>`) reports `CBMEM: X/Y projects indexed` so you can see what's covered.

## See Also

- [lwm-cbmem-cheatsheet](../../wiki/summaries/lwm-cbmem-cheatsheet.md) — quick command reference
- [codebase-memory](../../wiki/entities/codebase-memory.md) — tool entity
- [integrations-2026-06-30](../../wiki/insights/integrations-2026-06-30.md) — decision record
- [code-graph-querying](../../wiki/concepts/code-graph-querying.md) — concept