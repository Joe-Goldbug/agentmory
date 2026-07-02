# 项目会话上下文 (.memory/session.md)

本文件作为 **Session 层** 的持久化记忆载体，记录项目的核心背景、关键决策、当前进度与待办事项。

---

## 1. 用户偏好与画像 (User Profile & Preferences)
- **技术水平**：**代码小白**。所有技术解释、部署步骤、代码逻辑改动，必须用极其通俗易懂的语言详细陈述。
- **协作模式**：三层协作结构（Coordinator + Session + Remote Control）。
- **语言偏好**：英文思考（代码内部），**中文输出（与用户交流）**，简洁、明确、不说废话。
- **禁忌**：
  - 严禁未经定位就瞎猜、改动无关代码。
  - 严禁过度设计，优先使用最简单可靠的方案。
  - 严禁在关键事实未得到真实文件/环境验证前下结论或据此执行。

---

## 2. 知识库与工作流关联 (llm-workmem)
- **只读全局 Wiki**：`/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem`
  - 包含全局工作规范、思维模式、自动化 harvest snapshot。
- **项目级 Memory**：保存在本项目根目录下的 `.memory/`，用于记录当前项目的“病历本”（Bug 修复、技术细节与局部决策）。

---

## 3. 当前进度与待办 (Status & TODOs)
- [x] 初始化项目本地 `.agents/AGENTS.md` 规则并加入 Loop Engineering 正式版。
- [x] 在 `.memory/` 下创建及维护 Project Loop 状态文件（`STATE.md`, `DECISIONS.md`, `NEXT.md`, `VERIFY.md`）。
- [ ] 待命：开启下一次具体任务的目标、约束与上下文确认。

---

## 4. 状态与决策管理 (Project Status Logs)
为了满足 Sync Loop 的同步要求，我们在本地项目根目录 `.memory/` 下统一维护如下状态四文件以达成多端一致：
- **[.memory/STATE.md](file:///Users/ethan/Documents/antigravity/.memory/STATE.md)**：追踪项目当前所处阶段（Idea/MVP/Launch/Scale）与核心现状。
- **[.memory/DECISIONS.md](file:///Users/ethan/Documents/antigravity/.memory/DECISIONS.md)**：记录过程中的关键技术、设计或业务判断。
- **[.memory/NEXT.md](file:///Users/ethan/Documents/antigravity/.memory/NEXT.md)**：指定下一轮迭代/任务的最小执行动作。
- **[.memory/VERIFY.md](file:///Users/ethan/Documents/antigravity/.memory/VERIFY.md)**：记录每一轮执行后的具体验证手段及运行数据。

