---
title: lwiki cbmem Cheatsheet
type: summary
tags: [summary, cbmem, lwiki-extension, cheatsheet, reference]
sources: []
updated: 2026-06-30
---

# lwiki cbmem Cheatsheet

> One-page reference for the 9 `lwiki cbmem *` subcommands. For *why*
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
lwiki cbmem doctor   # should print [cbmem doctor] OK
```

## Commands at a glance

| Command | What it does | When to use |
|---|---|---|
| `lwiki cbmem doctor` | Check binary resolves + responds | First run, after upgrades |
| `lwiki cbmem index <dir>` | Build / refresh the code graph for `<dir>` | First use of `<dir>`, after major refactors |
| `lwiki cbmem search <dir> <q>` | Symbol/text search across the graph | "Where is X defined or used?" |
| `lwiki cbmem architecture <dir>` | Languages, packages, entry points, routes, hotspots | Onboarding to a new project |
| `lwiki cbmem trace <dir> <sym>` | Call-graph edges from `<sym>` | "What does X call / who calls X?" |
| `lwiki cbmem changes <dir>` | Map a git diff to affected symbols with risk classification | Pre-merge impact check |
| `lwiki cbmem dead <dir>` | Symbols with no incoming callers | Dead-code candidate hunt |
| `lwiki cbmem query <dir> <cypher>` | Ad-hoc graph query | "Show me routes that call into package Y" |
| `lwiki cbmem semantic <dir> "<q>"` | Vector search over indexed symbols | "Find code semantically similar to…" |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | OK |
| `1` | Binary not found / API call failed |
| `2` | `<dir>` is not yet indexed (run `lwiki cbmem index <dir>` first) |

The four commands that need an existing graph
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
lwiki cbmem index .
lwiki cbmem architecture .

# Find something
lwiki cbmem search . QueryReport
lwiki cbmem trace . run_query

# Pre-merge check
lwiki cbmem changes . --base main

# Quarterly cleanup
lwiki cbmem dead . | head -30
```

## Output handling

- The wrapper preserves the binary's stdout verbatim. With `lwiki cbmem`
  subcommands that map to `--json` upstream, the output is JSON.
- Pretty-printers (`render_*_report` in `lwiki/cbmem.py`) are used by
  the CLI layer; programmatic callers get the raw `CbmemResult` and
  decide their own formatting.
- Long outputs are truncated to 500–2000 chars in the pretty-printer
  to keep the terminal readable.

## Programmatic use

```python
from pathlib import Path
from lwiki import cbmem

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

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `CbmemNotFoundError` | Binary not on PATH or in `~/bin/` | Run the install block above; or `export LBM_CBMEM_BIN=/path/to/binary` |
| Exit 137 / -9 | Sandbox / shell killed the 270 MB binary | Run from a real terminal, not the Claude Code Bash sandbox |
| Exit 2 on `search` | `<dir>` is not indexed | `lwiki cbmem index <dir>` first |
| Stale results | Graph is from before recent edits | `lwiki cbmem index <dir> --force` |

## See Also

- [[codebase-memory]] — tool entity
- [[code-graph-querying]] — the concept
- [[integrations-2026-06-30]] — decision record
- [[architecture-policy]]
- [[workflow-policy]] — where cbmem fits explore → plan → execute → verify