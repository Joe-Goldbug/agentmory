# 全局共享状态规范 (.agents/GLOBAL.md)

本文件作为 **Sync Loop** 的全局媒介，记录多台 Mac/开发环境共享的全局工作习惯、当前跨项目全局状态，并指定当前活动的具体项目。

---

## 1. 全局开发习惯与禁忌 (Global Habits & Taboos)

### 🔹 交互原则
- **代码小白伙伴**：AI 必须永远使用最直观、通俗的中文解释，给出详细的指令与步骤。
- **穷尽探索，使命必达**：接收目标后不能随意停下或因为短期做不到而放弃。必须积极寻找和尝试所有方法、所有技能 (skills)、所有 MCP 工具、所有网络上的解决方案。除破坏系统或恶意删除文件的行为外，不设任何手段限制。
- **极简工程**：杜绝过度设计，除非用户主动要求，否则不引入复杂依赖。
- **真相比速度重要**：坚守 Truth-First Loop，没有看完日志/真实文件前，不随便下“这应该是权限问题”、“这应该是依赖没装好”之类的模糊结论。

### 🔹 框架与样式偏好
- **核心**：HTML + 原生 Javascript。
- **样式**：Vanilla CSS 优先，拒绝无意义的 TailwindCSS 堆叠，除非用户主动指定并确认版本。
- **交互**：优先使用 CSS transition/animation 配合原生 Web API 实现流畅的微动特效，打造精致的设计美学。

---

## 2. 跨设备同步状态区 (Multi-Device State Tracking)

在多台设备（如公司 Mac、家里 Mac）之间切换时，全局状态通过 iCloud（或 Git 共享库）的本文件进行同步。

| 字段 | 当前配置值 | 说明 |
| :--- | :--- | :--- |
| **当前活动项目** | `antigravity` | 当前正在主力开发的本地项目目录名 |
| **上次同步时间** | `2026-06-24 13:29:00` | 上次更新此全局状态的时间戳 |
| **当前多端主干分支** | `main` | 多端应当拉取并对齐的 Git 分支名称 |
| **待同步关键偏好** | 无额外变更 | 待应用到其他设备的全局 Instruction 变更 |

---

## 3. 设备切换检查清单 (Device Handover Checklist)

当你更换电脑，在另一台 Mac 上唤醒 AI 时，请让 AI 立即执行以下指令：
1. **[ ] 检查 GLOBAL.md**：核对全局偏好与“当前活动项目”是否一致。
2. **[ ] 检查项目四文件**：跳转至具体项目（如本项目的 `.memory/`），依次阅读 `STATE.md` 与 `NEXT.md` 继承进度。
3. **[ ] 本机环境校对**：核对本机层的权限、端口号占用情况与本地凭据，确认无误后在 `NEXT.md` 划定的任务边界内启动开发。

<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use this llm-workmem as the shared workflow and memory source for this tool.
Project: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/projects/antigravity`

Read order:
0. **On session start**, run `lwm hub context --tool <your-tool-name> --project /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/projects/antigravity /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem` to get the latest dynamic context (project memory, recent decisions, open questions). This is always fresher than the static files below.
1. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.txt` for compact context (fallback if step 0 is unavailable).
2. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/purpose.md` for scope and guardrails.
3. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/overview.md` for the current synthesis.
4. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms-full.txt` only when deeper context is needed.
5. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.json` for programmatic page metadata.

Write-back:
- After meaningful work, emit events via `lwm hub record` so the hub stays current.
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.
<!-- LLM-WIKI:END -->
