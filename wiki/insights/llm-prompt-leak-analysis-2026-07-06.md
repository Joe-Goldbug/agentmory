---
title: LLM Prompt Leak Analysis — 2026-07-06
type: insight
tags: [insight, security, prompt-engineering, fable5, sanitization, portable-template, vitto-leak, pliny-jailbreak]
sources:
  - /Users/ethan/Downloads/CLAUDE-FABLE-5系统题词.md
  - /Users/ethan/Downloads/CLAUDE-FABLE-5-SANITIZED.md
  - /Users/ethan/Downloads/prompt-template-portable.md
updated: 2026-07-06
---

# LLM Prompt Leak Analysis — 2026-07-06

> A single day of work produced a sanitized research artifact, a portable prompt template, and a wiki promotion. This page records the **decisions and findings**, not the artifacts themselves. The artifacts live in their respective files; the wiki entry is the durable summary.

## Context

On 2026-07-06 the user saw two Twitter screenshots:

1. **@VittoStack** (2026-07-01) — "Anthropic Sonnet 5 system prompt leaked. Link in the comments." Screenshot showed a "second-correction pass" reconstruction of the Claude Fable 5 / Sonnet 5 `claude.ai` chat interface system prompt, dated 2026-07-01.
2. **@elder_plinius** (2026-06-10) — "JAILBREAK ALERT. ANTHROPIC: PWNED. FABLE-5: LIBERATED." Screenshot showed multi-modal injection (elephant image), ASCII smuggling, many-shot attack vectors.

The user asked to "collect the system prompts" for analysis. Web search and fetch were blocked by domain restrictions; the user's local copy of the VittoStack leak (downloaded 2026-06-13) was the working source. Pliny's full jailbreak text was not retrievable.

## Decision 1: Treat the leak as research material, not as a usable prompt

**Date:** 2026-07-06
**Decider:** user
**Status:** accepted

The naive move would have been to "feed the leaked prompt to another model." This was rejected on multiple grounds:

- The leak is dated 2026-07-01 with hardcoded "current date: Tuesday, June 09, 2026" — feeding it to anything deployed today would create immediate date drift and identity confusion.
- The leak contains an `anthropic_api_in_artifacts` ("Claudeception") section teaching the model to recursively call `https://api.anthropic.com/v1/messages` from within user-rendered artifacts with implicit "no API key needed" auth. This is an implicit-auth footgun in any environment other than Claude.ai itself.
- The leak references an `end_conversation` tool that does not appear in the tool-definition catalog — an orphan capability reference.
- VittoStack himself disclaims byte-for-byte accuracy: "not 'byte-for-byte'."

### Outcome

Three files, in `~/Downloads/`:

| File | Lines | Purpose |
|---|---|---|
| `CLAUDE-FABLE-5系统题词.md` (original) | 1585 | Source of truth, kept untouched |
| `CLAUDE-FABLE-5-SANITIZED.md` (intermediate) | 1381 | Annotated research artifact with dangerous content flagged |
| `prompt-template-portable.md` (output) | 265 | Vendor-neutral template derived from analysis |

The user explicitly asked that the original be preserved verbatim.

## Decision 2: What to sanitize, what to keep

**Date:** 2026-07-06
**Decider:** user (via /goal hook: "1先修复【高】, 2然后修复【高】, 3 修复【低】")
**Status:** accepted

### High (3 categories, 8 replacements total)

1. **Identity + time anchoring** (lines 12-18, 142-151, 1351-1357). Hardcoded "Claude Fable 5" and "Tuesday, June 09, 2026" were the single biggest source of the "drift" VittoStack mentioned. Replaced with neutral templates.
2. **Claudeception recursive API** (lines 1359-1517, 159 lines of JS). Deleted. Replaced with a 5-point risk note + "correct posture" guidance for anyone who needs artifact-internal API calls.
3. **`end_conversation` orphan tool reference** (line 140). Replaced with "validate before honoring" — telling future readers that the tool name in the prompt does not exist in the tool catalog.

### Low (5 categories)

- `mcp_app_suggestions` (lines 238-286, Anthropic commercial push layer) — neutralized
- `localStorage` hard prohibition (line 398) — split into Claude.ai-specific + general environment
- `copyright hard limits` (lines 478-519, the 15-word-per-source rule) — softened to "default respect + short quotes with attribution fine"
- Network whitelist (lines 1564-1568) — replaced with generic package manager categories
- `/mnt/...` filesystem paths (lines 1572-1581) — replaced with generic read-only mount pattern
- `thumbs-down` sycophancy (2 mentions) — kept as conditional Claude.ai reference

Net change: -204 lines, -10.8 KB.

## Decision 3: The portable template is for OTHER IDEs, not Claude Code

**Date:** 2026-07-06
**Decider:** user
**Status:** accepted

The user's existing `CLAUDE.md` (in `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/`) is already a sophisticated constitution with Karpathy-style rules, L0 PDCA, and loop routing. The portable template is **not** a replacement for it.

Target consumers identified by the user:

- **Cursor** (project rules at `.cursor/rules/llm-system-prompt.mdc`)
- **Codex CLI** (via `~/.codex/AGENTS.md`, which already has LLM-WIKI:START/END block — this wiki page will reach Codex automatically)
- **OpenCode** (via `~/.opencode/opencode.json` → `agent.<name>.prompt`)
- **Trae / Kiro** (as the basis for their `steering/development-standards.md` and `trae_global_settings.json`)

This is the second application of the user's `feedback-tool-scope-separation` rule: capabilities live in the wiki, not in any single agent's runtime.

## Decision 4: Promote the template to llm-workmem as a concept, not an entity

**Date:** 2026-07-06
**Decider:** user
**Status:** accepted

The template is a **cross-cutting concept** (applies to all AI tools), not an entity (a specific tool). Per `architecture-policy`, the wiki is the durable coordination layer; per `memory-policy`, the global layer holds "durable working style, communication preferences, and cross-project rules" — which is exactly what the template is.

Created `wiki/concepts/portable-llm-system-prompt.md` (this wiki entry references the source file; the source file is the canonical artifact, not duplicated into the wiki body). Updated `wiki/concepts/tooling-policy.md` See Also to add `[[portable-llm-system-prompt]]`.

The user's existing `feedback-tool-scope-separation` rule applied here: the template went to the wiki, not to any single agent's `CLAUDE.md`.

## Local environment audit (the part that makes this wiki entry portable)

Before drafting the template, the user's local AI tooling was audited to understand the actual integration surface. Initial audit found 6 tools; a verification pass expanded this to 11.

| # | IDE | App 存在 | Config file | Already links to llm-workmem? | Integration priority |
|---|---|---|---|---|---|
| 1 | **Claude Code** | (CLI) | `~/.claude/CLAUDE.md` (symlink to iCloud `claude-code-config/CLAUDE.md`) | Implicitly (this conversation runs here) | Already integrated |
| 2 | **Codex CLI** | ✓ Codex.app | `~/.codex/AGENTS.md` (156 lines, has Karpathy + LLM-WIKI block) | **Yes — explicit `<!-- LLM-WIKI:START -->` block** | Already integrated; wiki auto-picks this page |
| 3 | **VSCode** | ✓ Visual Studio Code.app | `~/Library/Application Support/Code/` | n/a (not an AI tool itself) | Indirect (via Copilot / Continue extensions) |
| 4 | **Cursor** | (no .app, config-only) | `~/.cursor/` (7 items) — no `~/.cursorrules` legacy file | No | Pending — needs `.cursor/rules/llm-system-prompt.mdc` |
| 5 | **Trae** | ✓ Trae.app (running) | `~/.trae/trae_global_settings.json` + `memory/` + `memory-hook.json` | No | Pending |
| 6 | **Trae Solo** | ✓ TRAE SOLO.app (running) | `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/trae_solo_config.json` + `~/.config/trae-solo/poe_api_key` | No | Pending |
| 7 | **Kiro** | ✓ Kiro.app + Kiro CLI.app | `~/.kiro/steering/development-standards.md` (43 items total: 1 steering, 17 hooks, 6 skills, 3 specs, 10 MCPs) | No | Pending — use template as basis for steering |
| 8 | **Antigravity** | ✓ Antigravity.app (Google vendor) | `~/.gemini/antigravity/builtin/skills/` + `~/Library/Application Support/Antigravity/` + iCloud `AntigravitySync/brain/` | No | Pending |
| 9 | **OpenCode** | (CLI, aliased) | `~/.opencode/opencode.json` (prompt field) + `~/.config/opencode/oh-my-openagent.json` (bridges Claude Code structure) | No | Pending |
| 10 | **MiniMax Code** | ✓ MiniMax Code.app (running — this session) | `~/.minimax/config.yaml` + `~/.minimax/agents/{coder,general,mavis,verifier}/` + `.builtin-skills/` (10 skills) | No | **Highest priority** — the model running the user's sessions |
| 11 | **GitHub Copilot CLI** | (CLI, `brew install copilot-cli`) | `~/.copilot/config.json` (minimal: firstLaunchAt, trusted_folders, model, effortLevel) | No | Reference only — no system prompt in user-writable config |

**Not installed** (confirmed absent): Continue, Windsurf, Aider.

**Implication**: the Codex path picks up the new wiki page automatically via its LLM-WIKI block. **MiniMax Code integration is the highest-leverage follow-up** because it's the model running the user's actual sessions — the wiki concept page itself becomes the design reference. The remaining 9 IDEs need per-tool integration work; the Per-IDE Integration table in `[[portable-llm-system-prompt]]` is the integration spec.

## Anti-patterns catalog (extracted from the leak)

The most reusable content of this analysis. The original prompt demonstrates 8 specific failure modes that other LLM apps should not copy:

1. Hardcoded current date in identity preamble → drift
2. Marketing-tier claims ("most intelligent", "above Opus") → ages badly
3. Hidden or undefined tool references → orphan calls
4. Implicit-auth API patterns ("no API key needed") → sandbox-dependent
5. Force-push to commercial connectors → looks like helpfulness, is upsell
6. Platform-specific restrictions framed as universal → wrong guidance
7. Self-promotion of feedback channel after every friction → trains model to upsell
8. Stale model-version strings hardcoded into example code → drift, again

These are in section 15 of the portable template.

## Open questions

- **Per-IDE integration.** Should the next step be writing `.cursorrules` for Cursor, OpenCode prompt injection, Trae settings, Kiro steering? Each is a separate ~50-line file. Worth a separate round.
- **Pliny's jailbreak text.** The full Pliny 2026-06-10 Fable-5-Liberated prompt was not retrievable. If the user wants it for red-team purposes, the `agent-reach` skill (per the user's config) is the routing path.
- **Snapshot update.** The user's `raw/tool-snapshots/opencode/2026-07-01/agents.md` and other tool snapshots may now be stale relative to the actual configs (which include `oh-my-openagent.json` and the full 36+ skills). The next `lwm harvest` should pick this up.
- **Claude Code's auto-update failure.** The push found a `.last-update-result.json` with `install_failed` (2026-07-06 08:03). Not investigated yet. Likely network/permission. Worth checking if a `/doctor` is needed.
- **Initial audit was incomplete.** First audit claimed 6 tools; verification pass found 11 (added Antigravity, MiniMax Code, GitHub Copilot CLI; distinguished Trae and Trae Solo). Lesson: always cross-check `/Applications/` and `ps aux` in addition to `~/.config/` and `~/Library/Application Support/`. The wiki page is now updated to reflect 11 tools.

## See Also

- [[portable-llm-system-prompt]] — the wiki concept
- [[tooling-policy]] — updated to reference the new concept
- [[memory-policy]] — global layer scope
- [[architecture-policy]] — wiki as durable coordination layer
- [[memory-governance]] — the Working / Session / Project / Global layer model
- [[claude-code]] / [[codex]] / [[cursor]] / [[opencode]] / [[trae-solo]] / [[kiro]] / [[antigravity]] / [[minimax]] — affected tools (11 total; full list in `[[portable-llm-system-prompt]]` Per-IDE table)
- `feedback-tool-scope-separation` (memory file at `~/.claude/projects/-Users-ethan/memory/`, not wiki-internal) — the rule that drove the wiki-promotion decision
