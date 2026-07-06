---
title: Portable LLM System Prompt
type: concept
tags: [concept, prompt-engineering, llm, system-prompt, portable, cross-tool, fable5, sanitized]
sources:
  - /Users/ethan/Downloads/prompt-template-portable.md
  - /Users/ethan/Downloads/CLAUDE-FABLE-5系统题词.md
  - /Users/ethan/Downloads/CLAUDE-FABLE-5-SANITIZED.md
updated: 2026-07-06
---

# Portable LLM System Prompt

> A vendor-neutral, model-agnostic template for the system prompt of an LLM-based assistant. Distilled from analysis of a 2026 production prompt, with all brand-specific, model-specific, and platform-specific content removed. Use as a reference when designing or auditing a system prompt for any LLM tool in this setup.

## Source of truth

- **Full template** (265 lines, 16 sections + composition layer): `~/Downloads/prompt-template-portable.md`
- **Original leak analyzed**: `~/Downloads/CLAUDE-FABLE-5系统题词.md` (VittoStack leak, 2026-07-01, 1585 lines)
- **Sanitized intermediate**: `~/Downloads/CLAUDE-FABLE-5-SANITIZED.md` (1381 lines, with 8 surgical replacements + 1 deletion)

The wiki page is a **summary**; the template file is the **canonical artifact**. Do not duplicate the template body into the wiki — keep the single source of truth in `~/Downloads/`.

## What the template covers (16 sections + composition)

1. Identity — placeholder-based, no hardcoded dates or model names
2. Behavior Guidelines — tone, formatting, conversational shape
3. Refusal Handling — clean edges, no over-refusal
4. User Wellbeing — mental health, eating disorders, over-reliance, detachment
5. Evenhandedness on Contested Topics
6. Responding to Mistakes and Criticism
7. Knowledge Cutoff and Recency
8. File and Artifact Strategy
9. Tool Use (if your model has tools)
10. Search Result Hygiene
11. Copyright and Reproduction
12. Safety Rails (do not reveal)
13. Self-Check Before Replying
14. What to Customize (placeholder list)
15. What NOT to Copy (8 anti-patterns observed in real production prompts)
16. About This Template
17. Composition with Memory Systems — how this template layers with Karpathy-style rules, the LLM-WorkMem wiki, and L0/L6 loops

## Key Points

- The template is a **reference**, not a drop-in. Most IDEs already have their own `CLAUDE.md` / `AGENTS.md` / `.cursorrules`. Do not duplicate the same rule across layers.
- The 8 anti-patterns in section 15 are the most valuable part: hardcoded dates, marketing-tier claims, hidden/orphan tool references, implicit-auth API patterns, force-pushed connectors, platform-specific restrictions framed as universal, self-promotion of feedback channels, stale model strings.
- The wellbeing section (4) is the most transferable engineering content from the original — it codifies real production experience with self-harm substitution techniques, disordered eating, and crisis-resource referrals.

## Per-IDE Integration

| # | IDE | Config file | How to use this template |
|---|---|---|---|
| 1 | **Claude Code** | `~/.claude/CLAUDE.md` (symlink to iCloud) | User already has a sophisticated `CLAUDE.md`. Use the wiki + sections 13, 15 as a periodic review checklist. Do not re-inject the full template. |
| 2 | **Codex CLI** | `~/.codex/AGENTS.md` | Already has Karpathy rules + LLM-WIKI block. Add sections 1, 3, 7, 11, 12 selectively. The LLM-WIKI block will auto-pick this wiki page on next session. |
| 3 | **VSCode** | `~/Library/Application Support/Code/` | VSCode itself is not an AI tool — but the GitHub Copilot / Continue / Cline extensions that run inside it are. Use this template as a reference when configuring those extensions' prompts. |
| 4 | **Cursor** | `~/.cursor/rules/*.mdc` (project-level) | Save as `~/.cursor/rules/llm-system-prompt.mdc` for project-level use. Sections 2, 3, 13 are most relevant. No `~/.cursorrules` legacy file in this setup. |
| 5 | **Trae** | `~/.trae/trae_global_settings.json` | Use as the basis for trae global rules. The template's structure is the source; evaluate each rule against your own needs. Trae has a `memory/` + `memory-hook.json` system that the template's section 17 (composition) is directly relevant to. |
| 6 | **Trae Solo** | `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/trae_solo_config.json` + `~/.config/trae-solo/poe_api_key` | Trae Solo's config is in iCloud Downloads, not `~/.config/`. Use the template as the basis for the `trae_solo_config.json` rules section. Note: `poe_api_key` is a credential, do not read or echo. |
| 7 | **Kiro** | `~/.kiro/steering/development-standards.md` | Use as the basis for the steering file. Kiro has 17 hooks + 6 skills + 3 specs + 1 steering. The template's structure maps cleanly onto Kiro's "steering" concept. |
| 8 | **Antigravity** | `~/.gemini/antigravity/builtin/skills/` + `~/Library/Application Support/Antigravity/` + iCloud `AntigravitySync/brain/` | Google's product. Use the template as a `builtin/skills/portable-llm-system-prompt/` skill. Vendor: `com.google.antigravity`. |
| 9 | **OpenCode** | `~/.opencode/opencode.json` (prompt field per agent) | Inject into `agent.<name>.prompt`. Keep only sections 1, 2, 3, 7, 11, 12 (verbose for CLI). The `~/.config/opencode/oh-my-openagent.json` already bridges Claude Code's MCP/commands/skills/agents/hooks/plugins structure. |
| 10 | **MiniMax Code** | `~/.minimax/config.yaml` + `~/.minimax/agents/{coder,general,mavis,verifier}/` + `.builtin-skills/` | **The most important integration** — this is the model running most of the user's sessions, including this one. The system prompt for MiniMax-M3 lives in the mavis backend (`agent.minimaxi.com`), not on disk. The wiki concept page itself is what the model should consult when designing prompts for MiniMax-Code's 4 agents. |
| 11 | **GitHub Copilot CLI** | `~/.copilot/config.json` | Minimal config: just `firstLaunchAt`, `trusted_folders`, `model`, `effortLevel`. No system prompt file in the user-writable config — the prompt is determined by the Copilot backend. Use the template as a *design reference* for any custom Copilot extensions. |
| 12 | **Web chat / API** | (varies) | Full template applies. Pay special attention to section 8 (file/artifact strategy) and section 11 (copyright hard limits) — these vary most by deployment. |

## Relationship to existing rules

This page does **not** supersede:

- `[[tooling-policy]]` — which tools read which files
- `[[memory-policy]]` — what belongs in the global layer
- `[[memory-governance]]` — the Working / Session / Project / Global layer model
- `[[architecture-policy]]` — wiki as the durable coordination layer

It is one more **concept** page alongside them. The same precedence applies: rules in the wiki are durable; rules in per-tool `CLAUDE.md` / `AGENTS.md` are tool-specific.

## Coverage summary (as of 2026-07-06)

Total AI tools in user's environment: **11** (Claude Code, Codex, VSCode, Cursor, Trae, Trae Solo, Kiro, Antigravity, OpenCode, MiniMax Code, GitHub Copilot CLI). The Per-IDE Integration table above covers all 11. The single most important integration is **MiniMax Code** (the model running the user's sessions); the most auto-reachable integration is **Codex CLI** (via its LLM-WIKI block). The remaining 9 IDEs require per-tool integration work; the per-IDE table is the integration spec.

## See Also

- [[tooling-policy]]
- [[memory-policy]]
- [[architecture-policy]]
- [[llm-prompt-leak-analysis-2026-07-06]] — the analysis that produced this template
- [[claude-code]]
- [[cursor]]
- [[opencode]]
- [[codex]]
