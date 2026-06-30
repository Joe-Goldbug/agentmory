---
title: Codebase Memory (cbmem)
type: entity
tags: [entity, cbmem, codebase-memory, code-graph, mcp, lwiki-extension]
sources: []
updated: 2026-06-30
---

# Codebase Memory (cbmem)

> An indexable, queryable code graph for any project directory. Wrapped in lwiki
> as the `lwiki cbmem *` subcommand family.

## Profile

| Field | Value |
|---|---|
| Vendor | DeusData |
| Upstream repo | https://github.com/DeusData/codebase-memory-mcp |
| Upstream version | 0.8.1 (released 2026-06-12) |
| Binary | `~/bin/codebase-memory-mcp` (270 MB, Mach-O arm64) |
| Alias | `~/bin/cbmem` (symlink) |
| Wrapper module | `lwiki/cbmem.py` |
| CLI surface | `lwiki cbmem {doctor,index,search,architecture,trace,changes,dead,query,semantic}` |
| Languages parsed | 158 (tree-sitter, vendored) |
| Index speed | Linux kernel (28M LOC, 75K files) in 3 min |
| Query latency | < 1 ms (Cypher) / < 10 ms (name search) |
| Distribution | Single static binary, no Docker, no API key |
| Added to lwiki | 2026-06-30 |

## What it does

Indexes a code directory into a persistent knowledge graph of functions,
classes, call chains, HTTP routes, and cross-service links. Lets lwiki
answer structural questions in milliseconds instead of agent file-by-file
exploration.

The lwiki wrapper shells out to the binary using the documented contract:

```text
codebase-memory-mcp cli [--json] <tool_name> <json_args>
```

## Why it is in lwiki (not in Claude Code)

Per the user's hard rule (`feedback-tool-scope-separation`):

> 工具归属必须分清 —— Claude Code 用 MCP vs 本地独立 CLI 绝不能混

cbmem is exposed **only** as `lwiki cbmem *` subcommands. It is **not**
registered as a Claude Code MCP server, even though the upstream binary
itself supports MCP stdio.

## What the wrapper adds over the raw binary

- Resolves the binary via `~/bin/` → `PATH` → `LBM_CBMEM_BIN` env (graceful
  `CbmemNotFoundError` with install hint).
- Wraps every call in a `CbmemResult` dataclass (ok / command / returncode /
  stdout / stderr / `.json()` parser).
- Pretty-printers per subcommand (`render_*_report`).
- Per-project "is the graph fresh?" check via `is_indexed(project_dir)`.
- Hard timeout with normalised stderr (handles `subprocess.TimeoutExpired`
  where `exc.stdout` may be bytes).

## Source Set

- `lwiki/cbmem.py` (wrapper module, 22 public APIs)
- `lwiki/cli.py` (subcommand registration, 9 commands)
- `~/bin/codebase-memory-mcp` (vendored binary)

## See Also

- [[code-graph-querying]] — the concept
- [[integrations-2026-06-30]] — why we chose this
- [[lwiki-cbmem-cheatsheet]] — command reference
- [[architecture-policy]] — how this fits the wiki's role
- [[tooling-policy]] — agent ↔ tool ↔ wiki contract