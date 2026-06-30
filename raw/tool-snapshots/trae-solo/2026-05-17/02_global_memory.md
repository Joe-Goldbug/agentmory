# Global_Memory: The Unified Context (全局记忆体)

> **位置**: `~/.ai_brain/02_Global_Memory.md`
> **作用**: 作为所有 AI 工具（Trae, Claude Code, Cursor, CLI 等）共享的上下文数据库。AI 会在每次会话开始时读取，在结束时更新。

## 1. User Preferences (用户全局偏好)
- **语言**: 英文思考，中文回复。
- **行事风格**: 能动手绝不动口（自动执行），极简高效，注重验证闭环。

## 2. Active Projects Context (活跃项目上下文)
*(AI 自动维护区：记录当前正在处理的项目路径和关键状态)*
- `项目A`: [状态描述]
- `项目B`: [状态描述]

## 3. Lessons Learned & Anti-Patterns (经验教训与避坑)
*(AI 自动维护区：记录踩过的坑，避免重复犯错)*
- [x] **Kitchen Sink Session**: 发现上下文污染时，必须提醒用户执行 `/clear`。
- [x] **Trust-then-Verify Gap**: 绝对禁止未经验证就提交代码。
- [x] **Infinite Exploration**: 搜索必须指定具体目录，限制深度。

## 4. Temporary Scratchpad (临时草稿/当前任务进度)
*(AI 自动维护区：用于跨 Session 的任务接力)*
- [空]
