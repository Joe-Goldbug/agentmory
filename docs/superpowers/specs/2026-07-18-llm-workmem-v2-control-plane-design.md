# LLM-WorkMem V2 本机工作记忆控制中心技术规格

> 历史文档：本规格不再是当前架构权威。2026-07-28 Lean Core、经批准的
> goal-completion requirements 及其 HLD/LLD 已 supersede 本文的第二控制面、
> `projects/<id>/STATE.md` 层级和冲突的 source-of-truth 规则。本文仅保留
> 与当前架构不冲突的隐私、身份、来源、保留和验证要求供审计参考。

- 状态：待技术评审
- 日期：2026-07-18
- 目标仓库：`/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem`
- 目标平台：macOS Apple Silicon
- 目标用户：Ethan
- 文档用途：产品定义、架构设计、逐文件改造规格、测试与验收合同

## 1. 执行摘要

LLM-WorkMem V2 不再被定义为一个定时生成 Markdown 的脚本。它必须成为本机所有 AI 编程工具共同使用的工作流与记忆控制中心。

系统必须完成五个闭环：

1. 每个已支持工具在会话开始时读取项目与全局上下文，并留下真实读取回执。
2. 每个已支持工具在重要节点和会话结束时写入结构化工作结果。
3. 所有事件稳定归属到同一个项目身份，跨 IDE、CLI 和 Shell 共享。
4. codebase-memory-mcp 负责代码结构图，LLM-WorkMem 负责项目事实、决策、验证和召回，两者通过明确接口协作。
5. macOS 自动化在开机和唤醒后补跑，并且健康状态由时效、回执、数据流和索引覆盖共同决定。

本设计采用本地优先、文件真源、可重建索引、渐进式召回和能力矩阵。默认不上传原始对话或项目内容到云端。

## 2. 已验证事实

以下结论来自 2026-07-18 对本地代码、launchd、日志和产物的实际检查。

### 2.1 已经工作的部分

- `com.ethan.lwm.harvest` 已被 launchd 加载。
- `RunAtLoad=true`，`StartInterval=43200`。
- launchd 有历史运行记录，最近一次退出码为 0。
- `lwm hub context --tool codex ...` 可以返回动态上下文。
- Codex、Claude Code、OpenCode、Antigravity、Kiro 和 MiniMax 已存在静态入口文件。
- audit、schema 和基础评估可以通过。
- LLM-WorkMem 已具备事件、ingest、project memory、context、health、MCP 和 CBMEM 包装模块。

### 2.2 已验证的问题

- 最近一次成功周期距离检查时间约 21.5 小时，超过 12 小时规则。
- 当前健康分类没有把产物过期判断为 degraded 或 failed。
- `privacy_rejection_rate` 的算法错误地把所有 rejected 都计为隐私拒绝。
- 2026-07-17 的 68 条 rejected 实际为 66 条 `duplicate:dedup_key` 和 2 条 `duplicate:session_window`。
- 适配器周期性重复提交同一事件，制造大量无意义拒绝记录。
- 用户仓库的 `lwm-sources.json` 配置了 CBMEM 项目，但 launchd 运行时目录缺少该文件。
- 运行时因此报告 `CBMEM: 0/0 projects indexed`。
- 当前 `run_cycle` 同时承担适配器扫描、Shell 扫描、ingest、watch、audit、adapter 写入和 health，责任边界过大。
- 当前部分 Hook 配置是基于推测格式写入，存在“文件存在但工具不读取”的风险。
- 当前静态 instructions 只能证明入口已写入，不能证明工具真正读取。
- 当前 context 未强制传入实际工作项目时，会出现 `no project memory yet`。
- 现有设计规格 `docs/superpowers/specs/2026-07-11-llm-workmem-central-hub-design.md` 是 0 字节文件，不能作为实现依据。

## 3. 目标与非目标

### 3.1 必须达到的目标

- LLM-WorkMem 是全局工作规则和各项目状态的唯一中心。
- 活跃工具必须能够读取当前项目的精简上下文。
- 支持写入的活跃工具必须自动记录重要工作结果。
- 同一 Git 项目在不同路径别名、IDE 和 Shell 中解析为同一项目 ID。
- 项目事实必须包含来源、时间、置信度和替代关系。
- CBMEM 必须对所有启用项目保持可查询且索引不落后于目标 Git HEAD。
- 自动化必须在开机或唤醒后 15 分钟内检查补跑需求。
- 健康页面必须如实区分 installed、reachable、read-confirmed、write-confirmed 和 unsupported。
- 任何 `healthy` 结论必须有机器可核验的证据。

### 3.2 明确不做的内容

- 不抓取没有官方接口的封闭 IDE 全量聊天数据库。
- 不把未经筛选的全部聊天原文注入每个新会话。
- 不建立第二个 Obsidian 或 Basic Memory 仓库。
- 不默认部署 Neo4j、FalkorDB、PostgreSQL 或 Docker 服务。
- 不复制 OpenViking 或 Basic Memory 的 AGPL 源码。
- 不允许 LLM-WorkMem 修改 IDE 的实验开关、权限绕过或不受支持配置。
- 不删除现有 raw、wiki、项目记忆或用户未提交修改。

## 4. 外部最佳实践及采用边界

### 4.1 claude-mem

来源：[thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)

采用：

- SessionStart、UserPromptSubmit、PostToolUse、Stop、SessionEnd 生命周期思想。
- 本地 worker 与持久化事件存储分离。
- 搜索索引、时间线和完整观察的三段式渐进召回。
- 读取历史和 Web Viewer 可观察性。

不采用：

- 不直接引入第二套 Bun、Chroma 和独立记忆真源。
- 不对每次 PostToolUse 都生成长期记忆。

### 4.2 codebase-memory-mcp

来源：[DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)

采用：

- 基于官方能力的客户端矩阵。
- 无可靠 Hook 就不伪造自动 Hook。
- MCP 直接查询代码图。
- SessionStart 自动检查索引和后台 Git watcher。
- fail-open 的上下文增强。
- 工具分层：Scout、Verify、Auditor。

直接使用：

- 继续使用已安装的 `codebase-memory-mcp` 二进制和 MCP/CLI。
- 由 CBMEM 自己管理图数据库、自动索引和 watcher。

停止使用：

- LLM-WorkMem 不再每 12 小时调用五个 CBMEM 命令并复制大批 JSON 快照作为主要集成方式。

### 4.3 OpenViking

来源：[volcengine/OpenViking](https://github.com/volcengine/OpenViking)

只采用架构思想：

- 统一命名空间。
- L0 摘要、L1 概览、L2 证据三级上下文。
- 检索轨迹可观察。
- 会话结束后的记忆自迭代。

### 4.4 Graphiti

来源：[getzep/graphiti](https://github.com/getzep/graphiti)

采用：

- 事实有效期。
- 新事实替代旧事实，但旧历史不删除。
- 每条派生结论回指原始 episode/event。
- 增量更新而不是全量重算。

### 4.5 Hindsight

来源：[vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)

采用：

- Retain、Recall、Reflect 三阶段接口。
- World facts、Experiences、Mental models 三类记忆。
- 反思从多个经历中产生新洞察。

### 4.6 Mem0

来源：[mem0ai/mem0](https://github.com/mem0ai/mem0)

采用：

- 默认 ADD-only，避免错误 UPDATE/DELETE 毁坏历史。
- Agent 已验证的执行结果是一等记忆。
- 语义、BM25、实体和时间信号融合召回。

### 4.7 context-infrastructure

来源：[grapeot/context-infrastructure](https://github.com/grapeot/context-infrastructure)

采用：

- 行为规则、用户偏好、工作观察和技能分层。
- 每日 observer 和每周 reflector 分工。
- 个人公理必须从用户自己的历史中形成，不能复制别人的内容。

## 5. 总体架构

```text
┌─────────────────────────────────────────────────────────────┐
│ Codex / Claude Code / OpenCode / Kiro / Trae / Antigravity │
│ MiniMax / VS Code / Shell CLI                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                 capability-aware adapter
                           │
          ┌────────────────┴────────────────┐
          │                                 │
  Session handshake                  Session events
  context + read receipt             spool + write receipt
          │                                 │
          └────────────────┬────────────────┘
                           │
                  LLM-WorkMem Control Plane
      ┌───────────────┬───────────────┬────────────────┐
      │ Project ID    │ Retain/Recall │ Health/SLO     │
      │ Registry      │ Reflect       │ Supervisor     │
      └───────────────┴───────┬───────┴────────────────┘
                              │
      ┌───────────────────────┴────────────────────────┐
      │ GLOBAL.md / projects/<id>/STATE.md / raw/events│
      │ SQLite/FTS derived index / generated WebUI      │
      └───────────────────────┬────────────────────────┘
                              │
                    codebase-memory-mcp
                    code graph + auto watcher
```

## 6. 状态所有权

每类信息只能有一个主文件或主存储。

| 信息类型 | 唯一真源 | 说明 |
|---|---|---|
| Agent 行为规则 | `AGENTS.md` | 工具共同遵守的行为规则 |
| 用户与全局共享事实 | `GLOBAL.md` | 已审核、跨项目长期有效 |
| 项目当前状态 | `projects/<project-id>/STATE.md` | 目标、状态、决策、风险、验证 |
| 短期上下文缓存 | `MEMORY.md` | 可重建，不参与冲突裁决 |
| 原始工作证据 | `raw/events/` | append-only，隐私清洗后保存 |
| 会话与检索索引 | `state/lwm.sqlite3` | 派生数据，可重建 |
| 项目身份 | `state/project-registry.json` | 路径、remote、别名和启用能力 |
| 工具能力 | `config/tool-capabilities.toml` | 官方能力和本机验证结果 |
| 运行回执 | `state/receipts/` | read/write/adapter/cycle 证据 |
| 代码结构 | CBMEM 自有 SQLite/压缩图 | LWM 不复制为第二真源 |
| HTML/Wiki | 生成视图 | 不允许手工写入关键事实 |

冲突优先级：

```text
AGENTS.md / GLOBAL.md / projects/<id>/STATE.md
  > MEMORY.md
  > generated wiki/html
  > raw event interpretation
```

## 7. 组件设计

### 7.1 Supervisor

职责：每 15 分钟执行一次轻量检查，在完整周期到期或上次失败时启动周期。

输入：

- 当前时间。
- `state/cycle-state.json`。
- 运行锁。
- 电源/登录后的首次运行状态。

输出：

- `skipped_not_due`。
- `started` 和 cycle ID。
- `completed` 或 `failed`。
- 更新 `last_attempt_at`、`last_success_at`、`next_due_at`。

规则：

- launchd `StartInterval=900`。
- `RunAtLoad=true`。
- 完整周期成功后 12 小时再次到期。
- 失败后采用 15、30、60 分钟退避，最多 60 分钟。
- 单周期默认超时 30 分钟。
- 使用原子锁，已有周期运行时返回 `skipped_locked`。
- 系统睡眠期间不承诺执行；唤醒后下一次 15 分钟检查负责补跑。

### 7.2 Project Registry

职责：把不同工具、路径别名和工作树统一成稳定项目身份。

项目 ID 算法：

1. Git 仓库有 remote：规范化 remote URL 后计算 `git-<sha256前16位>`。
2. Git 仓库无 remote：使用 Git common dir 和首次注册 canonical path 计算 `local-git-<sha256前16位>`。
3. 非 Git 项目：canonical path 计算 `local-<sha256前16位>`。
4. 临时无项目会话：`adhoc-<sha256前16位>`，不得自动晋升为项目长期记忆。

注册字段：

```json
{
  "schema_version": 2,
  "project_id": "git-0123456789abcdef",
  "name": "LLM-WorkMem",
  "canonical_path": "/absolute/path",
  "aliases": ["/other/worktree/path"],
  "git_remote": "github.com/ethanlau1/llm-workmem",
  "enabled": true,
  "cbmem_enabled": true,
  "first_seen_at": "2026-07-18T16:00:00+08:00",
  "last_seen_at": "2026-07-18T16:00:00+08:00"
}
```

### 7.3 Capability Registry

职责：描述工具真实支持什么，不把静态入口冒充自动集成。

字段：

```toml
[tools.claude-code]
detect = ["~/.claude"]
read = "native_hook"
write = "native_hook"
mcp = true
session_start = true
session_end = true
source = "official"
verified_version = "local-current"

[tools.trae]
detect = ["~/Library/Application Support/Trae"]
read = "mcp_or_instructions"
write = "unsupported_until_verified"
mcp = "conditional"
session_start = false
session_end = false
source = "official_or_existing_config_only"
```

允许状态：

- `unsupported`
- `instructions_only`
- `mcp_configured`
- `hook_installed`
- `reachable`
- `read_confirmed`
- `write_confirmed`

状态只能逐级提升，且必须有回执。

### 7.4 Handshake 与回执

会话开始调用：

```bash
lwm hub handshake \
  --tool codex \
  --project "$PWD" \
  --session-id "$SESSION_ID" \
  --format markdown
```

返回：

```json
{
  "schema_version": 2,
  "receipt_id": "uuid",
  "tool": "codex",
  "project_id": "git-...",
  "context_revision": "sha256:...",
  "layers": ["L0", "L1"],
  "generated_at": "ISO8601",
  "markdown": "..."
}
```

握手成功后写入 `state/receipts/read/YYYY-MM-DD/<receipt-id>.json`。

禁止：

- 仅因为 `AGENTS.md` 存在就生成 read receipt。
- 仅因为 MCP 配置存在就生成 reachable receipt。
- 工具没有执行上下文命令时推测它已经读取。

### 7.5 Event V2

只保留对长期工作有意义的生命周期事件：

- `session_start`
- `checkpoint`
- `decision`
- `change`
- `verification`
- `session_end`
- `reflection`
- `fact_superseded`
- `adapter_probe`

事件示例：

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "timestamp": "2026-07-18T16:00:00+08:00",
  "tool": "codex",
  "tool_version": "current",
  "session_id": "session-uuid",
  "project_path": "/absolute/project/path",
  "project_id": "git-0123456789abcdef",
  "event_type": "verification",
  "importance": "project",
  "task": "修复 LLM-WorkMem 调度",
  "decisions": [],
  "changes": ["Supervisor 改为 15 分钟检查"],
  "verification": ["launchctl runs increased", "last_exit_code=0"],
  "open_questions": [],
  "files_touched": ["lwm/supervisor.py"],
  "source": {
    "kind": "native_hook",
    "receipt_id": "uuid"
  },
  "confidence": 1.0,
  "privacy": "sanitized"
}
```

### 7.6 事件队列和 ingest

事件写入采用 spool，不要求 Hub 服务常驻：

```text
raw/events/spool -> processed | deduplicated | blocked | failed
```

分类必须分开：

- `processed`：形成有效项目或全局状态。
- `deduplicated`：事件有效但与已有事实重复。
- `blocked`：隐私清洗后没有可保留内容。
- `invalid`：schema 不合法。
- `failed`：系统错误，可重试。

隐私规则：

- 发现密钥时先替换密钥值，再继续处理安全内容。
- 敏感路径只替换路径，不自动丢弃整个事件。
- 仅当清洗后无有效任务、决定、变更或验证时进入 blocked。
- rejected 不再作为统一桶。

幂等键：

```text
sha256(project_id + tool + session_id + event_type + normalized_payload)
```

### 7.7 Retain

Retain 将 processed 事件归类为：

- `world_fact`：项目、工具或环境的客观事实。
- `experience`：执行过什么、遇到什么问题、验证结果如何。
- `decision`：采用或拒绝了什么方案以及原因。
- `preference`：用户稳定偏好。
- `open_loop`：未完成问题和下一状态。

默认 ADD-only。修改现有事实时写一条新事实并使用：

```json
{
  "supersedes": "old-fact-id",
  "valid_from": "ISO8601",
  "valid_to": null,
  "source_event_ids": ["uuid"],
  "confidence": 0.95
}
```

旧事实更新 `valid_to`，但原文和来源不删除。

### 7.8 项目状态文件

`projects/<project-id>/STATE.md` 固定结构：

```markdown
# Project: <name>

## Identity
## Current Objective
## Current Status
## Decisions
## Changes
## Verifications
## Risks
## Open Questions
## Tool Activity
## CBMEM Status
## Sources
```

写入规则：

- 每个 section 由结构化记录编译，不允许自由覆盖整份文件。
- 每条事实包含事实 ID 和来源事件 ID。
- 状态只保留当前有效事实。
- 历史通过 SQLite/event source 查询。

### 7.9 Recall

召回分三层：

- L0：约 100 到 300 tokens，项目身份、当前目标、关键风险。
- L1：约 1,000 到 2,500 tokens，最近决定、变更、验证、未解决问题。
- L2：按需读取完整事件、文件证据、CBMEM 结果和时间线。

默认 session handshake 返回 L0 + L1。L2 只能由明确查询触发。

召回流程：

1. 精确项目 ID 过滤。
2. BM25/FTS 查询。
3. 实体、标签和文件路径匹配。
4. 时间衰减和当前有效事实提升。
5. 必要时调用可选语义检索。
6. 返回 compact results、timeline、full evidence 三段式结果。

每次召回生成 retrieval trace：

```json
{
  "query": "调度为什么失败",
  "project_id": "git-...",
  "stages": ["project_filter", "fts", "temporal_rank", "evidence_expand"],
  "selected_fact_ids": ["fact-1"],
  "token_estimate": 1320
}
```

### 7.10 Reflect

分为两个周期：

- Daily observer：每天完整周期中分析最近 24 小时 processed events。
- Weekly reflector：每 7 天分析重复模式、冲突、失败和跨项目规律。

反思输出必须标记为 candidate，不能直接写入 GLOBAL.md。

自动晋升条件：

- 同一模式跨至少两个项目出现，或同一项目三次出现。
- 至少包含两个独立 source event。
- confidence >= 0.85。
- 不与 GLOBAL.md 当前规则冲突。

冲突或低置信度内容进入 review queue。

### 7.11 CBMEM 集成

CBMEM 直接读取 Project Registry 中 `cbmem_enabled=true` 的项目。

流程：

1. 首次注册项目时执行 `index_repository`。
2. 后续由 CBMEM `auto_watch=true` 维护增量索引。
3. Session handshake 检查 `index_status`，不阻塞上下文返回。
4. Recall 需要代码证据时直接使用 MCP 工具。
5. LWM 只保存 project name、indexed commit、generation、更新时间和错误。

废弃行为：

- `cbmem_source.harvest_cbmem()` 不再是主周期必经步骤。
- 不再每天保存 architecture/search/dead-code/changes 全量快照。
- 只有需要长期引用的 ADR 或验证结论写回项目状态。

### 7.12 Health 与 SLO

Health 分类必须使用以下规则。

#### Healthy

- launchd 已加载。
- supervisor 最近检查 <= 20 分钟。
- 完整周期最近成功 <= 12 小时 15 分钟。
- failed spool = 0。
- invalid 事件在最近周期 = 0。
- 所有 active project 都有稳定 project ID。
- 所有 cbmem_enabled project 索引可用且不落后于指定 HEAD。
- audit 通过。

#### Degraded

- 周期过期但 <= 24 小时。
- 某个活跃工具只有 instructions，尚无真实 read receipt。
- 某个 CBMEM 项目索引落后但仍可查询。
- 单次周期失败但退避重试尚未耗尽。

#### Failed

- 周期成功时间 > 24 小时。
- launchd 未加载。
- 连续两次完整周期失败。
- state/项目真源不可读写。
- 事件发生数据丢失。
- CBMEM 全部不可达且项目需要代码记忆。

工具健康单独展示，不因长期未使用的工具拖累系统：

```text
detected -> configured -> reachable -> read_confirmed -> write_confirmed
```

### 7.13 Dashboard

WebUI 只读取状态，不承担调度。

首页必须显示：

- 总体状态及判定原因。
- 最近 supervisor 检查。
- 最近完整周期成功。
- 下一次到期时间。
- 各工具能力、安装、可达、读回执、写回执。
- 各项目最后活动和当前目标。
- CBMEM 项目覆盖和索引 HEAD。
- processed/deduplicated/blocked/invalid/failed 分布。
- 最近 retrieval trace。
- review candidates。

禁止用绿色 `OK` 隐藏过期、未连接或 0/0 覆盖。

## 8. CLI 与 MCP 合同

### 8.1 新增 CLI

```bash
lwm hub supervise ROOT [--force]
lwm hub cycle ROOT [--reason scheduled|startup|manual|retry]
lwm hub handshake --tool TOOL --project PATH --session-id ID ROOT
lwm hub checkpoint --tool TOOL --project PATH --session-id ID [event fields]
lwm hub close-session --tool TOOL --project PATH --session-id ID [summary fields]
lwm hub receipts ROOT [--tool TOOL] [--project PATH]
lwm hub capability ROOT [--tool TOOL] [--probe]
lwm hub health ROOT --strict --json

lwm project register PATH ROOT
lwm project list ROOT
lwm project status PATH ROOT
lwm project enable-cbmem PATH ROOT

lwm memory retain ROOT EVENT_JSON
lwm memory recall ROOT QUERY --project PATH --layer L0|L1|L2
lwm memory reflect ROOT --scope daily|weekly [--write-candidates]

lwm migrate v2 ROOT [--dry-run]
```

兼容保留：

- `lwm hub record` 继续支持 Event V1，内部迁移为 V2。
- `lwm hub context` 调用新的 handshake/context builder，但默认不写回执；只有 `handshake` 写真实回执。
- `lwm hub run-cycle` 暂时作为 `cycle` 别名，发出 deprecation warning。

### 8.2 MCP 工具

保留：

- `query_context`
- `record_event`
- `search_memory`
- `get_project_memory`

新增：

- `start_session`
- `record_checkpoint`
- `close_session`
- `recall_timeline`
- `get_evidence`
- `get_health`
- `get_capabilities`
- `get_cbmem_status`

所有 MCP 写操作返回 receipt ID；所有读操作返回 context revision 或 retrieval trace ID。

## 9. 工具接入矩阵

实现前必须再次核对本机工具版本和官方接口。以下为目标策略，不是未经验证的完成声明。

| 工具 | 读取优先级 | 写入优先级 | 不支持时的行为 |
|---|---|---|---|
| Claude Code | native SessionStart + MCP | Stop/SessionEnd hook | instructions fallback |
| Codex | trusted hook + MCP + AGENTS | hook 或 session close command | AGENTS + explicit receipt |
| OpenCode | MCP/plugin + AGENTS | plugin lifecycle | explicit `lwm-session` wrapper |
| VS Code/Copilot | user MCP + official session hook | official hook/extension | instructions only |
| Antigravity | MCP + GEMINI/AGENTS | documented CLI hook if present | durable instructions |
| Kiro | MCP + steering | verified hook only | no invented hook |
| Trae/Trae Solo | existing MCP config only | verified hook only | conditional/manual UI |
| MiniMax | MCP/custom agent + shell wrapper | wrapper or official hook | instructions only |
| Shell Claude/OpenCode | shell wrapper + native CLI files | shell/session wrapper | explicit command |
| Antigravity CLI | MCP/config + wrapper | lifecycle if documented | explicit command |

每个 adapter 必须具备：

- detect。
- plan。
- install。
- probe。
- uninstall owned changes。
- preserve user changes。
- version gate。
- receipt evidence。

## 10. 逐文件修改规格

### 10.1 新增文件

| 文件 | 责任 |
|---|---|
| `lwm/supervisor.py` | 到期判断、退避、锁和 cycle ledger |
| `lwm/cycle_state.py` | 原子读写 cycle state |
| `lwm/project_registry.py` | 项目注册、别名、CBMEM 开关 |
| `lwm/capabilities.py` | 工具能力矩阵和状态机 |
| `lwm/receipts.py` | read/write/adapter/cycle 回执 |
| `lwm/spool.py` | 原子事件 spool 和重试 |
| `lwm/memory_store.py` | SQLite/FTS 派生索引 |
| `lwm/retain.py` | 事件到事实/经历/决定/open loop |
| `lwm/recall.py` | L0/L1/L2 和 retrieval trace |
| `lwm/reflect.py` | daily/weekly candidates |
| `lwm/cbmem_bridge.py` | CBMEM 项目状态和直接查询适配 |
| `lwm/migrate_v2.py` | V1 到 V2 非破坏迁移 |
| `config/tool-capabilities.toml` | 工具官方能力真源 |
| `tests/test_supervisor.py` | 到期、唤醒补跑、退避和锁 |
| `tests/test_capabilities.py` | 状态机和版本 gate |
| `tests/test_receipts.py` | 不可伪造回执 |
| `tests/test_project_registry_v2.py` | 跨路径/工作树项目身份 |
| `tests/test_event_v2.py` | 新 schema 和兼容迁移 |
| `tests/test_spool.py` | 原子写、重试和分类 |
| `tests/test_retain_recall.py` | 三级召回和事实替代 |
| `tests/test_reflect.py` | 候选晋升规则 |
| `tests/test_cbmem_bridge.py` | 项目覆盖和 HEAD 新鲜度 |
| `tests/test_health_v2.py` | SLO 分类 |
| `tests/test_adapter_contract.py` | detect/install/probe/uninstall 合同 |

### 10.2 修改文件

| 文件 | 必须修改的内容 |
|---|---|
| `lwm/events.py` | 增加 schema_version、V2 类型、supersedes、receipt、有效期 |
| `lwm/ingest.py` | 分离 deduplicated/blocked/invalid/failed；调用 retain |
| `lwm/dedup.py` | 新幂等键，重复不进入 rejected |
| `lwm/privacy.py` | 红action 后继续处理；只在无有效内容时 blocked |
| `lwm/project_id.py` | 代理给 Project Registry；保留 V1 映射兼容 |
| `lwm/project_memory.py` | 编译 `projects/<id>/STATE.md`，不自由重写 |
| `lwm/context.py` | L0/L1/L2、项目必选、context revision |
| `lwm/query.py` | 使用 recall pipeline 和 retrieval trace |
| `lwm/health.py` | 时效、真实拒绝分类、回执、CBMEM 覆盖和 strict 状态 |
| `lwm/runner.py` | 只编排完整 cycle，不生成重复 adapter 事件 |
| `lwm/harvest.py` | launchd 改为 supervisor 900 秒；复制完整运行时配置 |
| `lwm/hooks_gen.py` | 重构为能力驱动 adapter；删除推测 Hook |
| `lwm/adapters.py` | 区分 instructions、MCP 和 hook；写 owned marker |
| `lwm/cbmem.py` | 对齐当前二进制 CLI/MCP；暴露 list/index status |
| `lwm/cbmem_source.py` | 标记 deprecated，不再进入默认周期 |
| `lwm/central_cli.py` | 注册新 CLI，保留兼容别名 |
| `lwm/audit.py` | 新增真源、状态、回执和索引审计 |
| `lwm/dashboard.py` | 新健康矩阵、项目、事件分类和检索轨迹 |
| `mcp/lwm_server.py` | 新增 session/receipt/health tools |
| `automation/launchd/com.ethan.lwm.harvest.plist` | 900 秒 supervisor，名称可暂时兼容旧 label |
| `pyproject.toml` | 版本升级、必要依赖和 console contract |
| `README.md` | V2 架构、CLI、健康和迁移 |
| `README.zh-CN.md` | 与英文 README 同步 |

### 10.3 停止或废弃

- 停止 `_sweep_shell_events()` 每周期只读取最后一行并重复提交。
- 停止 health 用 rejected 总数计算 privacy rate。
- 停止 adapter 只返回 `ok` 而没有实际 probe 证据。
- 停止运行时依赖用户 iCloud 仓库中的 Python import。
- 停止 CBMEM 0/0 时仍显示总体 healthy。
- 保留旧命令至少一个兼容版本，不立即删除数据或 CLI。

## 11. 实现顺序和停止条件

### 阶段 A：Truthful Core

实现：

- cycle state 和 supervisor。
- Event V2 分类。
- health V2。
- project registry。

停止条件：

- 过期任务必定 degraded/failed。
- duplicate 不再算 privacy。
- runtime 配置缺失必定被 audit 发现。

### 阶段 B：Read/Write Receipts

实现：

- capability registry。
- handshake。
- receipt store。
- Claude Code、Codex、OpenCode 和 Shell 第一批 adapter。

停止条件：

- 至少四个工具通过真实会话回执验证。
- 静态文件存在不能生成 confirmed 状态。

### 阶段 C：Project Memory

实现：

- retain。
- STATE.md compiler。
- L0/L1/L2 recall。
- temporal facts。

停止条件：

- 同一项目跨工具读取到同一 current objective、decision 和 verification。
- 旧事实被替代但仍可追溯。

### 阶段 D：CBMEM Direct Bridge

实现：

- registry 驱动 CBMEM。
- auto index/watch 状态。
- MCP direct query。
- 索引覆盖 health。

停止条件：

- 所有启用项目显示实际 indexed project count。
- 当前项目能返回 architecture、symbol 和 change impact。

### 阶段 E：剩余 IDE 与 UI

实现：

- Kiro、Trae、Antigravity、MiniMax、VS Code 逐个能力审计和 adapter。
- Dashboard V2。
- daily/weekly reflect。

停止条件：

- 每个工具显示真实能力级别和最近证据。
- 不支持的能力明确显示 unsupported/manual，不伪装成功。

## 12. 测试合同

### 12.1 单元测试

- 使用注入时钟测试 12 小时到期和 15 分钟补跑。
- 测试并发 supervisor 只允许一个周期。
- 测试 duplicate、blocked、invalid、failed 独立计数。
- 测试 sensitive value 被 redacted 后事件仍 processed。
- 测试 Git remote、无 remote、worktree、路径别名项目 ID。
- 测试事实 supersede 和时间查询。
- 测试 L0/L1/L2 token budget。
- 测试 health 每个阈值边界。

### 12.2 集成测试

- 临时 HOME 中安装和卸载 adapter，不覆盖用户内容。
- MCP `start_session -> checkpoint -> close_session -> recall` 全链路。
- runtime repo 与 user repo 配置同步。
- CBMEM binary missing、项目未索引、索引落后、索引正常四种状态。
- V1 事件和 project pages 非破坏迁移。

### 12.3 本机真实验收

每个工具必须执行一次真实会话，不接受只检查文件：

1. 启动工具进入测试 Git 项目。
2. 验证 read receipt 包含真实 tool、project ID 和 context revision。
3. 完成一个小修改和验证。
4. 结束会话。
5. 验证 write receipt、processed event 和 STATE.md。
6. 从另一个工具启动同一项目。
7. 验证它能召回前一个工具的决定和验证。

### 12.4 完整验证命令

最终工程师必须提供等价命令的真实输出：

```bash
pytest -q
ruff check .
lwm audit <root> --eval-suite <root>/wiki/eval-suite.txt
lwm hub health <root> --strict --json
lwm project list <root>
lwm hub receipts <root>
codebase-memory-mcp cli list_projects
launchctl print gui/$(id -u)/com.ethan.lwm.harvest
```

## 13. 验收标准

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| AC-01 | 开机补跑 | 登录/唤醒后 15 分钟内 supervisor 有回执 |
| AC-02 | 12 小时周期 | last_success 不超过 12 小时 15 分钟 |
| AC-03 | 健康真实性 | 制造过期/失败后不能显示 healthy |
| AC-04 | 读取真实性 | 工具没有执行 handshake 时不能 read_confirmed |
| AC-05 | 写入真实性 | session_end 后有 write receipt 和 processed event |
| AC-06 | 跨工具共享 | 工具 B 能召回工具 A 的项目决定和验证 |
| AC-07 | 项目身份 | 同一 repo 不因 IDE/路径别名产生多个项目 ID |
| AC-08 | 去重 | 重复事件进入 deduplicated，不进入 blocked/invalid |
| AC-09 | 隐私 | 密钥值不落盘，安全结论仍保留 |
| AC-10 | CBMEM 覆盖 | enabled 项目 100% 显示真实索引状态 |
| AC-11 | CBMEM 新鲜度 | 索引状态绑定当前目标 HEAD/generation |
| AC-12 | 三级召回 | 默认不加载 L2，大证据按需读取 |
| AC-13 | 时间事实 | 被替代事实不再作为当前事实但可查询历史 |
| AC-14 | 用户文件保护 | adapter install/uninstall 不覆盖用户自定义内容 |
| AC-15 | 运行时独立 | launchd 不从 iCloud repo import Python 包 |
| AC-16 | 无伪造支持 | 无官方接口的工具显示 unsupported/manual |

全部 AC-01 到 AC-16 通过，才允许声明“达到工具目标”。

## 14. 迁移策略

迁移必须非破坏。

1. 创建只读备份清单，记录现有文件和哈希，不复制密钥文件。
2. `lwm migrate v2 --dry-run` 输出将创建、兼容和跳过的对象。
3. 保留 V1 raw events、wiki pages 和 event index。
4. 从 V1 project map 建立 V2 registry。
5. 从 V1 processed events 重建 SQLite 派生索引。
6. V1 wiki project pages 转换为 STATE.md candidates，保留 source link。
7. 先 dual-read，不 dual-write 两份真源。
8. V2 验收通过后，wiki/html 改为从 V2 真源生成。
9. 旧 CLI 保持兼容，输出 deprecation warning。
10. 不自动删除 V1 文件；删除属于独立、明确授权的后续任务。

## 15. 回滚策略

- launchd plist 更新前保存上一版本副本和哈希。
- V2 使用独立 `state/lwm.sqlite3`，不覆盖 V1 event index。
- adapter 只修改带 owned marker 的块。
- 回滚时恢复旧 plist、旧 runtime app 和旧 adapter owned block。
- GLOBAL.md、STATE.md 和 raw events 不随代码回滚删除。
- CBMEM 图数据库由 CBMEM 自己管理，LWM 回滚不能删除其索引。

## 16. 安全和隐私

- 默认本地存储。
- API key 只从环境变量或系统密钥工具读取，不写入事件。
- raw event 落盘前先做 deterministic redaction。
- 日志禁止输出完整 prompt、Authorization header、cookie 和 token。
- adapter 执行 fail-open：LWM 不可用时不能阻止 IDE 或 Shell 工作。
- MCP 写工具限制在 LWM root；CBMEM 可配置 allowed root。
- 所有自动生成配置都带 owned marker 和来源版本。
- 不读取没有明确支持或用户授权的 IDE 私有聊天数据库。

## 17. 性能预算

- handshake P95 <= 500ms，不含首次 CBMEM 索引。
- session event 写 spool P95 <= 50ms。
- L0 context <= 300 tokens。
- L0 + L1 默认 <= 2,500 tokens。
- health P95 <= 2s，不执行完整索引。
- supervisor 非到期检查 <= 1s。
- daily reflect 可异步，默认 <= 10 分钟。
- CBMEM 索引由其 watcher 独立执行，不阻塞 session start。

## 18. 技术团队执行指令

以下文本可以直接交给实施工程师：

> 目标是实现本规格中的 LLM-WorkMem V2，不是继续添加静态 Markdown 入口。
>
> 开始前先读取仓库真实状态和用户未提交修改，任何已有修改都视为用户资产，不得回退。按阶段 A 到 E 逐项实现，每阶段只解决该阶段的责任并运行对应测试。
>
> 不得使用“配置文件存在”作为工具接通证据，必须产生真实 read/write receipt。不得为没有官方接口的 IDE 发明 Hook。CBMEM 必须使用自身 auto-index/auto-watch，LLM-WorkMem 只维护关联状态。
>
> 所有数据迁移必须 dry-run、可回滚且不删除 V1 数据。每个阶段交付 Verified、Inferred、Unknown、Change boundary、Verification，并附真实命令输出。只有 AC-01 到 AC-16 全部通过，才可以宣布完成。

## 19. 规格自检清单

- [x] 没有未决占位内容。
- [x] 所有新增状态都有唯一真源。
- [x] 所有自动成功声明都有回执。
- [x] 所有工具都有不支持时的明确降级行为。
- [x] Supervisor、session event 和 reflect 的频率没有混用。
- [x] CBMEM 与 LLM-WorkMem 的所有权没有重叠。
- [x] V1 数据不会被自动删除。
- [x] 测试能证明错误状态不会显示 healthy。
- [x] 技术团队可以从逐文件清单定位修改范围。
- [x] 验收标准可以用命令或真实会话复核。

## 20. 最终完成定义

系统只有同时满足以下条件才算完成：

1. 自动运行及时且能在唤醒后补跑。
2. 活跃工具真实读取 LLM-WorkMem 并留下回执。
3. 活跃工具自动记录重要工作结果，而不是重复噪声。
4. 同一项目跨工具共享当前目标、决定、变更、验证和未解决问题。
5. CBMEM 对启用项目可查询且索引新鲜。
6. 三级召回降低上下文噪声并可追溯到原始证据。
7. 健康系统能够主动暴露过期、未连接、配置缺失和索引问题。
8. 所有数据有唯一真源、迁移可回滚、用户文件不被破坏。
