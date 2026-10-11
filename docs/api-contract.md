# LLM-WorkMem 网关 API 契约（前端 ↔ `lwm/gateway.py`）

> 本文是前端 `web/src/api/` 与后端网关的**共同验收基准**。
> 文中"实测"字段均来自本机 `lwm hub context --format json` 的真实输出（2026-10-11，main @ `1b69ffc`）。
>
> **状态：网关已实现** —— `lwm/gateway.py` + `lwm gateway <root> --port 8766`，标准库 `http.server`，
> 全部端点已实测返回 200。下文即为当前实现契约；标注"占位"的端点（teams / subscription）后端本就无对应能力。

## 0. 传输与通用约定

| 项 | 约定 |
|---|---|
| 协议 | HTTP/1.1，JSON（`Content-Type: application/json; charset=utf-8`） |
| 默认监听 | `127.0.0.1:8766`（与 `lwm serve` 的 8765 错开） |
| 鉴权 | **无**。安全边界＝仅绑定回环地址。跨机联调需显式加 `Access-Control-Allow-Origin` |
| CORS | 生产形态由 Vite dev proxy 同源转发规避；网关默认不发 CORS 头 |
| 超时 | 前端 10s；`/api/candidates` 触发 LLM 分析时放宽至 60s |

### 统一响应结构

```jsonc
// 成功 HTTP 200
{ "ok": true, "data": <T> }

// 失败 HTTP 4xx / 5xx
{ "ok": false, "error": { "code": "E_SCHEMA", "message": "...", "detail": [...] } }
```

> 本项目原本无 HTTP 响应约定（本地优先、纯 CLI），以上为**本网关自定义**，前端 `src/api/client.ts` 按此解包。

### 错误码

| code | HTTP | 含义 | 触发场景 |
|---|---|---|---|
| `E_SCHEMA` | 400 | 事件/参数不符合 schema | `validate_event` 返回 issues，`detail` 原样透出（形如 `$.event_id: missing required key`） |
| `E_NOT_FOUND` | 404 | 资源不存在 | 项目页/候选不存在；`/raw/` 路径越界（沿用 `dashboard.py` 的 `relative_to(root)` 防护） |
| `E_FORBIDDEN` | 403 | 越权访问 | 路径穿越出 `LWM_ROOT` |
| `E_TIMEOUT` | 504 | 处理超时 | LLM 分析器（`LWM_ANALYSIS_*`）不可达 |
| `E_INTERNAL` | 500 | 未捕获异常 | 网关内部错误 |
| `E_NETWORK` / `E_BAD_JSON` | — | 前端侧错误 | 连不上网关 / 返回非 JSON（由 client.ts 本地生成，不经网络） |

---

## 1. 路由清单

### 1.1 `GET /api/health`

- 包装：`lwm/health.py`（等价 `lwm hub health`）；MCP 工具 `health`
- 参数：无
- 返回（前端按此映射状态栏）：

```jsonc
{ "ok": true, "data": {
    "status": "ok | warning | degraded | quality_warning | failed_core", // 实测字段名
    "checked_at": "2026-10-10T19:32:38.014463+00:00",                    // 实测
    "monthly_events": 6,        // 网关补充：当月 raw/events 计数（近似"沉淀条数"）
    "token_budget_used_percent": null  // LWM_ANALYSIS_DAILY_TOKEN_BUDGET 已用比例；未启用为 null
} }
```

### 1.2 `GET /api/projects`

- 扫描 `projects/` + 项目身份注册表（`lwm/project_id.py`，身份形如 `git-9f1cb19971812dd3`）
- 参数：无
- 返回：

```jsonc
{ "ok": true, "data": [
  { "project_id": "git-9f1cb19971812dd3", "title": "Project git-9f1cb19971812dd3", "tag": "前端 · 进行中" }
] }
```

> `tag` 后端无此字段，由网关从项目页 front-matter 或路径推导；无法推导时前端显示"未分类"。

### 1.3 `GET /api/context`

- 包装：`hub_service.context_for_tool()`（等价 `lwm hub context --tool <t> --project <p> --format json`）
- 参数（query，均必填）：`tool`（如 `codex`）、`project`（项目**绝对路径**）
- 返回（**实测结构**）：

```jsonc
{ "ok": true, "data": {
  "tool": "codex",
  "project_path": "D:\\start-up\\LLM-WorkMem",
  "project_id": "git-9f1cb19971812dd3",
  "scope": "project",
  "warnings": ["Canonical GLOBAL.md behavior contract is unavailable."],
  "global_rules": [],
  "project": {
    "project_id": "git-9f1cb19971812dd3",
    "title": "Project git-9f1cb19971812dd3",
    "status":        ["(no status yet)"],
    "decisions":     ["- 2026-10-11T03:36:17+08:00 — 新增 lwm/gateway.py …"],
    "bugfixes":      ["- … — changes: lwm/capability_proof.py — verified: …"],
    "verifications": ["- … 输出 0.1.0", "↳ codex · c61466f4…"],
    "open_questions":["(no open_questions yet)"]
  },
  "active_handoff": null,   // 有值时含 objective/current_state/decisions/changes/verifications/open_questions/next_action
  "behavior_contract": { "path": "GLOBAL.md", "version": "unknown", "sha256": "", "status": "missing" },
  "recent_activity": [ { "key": "…", "tool": "codex", "project_id": "…",
                         "event_type": "workflow_observation", "timestamp": "…",
                         "bucket": "processed", "file": "…\\raw\\events\\processed\\…\\<uuid>.json" } ],
  "insight_candidates": [],
  "accepted_candidates": [],
  "unified_memory": { "release_id": null, "claims": [], "conflicts": [] }
} }
```

**适配要点（前端 `contextAdapter.ts` 已实现）**
1. `decisions/bugfixes/verifications` 元素是**已格式化字符串**（含 `— ` 分隔的时间戳前缀），不是结构化对象，不做二次解析；
2. 空槽位是占位串 `"(no status yet)"` / `"(no open_questions yet)"`，**必须过滤**后再渲染；
3. 工作台"当前目标"取值优先级：`active_handoff.objective` > `project.status[0]` > 空；
4. `active_handoff` 为 `null` 属正常态（无活跃交接包）。

### 1.4 `GET /api/handoff/current`

- 包装：`lwm hub handoff current`（`lwm/handoff.py`）
- 参数：`project`
- 返回：handoff 包或 `{ "ok": true, "data": null }`

### 1.5 `GET /api/behavior`

- 包装：`hub_service.behavior_show()`（`GLOBAL.md` 版本 + SHA-256）
- 返回：`{ version, sha256, path, body }`，`body` 为 Markdown 原文
- **前端不做结构化解析**，直接渲染 Markdown（后端本就是自由文本）

### 1.6 `GET /api/candidates` / `POST /api/candidates/<id>/review`

- 读取：扫描 `state/analysis/candidates/*.md`（`memory_compiler.ANALYSIS_DIR`）
- 写入：`hub_service.review_analysis(root, id, decision=...)`
- POST body：`{ "decision": "accept" | "reject" | "promote" }`；非法值 → `400 E_SCHEMA`
- 候选不存在 → `404 E_NOT_FOUND`
- ⚠️ **无 `edit` 动作**：Demo 的"修正"按钮无后端对应（待确认，见集成文档 §6.3）
- ⚠️ **候选由 LLM 编译器生成**（`lwm hub analyze --pending`，需 `LWM_ANALYSIS_*` 五个环境变量）。
  未配置时本端点恒返回 `[]` —— 这是确定性模式的正常表现，不是故障。

### 1.7 `GET /api/events`

- 扫描 `raw/events/{inbox,processed}/` 下事件 JSON
- 参数：`project`（可选）、`limit`（默认 50）
- 返回：事件数组，字段见 §2 事件 schema

### 1.8 `GET /api/tools` / `POST /api/tools/probe` / `GET /api/tools/coverage`

- 包装：`hub_service.list_tools()` / `coverage_report()`
- 返回项字段：`tool`、`proof_level`、`last_seen`、`readable`、`writable`、`status_reason`、`gaps`
- **Proof 等级由网关推导**（`hub_service.coverage_report` 本身不直接给出）：

| 条件（精确匹配） | proof_level |
|---|---|
| `read_status == "verified"` 或 `write_status == "verified"` | `native-hook` |
| `capture_status == "ok"`，或 read/write 为 `observed` | `watcher-observed` |
| `delivery_status` 以 `configured` 开头，或 `capture_status == "awaiting_first_event"` | `configured` |
| 其余 | `none` |

> ⚠️ **必须精确匹配**：`delivery_status` 的取值是 `configured_unverified`，其中含子串 `verified`，
> 用 `in` 判断会把"仅配置"误判成最高等级 `native-hook`（实现时已踩过此坑）。

- 真实底层字段（实测）：`tool_id`、`status`、`capture_status`、`delivery_status`、`read_status`、`write_status`、`last_capture_at`、`last_read_at`、`last_write_at`、`gaps`、`status_reason`

### 1.9 `GET /api/federation/releases` / `POST /api/federation/restore`

- 包装：`lwm hub federation compile/restore`（`release-*.json` 版本回退）

### 1.10 `GET /api/search`

- 包装：`lwm query` / MCP `search_memory`
- 参数：`q`
- 返回：`[{ title, snippet, pagePath }]`

### 1.11 `GET /api/teams` / `GET /api/subscription`

- **后端无实现**，占位返回：`{ ok: true, data: { available: false, members: [] } }` / 固定套餐列表（仅 Local 档可用）

---

## 2. 事件 schema（写入侧）

来源 `lwm/events.py::REQUIRED_KEYS`，八项必填：

```
event_id, timestamp, tool, project_path, project_id, event_type, importance, privacy
```

可选字符串数组：`decisions`、`changes`、`verification`、`open_questions`

### 准入分类（`lwm/project_memory.py::classify_event`）

| 判定 | 条件 | 后果 |
|---|---|---|
| `durable` | `event_type ∈ {decision, bugfix, verification, project_status}` 且对应字段非空 | **进入项目记忆页**，工作台可见 |
| `operational` | `event_type` 为 `workflow_observation` 等运行事件，或字段不足 | 仅留在 raw 证据，可作最近活动 |
| `rejected` | 命中噪音标记 / 含密钥 | 不渲染 |

> **实操要点（实测踩坑）**：`lwm hub record` 的 `--type` 默认是 `workflow_observation`（操作噪音），
> 不显式指定会让工作台 `project` 字段长期为 `null` 并报 `no admitted durable evidence yet`。
> 制造演示数据务必用 `--type decision|verification|bugfix`。

---

## 3. 环境差异

| 环境 | API 基址 | 说明 |
|---|---|---|
| 本地 | 空（同源 `/api` → Vite proxy → `127.0.0.1:8766`） | 推荐，规避 CORS |
| 联调 | `VITE_LWM_API_BASE=http://<host>:8766` | 网关需临时加 CORS 头 |
| 预发 | **无**（本项目本地优先，无云端形态） | 见集成文档 §4.3 |

## 4. 降级约定

- `VITE_LWM_USE_MOCK=1` → 前端 adapter 直接返回 `web/src/mocks/`，**不发任何请求**；写操作（review/handoff）显式报错禁用，避免假写入。
- 网关运行中不可用 → `client.ts` 置 `degraded=true`，顶部展示降级横幅，页面保留上次数据不白屏。
