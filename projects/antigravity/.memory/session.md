# 项目会话上下文 (.memory/session.md)

本文件作为 **Session 层** 的持久化记忆载体，记录项目的核心背景、关键决策、当前进度与待办事项。

---

## 1. 用户偏好与画像 (User Profile & Preferences)
- **技术水平**：**代码小白**。所有技术解释、部署步骤、代码逻辑改动，必须用极其通俗易懂的语言详细陈述。
- **协作模式**：三层协作结构（Coordinator + Session + Remote Control）。
- **语言偏好**：英文思考（代码内部），**中文输出（与用户交流）**，简洁、明确、不说废话。
- **禁忌与要求**：
  - **盲点扫描 (Blind Spot Pass)**：行动前主动排查并汇报“我不知道且用户可能没考虑到的事”。
  - **访谈模式 (Interviews)**：遇到模糊设定，必须主动确认事实，不瞎猜。
  - **原型优先 (Prototypes)**：高风险修改必须先跑最简 Demo 验证。
  - **测验机制 (Comprehension Quiz)**：代码交付前，针对复杂修改向用户发问，确保消除认知债。
  - **穷尽探索，使命必达**：绝对不能中途放弃。必须竭尽全力调用所有手段解决问题，除破坏系统或恶意删文件外，不设任何手段限制。

---

## 2. 知识库与多端物理同步 (Sync Architecture)
- **多端一致性**：本项目的 `.agents/` 和 `.memory/` 均已与 iCloud (`LLM-WorkMem/projects/antigravity/`) 建立**物理软链接**。
- **全局读取层 (LLM-WorkMem)**：
  - 路径：`/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem`
  - 严格遵守 EPEV (Explore, Plan, Execute, Verify) 全局策略。

---

## 3. 当前进度与待办 (Status & TODOs)
- [x] Loop Engineering 3.0 (EPEV + 未知管理) 规则落地。
- [x] 完成物理软链接跨设备同步配置。
- [ ] 待命：开启下一次具体任务，执行 Loop Engineering 3.0。

---

## 4. 状态与决策管理 (Project Status Logs)
为了满足 Sync Loop，在 `.memory/` 下统一维护如下状态四文件（通过软链接同步云端）：
- **[.memory/STATE.md](file:///Users/ethan/Documents/antigravity/.memory/STATE.md)**：追踪项目当前所处阶段（Idea/MVP/Launch/Scale）与核心现状。
- **[.memory/DECISIONS.md](file:///Users/ethan/Documents/antigravity/.memory/DECISIONS.md)**：记录过程中的关键技术、设计或业务判断（包括 Implementation Notes）。
- **[.memory/NEXT.md](file:///Users/ethan/Documents/antigravity/.memory/NEXT.md)**：指定下一轮迭代/任务的最小执行动作。
- **[.memory/VERIFY.md](file:///Users/ethan/Documents/antigravity/.memory/VERIFY.md)**：记录每一轮执行后的具体验证手段及运行数据。
