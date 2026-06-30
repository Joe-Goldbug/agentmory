---
title: Integration Decisions 2026-06-30
type: insight
tags: [insight, cbmem, integration, decision, agent-reach, social-copilot, tool-scope]
sources: []
updated: 2026-06-30
---

# Integration Decisions — 2026-06-30

> A single day of work produced two new tools and a hard rule. This page
> records the *decisions*, not the docs. The docs live in their respective
> entities / concepts / summaries.

## Decision 1: codebase-memory-mcp is wrapped in lwiki, not Claude Code MCP

**Date:** 2026-06-30
**Decider:** user
**Status:** accepted, implemented in `lwiki/cbmem.py`

### Context

GitHub trending the week of 2026-06-23 highlighted `DeusData/codebase-memory-mcp`
(weekly +8,926 ⭐). The user asked how to integrate it into their local
LLM wiki. The naive answer was "install as a Claude Code MCP server."

The user pushed back twice:

1. "方案 a 集成 mcp 是给 Claude code 用的——不，是融入 LLM wiki"
2. "**没有东西是给 Claude code 用**"

### Options considered

| Option | Pros | Cons | Outcome |
|---|---|---|---|
| A. Claude Code MCP server | Auto-loaded for the agent | Violates user's tool-scope rule; expands agent's secret-bearing surface | ❌ rejected |
| B. lwiki subcommand | Stays in wiki, follows the wiki's role per `architecture-policy`; agent reads wiki rules, not the binary | Slight friction: agent has to call `lwiki cbmem ...` via Bash | ✅ **accepted** |
| C. Standalone CLI in `~/tools/` | Decoupled from any wiki | Loses the wiki as the single coordination layer; reinvents the wheel | ❌ rejected |

### Why B

- The wiki is the durable coordination layer for cross-tool rules
  (per `architecture-policy`). A new capability should land as a wiki
  capability, not as a side-channel.
- An `lwiki cbmem *` command is first-class in the same way that
  `lwiki query`, `lwiki harvest`, `lwiki audit` are first-class.
- It keeps the binary out of any agent's secret-bearing runtime.

### Constraints discovered during integration

- The binary's real CLI contract is `codebase-memory-mcp cli [--json]
  <tool> <json_args>` — **not** `<tool> <args>` as the README hints.
  Confirmed by `strings(1)` on the binary.
- The binary is 270 MB. The Claude Code Bash sandbox SIGKILLs processes
  that large (exit 137). The wrapper still works; the binary just
  cannot be exercised end-to-end inside the sandbox. Verification of
  argv shape was done via `unittest.mock` patch on `subprocess.run`.
- Per-project graph lives at `<dir>/.codebase-memory/graph.db.zst`.
  The wrapper exposes `is_indexed(dir)` so commands fail fast with a
  clear "run index first" message instead of an opaque empty result.

## Decision 2: social-copilot is a standalone local CLI, never a Claude Code MCP

**Date:** 2026-06-30
**Decider:** user
**Status:** accepted, implemented at `~/tools/social-copilot/`

### Context

The same trending week surfaced `Panniantong/Agent-Reach` (weekly +7,692 ⭐).
The user asked whether it could power an automated "draft → publish to
Twitter / Reddit / 小红书" pipeline. Initial draft proposed both a CLI
and a Claude Code MCP integration; the user rejected the MCP route.

### What the CLI does

- `social-copilot read {twitter,reddit,xhs,bilibili,youtube,web,rss} <url>`
  — fetch + format content as markdown. Backends: tweepy, praw, yt-dlp,
  urllib; falls back to Jina Reader for xhs without `xhs-mcp`.
- `social-copilot write {twitter,reddit,xhs} ...` — publish. Backends:
  tweepy v2 API, praw, `xhs-mcp` (separate CLI).
- `social-copilot pipeline --draft <md> --platforms a,b,c` — adapt
  + publish in one call. Adaptation is a placeholder; wire to Claude
  API for real style-aware rewrites.
- `social-copilot doctor` — creds file mode check, dependency probe.

### Why NOT a Claude Code MCP

Three reasons, in order of importance:

1. **Credential blast radius.** Twitter / Reddit / 小红书 tokens must
   not pass through any agent's context. A local CLI keeps them at
   `~/.social-copilot/credentials.json` (mode 600) and out of agent
   prompts and tool results.
2. **User-driven action.** Publishing is a *user* action with
   real-world consequences (account bans, content policy). It must
   not be an agent-driven background loop.
3. **Platform anti-bot.** 小红书 and 推特 are aggressive about
   fingerprinting automated agents. A direct CLI run by the user
   flies under that radar; a long-lived agent session does not.

## Decision 3: the `tool-scope-separation` rule is durable

The two push-backs above establish a pattern. Codified in
`feedback-tool-scope-separation` (memory):

> 工具归属必须分清 ——
> - LLM Wiki 用 → 走 lwiki 集成
> - 本地独立工具 → 纯 CLI，**不**接入任何 agent
> - Claude Code 自身不装任何 MCP server 来做这两类事

Any future "agent capability" proposal must first answer the
scope question before any code is written.

## Open questions

- **Auto-reindex.** Should `lwiki watch` (the existing 12-hour
  scheduler) trigger a cbmem reindex on detected source drift?
  Currently it does not. Probably should.
- **Graph sharing across repos.** codebase-memory supports cross-repo
  linking. lwiki does not expose it yet. Likely a future subcommand.
- **agent-reach CLI vs MCP.** The `agent-reach` package itself is a
  provisioning tool that registers a SKILL.md for Claude Code. The
  user does not want that path. social-copilot therefore calls the
  underlying backends (yt-dlp, tweepy, praw) directly rather than
  shelling out to `agent-reach`. This is a non-obvious decision; if
  anyone revisits social-copilot, they should re-read this page first.

## See Also

- [[codebase-memory]] — the tool entity
- [[code-graph-querying]] — the concept
- [[lwiki-cbmem-cheatsheet]] — command reference
- [[architecture-policy]]
- [[memory-governance]]