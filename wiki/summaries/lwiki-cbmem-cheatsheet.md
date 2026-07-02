---
title: lwm cbmem Cheatsheet
type: summary
tags: [summary, cbmem, lwm-extension, cheatsheet, reference]
sources: []
updated: 2026-06-30
---

# lwm cbmem Cheatsheet

> One-page reference for the 10 `lwm cbmem *` subcommands. For *why*
> see [[integrations-2026-06-30]]. For *what* see [[codebase-memory]].
> For the underlying concept see [[code-graph-querying]].

## Install (one-time)

```bash
# Binary
curl -sSL -o /tmp/cbmem.tar.gz \
  https://github.com/DeusData/codebase-memory-mcp/releases/download/v0.8.1/codebase-memory-mcp-darwin-arm64.tar.gz
tar -xzf /tmp/cbmem.tar.gz -C ~/bin/
rm /tmp/cbmem.tar.gz
chmod +x ~/bin/codebase-memory-mcp
ln -sf ~/bin/codebase-memory-mcp ~/bin/cbmem

# Verify
lwm cbmem doctor   # should print [cbmem doctor] OK
```

## Commands at a glance

| Command | What it does | When to use |
|---|---|---|
| `lwm cbmem doctor` | Check binary resolves + responds | First run, after upgrades |
| `lwm cbmem index <dir>` | Build / refresh the code graph for `<dir>` | First use of `<dir>`, after major refactors |
| `lwm cbmem index-status <dir>` | Show index freshness (path, size, age) | Check if a re-index is needed |
| `lwm cbmem search <dir> <q>` | Symbol/text search across the graph | "Where is X defined or used?" |
| `lwm cbmem architecture <dir>` | Languages, packages, entry points, routes, hotspots | Onboarding to a new project |
| `lwm cbmem trace <dir> <sym>` | Call-graph edges from `<sym>` | "What does X call / who calls X?" |
| `lwm cbmem changes <dir>` | Map a git diff to affected symbols with risk classification | Pre-merge impact check |
| `lwm cbmem dead <dir>` | Symbols with no incoming callers | Dead-code candidate hunt |
| `lwm cbmem query <dir> <cypher>` | Ad-hoc graph query | "Show me routes that call into package Y" |
| `lwm cbmem semantic <dir> "<q>"` | Vector search over indexed symbols | "Find code semantically similar to…" |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | OK |
| `1` | Binary not found / API call failed |
| `2` | `<dir>` is not yet indexed (run `lwm cbmem index <dir>` first) |

The seven commands that need an existing graph
(`search`, `architecture`, `trace`, `changes`, `dead`, `query`, `semantic`)
all check `is_indexed(<dir>)` and return `2` with a clear hint if the
`.codebase-memory/graph.db.zst` artifact is missing.

## Common options

Most subcommands accept:

| Option | Default | Meaning |
|---|---|---|
| `--force` (index) | off | Discard existing graph and re-index from scratch |
| `--limit N` (search / semantic) | 20 / 10 | Maximum matches to return |
| `--depth N` (trace) | 3 | Maximum graph hops |
| `--base REF` (changes) | `HEAD` | Git ref to diff against |
| `--timeout SEC` (index) | 600 | Max seconds to wait |

## Typical session

```bash
cd ~/code/some-project

# First time on a project
lwm cbmem index .
lwm cbmem architecture .

# Find something
lwm cbmem search . QueryReport
lwm cbmem trace . run_query

# Pre-merge check
lwm cbmem changes . --base main

# Quarterly cleanup
lwm cbmem dead . | head -30
```

## Output handling

- The wrapper preserves the binary's stdout verbatim. With `lwm cbmem`
  subcommands that map to `--json` upstream, the output is JSON.
- Pretty-printers (`render_*_report` in `lwm/cbmem.py`) are used by
  the CLI layer; programmatic callers get the raw `CbmemResult` and
  decide their own formatting.
- Long outputs are truncated to 500–2000 chars in the pretty-printer
  to keep the terminal readable.

## Programmatic use

```python
from pathlib import Path
from lwm import cbmem

# Get a structured result
result = cbmem.search(Path("."), "QueryReport", limit=10)
if result.ok:
    try:
        data = result.json()
    except ValueError:
        data = result.stdout
else:
    raise RuntimeError(result.stderr)

# Check before issuing a graph-dependent call
if not cbmem.is_indexed(Path(".")):
    cbmem.index_project(Path("."))
```

## Automation: as part of `lwm harvest`

`lwm harvest` (and the launchd-powered `lwm watch`) automatically
captures cbmem snapshots for every project listed in `lwm-sources.json`
under `cbmem.projects`. For each project, the harvest cycle runs:

1. `index` → refreshes the code graph
2. `architecture` → languages, packages, entry points
3. `search <query>` → per-query symbol hits (default: `<TODO>`, `<FIXME>`, `<XXX>`)
4. `dead_code` → dead-code candidates
5. `changes` → git-diff impact map (base = `HEAD`)

Output lands under `raw/cbmem-snapshots/<YYYY-MM-DD>/<project>/` and is
picked up by the next `lwm compile` cycle. cbmem failures never block
the other 11 source groups.

To add a project:
```bash
# Edit lwm-sources.json → cbmem.projects and cbmem.search_queries
# Then trigger a cycle manually or wait for the next launchd tick:
lwm harvest
```

### When NOT to use harvest-based cbmem

- Interactive exploration → use `lwm cbmem search|trace|architecture *` directly
- The harvest snapshot is a regular dump, not a live graph pointer
- If a project is not in `lwm-sources.json::cbmem.projects`, it won't be indexed by harvest

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `CbmemNotFoundError` | Binary not on PATH or in `~/bin/` | Run the install block above; or `export LBM_CBMEM_BIN=/path/to/binary` |
| Exit 137 / -9 | Sandbox / shell killed the 270 MB binary | Run from a real terminal, not the Claude Code Bash sandbox |
| Exit 2 on `search` | `<dir>` is not indexed | `lwm cbmem index <dir>` first |
| Stale results | Graph is from before recent edits | `lwm cbmem index <dir> --force` |

## See Also

- [[codebase-memory]] — tool entity
- [[code-graph-querying]] — the concept
- [[integrations-2026-06-30]] — decision record
- [[architecture-policy]]
- [[workflow-policy]] — where cbmem fits explore → plan → execute → verify