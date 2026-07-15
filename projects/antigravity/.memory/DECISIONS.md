# Project Decisions (项目关键决策)

### [2026-06-24] 确立 Loop Engineering 四大闭环运行规范
- **决策内容**：正式通过 `Loop Engineering` 草案作为双端/双机开发的最核心同步与工程规范。
- **背景原因**：为了让 AI (Antigravity) 做到不说错、不瞎猜，在跨设备开发中保持状态与习惯的一致。
- **影响范围**：约束所有未来的 Project 迭代与 Bug 修复行为。

### [2026-06-24] 融入最新正式版 Loop Engineering 规范并建立适配文件
- **决策内容**：在 `.agents/` 目录下完成 `AGENTS.md` 的更新，并新建 `ai-product-code-iteration-memory.md` 与 `GLOBAL.md`。
- **背景原因**：为了让当前 IDE（Google DeepMind 平台/Antigravity）能够以最优化、最适配的模式执行和加载最新闭环流规范。
- **影响范围**：在多台 Mac/开发环境同步时提供明确的全局和局部记忆规范约束。

### [2026-07-03] 融入“穷尽探索，使命必达”核心规范
- **决策内容**：在所有核心规范文件（`AGENTS.md`、`ai-product-code-iteration-memory.md`、`GLOBAL.md` 和 `.memory/session.md`）中，加入了穷尽技术路径与工具、永不放弃的执行原则，并划定了“不破坏系统、不恶意删除文件”的安全底线。
- **背景原因**：为了让 AI (Antigravity) 拥有更坚韧的开发决心，在面临复杂或短期难以解决的问题时，不轻易停下或放弃，积极尝试一切备选方案，同时保障物理及数据安全。
- **影响范围**：约束后续所有的任务执行与研究阶段。
