---
type: tool-memory-recovery
source: claude-code
tool_type: CLI
recovered_at: 2026-04-17 00:23:25
status: pending-review
---

# Claude Code 全局记忆索引

> 每次会话自动加载前200行。详细内容在各 topic 文件中按需加载。

## 身份与偏好
- 用户：Ethan，macOS，中文输出
- 工作方式：全自动执行，不逐步确认，事后报告
- 代码风格：最小改动原则，改完必须验证

## 记忆体架构（防遗忘协议）

```
层级 1 — 全局持久（所有项目）
  ~/.claude/CLAUDE.md          ← 全局规则（每次会话加载）
  ~/.claude/rules/             ← 结构化规则模块（每次加载）
    memory-persistence.md     ← 何时/如何持久化记忆
    workflow.md               ← 执行风格与代码规范
    communication.md          ← 输出格式与沟通方式

层级 2 — 自动积累（项目级）
  ~/.claude/projects/<proj>/memory/MEMORY.md  ← Auto Memory 入口
  ~/.claude/projects/<proj>/memory/*.md       ← 按需加载的主题文件

层级 3 — 项目指令（人工维护）
  项目/CLAUDE.md              ← 团队共享规则（git 追踪）
  项目/CLAUDE.local.md        ← 个人私有规则（不提交）
  项目/.claude/rules/         ← 模块化规则（可路径作用域）

层级 4 — 项目经验（AI 自由写）
  项目/.memory/               ← Bug 记录、决策、经验
```

## 触发持久化的条件（每次对话检查）
1. 用户纠正同一行为第二次 → 写入 CLAUDE.md 或 rules/
2. 用户说"记住/以后/不要再" → 写入 Auto Memory 或 CLAUDE.md
3. /compact 前 → 检查有无只存在对话中的重要约定

## 项目状态索引
- OpenClaw: DashScope Coding API，6模型路由，~/.openclaw/openclaw.json 是活动配置
- claude-code-config: 本仓库，全局 Claude Code 规则和技能配置

## 关键经验（已验证）
- /compact 后只有项目根 CLAUDE.md 自动重注入，对话中说的规则会消失
- 活动配置在 ~/.openclaw/openclaw.json，不是仓库 config.json
- 持久化写入目标选错会导致跨会话失效

*最后更新: 2026-04-16*

