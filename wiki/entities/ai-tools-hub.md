---
title: AI Tools Hub
type: entity
tags: [entity, hub, readonly]
sources:
  - /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/ObsidianVault/AI-Hub-架构.md
updated: 2026-05-14
---

# AI Tools Hub

AI Tools Hub 是你把 llm-wiki 全局规则整理出去后形成的只读副本，供各种 AI 工具统一读取。

## Overview

这个 Hub 的作用是锁住主规则，避免不同工具读取到不同版本的记忆体。它是你多工具协作的一致性层。

## Key Facts

- 只读
- 由广播脚本生成
- 供 Claude Code / Cursor / VSCode / OpenCode 读取

## Appearances

- [[architecture-policy]] — 广播链路
- [[tooling-policy]] — 工具读取入口

## See Also

- [[legacy-source-vault]]
- [[claude-code]]
