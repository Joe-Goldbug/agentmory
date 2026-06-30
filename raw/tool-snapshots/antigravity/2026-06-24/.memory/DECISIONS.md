# Project Decisions (项目关键决策)

### [2026-06-24] 确立 Loop Engineering 四大闭环运行规范
- **决策内容**：正式通过 `Loop Engineering` 草案作为双端/双机开发的最核心同步与工程规范。
- **背景原因**：为了让 AI (Antigravity) 做到不说错、不瞎猜，在跨设备开发中保持状态与习惯的一致。
- **影响范围**：约束所有未来的 Project 迭代与 Bug 修复行为。

### [2026-06-24] 融入最新正式版 Loop Engineering 规范并建立适配文件
- **决策内容**：在 `.agents/` 目录下完成 `AGENTS.md` 的更新，并新建 `ai-product-code-iteration-memory.md` 与 `GLOBAL.md`。
- **背景原因**：为了让当前 IDE（Google DeepMind 平台/Antigravity）能够以最优化、最适配的模式执行和加载最新闭环流规范。
- **影响范围**：在多台 Mac/开发环境同步时提供明确的全局和局部记忆规范约束。
