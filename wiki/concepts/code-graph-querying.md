---
title: Code Graph Querying
type: concept
tags: [concept, cbmem, code-graph, code-intelligence, static-analysis]
sources: []
updated: 2026-06-30
---

# Code Graph Querying

> Replacing file-by-file exploration (grep + read) with a queryable graph of
> the code's actual structure. cbmem is the lwm implementation of this
> concept.

## What this is

A **code graph** is a directed graph where nodes are code units (functions,
classes, methods, routes, RPC handlers) and edges are relationships
(definitions, calls, imports, HTTP route → handler, gRPC service → method).

Instead of asking an agent "grep for `foo` and read the file", the agent
asks the graph: "what calls `foo`? what does `foo` call? what is the
blast radius of changing `foo`?"

## Why it matters

The default agent workflow — *grep, read, reason, repeat* — has three
failure modes that a graph eliminates:

1. **Token explosion.** A typical 5-query exploration of a real repo
   consumes ~412k tokens. The same 5 queries on a graph cost < 1k tokens
   (per the codebase-memory-mcp published benchmark: 99.2% token reduction,
   10× fewer tokens, 2.1× fewer tool calls across 31 real-world repos).
2. **Missed cross-file relationships.** `grep` finds text; it does not
   find call chains, route definitions, or pub/sub wiring. A graph does.
3. **Slow iteration.** A sub-millisecond query is feedback-loop-friendly.
   A 30-second read+reason cycle is not.

## How it fits lwm

`lwm cbmem *` is the only interface. The wrapper never parses the
graph output into Python objects; it surfaces the binary's stdout verbatim
(or as JSON when `--json` is set). This keeps the wrapper forward-compatible
as the upstream binary evolves its output schema.

```
User / agent
    │
    ▼
lwm cbmem {doctor|index|search|architecture|trace|changes|dead|query|semantic}
    │
    ▼
lwm/cbmem.py
    │
    ▼
~/bin/codebase-memory-mcp cli --json <tool> <json_args>
    │
    ▼
.codebase-memory/graph.db.zst  (per-project artifact)
```

## When to use which subcommand

| If you want to know… | Use |
|---|---|
| …is the binary installed? | `lwm cbmem doctor` |
| …what does the project look like? | `lwm cbmem architecture <dir>` |
| …where is symbol `X` defined or used? | `lwm cbmem search <dir> X` |
| …what does `X` call / who calls `X`? | `lwm cbmem trace <dir> X` |
| …what symbols did a diff touch? | `lwm cbmem changes <dir>` |
| …what code is dead (no callers)? | `lwm cbmem dead <dir>` |
| …semantic similarity to a phrase? | `lwm cbmem semantic <dir> "<query>"` |

## What this concept is **not**

- Not a debugger. It does not run code; it indexes static structure.
- Not a search engine. Semantic search is vector-over-symbols, not
  full-text-over-docs (use `lwm query` for wiki search).
- Not a build system. The graph is a side-effect of indexing; you do not
  compile to it.
- Not a Claude Code capability. Per `feedback-tool-scope-separation`,
  this lives in lwm / the wiki, not in any agent runtime.

## When NOT to use it

- **Small one-file changes.** `grep` is fine.
- **Repos that change constantly.** Re-indexing minutes-to-hours per
  million LOC; do not run on every save.
- **Closed-source / proprietary repos on shared machines.** The artifact
  `.codebase-memory/graph.db.zst` is a fairly complete structural map of
  the code. Treat it as sensitive as the source.

## See Also

- [[codebase-memory]] — the tool entity
- [[integrations-2026-06-30]] — why we chose this tool
- [[lwm-cbmem-cheatsheet]] — quick command reference
- [[architecture-policy]] — wiki's role vs tools
- [[workflow-policy]] — explore → plan → execute → verify, where cbmem fits step 1