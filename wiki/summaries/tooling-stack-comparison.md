---
title: Tooling Stack Comparison
type: summary
tags: [summary, tooling, codex, claude-code, trae, copilot]
sources:
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Codex/2026-04-22-m-flow-githubstar/codex_global_AGENTS.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Codex/2026-04-22-m-flow-githubstar/codex_memory_model.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Codex/2026-04-22-m-flow-githubstar/codex_workflow_transfer.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/CLAUDE.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/memory/quick-reference.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/TRAE.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/Unified_Brain/00_Meta_Workflow.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Trae solo配置/Unified_Brain/02_Global_Memory.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ethan-GitHub-Copilot/.memory/copilot-borrowed/README.md
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ethan-GitHub-Copilot/.memory/copilot-borrowed/03-Memory/Copilot-Obsidian中间媒体规范.md
updated: 2026-05-14
---

# Tooling Stack Comparison

> 这一页把你常用的四个工具统一成同一种观察框架：谁负责执行、谁负责记忆、谁负责同步、谁负责归档。

## Codex

Codex 的中心是 Ethan 的工作方式和跨项目决策模型，不是单个项目笔记。它强调：

- 先探索，再计划，再执行，再验证，再反思
- diff-only、函数切片、上下文摘要
- memory 只存可复用的偏好、工作流、错误 playbook、项目索引

它更像一个**代码执行器 + 工作流压缩器**。

## Claude Code

Claude Code 是你最明确的 CLI 执行器之一，重点是：

- 原生 hook
- SessionEnd 回收
- 读 `CLAUDE.md` / 项目 `CLAUDE.md`
- 通过 `memory/error-cache.json`、skills、hooks 形成强约束工作流

它更像一个**强规则、强验证、强记忆回收的 CLI 代理**。

## Trae Solo

Trae Solo 更像一个**IDE 侧的层级记忆与反思系统**：

- Think → Plan → Build → Verify → Reflect → Commit
- diff 传变更、函数级分块、上下文摘要
- Working / Session / Project / Global 四层记忆
- Bug 缓存、函数缓存、问答缓存
- 通过 `.traerules` 和 `.trae/*` 把项目级宪法固定下来

它更像一个**面向 IDE 的细粒度节流器和记忆体架构**。

## GitHub Copilot

Copilot 这套总结的核心不是“它会什么”，而是“怎么把它纳入统一中间媒体”：

- 主规范一份，Obsidian 保存镜像
- 所有工具读取同一个只读共享层
- `.memory/copilot-borrowed/` 作为借鉴层
- `.memory/obsidian-broadcast/shared/` 作为统一工具读取层

它更像一个**多工具共享规则分发系统**，重点是标准化接入，而不是单工具优化。

## Cross-Tool Pattern

- Codex：偏执行和跨项目 reasoning
- Claude Code：偏 CLI 约束和回收
- Trae Solo：偏 IDE 内部节流、缓存和反思
- Copilot：偏中间媒体、共享层和规范分发

## What This Means For You

你真正要的是：

1. 一份主规范
2. 一层共享只读记忆
3. 一套工具各自的薄接入
4. 一条把项目经验晋升为工作方式的审核管道

## See Also

- [[memory-policy]]
- [[workflow-policy]]
- [[architecture-policy]]
- [[tooling-policy]]
