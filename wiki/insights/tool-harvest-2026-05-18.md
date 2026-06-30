---
title: Tool Harvest
type: insight
tags: [insight, harvest, automation, memory]
sources: []
updated: 2026-05-18
---

# Tool Harvest

This snapshot is generated automatically from the active tool memory sources and working docs.

## Captured Sources

| Tool | Source | Snapshot |
|------|--------|----------|
| codex | MEMORY.md | raw/tool-snapshots/codex/2026-05-18/memory.md |
| codex | memory_summary.md | raw/tool-snapshots/codex/2026-05-18/memory_summary.md |
| codex | ad_hoc_notes | raw/tool-snapshots/codex/2026-05-18/ad_hoc_notes/20260514-235508-railway-settings-clarity.md |
| codex | ad_hoc_notes | raw/tool-snapshots/codex/2026-05-18/ad_hoc_notes/20260515-001400-railway-source-verification-first.md |
| codex | ad_hoc_notes | raw/tool-snapshots/codex/2026-05-18/ad_hoc_notes/20260515-002650-deploy-guardrails-enforce.md |
| codex | ad_hoc_notes | raw/tool-snapshots/codex/2026-05-18/ad_hoc_notes/20260515-003020-universal-verification-workflow.md |
| claude-code | CLAUDE.md | raw/tool-snapshots/claude-code/2026-05-18/claude.md |
| claude-code | quick-reference.md | raw/tool-snapshots/claude-code/2026-05-18/quick-reference.md |
| claude-code | hooks-guide.md | raw/tool-snapshots/claude-code/2026-05-18/hooks-guide.md |
| trae-solo | TRAE.md | raw/tool-snapshots/trae-solo/2026-05-18/trae.md |
| trae-solo | .traerules | raw/tool-snapshots/trae-solo/2026-05-18/traerules.md |
| trae-solo | 00_Meta_Workflow.md | raw/tool-snapshots/trae-solo/2026-05-18/00_meta_workflow.md |
| trae-solo | 02_Global_Memory.md | raw/tool-snapshots/trae-solo/2026-05-18/02_global_memory.md |
| github-copilot | README.md | raw/tool-snapshots/github-copilot/2026-05-18/readme.md |
| github-copilot | Copilot-Obsidian中间媒体规范.md | raw/tool-snapshots/github-copilot/2026-05-18/copilot-obsidian-.md |
| github-copilot | AI工具通用启动提示词.md | raw/tool-snapshots/github-copilot/2026-05-18/ai-.md |
| workspace-memory | MASTER-记忆体.md | raw/tool-snapshots/workspace-memory/2026-05-18/master--.md |
| workspace-memory | MASTER-工作流.md | raw/tool-snapshots/workspace-memory/2026-05-18/master--.md |
| workspace-memory | AI-Hub-架构.md | raw/tool-snapshots/workspace-memory/2026-05-18/ai-hub--.md |
| workspace-memory | IDE-CLI 统一集成指南.md | raw/tool-snapshots/workspace-memory/2026-05-18/ide-cli-.md |
| workspace-memory | SCHEMA.md | raw/tool-snapshots/workspace-memory/2026-05-18/schema.md |
| workspace-memory | 20260417-002325-claude-code-Memory-Draft.md | raw/tool-snapshots/workspace-memory/2026-05-18/20260417-002325-claude-code-memory-draft.md |
| vscode | MEMORY.md | raw/tool-snapshots/vscode/2026-05-18/memory.md |

## Missing Sources

- vscode: WORKFLOW.md
- vscode: HIERARCHICAL_MEMORY_SYSTEM.md

## Current Snapshot

## Codex
### MEMORY.md
- Source: `/Users/ethan/.codex/memories/MEMORY.md`
# Task Group: iDream V1 rollout, monolith boundaries, execution planning, and verification gates
scope: V1 feed/product rollout in the Next.js monolith, local validation and Node compatibility, product-boundary cleanup, TOC+DP execution...
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/iDream- reborn; reuse_rule=safe inside the iDream-reborn...
## Task 1: Implement V1 feed changes and validate locally
### rollout_summary_files
  - - rollout_summaries/2026-04-23T05-25-04-a9eR-idream_v1_x_algorithm_and_node20_upgrade.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/iDream- reborn, rollout_path=/Users/ethan/.codex/sessions/2026/04/23/rollout-2026-04-23T13-25-04-019db8cc-85e9-70d3-8b90-2b3ea4d79c1d.jsonl, updated_at=2026-05-17T09:31:17+00:00, thread_id=019db8cc-85e9-70d3-8b90-2b3ea4d79c1d, correctness-first V1 rollout plus local validation evidence)
### keywords
  - - Next.js 16, smart_v1, V1 feed ranking, resonance, 同频, 收藏, blocklist verify, npm exec tsc --noEmit --pretty false, npm run lint, npm run bugfix:verify, next build --webpack
### memory_summary.md
- Source: `/Users/ethan/.codex/memories/MEMORY.md`
# Task Group: iDream V1 rollout, monolith boundaries, execution planning, and verification gates
scope: V1 feed/product rollout in the Next.js monolith, local validation and Node compatibility, product-boundary cleanup, TOC+DP execution...
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/iDream- reborn; reuse_rule=safe inside the iDream-reborn...
## Task 1: Implement V1 feed changes and validate locally
### rollout_summary_files
  - - rollout_summaries/2026-04-23T05-25-04-a9eR-idream_v1_x_algorithm_and_node20_upgrade.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/iDream- reborn, rollout_path=/Users/ethan/.codex/sessions/2026/04/23/rollout-2026-04-23T13-25-04-019db8cc-85e9-70d3-8b90-2b3ea4d79c1d.jsonl, updated_at=2026-05-17T09:31:17+00:00, thread_id=019db8cc-85e9-70d3-8b90-2b3ea4d79c1d, correctness-first V1 rollout plus local validation evidence)
### keywords
  - - Next.js 16, smart_v1, V1 feed ranking, resonance, 同频, 收藏, blocklist verify, npm exec tsc --noEmit --pretty false, npm run lint, npm run bugfix:verify, next build --webpack

## Claude Code
### CLAUDE.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/CLAUDE.md`
# Claude Code 规则
## 红线（不商量）
  - - 不删文件，不先确认不删
  - - 不暴露密钥，环境变量注入用占位符
  - - 不读 .env / *.key / settings.local.json
## 工作原则
  - - 先思考，再动手 — 理解目标和上下文再做
  - - 能简单就简单 — 只改必须改的，不预防性重构
### quick-reference.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/memory/quick-reference.md`
# ⚡ Claude Code 快速参考
## 🎯 当前模型和环境
  - - **当前模型**：Claude Opus 4.6 / Sonnet 4.6 / Haiku 4.5
  - - **CLI 版本**：Claude Code v2.1.114
  - - **平台**：macOS (Darwin)
  - - **Shell**：zsh
## 🔑 核心快捷键和命令
### 常用 Slash 命令
### hooks-guide.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/memory/hooks-guide.md`
# Claude Code Hooks 完整配置指南
## 什么是 Hooks？
Hooks 是在特定事件发生时自动执行的脚本，让你可以实现确定性自动化行为，而非依赖 LLM 选择执行。
## 完整 Hook 事件列表 (v2.1.100 - 已补齐)
| 事件 | 触发时机 | Matcher 支持 | 当前配置状态 |
|------|----------|--------------|-------------|
| `SessionStart` | 会话开始或恢复时 | `startup`, `resume`, `clear`, `compact` | ✅ 已配置 |
| `SessionEnd` | 会话终止时 | `clear`, `resume`, `logout`, ... | ✅ 已配置 |

## Trae Solo
### TRAE.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/TRAE.md`
# Trae Solo v5.1 - 增强版主配置
> Personal AI Development Config Vault
> 参考 Claude Code 规则精简 | MemPalace + Obsidian 双记忆驱动 | 层级记忆 + Reflection Loop
---
## 核心规则文件
| 文件 | 作用 |
|------|------|
| `user_rules/rule-global.md` | 全局硬性规则 + Bug Fix Protocol |
### .traerules
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/.traerules`
# Trae Solo 项目级安全与工作流规范 (.traerules)
> 本文件是 Trae IDE (SOLO 模型) 的项目级宪法，每次会话启动时自动读取。
## 1. 终端安全拦截 (Terminal Safety)
*作为 Builder/Agent，你在执行以下高危操作前，**必须**使用 `AskUserQuestion` 或 `NotifyUser` 向我确认，绝不允许静默执行：*
### 绝对禁止静默执行
  - - **危险文件操作**: `rm -rf *`, `rm -rf /`, `rm -rf /*`, `rm -rf ~/*`
  - - **破坏性 Git 操作**: `git push --force`, `git push -f`, `git reset --hard`, `git clean -fdx`
  - - **系统级配置更改**: 修改 `~/.zshrc`, `~/.bashrc`, `~/.profile`, `~/.ssh/`, `/etc/` 等深层系统文件
### 00_Meta_Workflow.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/Unified_Brain/00_Meta_Workflow.md`
# Meta_Workflow: The Standard Operating Procedure (统一工作流)
> 这是全局唯一的标准执行链路，适用于所有 Mac IDE (Trae, Cursor, VSCode) 和 CLI (Claude Code, Terminal 等)。
## The 5-Step Loop (标准五步闭环)
1. **探索 (Explore)**
  - - 限制范围：不要进行漫无目的的全盘搜索。
  - - 工具：使用 `grep`, `search`, `find` 快速定位核心文件。
  - - 输出：获取足够的上下文，了解当前项目状态。
2. **计划 (Plan)**
### 02_Global_Memory.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/Unified_Brain/02_Global_Memory.md`
# Global_Memory: The Unified Context (全局记忆体)
> **位置**: `~/.ai_brain/02_Global_Memory.md`
> **作用**: 作为所有 AI 工具（Trae, Claude Code, Cursor, CLI 等）共享的上下文数据库。AI 会在每次会话开始时读取，在结束时更新。
## 1. User Preferences (用户全局偏好)
  - - **语言**: 英文思考，中文回复。
  - - **行事风格**: 能动手绝不动口（自动执行），极简高效，注重验证闭环。
## 2. Active Projects Context (活跃项目上下文)
*(AI 自动维护区：记录当前正在处理的项目路径和关键状态)*

## GitHub Copilot
### README.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ethan-GitHub-Copilot/.memory/copilot-borrowed/README.md`
# ObsidianVault - Trae Second Brain
> LLM-powered knowledge management based on Karpathy approach
## What is This
Personal knowledge management system integrating:
  - - Trae + Claude Code workflow automation
  - - GStack Skills system
  - - sage-wiki LLM compilation engine
  - - Obsidian visual knowledge base
### Copilot-Obsidian中间媒体规范.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ethan-GitHub-Copilot/.memory/copilot-borrowed/03-Memory/Copilot-Obsidian中间媒体规范.md`
# Copilot / Obsidian 中间媒体规范
> 这是一份写在 ObsidianVault 里的正式规则。它描述的是“主规范 + 共享层 + 薄接入”的统一方案，适用于 Copilot、Trae、Claude Code、CLI 和其他本地工具。
## 1. 核心目标
  - - 规则只保留一份主来源。
  - - Obsidian 保存镜像和长期记忆。
  - - 所有工具都读取同一个只读共享层。
  - - 不要求每个工具重复写整套规则。
## 2. 角色分工
### AI工具通用启动提示词.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ethan-GitHub-Copilot/.memory/copilot-borrowed/03-Memory/AI工具通用启动提示词.md`
# AI工具通用启动提示词
> 这是一份只放在 ObsidianVault 里的通用启动提示词。启动任何 IDE、shell 或 CLI 工具时，都可以直接粘贴这一段。
```text
你现在是我的本地 AI 工具代理。请先读取并遵守以下两处：
1. /Users/ethanmini/Documents/ObsidianVault/MASTER-记忆体.md
2. /Users/ethanmini/Documents/Ethan-GitHub-Copilot/.memory/obsidian-broadcast/shared/
如果第 2 个路径不存在，先运行：
/Users/ethanmini/Documents/Ethan-GitHub-Copilot/scripts/obsidian_broadcast_to_tools.sh

## Workflow Memory System
### MASTER-记忆体.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/MASTER-记忆体.md`
# 全局统一记忆体 (Master Memory)
> **版本**: v3.3-结论型
> **最后更新**: 2026-04-21
---
## 核心原则（一句话）
```
英文思考 → 中文输出 | 简洁优先 | 先分析后行动 | 每次修改必须验证
```
### MASTER-工作流.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/MASTER-工作流.md`
# 全局统一工作流 (Master Workflow)
> **版本**: v2.2-结论型
> **最后更新**: 2026-04-21
## 模块: EPEV 循环（核心工作流）
**先探索，后动手，大改先确认。**
1. **探索 (Explore)** → 绝不盲目写代码
  - - 用 Glob/Grep 定位，不读整文件
  - - 大文件用 offset/limit
### AI-Hub-架构.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/AI-Hub-架构.md`
# AI-Hub 统一记忆体架构
> **版本**: v2.1-结论型
> **更新**: 2026-04-21 — OpenMythos 笔记原则融入
> **状态**: ✅ 使用中
---
## 核心理念
**Obsidian 记忆体 = ethanmini 的大脑（工作方式/思维模式）**
**项目 .memory/ = 项目的本地病历本（项目分析/Bug/技术方案）**
### IDE-CLI 统一集成指南.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/IDE-CLI 统一集成指南.md`
# IDE/CLI 统一记忆体集成指南
> **版本**: v2.1-链接型
> **日期**: 2026-04-21
> **状态**: ✅ 使用中
---
## 快速入口
  - - 架构：[[AI-Hub-架构.md]]
  - - 记忆规则：[[MASTER-记忆体.md]]
### SCHEMA.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/SCHEMA.md`
# ObsidianVault SCHEMA
> **Obsidian 记忆体 = ethanmini 的大脑（工作方式/思维模式）**
> **项目 .memory/ = 项目的本地病历本（项目分析/Bug/技术方案）**
---
## 快速入口（MOC）
| 模块 | 文件 | 核心内容 |
|------|------|---------|
| 记忆规则 | [[MASTER-记忆体.md]] | 语言规则、工具分工、自主程度 |
### 20260417-002325-claude-code-Memory-Draft.md
- Source: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/06-Agent-Inbox/20260417-002325-claude-code-Memory-Draft.md`
# Claude Code 全局记忆索引
> 每次会话自动加载前200行。详细内容在各 topic 文件中按需加载。
## 身份与偏好
  - - 用户：Ethan，macOS，中文输出
  - - 工作方式：全自动执行，不逐步确认，事后报告
  - - 代码风格：最小改动原则，改完必须验证
## 记忆体架构（防遗忘协议）
```

## VSCode
### MEMORY.md
- Source: `/Users/ethan/.vscode/memory/MEMORY.md`
# vscode 局部记忆体 (已清空)
> 本会话记忆体已回收到 Inbox，等待审核。


## Memory Governance

- See [[memory-governance]] for the current layer model and promotion rules.
- Harvest before promotion, not after.
- Keep durable rules separated from temporary work threads.

## See Also

- [[overview]]
- [[purpose]]
- [[memory-governance]]
