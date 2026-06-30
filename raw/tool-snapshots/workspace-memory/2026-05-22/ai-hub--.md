# AI-Hub 统一记忆体架构

> **版本**: v2.1-结论型
> **更新**: 2026-04-21 — OpenMythos 笔记原则融入
> **状态**: ✅ 使用中

---

## 核心理念

**Obsidian 记忆体 = ethanmini 的大脑（工作方式/思维模式）**
**项目 .memory/ = 项目的本地病历本（项目分析/Bug/技术方案）**

---

## 架构图

```
Obsidian (MASTER-记忆体.md / MASTER-工作流.md)
    ↓ 人工编辑，AI 只读
broadcast_to_hub.sh
    ↓
~/.ai_shared_hub/obsidian_ro/ (只读 Hub)
    ↓
所有 AI 工具读取（只读）

vs

AI 工作会话
    ↓ 写入（自由）
项目/.memory/ (项目分析/Bug/技术方案)
    ↓ promote_to_obsidian.sh（需人工确认）
06-Agent-Inbox/ (工作方式草稿)
    ↓ 人工审核
Obsidian MASTER (晋升) / 删除（阅后即焚）
```

---

## 记忆分类表

| 存储位置 | 内容类型 | AI 权限 | 晋升规则 |
|---------|---------|---------|---------|
| `ObsidianVault/MASTER-*.md` | 工作方式/思维模式 | 只读 | — |
| `~/.ai_shared_hub/obsidian_ro/` | 同上，只读副本 | 只读 | — |
| `项目/.memory/` | 项目分析/Bug/技术方案 | 自由读写 | ❌ 禁止晋升 |
| `06-Agent-Inbox/` | 工作风格待审草稿 | 只能写草稿 | 晋升审核 |
| `Auto Memory` | 跨会话积累 | 自动读写 | 说"记住这个" |

---

## 四级知识管道

```
L1 局部记忆 (项目级)
    位置：各项目 .memory/
    写入：AI 自由写项目经验
         ↓ [promote_to_obsidian.sh — 仅当内容是工作方式时]

L2 实时审批 (macOS 弹窗)
    ❌ 禁止晋升：项目分析/Bug/技术方案
    ✅ 可以晋升：沟通偏好/决策规则/AI 工作规范

L3 候选记忆 (全局草稿)
    位置：06-Agent-Inbox/
    写入：弹窗通过后自动放入

L4 主记忆 (全局真理)
    位置：MASTER-*.md
    写入：人类唯一（AI 绝对禁止直接修改）
```

---

## 支持的工具

| 类型 | 工具 | 记忆体位置 | 备注 |
|------|------|---------|------|
| IDE | VSCode | `~/.vscode/memory/MEMORY.md` | 包装脚本启动 |
| IDE | Trae | `~/.trae/memory/MEMORY.md` | 包装脚本启动 |
| IDE | Cursor | `~/.cursor/memory/MEMORY.md` | 包装脚本启动 |
| CLI | Claude Code | `~/Documents/claude-code-config/memory/MEMORY.md` | 原生 Hook |
| CLI | OpenCode | `~/.opencode/memory/MEMORY.md` | 需手动配置 |

---

## 核心脚本

| 脚本 | 功能 | 触发方式 |
|------|------|---------|
| `broadcast_to_hub.sh` | Obsidian → 只读 Hub 广播 | 启动钩子 / 手动 |
| `promote_to_obsidian.sh` | 项目 .memory → 晋升审核 | 需显式调用 |
| `unified-memory-recovery.sh` | 多工具记忆体回收到 Inbox | 会话结束 Hook |
| `opencode_startup_hook.sh` | OpenCode 启动同步 Obsidian | 启动时 |

---

## 快速使用

### 手动广播（确保 Hub 最新）
```bash
bash ~/Documents/ObsidianVault/broadcast_to_hub.sh
```

### 回收工具记忆体
```bash
bash ~/Documents/ObsidianVault/unified-memory-recovery.sh claude-code
bash ~/Documents/ObsidianVault/unified-memory-recovery.sh --all
```

### 晋升工作方式经验
```bash
promote_to_obsidian.sh <项目路径> <经验文件> [标题]
```

---

---

## 关联文档

- 记忆规则：[[MASTER-记忆体.md]]
- 工作流：[[MASTER-工作流.md]]
- IDE 集成：[[IDE-CLI 统一集成指南.md]]
- 索引：[[SCHEMA.md]]

- ❌ 禁止把项目分析晋升到 Obsidian
- ❌ 禁止把工作风格经验写入项目 .memory/
- ❌ 禁止 AI 直接修改 MASTER-*.md
- ❌ 禁止把 Obsidian 当成项目档案室

---
