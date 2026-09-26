---
title: LLM-WorkMem 统一行为与记忆接口完整实施方案
type: spec
status: approved
source: codex-session/rollout-2026-04-23T13-54-45-019db8e7-b3b3-7763-a9b9-e398228553e2.jsonl#5961
authored_at: 2026-07-31T04:12:33Z
supersedes: docs/superpowers/plans/2026-07-31-llm-workmem-goal-completion.md
---

> 本文件为 Codex 于 2026-07-31 04:12 产出的 `<proposed_plan>` 正文逐字存档，作为本次实施的权威 HLD/LLD/追踪文档
> （依据方案 Assumptions：「工程执行时把本方案同步为 HLD、LLD 和实施追踪文档」）。
> 正文未作任何改写。原方案的 Requirements 为 21 组，正文中的固定默认值与验收标准具约束力。

# LLM-WorkMem 统一行为与记忆接口完整实施方案

## Summary

把现有 LLM-WorkMem 从“多个工具能读取的被动记忆目录”升级为 Ethan 的统一行为、工作流和记忆接口：

```text
本地 IDE / CLI 启动
→ 自动识别工具、项目、会话和任务
→ 注入统一行为合同、项目记忆和 handoff
→ 自动收集结构化工作证据
→ 确定性准入和隐私过滤
→ LLM Memory Compiler 分析工作流、关系与冲突
→ 验证后生成项目记忆和跨项目知识
→ 反向提供给下一次 IDE / CLI 会话
```

完成标准不是“模块和配置文件存在”，而是所有本机已发现工具都完成真实读取、真实写回和跨工具任务延续验证。任何工具仍未验证，都不得宣称“统一接口完整完成”。

本次只改本地代码、本地运行时和本地数据结构，不部署云端。

## Architecture And Interfaces

### 1. 四层统一架构

| 层 | 职责 |
| --- | --- |
| Capture Plane | 发现 IDE/CLI、识别项目、采集启动/结束和结构化工作证据 |
| Evidence And Compiler Plane | 隐私过滤、去重、durable admission、项目记忆、工作流/关系候选、LLM 分析 |
| Delivery Plane | 向所有工具提供行为合同、项目上下文、Recall 和 handoff |
| Control Plane | 单一 supervisor、逐源状态、审计、健康、不可变回执、安装与回滚 |

`GLOBAL.md` 是唯一的人类维护的跨工具行为合同。平台安全规则保持最高边界，当前用户指令和项目局部规则分别保留来源与作用域，不允许静默混写。

### 2. Tool Registry

用版本化注册表替换 `runner.py` 中硬编码的 `ADAPTER_MODULES`。

```python
@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    display_name: str
    aliases: tuple[str, ...]
    surfaces: tuple[Literal["ide", "cli", "shell"], ...]
    discovery_paths: tuple[str, ...]
    capture_mode: Literal["native_hook", "session_adapter", "file_tail", "shell_lifecycle"]
    delivery_mode: Literal["native_hook", "instruction_pointer", "mcp", "shell_context"]
    collector_modules: tuple[str, ...]
    observer_modules: tuple[str, ...]
    adapter_module: str | None
    host_commands: tuple[str, ...]
    host_app_paths: tuple[str, ...]
    enabled: bool
```

`collector_modules` 是主动轮询采集器；`observer_modules` 是只读的本地会话或元数据观察器。
后者可以与 `native_hook` 同时存在，用来覆盖宿主没有稳定 hook 的 fallback，但只能写
`watcher-observed` 等 observation 证据，不能声明宿主 proof。supervisor 必须分别执行并在
source receipt 中区分 collector 与 observer，不能因为有 native hook 就跳过 observer。

```python
@dataclass(frozen=True)
class ToolCoverage:
    tool_id: str
    status: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "pending_integration",
    ]
    capture_status: str
    delivery_status: str
    read_status: str
    write_status: str
    last_capture_at: str | None
    last_read_at: str | None
    last_write_at: str | None
    gaps: tuple[str, ...]
```

首批注册并验证：

| 工具 | 采集方式 | 反向提供方式 |
| --- | --- | --- |
| Codex | `SessionStart`/`SessionEnd` native hook contract with real local proof | `~/.codex/hooks.json` + `~/.codex/AGENTS.md` |
| Claude Code | SessionStart/Stop 原生 hook | `~/.claude/CLAUDE.md` + hook 返回 context |
| OpenCode | shell lifecycle + 结构化 write-back | `~/.config/opencode/AGENTS.md` |
| AGY/Antigravity | native `PreInvocation`/`Stop` hook + shared MCP contract configured; live host proof pending; session/watch fallback | `.agents/AGENTS.md`、`.agents/GLOBAL.md` + `~/.gemini/config/hooks.json`、`~/.gemini/settings.json` |
| Kiro | session/steering adapter + VS Code-compatible companion with real local proof | Kiro steering + companion package |
| Trae | attach/session adapter + VS Code-compatible companion with real local proof | `.traerules` + companion package |
| MiniMax | Registered `minimax-mcp` bridge + session adapter + shell wrapper; live host proof pending | `~/.minimax/agents`、runtime SQLite、`~/.minimax/mcp/mcp.json` + shell context |
| VS Code/Copilot | session/task observer + companion with real local proof | User instruction file + companion package |
| Cursor | optional companion task adapter or shell lifecycle; local host proof unavailable | `.cursor/rules/llm-workmem.mdc`、`.llm-workmem/events.jsonl` + companion package |
| Gemini CLI | `SessionStart`/`SessionEnd` native hook + registered `gemini-cli-mcp` bridge; local CLI proof pending | `~/.gemini/settings.json` + `~/.gemini/GEMINI.md`、项目 `GEMINI.md` |
| 通用 shell CLI | zsh native lifecycle hook（start/exit proof）+ preexec/precmd 命令观察 | `lwm-context` 和注册工具指针 |

Tool Registry 当前版本为 5。每个注册项还声明 `host_commands` 与
`host_app_paths`，用于只读探测宿主的本地可用性；这一步不启动工具、不调用模型，
也不产生 proof。探测结果固定为：`available`（命令可执行）、`app_present`
（应用目录存在但没有可执行命令证据）、`not_found` 或 `not_applicable`。
配置文件被发现、应用存在、CLI 可执行和真实宿主 proof 是四个不同事实，任何前者
都不能自动提升后者。

`hub tools list` 和 `hub coverage` 必须同时暴露 `configured` 与 `host_probe`；
`ToolCoverage` 的 `read_status`、`write_status` 仍只由真实 receipt/capability
proof 更新。这样可以明确区分“机器上没有宿主”“宿主已安装但尚未产生事件”“已配置
但没有真实 proof”和“已完成双向验证”，避免把安装状态误报成接入完成。

每个注册项可声明 `proof_integrations`：它列出
允许该工具通过 lifecycle/session bridge 声明 proof source 的已验证宿主集成；
空数组表示当前只能 observation。旧版持久化注册项如果没有这个字段，加载时
继承同一工具的默认安全绑定；显式写入空数组仍然可以关闭该工具的 proof。

新工具必须只新增一个注册项和一个适配器，不修改核心准入、健康或 Context 逻辑。

### 3. Event And Handoff Contracts

新事件使用兼容式 schema v2；旧事件无 `schema_version` 时按 v1 读取，不重写历史文件。

新增可选字段：

```python
schema_version: int = 2
task_id: str | None
handoff_id: str | None
operation_id: str | None
source_receipt_id: str | None
```

Handoff 固定结构：

```python
@dataclass(frozen=True)
class HandoffPacket:
    handoff_id: str
    project_id: str
    task_id: str
    objective: str
    current_state: str
    decisions: tuple[str, ...]
    changes: tuple[str, ...]
    verifications: tuple[str, ...]
    risks: tuple[str, ...]
    open_questions: tuple[str, ...]
    next_action: str
    source_tool: str
    evidence_ids: tuple[str, ...]
    created_at: str
    supersedes: str | None
```

每个项目只能有一个当前 active handoff。新 handoff 必须声明 `supersedes`；旧工具不能覆盖更新版本。Handoff 属于运行状态，完成后的决定、改动和验证通过正常事件准入进入长期记忆。

### 4. Public CLI And MCP

保留现有 `context`、`retain`、`recall`、`capabilities`、`receipt`、`run-cycle` 和 `run-supervisor`。

新增：

```text
lwm hub tools list|probe
lwm hub coverage [--tool TOOL] [--json]
lwm hub behavior show|sync|verify
lwm hub handoff create|current|ack|close
lwm hub analyze --pending
lwm hub verify-cycle CYCLE_ID
lwm hub bridge <request-json>
lwm hub bridge-stop --tool TOOL --project PROJECT [--handoff-json JSON]
lwm hub bridge-contract --simulate
```

MCP 暴露同语义接口：

```text
lwm_context
lwm_retain
lwm_recall
lwm_handoff
lwm_coverage
lwm_health
```

#### 4.1 Shared Session Bridge

宿主集成使用版本化 JSON bridge 作为统一会话边界契约，避免每个 IDE/CLI
自行拼接参数或实现一套不同的写回逻辑：

```text
lwm hub bridge <request-json> --root <DATA_ROOT>
```

请求的 `phase` 只能是 `context`、`start` 或 `stop`；请求至少包含
`tool` 和 `project_path`，可选 `session_id`、`task_id`、`source` 和受限的
`handoff` 对象。返回固定包含 `schema_version`、canonical `tool`、项目身份、
事件路径、operation id、receipt 状态、上下文或 handoff 状态。

bridge 只负责传输和契约验证，实际业务仍调用同一套 `hub_service`、
`lifecycle`、receipt 和 handoff 服务。`lifecycle` 命令保留为兼容入口，不得
演化出第二套规则。`bridge-stop` 只是给 shell/Markdown 指令使用的便捷包装，
必须委托给同一个 bridge dispatch；生成适配器不得再引导调用旧 lifecycle 写回。
`watcher-observed` 只能产生 observation；只有宿主真实
调用并提供证据文件的 `native-hook` 等 proof source 才能进入
`verified_*` 状态。`bridge-contract --simulate` 只运行隔离模拟，绝不升级
为真实工具能力证明。bridge/lifecycle 对 proof source 还必须收到
`host_proof`，其中的 `integration` 必须命中该工具注册表的
`proof_integrations`，`event` 必须非空，且 `session_id`（如有）必须与宿主
会话一致。当前代码包把 `claude-code-hook`、`opencode-plugin`、`shell-hook`、
`codex-hook`、`gemini-cli-hook`、`antigravity-hook` 以及已打包但尚未触发的
`vscode-extension`、`cursor-extension`、`trae-extension`、`kiro-extension` 注册为允许的宿主绑定；
注册或生成 companion 不等于真实 proof。普通 CLI、观察器和未注册工具不能靠手工传
`source=native-hook` 伪造 `host-reported`。规范化后的证明绑定会
写入生命周期事件的 source 元数据，供后续审计回链。

通用 MCP `record_receipt` 同样只能写 observation；MCP 请求本身没有可靠的
宿主身份或生命周期事件绑定，不能把 `native-hook`、`lifecycle-hook`、
`ide-extension` 或 `explicit-smoke` 标签升级为 proof。公开 JSON bridge
默认只能产生 observation；只有已安装的宿主适配器通过内部受信入口才能提交
proof-bearing request，shell hook 也必须把受信标记绑定在实际 bridge 子进程上，
不能让用户手写 JSON 冒充宿主。真实 MCP 宿主若需要
证明，必须通过已注册的宿主 bridge/adapter 产生绑定事件，而不是调用通用
receipt 工具自报完成。当前 MiniMax 的 `minimax-mcp` bridge 和 Gemini CLI
的 `gemini-cli-mcp` bridge 只在 MCP 进程由安装器注入匹配的
`LWM_MCP_TOOL` 与 `LWM_MCP_INTEGRATION`，且请求中的 tool 与注册项一致时，
才允许写入受限的 `mcp-bridge` proof；缺少或伪造身份仍然只能是 observation。
注册桥接存在不等于对应宿主已经真实触发。

CLI、MCP 和生成适配器必须调用同一业务函数，禁止形成三套判断逻辑。

所有生成的宿主适配器必须使用明确的 canonical `tool_id`，不能把
`<your-tool-name>` 作为可执行命令输出。动态 shell Context 必须先对
`PWD` 做 JSON 编码再调用 bridge；这样带空格、引号或其他 shell 字符的项目
路径仍然进入同一个项目身份解析链路。

### 5. Startup Context

每次受支持工具启动时：

1. 识别 `tool_id`、Git 项目根、`project_id`、`session_id` 和 active `task_id`。
2. 读取当前 `GLOBAL.md` 编译快照、项目记忆、active handoff、相关工作流和必要警告。
3. 生成最多 `12,000` 字符的 Context。
4. 通过工具原生方式提供内容。
5. 写入真实 read receipt。
6. 超时或失败时工具正常启动，同时把该工具标记为 degraded。

固定预算：

| 内容 | 最大字符 |
| --- | ---: |
| 行为合同摘要与版本 | 2,500 |
| 项目状态、决定、改动、验证 | 5,500 |
| active handoff | 2,000 |
| 工作流、关系和全局规则 | 1,500 |
| 警告、缺失信息和元数据 | 500 |

生成适配器只保存行为合同路径、版本、SHA、启动命令和 write-back 规则，不复制可独立漂移的完整 `GLOBAL.md`。

## Implementation Changes

### 1. 安全冻结与基线

- 在任何源码修改前读取并备份 `com.ethan.lwm.harvest` 和 `com.ethan.lwm.dream` 两个 plist。
- 同时暂停两个任务，记录 plist SHA、launchctl 状态、当前可执行文件、editable import 路径和数据目录哈希。
- 冻结期间不改 raw、wiki、state、symlink 和运行应用。
- 所有后续任务都检查两个旧任务仍未重新加载。

### 2. Truthful Core

- 实现统一 `classify_event()`，输出 `durable / operational / rejected`。
- 只有结构化决定、改动、验证、风险、项目状态和开放问题可进入长期记忆。
- 命令、完整提示词、环境信息、会话生命周期、watcher observation 保留为 operational 或 rejected。
- 从 `raw/events/processed` 确定性重建项目页；相同输入产生字节一致结果。
- 每条项目记忆保留 `event_id`、来源工具和证据路径。
- 旧 raw 事件永不删除或手工改写。

### 3. Tool Registry、自动采集与行为合同

- 把所有工具发现、适配器执行、捕获状态、Context 交付和 capability proof 统一到 Tool Registry。
- shell identity、lifecycle canonicalization 和 capability facade 必须读取当前 `DATA_ROOT/state/tool-registry.json`；持久化覆盖定义时必须重建 alias index，不能保留旧 alias。
- 修正当前生成适配器只写“auxiliary evidence”的语义，明确 `GLOBAL.md` 是用户行为默认合同，项目记忆仍是辅助证据。
- 给每个工具生成 startup Context 和完成时 structured retain/handoff 指令。
- Claude Code 等有原生 hook 的工具直接返回 Context；其余工具使用原生 instruction pointer、MCP 或 shell lifecycle。
- 安装器只能写入已知宿主契约或显式 companion 配置，不能猜测 hook schema。Claude Code、OpenCode、Codex 和 shell 已有真实双向 proof；Gemini CLI 和 Antigravity 的 native hook 合同已配置但仍需真实宿主 receipt；VS Code、Trae 和 Kiro 的 companion 已产生真实 receipt，Cursor 的本机 host 不可用；Kiro 仍保留 observer/instruction fallback。
- Antigravity `Stop` hook 必须返回宿主要求的 `decision` 字段；LLM-WorkMem 的正常结束响应为 `{"decision":"allow"}`，只有明确返回 `continue` 才阻止宿主结束。这个响应契约修复不等于真实 proof。
- Gemini CLI 的自动 source 只允许用户维护的 `~/.gemini/GEMINI.md`；对话数据库、transcript 和模型输出不进入默认 harvest。Gemini native hook 仍必须等待真实 CLI 事件才能提升 capability。
- `GLOBAL.md` 生成带版本和 SHA 的 runtime snapshot；源文件不可用时使用最后一次验证快照并报告 stale。
- 所有已发现工具必须经过真实启动、read receipt、write receipt 和项目解析验证。
- zsh `precmd` 必须在任何后续命令前保存上一条命令的退出码，并对路径、会话和命令字段做 JSON 转义；否则采集结果不能进入验证链路。

### 4. Handoff 和统一任务身份

- 新建 handoff 服务和 CLI/MCP 接口。
- SessionStart 恢复 active task；SessionStop 从本次结构化事件生成 handoff，不读取或保存完整聊天记录。
- Context 优先返回 active handoff，再返回普通历史。
- 目标工具 `ack` 后记录 read proof；写回新证据后更新 task state。
- handoff 关闭后只保留审计状态；长期事实仍来自 admitted events。

### 5. Memory Compiler

使用可选、非驻留的 OpenAI-compatible API。核心在没有 API 时仍完整工作。

环境变量固定为：

```text
LWM_ANALYSIS_ENABLED=0
LWM_ANALYSIS_BASE_URL=
LWM_ANALYSIS_API_KEY=
LWM_ANALYSIS_MODEL=
LWM_ANALYSIS_TIMEOUT_SECONDS=30
LWM_ANALYSIS_DAILY_TOKEN_BUDGET=50000
LWM_ANALYSIS_MAX_ATTEMPTS=3
```

- 使用懒加载 `httpx` 可选依赖；未安装或未配置时返回 `analysis_pending`。
- localhost/127.0.0.1 端点允许无 API key；远程端点必须有 key。
- 调用 `/chat/completions`，`temperature=0`，只发送准入后、去敏、限长证据。
- 缓存键为 provider、model、prompt version、evidence hash。
- 重试间隔固定为 60 秒、300 秒、1800 秒，最多三次。
- 实际 token 用 API usage；缺失时用字符数估算并计入预算。
- API key、完整输入和完整输出不得进入 wiki、事件、回执或日志。

候选状态：

```text
pending_analysis
→ analyzing
→ analyzed
→ accepted | rejected
→ promotion_pending
→ promoted
```

确定性候选与 LLM 候选使用两个有明确职责的目录，但不能断链：

- `state/candidates/` 保存从 admitted durable events 生成的可人工审核
  workflow/relationship 候选；重复周期不得覆盖用户的 accept、reject 或
  correction。
- supervisor 在候选生成后，把未拒绝且证据 ID 仍存在的候选 seed 到
  `state/analysis/candidates/`，保留同一 `candidate_id`、scope 和 evidence
  IDs；已有分析状态不得被重新 seed 覆盖。
- `lwm hub analyze --pending` 只负责可选 LLM 分析。LLM 输出先经过结构、
  证据、秘密和状态验证，不能直接写入全局事实。
- `lwm hub review-analysis <candidate-id> --decision accept|reject|promote`
  是人工审核入口；只有 `accepted` 候选允许进入 bounded Context。
- `lwm hub promote-analysis <candidate-id>` 是独立的显式晋级入口；它使用
  候选携带的 evidence IDs 重新通过 durable、跨项目和 verification 门，使用
  稳定 claim key 写入 `pattern`、`relationship` 或 `principle`，并记录 actor、
  reasons、event IDs 和 rollback 信息。

失败状态：

```text
retry_wait
→ analyzing
→ dead_letter
```

LLM 只返回候选：

```json
{
  "kind": "workflow|relationship|conflict|summary",
  "claim": "...",
  "scope": ["project-id"],
  "evidence_ids": ["event-id"],
  "counterevidence_ids": [],
  "context": "...",
  "uncertainty": "...",
  "validity": "current|time_bounded|unknown"
}
```

验证器拒绝不存在的 event ID、新增事实、秘密、指令注入、永久身份判断和非法状态迁移。

### 6. 工作流与关系整理

- 项目页保存当前状态、决定、改动、验证、风险和开放问题。
- 工作流候选必须包含 trigger、context、steps、verification、outcome、exceptions 和 evidence IDs。
- 关系候选必须说明相关项目/想法/行为及证据，不得把相关性写成因果。
- 重复 tag 或次数不能直接生成规则。
- 项目内工作流写入项目页的 versioned section。
- 跨项目 workflow、relationship 和 principle 使用稳定 claim key 写入 `wiki/global`，分别用 `type: pattern / relationship / principle`。
- 项目数量变化只更新同一 claim，不产生 39/40/41 项目重复文件。
- 所有全局 promotion 保留 actor、原因、证据和 rollback 记录。

### 7. Cycle、失败隔离和健康

单一 supervisor 顺序：

```text
tool discovery
→ adapters and shell capture
→ ingest and admission
→ deterministic rebuild
→ workflow/relationship candidates
→ optional LLM analysis
→ validated promotion
→ behavior/adapters/exports
→ audit and eval
→ health
→ immutable cycle receipt
→ derived daily digest
```

逐源状态：

```text
ok
warning
degraded
analysis_pending
quality_warning
rebuild_required
failed_core
```

只有以下情况返回非零 core exit：

- raw evidence 无法安全写入；
- 索引重建后所有 Recall 入口仍不可用；
- immutable cycle receipt 无法提交。

单适配器、CBMEM、LLM、单 Markdown、audit 或 eval 失败不能伪装成 core failure。Audit/eval 失败产生 `quality_warning`，阻止最终 healthy/complete 声明。

`CycleReceiptV2`：

```python
@dataclass(frozen=True)
class CycleReceiptV2:
    schema_version: Literal[2]
    cycle_id: str
    runtime_id: str
    started_at: str
    finished_at: str
    core_status: Literal["success", "success_with_warnings", "failed_core"]
    overall_status: str
    sources: tuple[SourceResult, ...]
    stages: tuple[StageResult, ...]
    quality: dict[str, object]
    analysis: dict[str, object]
    counts: dict[str, int]
    artifacts: tuple[str, ...]
    errors: tuple[str, ...]
```

每轮写入独立文件，永不覆盖；`latest-cycle.json` 只是原子替换的指针。旧 v1 receipt 继续只读兼容。

### 8. Runtime 和数据归属

目标物理布局：

```text
RUNTIME_BASE/
  app/
    venv/
    runtime-manifest.json
  llm-workmem/
    wiki/
    raw/
    automation/
    state/
    adapters/                 # generated runtime copy; checkout adapters remain source-owned
    llms.txt
    llms-full.txt
    llms.json
    lwm-sources.json
    knowledge-digest.html
    knowledge-digest.pages/
  logs/
```

状态目录固定包含：

```text
state/tool-coverage.json
state/behavior/current.json
state/cursors/
state/handoffs/
state/analysis/candidates/
state/analysis/transitions/
state/analysis/cache/
state/analysis/dead-letter/
state/receipts/cycles/
state/receipts/tools/
state/receipts/latest-cycle.json
```

- 从源码构建 wheel，以非 editable 方式安装到 staging app。
- 验证 `sys.path` 和 `lwm.__file__` 不包含 `/Mobile Documents/`。
- `app/venv` 和 runtime manifest 作为一个原子安装/回滚单元。
- `DATA_ROOT` 是全部可变数据的唯一物理所有者；仓库只保留访问链接。
- `state.pre-link`、`item/`、旧 runtime code mirror 和 dream 状态进入迁移归档，不直接删除。
- `knowledge-digest.*` 保留为可重建生成物。
- `dream` 合并入 supervisor，取消独立自动 promote 和独立 `wiki/daily` 写入。
- 最终只加载一个 LaunchAgent。

### 9. 迁移和回滚

- 先构建非破坏性 manifest：路径、类型、symlink target、大小、SHA、动作、目标所有者、备份位置和 rollback 命令。
- manifest 必须覆盖两个 plist、app、bin、item、顶层 state、DATA_ROOT 全部实体、dot cursor state 和旧 code mirror。
- 用户批准必须绑定该 manifest 的 SHA-256；任何受保护路径漂移都会使批准失效。
- 迁移前后分别验证全部 processed raw 证据哈希。
- 先安装并隔离验证新 app，再切换 state/link，最后加载唯一 LaunchAgent。
- 任一 core/runtime/E2E 验证失败，恢复旧 app、两个旧 plist、原 symlink 和 state。
- 回滚不得恢复错误生成的全局结论，也不得改写 raw。

## Test Plan

### 1. Contract And Unit Tests

- Tool Registry：发现、别名、项目识别、未知工具、disabled、真实 coverage。
- Event v1/v2：旧事件读取、新字段验证、未知字段、隐私、重复、operation idempotency。
- Admission：durable、operational、rejected、截断、指令/环境/秘密过滤。
- Handoff：创建、恢复、ack、close、supersedes、stale write、跨项目隔离。
- Behavior：`GLOBAL.md` SHA、runtime snapshot、project/global 分离、stale fallback。
- Provider：disabled、远程缺 key、本地无 key、timeout、HTTP 错误、非法 JSON、预算、cache、retry。
- Compiler：全部状态迁移、非法迁移、虚构 evidence ID、冲突和 dead letter。
- Workflow/relationship：稳定 claim key、counterexample、非因果、相关 Recall。
- Receipt：v1 读取、v2 immutable、latest pointer、重复 cycle ID、写入失败。

### 2. Source Isolation Tests

分别注入以下故障并验证只有目标 source/stage 降级：

- VS Code/session adapter 或 companion 失败；Codex native hook 失败必须通过其 fail-open hook 入口单独验证。
- Claude Hook 超时。
- OpenCode 或 Gemini shell session 缺失。
- CBMEM 不可用。
- LLM API 超时或超预算。
- 单个 Markdown 损坏。
- Audit 或 eval 失败。
- 可重建索引损坏。
- raw store 或 immutable receipt 不可写时才产生 `failed_core`。

### 3. Per-Tool End-To-End Tests

每个已发现工具都必须完成：

```text
真实启动
→ 项目识别
→ 行为合同和 Context 读取
→ read receipt
→ 一次结构化决定/改动/验证写回
→ write receipt
→ 下一工具读取更新
```

Codex、Claude Code、OpenCode、AGY/Antigravity、Kiro、Trae、MiniMax、VS Code/Cursor、Gemini CLI 和 shell 都必须有真实证据。任何命名工具仍为 `partially_supported` 都阻止“完整目标完成”结论。

### 4. Cross-Tool Product Scenarios

- Codex 在 Ather 创建任务和 handoff，Claude Code 继续并写回验证，OpenCode 再读取最新状态。
- 同一 `GLOBAL.md` 版本通过不同适配器进入两个工具，语义一致且无独立副本。
- 两个项目产生可复用调试工作流，LLM 生成候选，验证器保留反例并正确 Recall。
- API 关闭时，自动采集、项目记忆、Context、handoff 和 Recall 全部继续工作。
- 用户纠正 workflow/relationship 后，旧候选保留审计记录但不再返回为当前结论。
- Ather Context 不含完整 prompt、环境块、命令转录和 lifecycle global noise。

### 5. Runtime And Migration Verification

必须通过：

```text
full pytest
Ruff
wheel build
isolated wheel install
packaged resource check
non-iCloud import check
manifest dry-run
rollback dry-run
raw hash preservation
audit
eval
health
context smoke
recall smoke
handoff smoke
coverage smoke
one real scheduled cycle
restart后的第二次真实周期
```

最终检查：

- 仅一个 LaunchAgent。
- 仅一个可变 state 所有者。
- 每轮一个 immutable receipt。
- 所有发现工具都有包含配置状态、宿主可用性和 proof 状态的真实 coverage；
  宿主存在或配置发现本身不得被当作真实 proof。
- 所有 P0 Requirements 都有代码、测试和运行证据。
- 没有测试通过但真实工具仍走旧路径的双权威情况。

## Assumptions And Fixed Defaults

- 用户本次“确认”批准 21 组 Requirements 和本方案的产品目标，不需要再拆成 Requirements、HLD、LLD 和旧计划四次确认。
- 工程执行时把本方案同步为 HLD、LLD 和实施追踪文档，但不中断实现等待重复设计确认。
- `GLOBAL.md` 是统一的用户行为默认合同；平台安全、当前明确请求和项目局部规则保留各自来源与边界。
- LLM 是可选 Memory Compiler，不是常驻服务、最终回答者或事实 authority。
- 默认使用 OpenAI-compatible API，支持 MiniMax、Qwen、OpenAI 和本地兼容端点。
- 不增加数据库或向量库，继续使用文件、JSON、Markdown 和可重建索引。
- 不保存完整聊天记录，不删除 processed raw evidence。
- 不部署云端，不改远程部署。
- `dream` 并入唯一 supervisor；generated digest 保留但不属于正式证据。
- 未来未知工具通过 Tool Registry 扩展；当前机器所有已发现工具必须被分类并完成真实验证。
- 精确 destructive migration 仍绑定执行时生成的 manifest SHA；这是数据安全校验，不是遗留给工程师决定的产品或技术问题。
