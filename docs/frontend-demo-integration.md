# 前端 Demo 对接 LLM-WorkMem 后端落地文档

- **Demo 文件**：`ai_working_memory.tsx`（微信传输副本，位于 `D:\wechat\xwechat_files\wxid_mqzelbakr90t22_03b5\msg\file\2026-10\`，建议先拷贝入仓 `web/demo/ai_working_memory.tsx`）
- **目标后端**：本仓库 `llm-workmem`（`lwm` CLI + MCP stdio + `lwm serve` 本地 HTTP）
- **撰写基准**：main 分支 `1b69ffc`，全部路径、命令、字段名以本仓库真实代码为准

> **先读结论**：本项目的"后端"不是 REST 服务，而是 **① `lwm` CLI（typer）、② `lwm hub bridge` JSON-IPC（stdin/stdout）、③ MCP stdio 服务器（`python -m mcp.lwm_server`）、④ `lwm serve` 本地 HTTP（仅 GET、仅服务端渲染 HTML）**。Demo 要拿到结构化数据，必须新增一个薄 JSON 网关（本文 §3 给出贴合项目"标准库优先"哲学的最小方案），其余全部围绕真实 CLI/函数签名展开，缺失项一律显式标注。

---

## 1. 现状梳理（Demo 侧）

### 1.1 技术栈

| 项 | 实际情况 |
|---|---|
| 框架 | React（函数组件 + Hooks，语法基准 ≥ React 17；仅用到 `useState`） |
| 语言 | TypeScript（`.tsx`，但文件内**未出现类型标注**，实质是可编译为 tsx 的 JS） |
| 样式 | Tailwind CSS 类名（含 `animate-in fade-in`，依赖 `tailwindcss-animate` 插件的类；另有多处**动态拼接类名**如 `` bg-${item.color}-100 ``，JIT 模式下不会生成，见 §6 排障） |
| 构建 | **无**。没有 package.json、无 vite/webpack 配置、无 tsconfig —— 单文件组件，需自建工程（§5） |
| 依赖版本 | **待确认：Demo 未携带任何锁文件，React / Tailwind / TS 版本均未锁定。建议落地时自行定版（§5.1 给出推荐组合）** |

### 1.2 目录结构（Demo 侧）

单文件，共 1009 行，结构如下（行号以微信副本为准）：

```
ai_working_memory.tsx
├── L4-95    Icons            # 18 个内联 SVG 图标组件
├── L97-104  NAVIGATION       # 侧边导航（含写死的"待确认 (3)"计数）
├── L106-110 PROJECTS         # 项目卡片（3 个写死项目）
├── L112-238 App()            # 布局骨架 + 状态栏 + 订阅弹窗挂载
├── L240-354 SubscriptionModal # 订阅套餐（4 个写死 plan）
├── L356-490 WorkspaceView    # 项目工作台
├── L492-616 WorkStyleView    # 我的工作方式
├── L618-701 ConfirmView      # 待确认
├── L703-827 HistoryView      # 历史与恢复
├── L829-926 ToolsView        # 工具连接
└── L928-1009 TeamView        # 团队共享
```

### 1.3 运行环境

Demo 本身无运行环境（无构建链）。落地时按本仓库环境执行：

- 本机 Python：3.13.12（managed）与 3.11.5（system）均满足 `pyproject.toml` 的 `requires-python >= 3.11`
- 本机 Node：22.22.2（managed）
- ⚠️ README 声明支持操作系统为 **macOS / Linux**；本机为 **Windows**，`lwm hub install-shell-hook`（Zsh）等命令在 Windows 不可用，不影响网关方案（见 §5.4）

### 1.4 数据来源清单（全部为文件内写死常量，无 mock 文件、无本地假接口、无第三方接口、零 `fetch` 调用）

| # | 数据 | 所在位置（文件 + 行号） | 消费视图 |
|---|---|---|---|
| 1 | 导航项 + 待确认计数 `待确认 (3)` | `ai_working_memory.tsx` L97-104 `NAVIGATION` | 侧边栏 |
| 2 | 用户身份"李 慢走 / 免费版" | L159-167 内联 JSX | 侧边栏底部 |
| 3 | 项目卡片 `p1/p2/p3` | L106-110 `PROJECTS` | WorkspaceView |
| 4 | 订阅方案 Local/Personal/Pro/Team（含价格 ¥39/¥89/¥69） | L241-278 `plans` | SubscriptionModal |
| 5 | 当前目标（token 过期修复） | L417 内联 JSX | WorkspaceView |
| 6 | 最近成果 3 条 + "更新于 2 小时前" | L424-437 内联 | WorkspaceView |
| 7 | 关键决定 2 条 | L445-449 内联 | WorkspaceView |
| 8 | 验证结果（单测 5/5、E2E 3/3） | L456-461 内联 | WorkspaceView |
| 9 | 未完成事项 2 条 | L476-484 内联 | WorkspaceView |
| 10 | 偏好设置表（语言/风格/测试/文档） | L526-538 内联 | WorkStyleView |
| 11 | 执行规则 3 条 | L549-552 内联 | WorkStyleView |
| 12 | 适用范围 + 适用工具（Claude Code/Codex/OpenCode） | L573-604 内联 | WorkStyleView |
| 13 | 待确认 items（rule/conflict/outdated 三类） | L619-623 `items` | ConfirmView |
| 14 | 历史 4 条（含状态/来源/时间） | L704-709 `history` | HistoryView |
| 15 | 版本详情（变更内容/验证/来源） | L782-808 内联 | HistoryView |
| 16 | "区块链证明 / 查看哈希值" | L816-820 内联 | HistoryView |
| 17 | 工具连接 3 项 + 开关 | L830-834 `tools` | ToolsView |
| 18 | 连接设置（允许读取的项目/自动记录/同步云端） | L876-914 内联 | ToolsView |
| 19 | 团队成员 4 人 + 团队设置 | L929-934 `members` | TeamView |
| 20 | 状态栏（云端同步: 正常 / 节省 28 次 / 额度 42%） | L220-229 内联 | 全局底栏 |

---

## 2. 后端现状（本项目侧）

### 2.1 已有的"服务"清单（真实存在，全部本地）

| 服务 | 启动方式 | 形态 | 前端可用性 |
|---|---|---|---|
| `lwm` CLI | `lwm <command>`（入口 `lwm.cli:main`，`pyproject.toml [project.scripts]`） | 同步命令行，多数子命令支持结构化输出（`--format json` 等） | ⚠️ 不能被浏览器直接调用，需网关转译 |
| `lwm hub bridge` | `lwm hub bridge`（读 stdin JSON） | **JSON IPC**（stdin/stdout，`lwm/central_cli.py`） | ⚠️ 仅适合 Node/Electron 宿主进程 spawn，浏览器不可用 |
| MCP 服务器 | `python -m mcp.lwm_server <root>` | JSON-RPC 2.0 over stdio（`mcp/lwm_server.py`，刻意不依赖官方 MCP SDK） | ⚠️ 同上，浏览器不可用 |
| `lwm serve` | `lwm serve <root> --host 127.0.0.1 --port 8765` | **唯一 HTTP 服务**：`lwm/dashboard.py::serve_wiki`，`ThreadingHTTPServer` + `BaseHTTPRequestHandler` | ❌ 仅 GET，仅返回服务端渲染 HTML，**没有 `/api/*` JSON 路由** |

`lwm serve` 的全部路由（`dashboard.py` L997-1028）：

```
GET / | /index.html | /dashboard   → 服务端渲染仪表盘 HTML
GET /_refresh                      → 302 跳回 /
GET /page/<rel>                    → 渲染单页 HTML（404 文本兜底）
GET /raw/<rel>                     → raw/ 目录内纯文本（有路径穿越防护，越界返回 403）
其余                               → 404 "Not found"（纯文本）
```

**缺失项（显式标注）**：本项目**不存在 HTTP JSON API、不存在鉴权（token/cookie/网关）、不存在统一 HTTP 响应结构与错误码约定**。这些不是"没找到"，是架构上就没有 —— 本项目设计原则为"本地优先与确定性"（README.zh-CN.md §核心设计原则 5），安全边界就是 `127.0.0.1` 绑定本身。占位方案见 §3.0（网关自带最小 `{ok, data, error}` 约定）。

### 2.2 可复用的数据/函数接口清单（网关将包装它们）

以下全部为真实函数，位于 `lwm/` 包，可被网关直接 import：

| 能力 | 函数 / 命令 | 位置 | 输出要点 |
|---|---|---|---|
| 启动上下文 | `hub_service.context_for_tool()`；CLI `lwm hub context --tool <t> --project <p> --format json` | `lwm/hub_service.py` L182；`lwm/context.py` | 行为规范状态、活跃 handoff、项目记忆、全局经验、审查候选，上限 12k 字符 |
| 提交事件 | `hub_service.record_event()` / `retain_event()`；CLI `lwm hub record` | `lwm/hub_service.py` L61/L166 | 写入 `raw/events/inbox/`，经 `lwm/events.py::validate_event` 校验 |
| 项目记忆页 | `memory_api.reflect_project()`；MCP `get_project_memory` | `lwm/memory_api.py` L95 | `projects/<project_id>/` 下的 Markdown 状态页 |
| 证据召回 | `memory_api.recall()`；CLI `lwm hub recall` | `lwm/memory_api.py` L51 | 渐进检索，返回计划/证据来源/覆盖/缺失 |
| 候选分析与审查 | `memory_compiler.analyze_pending / review_analysis_candidate / promote_analysis`；CLI `lwm hub analyze --pending` / `review-analysis` / `promote-analysis` | `lwm/memory_compiler.py` | 候选 `candidates-*.md`，审查动作 accept / reject / promote |
| 工具探查 | `hub_service.list_tools()` / `coverage_report()`；CLI `lwm hub tools probe` / `coverage` | `lwm/hub_service.py` L421/L493 | 工具发现状态、双向读写 Proof 等级 |
| 健康快照 | `lwm/health.py`；MCP `health`；CLI `lwm hub health` | `lwm/health.py` | ok / warning / degraded / quality_warning / failed_core 分级 |
| 行为合同 | `hub_service.behavior_show / behavior_verify` | `lwm/hub_service.py` L532/L536 | `GLOBAL.md` 版本 + SHA-256 |
| 任务交接 | `lwm hub handoff create/current/ack/close`（`lwm/handoff.py`） | `lwm/handoff.py` | handoff 包字段见 §3 映射表（与 Demo 工作台字段高度同构） |
| 周期回执 | `hub_service.verify_cycle()`；`lwm/cycle_receipt.py`（CycleReceiptV2） | `lwm/cycle_receipt.py` | 不可变回执 + 证据哈希校验 |
| 联邦记忆 | `lwm hub federation compile / restore`（`lwm/memory_federation.py`） | `lwm/memory_federation.py` | 统一发布版本 `release-*.json`，可回退历史版本 |
| 知识检索 | `lwm query` / MCP `search_memory` | `lwm/query.py` | 顶栏搜索框可用 |

事件 schema（`lwm/events.py` L52-61，前端提交事件时的必填字段）：

```
必填：event_id, timestamp, tool, project_path, project_id,
      event_type, importance, privacy
可选（字符串数组）：decisions, changes, verification, open_questions …
校验失败返回 issues 列表，字段定位格式为 "$.<key>"（如 "$.event_id: missing required key"）
```

### 2.3 数据落盘位置（网关读取的数据源）

| 目录 | 内容 |
|---|---|
| `raw/events/inbox/` | 事件 JSON（前端"历史"视图的原始证据） |
| `projects/<project_id>/` | 项目记忆页（工作台视图数据；项目身份 = `git-<hash>`，见 `lwm/project_id.py`） |
| `wiki/`、`global/` | 知识页与晋级后的全局规则（`promote-analysis` 产出 `wiki/global/*.md`） |
| `state/` | 健康快照、回执等运行时状态（README 注明本目录不入库，仅本机有效） |

---

## 3. 对接方案

### 3.0 前置：新增薄 JSON 网关 ✅ **已实现**

> **实现状态（2026-10-11）**：`lwm/gateway.py` 与 `lwm gateway` 子命令已完成，8 个端点实测全部 200，
> 错误码符合契约，端到端写入回路已验证（record → ingest → `/api/context` 读到新决定）。
> 前端已切换至真实数据（`web/.env.local` 的 `VITE_LWM_USE_MOCK=0`）。
> 其余章节的对接映射照此实现；`teams` / `subscription` 为后端无能力项，按占位返回。

由于本项目没有 HTTP JSON API，**落地第一步是在仓内新增 `lwm/gateway.py`**，用标准库 `http.server` 扩展（与 `dashboard.py::serve_wiki` 同款技术栈，不引入 FastAPI/flask —— 遵守 `GLOBAL.md` "标准库优先、避免无用抽象" 的行为合同）：

```
lwm/gateway.py        # 新增：ThreadingHTTPServer + /api/* JSON 路由
                      # 复用 hub_service / memory_api 的现有函数，不写新业务逻辑
lwm/cli.py            # 修改：新增 `lwm gateway <root> --host --port` 子命令（模仿 serve_cmd，cli.py L1001 附近）
```

网关统一响应约定（**本网关自定义**，因项目无既有约定）：

```json
// 成功：HTTP 200
{ "ok": true, "data": { ... } }
// 失败：HTTP 4xx/5xx
{ "ok": false, "error": { "code": "E_SCHEMA" | "E_NOT_FOUND" | "E_INTERNAL", "message": "...", "detail": [...] } }
```

~~待确认：是否接受"仓内新增 gateway.py"这一改动~~ → **已按此方案实现**。
⚠️ 该改动触及 `lwm` 包源码（`gateway.py` 新增 + `cli.py` 新增子命令 + `capability_proof.py` 跨平台修复），
**合入上游前建议与仓库所有者确认**（配合笔者为协作者身份）。

### 3.1 逐条数据替换映射（Demo 数据位置 → 接口 → 调用方式 → 字段映射）

#### ① 项目卡片 + 工作台（数据 #3 #5 #6 #7 #8 #9）—— 对接优先级最高

| 项 | 内容 |
|---|---|
| 原数据位置 | `PROJECTS`（L106-110）+ WorkspaceView 内联 JSX（L417-L484） |
| 对应接口 | `GET /api/context?tool=<t>&project=<abs-path>`（网关包装 `hub_service.context_for_tool`，等价 `lwm hub context --format json`）；活跃交接用 `GET /api/handoff/current?project=<abs-path>`（包装 `lwm hub handoff current`） |
| 调用方式 | GET，query 参数：`tool`（如 `codex`）、`project`（项目**绝对路径**，经 `lwm/project_id.py` 解析为 `git-<hash>` 身份） |
| 字段差异映射 | Demo 写死字段 → handoff 包真实字段（`lwm/handoff.py`，README §跨 Agent 任务交接）：当前目标→`objective`；最近成果→`changes`+`verifications`；关键决定→`decisions`；未完成事项→`open_questions`；"Claude Code 徽标"→`tool`。**适配层位置**：前端 `src/api/adapters/contextAdapter.ts`，把 context/handoff JSON 摊平为视图模型 `{goal, outcomes[], decisions[], verifications[], open[]}` |

> Demo 的"项目卡片列表"没有专门接口 —— 项目列表来自 `lwm hub context` 遍历已知项目 + `state/` 项目路径映射。**待确认：是否需要网关新增 `GET /api/projects`（扫描 `projects/` 目录 + `project_id` 注册表）。建议加，工作量约 20 行。**

#### ② 我的工作方式（#10 #11 #12）

| 项 | 内容 |
|---|---|
| 原数据位置 | WorkStyleView 内联（L526-604） |
| 对应接口 | `GET /api/behavior`（包装 `hub_service.behavior_show`，返回 `GLOBAL.md` 版本与 SHA-256）；全局规则列表读 `wiki/global/*.md`（`promote-analysis` 的晋级产物）；"适用工具"读 `GET /api/tools`（见 ⑤） |
| 字段差异映射 | 偏好表/执行规则在真实系统中**不是结构化键值**，而是 `GLOBAL.md` 与 `wiki/global/*.md` 的 Markdown 正文。**适配层位置**：前端 `src/api/adapters/behaviorAdapter.ts`，将 Markdown 按标题切片渲染（或直接用 react-markdown 展示原文，推荐后者，避免解析脆弱） |

#### ③ 待确认（#1 #13）—— 与"候选审查"天然对应

| 项 | 内容 |
|---|---|
| 原数据位置 | `NAVIGATION` 计数（L100）+ `ConfirmView items`（L619-623） |
| 对应接口 | 列表：`GET /api/candidates`（包装 `memory_compiler.analyze_pending` 的读取路径 / `lwm hub analyze --pending` 输出）；操作：`POST /api/candidates/<id>/review`，body `{"decision": "accept"|"reject"|"promote"}`（包装 `review_analysis_candidate`，等价 `lwm hub review-analysis <id> --decision <d>`） |
| 字段差异映射 | Demo 的三类 item → 真实候选类型：`rule`→新规则候选、`conflict`→`lwm/conflict.py` 冲突检测结果、`outdated`→过期候选。Demo 按钮"接受/修正/拒绝"→ 真实动作 `accept`/`promote`/`reject`（**"修正"无对应动作**，见待确认）。导航计数 = 待审候选数量 |
| **待确认** | ① "修正"按钮：`review-analysis` 只有 accept/reject/promote 三种 decision，无"编辑后接受"，需要前端先展示候选 Markdown、再由用户提交修正事件（`POST /api/events`）；② 候选的优先级字段（Demo 的高/中/低）：`candidates-*.md` 是否携带 priority 元数据需查 `lwm/memory_compiler.py::Candidate` dataclass 后定，**当前版本未见显式 priority 字段** |

#### ④ 历史与恢复（#14 #15 #16）

| 项 | 内容 |
|---|---|
| 原数据位置 | `HistoryView history`（L704-709）+ 版本详情（L782-808）+ 区块链证明（L816-820） |
| 对应接口 | 时间线：`GET /api/events?project=<id>&limit=50`（网关扫描 `raw/events/inbox/`，读事件 JSON 原文）；版本恢复：`GET /api/federation/releases` + `POST /api/federation/restore`（包装 `lwm hub federation restore`，可回退到指定 `release-*.json`）；"哈希值"：事件证据链的 SHA-256（`hub_service._sha256` / `verify_cycle` 使用的哈希校验） |
| 字段差异映射 | Demo `status`（已验证/已确认/已废弃）→ 真实字段 `event_type` + `importance` + 隐私分类结果（`durable`/`operational`/`rejected`，`classify_event`）；Demo "区块链证明" → **本项目没有区块链**，真实对应物是 CycleReceiptV2 的证据哈希校验。**建议 UI 文案改为"证据哈希校验"**，语义才成立（`lwm/cycle_receipt.py`） |

#### ⑤ 工具连接（#17 #18）

| 项 | 内容 |
|---|---|
| 原数据位置 | `ToolsView tools`（L830-834）+ 连接设置（L876-914） |
| 对应接口 | `GET /api/tools`（包装 `hub_service.list_tools`，等价 `lwm hub tools list`）；探测 `POST /api/tools/probe`（等价 `lwm hub tools probe --root`）；覆盖报告 `GET /api/tools/coverage`（包装 `coverage_report`，等价 `lwm hub coverage`） |
| 字段差异映射 | Demo `status: '已连接'` → 真实的**三级 Proof 等级**：`configured`（仅配置）/ `watcher-observed`（观察器捕获）/ `native-hook verified`（宿主原生 Hook 凭证），这是本项目最核心的区分（README §真实凭证严格审计）；"最近使用：2 小时前" → capability receipt 的时间戳（`lwm/capability_proof.py`）。连接设置里的开关（自动记录/同步云端）→ **无对应配置项**，见缺失清单 |

#### ⑥ 团队共享（#19）—— 无后端，显式缺失

本项目 `federation` 是**本机跨 Agent** 记忆联邦，不是多人协作系统。成员、角色、权限、邀请、审计日志在仓库中**均不存在**。占位方案：TeamView 保留 UI 但数据源挂 `GET /api/teams`（网关固定返回 `{ok:true, data:{members:[], feature:"not_available"}}`），前端展示"团队功能未在本部署中启用"空态。**待确认：团队功能是否在产品规划内；若是，需要后端先设计多用户模型（当前连用户概念都只有 `GLOBAL.md` 行为合同）。**

#### ⑦ 订阅弹窗（#4）与用户身份（#2）—— 无后端，显式缺失

无支付/订阅/计费模块，无用户账号体系。占位方案同 ⑥：`GET /api/subscription` 返回固定 `{plan: "local", features: [...]}` —— 注意项目 README 明确 **Local 档 = 免费本地运行**，这与 Demo 的 Local 档文案（"¥0 / 月，本地记忆"）恰好兼容，可以直接用真实语义填充 Local 档，其余三档置灰"未开放"。**待确认：商业化方案（¥39/¥89/¥69 定价）是否为既定产品决策。**

#### ⑧ 全局状态栏（#20）

| 项 | 内容 |
|---|---|
| 对应接口 | `GET /api/health`（MCP `health` 工具 / CLI `lwm hub health`） |
| 字段差异映射 | "云端同步: 正常" → health 分级 `ok`（**注意文案应为"本地记忆服务"** —— 本项目无云端）；"额度 42%" → `LWM_ANALYSIS_DAILY_TOKEN_BUDGET` 已用比例（`lwm/memory_compiler.py` 的每日 Token 预算控制）；"本月节省重复解释 28 次" → **无对应指标，显式缺失**，占位：网关统计 `raw/events/inbox/` 当月事件数近似展示，文案改为"本月沉淀工作事件 N 条" |

#### ⑨ 顶栏搜索（L185-199）

对应 `lwm query` / MCP `search_memory`（大小写不敏感子串检索 wiki 页）。适配层：`src/api/adapters/searchAdapter.ts`，把命中页片段转 `{title, snippet, pagePath}`，点击跳 `/page/<rel>`（复用 `lwm serve` 已有页面路由或前端路由内渲染）。

### 3.2 适配层总览（前端侧唯一允许改写数据形状的位置）

```
web/src/api/
├── client.ts            # fetch 封装：统一解 {ok,data,error}，超时 10s，错误抛 typed Error
├── endpoints.ts         # 全部 URL 常量，一处管理
└── adapters/
    ├── contextAdapter.ts    # ① context/handoff → 工作台视图模型
    ├── behaviorAdapter.ts   # ② GLOBAL.md / wiki/global → 工作方式
    ├── candidateAdapter.ts  # ③ candidates → 待确认列表
    ├── eventAdapter.ts      # ④ inbox 事件 → 历史时间线
    ├── toolAdapter.ts       # ⑤ probe/coverage → 工具卡片 + Proof 等级
    └── searchAdapter.ts     # ⑨ query 结果 → 搜索下拉
```

**规则**：视图组件只认 adapter 输出的视图模型；后端字段名变化只改 adapter，不动视图。

---

## 4. 环境配置

### 4.1 后端已有环境变量（真实，`lwm/` 代码中出现）

| 变量 | 用途 | 出处 |
|---|---|---|
| `LWM_ROOT` | 工作记忆数据根目录（网关必须接收，等价 CLI `--root`） | `lwm/adapters.py` L239 |
| `LWM_ANALYSIS_ENABLED` / `LWM_ANALYSIS_BASE_URL` / `LWM_ANALYSIS_API_KEY` / `LWM_ANALYSIS_MODEL` / `LWM_ANALYSIS_DAILY_TOKEN_BUDGET` | 可选 LLM 离线编译器（未配置时系统纯确定性运行，核心功能不受影响） | README §内存编译器配置 |
| `LWM_GLOBAL_PATH` | 覆盖 `GLOBAL.md` 权威路径 | `lwm/behavior_contract.py` L101 |
| `LWM_HOST_BRIDGE` | `== "1"` 时 bridge 信任宿主 | `lwm/central_cli.py` L615 |

### 4.2 需新增的环境变量与配置项

| 新增项 | 命名 | 说明 |
|---|---|---|
| 前端 API 基址 | `VITE_LWM_API_BASE` | 开发默认空（走 Vite 同源代理）；显式指定时直连网关 |
| Mock 兜底开关 | `VITE_LWM_USE_MOCK` | `=1` 时前端完全不发请求，adapter 返回内置 mock（见 §5.5），用于后端不可用时演示 UI |
| 网关端口约定 | 网关默认 `127.0.0.1:8766`（与 `lwm serve` 默认 8765 错开，避免同时启动时冲突） | 建议写死为 CLI 默认值而非环境变量 |
| 命名规范 | 前端环境变量一律 `VITE_LWM_` 前缀；网关路由一律 `/api/` 前缀 + 小写连字符资源名 | 与仓内 `LWM_` 前缀习惯保持一致 |

### 4.3 三环境差异

| 环境 | 形态 | 差异说明 |
|---|---|---|
| **本地开发** | Vite dev server（5173）+ proxy `/api → http://127.0.0.1:8766`；网关由开发者手动起 | 同源代理规避 CORS（`BaseHTTPRequestHandler` **不带任何 CORS 响应头**，直连必被浏览器拦截，见 §6） |
| **联调** | 同本地，但 `VITE_LWM_API_BASE` 显式指向协作者机器的网关；网关需临时加 `Access-Control-Allow-Origin: <联调源>`（仅联调期） | 项目无联调基础设施，此行即联调规范 |
| **预发** | **缺失，显式标注**：本项目本地优先、无云端部署形态（README §核心设计原则 5），不存在预发环境。占位方案：若未来需要，用同一网关二进制部署到内网主机并改绑 `--host`，但这超出当前仓库范围。**待确认：是否有预发部署计划** |

---

## 5. 启动步骤（Windows 本机，从零到页面）

### 5.1 建立前端工程（一次性）

```powershell
# 在仓库根新建 web/（与 lwm/ 平级，不进 python 包）
cd D:\start-up\LLM-WorkMem
npm create vite@latest web -- --template react-ts
cd web
npm install
npm install -D tailwindcss @tailwindcss/vite tailwindcss-animate
# vite.config.ts: 注册 @tailwindcss/vite 插件；src/index.css: @import "tailwindcss";
# （Tailwind v4 写法；若锁 v3 则用 postcss 方案 —— 建议 v4，与 Demo 的任意值语法 bg-[#f8f9fa] 兼容）
# 把 ai_working_memory.tsx 拷入 web/src/，拆分视图到 web/src/views/，mock 常量迁到 web/src/mocks/
```

### 5.2 安装后端 CLI（Python 侧）

```powershell
cd D:\start-up\LLM-WorkMem
# 用本机 Python 3.11.5（系统）或 3.13.12（managed）皆可；推荐建 venv：
D:\python\python.exe -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\lwm --version          # 预期输出版本号，验证安装
```

> `pyproject.toml` 运行依赖仅 `typer>=0.12.0`，无其他强制依赖，安装应秒级完成。**待确认：本机是否装有 `uv`；有则用 `uv pip install -e ".[dev]"` 更快，无则 pip 即可。**

### 5.3 起网关（依赖 §3.0 的 gateway.py 已合入）

```powershell
# 终端 1：网关（数据根 = 仓库本身，LWM_ROOT 指向本仓库）
.venv\Scripts\lwm gateway D:\start-up\LLM-WorkMem --port 8766
# 预期输出类似：Serving LLM-WorkMem API gateway at http://127.0.0.1:8766/
```

### 5.4 起前端

```powershell
# 终端 2：
cd web
npm run dev
# 预期：http://localhost:5173 打开"AI 工作记忆"界面，侧边栏六项导航可切换
# 注意：Windows 下不要执行 README 中的 install-shell-hook / install-ide-hooks 中的 Zsh 部分
```

### 5.5 后端不可用时的 mock 兜底降级

```powershell
# 方式一：环境开关（推荐，进入 web/ 后）
$env:VITE_LWM_USE_MOCK = "1"; npm run dev
# 方式二：.env.local 文件写 VITE_LWM_USE_MOCK=1
```

降级行为规范（实现在 `src/api/client.ts`）：`VITE_LWM_USE_MOCK=1` → adapter 全部返回 `web/src/mocks/` 下从 Demo 原常量整理的固定数据；网关中途挂掉 → client.ts 捕获 fetch 异常，展示"后端不可用，已切换演示数据"横幅，页面不白屏。**降级只影响读取；所有写操作（review/handoff）在 mock 模式下直接禁用按钮，避免假写入误导。**

---

## 6. 验证与排障

### 6.1 分模块验证清单（先 curl 后页面，逐模块打勾）

| 模块 | 验证命令（网关起后） | 预期结果 |
|---|---|---|
| 网关本身 | `curl http://127.0.0.1:8766/api/health` | `{"ok":true,"data":{...health 分级...}}` |
| 工作台 | `curl "http://127.0.0.1:8766/api/context?tool=codex&project=D%3A%5Cstart-up%5CLLM-WorkMem"` | JSON 含 behavior/handoff/project memory 段；页面"项目工作台"显示真实目标/决定而非"token 过期"示例 |
| 待确认 | `lwm hub analyze --pending --root .` 生成候选后刷新页面 | 列表出现真实候选；点"接受"后 `lwm hub review-analysis <id> --decision accept` 幂等（再查不再出现） |
| 历史 | `curl "http://127.0.0.1:8766/api/events?limit=10"` | 返回 `raw/events/inbox/` 真实事件；页面时间线与其一一对应 |
| 工具 | `curl http://127.0.0.1:8766/api/tools/coverage` | 各工具带 proof 等级；页面卡片显示"已配置/已验证"而非清一色"已连接" |
| 搜索 | 页面顶栏输入 `handoff` | 出现命中 wiki 页片段，点击可跳转 |
| 写入回路 | 页面提交一条事件 → `ls raw/events/inbox/` | inbox 出现新 JSON，`lwm hub ingest .` 后项目页更新 |

### 6.2 常见问题定位

| 症状 | 根因 | 定位与解法 |
|---|---|---|
| **鉴权失败（401/403）** | 本项目**没有鉴权**，出现 403 只可能是两种情况：① 命中了 `/raw/` 路径穿越防护（`dashboard.py` L1019 `resolved.relative_to(root)` 抛 ValueError → 403）——检查请求路径是否越出 `LWM_ROOT`；② 网关自定义的 E_NOT_FOUND 规则 —— 看响应体 `error.message`。若未来真的加了鉴权，**待确认：鉴权方案设计（当前仓库无任何相关代码）** |
| **跨域拦截（浏览器 CORS 报错）** | `BaseHTTPRequestHandler` 不发 CORS 头，前端直连 `127.0.0.1:8766` 必挂 | 正确形态是走 Vite 同源代理（§4.3）；必须直连时在 gateway.py 临时加 `Access-Control-Allow-Origin` 响应头。诊断：DevTools Network 看响应头缺 `Access-Control-Allow-*` 即为此因 |
| **接口超时** | `ThreadingHTTPServer` 无超时中间件；`memory_compiler` 若启用 LLM 分析（`LWM_ANALYSIS_ENABLED=1`）且 API Key 无效/网络不通会长时间阻塞 | ① client.ts 设 10s 超时并提示重试；② 分析类端点（`/api/candidates` 触发 analyze 时）单独放 60s；③ 检查 `LWM_ANALYSIS_BASE_URL` 可达性（本机需走代理的场景注意：Python 进程不继承浏览器代理设置） |
| **返回字段缺失** | 事件校验层会拒绝缺字段请求：`validate_event` 返回 `issues`，形如 `{"path":"$.event_id","message":"missing required key"}` | 前端提交前对照 §2.2 的 REQUIRED_KEYS 八项自查；网关把 issues 原样放进 `error.detail`，页面展示 `$.<字段>` 定位；读取侧字段缺失（如候选无 priority，见 §3.1③）→ adapter 里显式 `?? null` 并在 UI 空态兜底 |
| **动态 Tailwind 类名不生效** | Demo 用 `` bg-${item.color}-100 `` 拼类名（L647、L739、L849 等），JIT 扫描不到字符串拼接产物 | 重构为显式映射表：`const COLOR_MAP = { orange: 'bg-orange-100 text-orange-600 …', … }`，全量枚举后 JIT 才能生成 |
| **`lwm: command not found`（Windows）** | pip 装进了别的解释器/未激活 venv | 用 `.venv\Scripts\lwm` 绝对路径调用，或先 `Activate.ps1`；确认 `pip install -e` 输出里含 `lwm.exe` 安装路径 |
| **端口冲突** | `lwm serve` 默认 8765 与网关 8766 需同时空余 | `netstat -ano | findstr 876` 查占用；网关端口可用 `--port` 改 |
| **数据为空（页面全空态）** | `raw/events/inbox/`、`projects/` 在新克隆的仓库里几乎是空的（本仓库当前仅 `projects/antigravity` 有内容） | 这是**真实状态而非 bug**。可先跑 `lwm hub record --tool shell --project <路径> --task "演示" --decision "…" --root .` + `lwm hub ingest .` 制造真实数据，或开 `VITE_LWM_USE_MOCK=1` 看完整 UI |

### 6.3 待确认清单汇总（本文档全部显式待确认项）

1. 是否接受仓内新增 `lwm/gateway.py` + `lwm gateway` 子命令（§3.0）
2. 是否需要 `GET /api/projects` 项目列表端点（§3.1①）
3. 待确认"修正"按钮的产品语义（后端只有 accept/reject/promote）（§3.1③）
4. 候选是否携带优先级元数据（需查 `Candidate` dataclass）（§3.1③）
5. 团队共享功能的产品规划（后端完全缺失）（§3.1⑥）
6. 订阅/计费的产品决策（后端完全缺失）（§3.1⑦）
7. "节省重复解释次数"指标的统计口径（后端缺失，现有近似方案）（§3.1⑧）
8. 本机是否安装 `uv`（影响安装命令选择）（§5.2）
9. 预发环境是否存在部署计划（§4.3）
10. 若未来引入鉴权，方案设计（当前零鉴权代码）（§6.2）

---

## 7. 本机实测补充（Windows，2026-10-11 前置工作中实测）

README 声明支持 macOS / Linux，本机为 Windows。以下均为真实踩坑与已验证处置。

### 7.1 `lwm/capability_proof.py` 导入 `fcntl`，Windows 下 CLI 入口即崩

- 现象：任何 `lwm` 命令均 `ModuleNotFoundError: No module named 'fcntl'`。
- 位置：`lwm/capability_proof.py:16`，仅用于 `_receipt_lock()` 的 `fcntl.flock` 文件加锁。
- 已处置：改为守卫式导入 —— POSIX 用 `fcntl.flock`，Windows 用 `msvcrt.locking`，两者皆无时退化为不加锁。**全仓仅此一处 POSIX-only 依赖**（已扫 `termios/pwd/grp/resource/os.fork` 均无）。
- ⚠️ 属对上游仓库源码的改动，合入前建议与仓库所有者确认。

### 7.2 `raw/` `wiki/` `automation/` 是 git 符号链接，Windows 克隆后退化成文本占位文件

- 现象：`git ls-files -s` 显示 mode `120000`（符号链接），指向 `/Users/ethan/Library/Application Support/llm-workmem-runtime/llm-workmem/raw` 等 macOS 路径；Windows 克隆后变成 76/77 字节普通文本，导致 `mkdir` 抛 `FileExistsError: [WinError 183] 当文件已存在时，无法创建该文件`。
- 已处置：建立本地运行时数据根 `.runtime/`（含 `raw/events/inbox`、`wiki`、`projects`、`global`、`state`），所有命令显式 `--root` 指向它。
- 结论：**Windows 上数据根必须是真实目录，不能直接用仓库根**；网关启动同样需传该路径。

### 7.3 沙箱删除守卫阻止 `lwm hub ingest` 清理锁文件

- 现象：`OSError: [safe-delete][SAFE_DELETE_FAIL_CLOSED] … windows-sandbox-recycle-bin-unavailable`，目标为项目自己的 `state/locks/ingest.lock`。
- 根因：WorkBuddy 注入的 `sitecustomize.py` 删除守卫（`CODEBUDDY_SAFE_DELETE_SANDBOX=1` 时启用），**非项目代码**。
- 已处置：对该条命令临时 `CODEBUDDY_SAFE_DELETE_SANDBOX=0`，随后 `ingest ok=True processed=3 rejected=0 failed=0`。

### 7.4 事件准入：默认 `--type` 是操作噪音，工作台会长期空

- `lwm hub record` 的 `--type` 默认 `workflow_observation` → 判为 `operational`，**不进项目记忆**。
- 表现：`lwm hub context` 返回 `project: null` + 警告 `Project is registered but has no admitted durable evidence yet`。
- 正确做法：`--type decision | verification | bugfix | project_status`（白名单 `lwm/project_memory.py::DURABLE_EVENT_TYPES`）。按此重录 3 条后，`project.decisions/verifications/bugfixes` 正常填充。
- 另注：`decisions/verifications` 元素是**已格式化字符串**（含时间戳前缀），空槽位用 `"(no status yet)"` 占位，前端必须过滤（已在 `contextAdapter.ts` 实现）。

### 7.5 前端工程已在 Windows 验证通过

- `npm install` → `npm run build`（`tsc -b && vite build`）通过：53 modules，CSS 28.52 kB —— 说明静态配色表被 Tailwind 正确生成，§6.2 的动态类名坑已消除。
- `npm run dev` 后 `http://localhost:5173` 返回 200。

### 7.6 网关实现期的两个实测坑（已修，写网关时勿重犯）

1. **中文查询串乱码**：`http.server` 按 **ISO-8859-1** 解码请求行，`/api/search?q=网关` 直接搜会永远为空。
   修复：在 handler 内 `self.path.encode("iso-8859-1").decode("utf-8")` 还原后再 `urlparse`（`gateway.py::_serve`）。
2. **Proof 等级误判**：`delivery_status` 取值 `configured_unverified` 含子串 `verified`，
   用 `in` 判断会把"仅配置"误判为最高级 `native-hook`。必须用**精确等值**判断（见 `docs/api-contract.md` §1.8）。

### 7.7 跑起来的完整命令（本机已验证）

```bash
# 终端 1：网关（数据根必须是真实目录，见 §7.2；Windows 需解除沙箱删除守卫，见 §7.3）
cd D:/start-up/LLM-WorkMem
CODEBUDDY_SAFE_DELETE_SANDBOX=0 ./.venv/Scripts/lwm.exe gateway "D:/start-up/LLM-WorkMem/.runtime" --port 8766

# 终端 2：前端
cd web && npm run dev      # http://localhost:5173

# 制造/刷新数据（注意 --type 必须落在 DURABLE 白名单内，见 §7.4）
./.venv/Scripts/lwm.exe hub record --tool codex --project "D:/start-up/LLM-WorkMem" \
  --type decision --task "..." --decision "..." --root "D:/start-up/LLM-WorkMem/.runtime"
./.venv/Scripts/lwm.exe hub ingest "D:/start-up/LLM-WorkMem/.runtime"
```
