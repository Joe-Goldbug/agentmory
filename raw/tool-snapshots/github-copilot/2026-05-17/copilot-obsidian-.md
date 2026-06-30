---
uid: copilot-obsidian-media-spec
title: Copilot / Obsidian 中间媒体规范
tags:
  - memory
  - spec
  - cross-tool
created: 2026-04-10
---

# Copilot / Obsidian 中间媒体规范

> 这是一份写在 ObsidianVault 里的正式规则。它描述的是“主规范 + 共享层 + 薄接入”的统一方案，适用于 Copilot、Trae、Claude Code、CLI 和其他本地工具。

## 1. 核心目标

- 规则只保留一份主来源。
- Obsidian 保存镜像和长期记忆。
- 所有工具都读取同一个只读共享层。
- 不要求每个工具重复写整套规则。

## 2. 角色分工

### 主规范

- 位置：仓库根目录的 `COPILOT_CANONICAL.md`
- 作用：定义全局规则、同步顺序、边界和验证标准

### Obsidian Vault

- 作用：保存镜像、摘要、长期记忆和人类可读说明
- 原则：可以编辑、可以同步，但不作为唯一事实源

### 共享层

- 位置：`.memory/obsidian-broadcast/shared/`
- 作用：给所有工具统一读取的只读目录
- 原则：工具启动时只读，不直接回写 Obsidian 原件

### 借鉴层

- 位置：`.memory/copilot-borrowed/`
- 作用：先把 Obsidian 中允许的内容借到仓库本地，再广播到共享层
- 原则：只读源内容，不反向写回 Obsidian

## 3. 全局路径

```text
COPILOT_CANONICAL.md
  ├─→ Obsidian Vault / MASTER-*.md 镜像
  ├─→ .memory/copilot-borrowed/
  └─→ .memory/obsidian-broadcast/shared/
            ├─→ Copilot
            ├─→ Trae
            ├─→ Claude Code
            ├─→ CLI 工具
            └─→ 其他新工具
```

## 4. 自动化流程

1. Obsidian 中更新镜像或长期记忆。
2. 借鉴脚本把允许的内容放入 `.memory/copilot-borrowed/`。
3. 广播脚本把借鉴结果同步到 `.memory/obsidian-broadcast/shared/`。
4. 各工具启动时读取共享层。
5. 验证脚本检查路径、内容和一致性。

## 5. 统一工具接入原则

- 只做一次薄接入，不为每个工具重复维护完整规则。
- 工具只要能读本地 Markdown 目录，就接入共享层。
- 如果工具支持启动参数、环境变量或本地配置，就把共享层路径指过去。
- 如果工具不支持，就用本地启动脚本包装它。

## 6. 工具启动通用提示词

```text
你是我的本地 AI 工具代理。请先读取并遵守：
1. /Users/ethanmini/Documents/Ethan-GitHub-Copilot/COPILOT_CANONICAL.md
2. /Users/ethanmini/Documents/Ethan-GitHub-Copilot/.memory/obsidian-broadcast/shared/

执行规则：
- 默认中文，简洁直接。
- 只改仓库和 ObsidianVault 内文件，不改任何全局 IDE / CLI / shell 配置。
- 优先使用现有规则，最小改动，先验证后结束。
- Obsidian 是镜像/记忆来源，shared 是统一只读读取层。
- 如果任务涉及危险操作，先提醒确认。
- 完成后只输出结果、变更点、是否需要同步到 Obsidian。
```

## 7. 禁止事项

- 不要把规则分散写到多个工具配置里。
- 不要让工具直接回写 Obsidian 原件。
- 不要把共享层当成可写工作区。
- 不要绕过主规范直接新增另一套规则。

## 8. 验收标准

- 主规范只有一份。
- ObsidianVault 里能找到这份规则。
- 所有工具都可以只读共享层。
- 新工具接入时只需要薄适配，不需要重写规则。

**最后更新**: 2026-04-10