# LLM-WorkMem 轻量证据召回层设计

- 日期：2026-07-19
- 状态：B 方向已批准，迭代规格待用户审阅
- 目标仓库：`LLM-WorkMem`
- 设计代号：Evidence Recall B2

## 1. 决策

LLM-WorkMem 继续作为本机 IDE 与 Shell 共用的工作流和记忆中心，但不引入 HMS 的数据库和服务栈。系统只在现有 Retain、Recall、Reflect 之上增加一个轻量的证据召回层。

证据召回层的职责是：

1. 正确识别当前项目和问题类型。
2. 从项目状态、原始事件、全局规则和按需 CBMEM 结果中选取证据。
3. 区分当前事实、历史事实、冲突事实和未验证信息。
4. 返回有来源、有时间、有覆盖检查的精简证据包。
5. 不替 IDE 中的模型生成最终答案。

这项设计不建立第二个记忆中心，不增加常驻 LLM，不增加 PostgreSQL、Neo4j、pgvector、Chroma 或 Docker 服务。

## 2. 已验证的当前差距

当前仓库已经拥有事件、ingest、项目 ID、项目记忆、Retain/Recall/Reflect、MCP、CBMEM、Supervisor、Health 和工具回执。需要修正的是连接和召回质量，而不是重新建设存储层。

当前差距如下：

- `memory_api.recall()` 接收 `project_path`，但查询没有按该项目过滤。
- `_recall_plan()` 只声明检索维度，没有让不同维度执行不同检索和排序。
- Recall 返回页面命中，而不是可供判断的结构化事实。
- 当前评估主要检查第一条页面 slug，不能证明时间、状态、冲突和答案覆盖正确。
- `hub context` 的读取回执写入失败会阻断上下文本身。
- 未提供项目路径时会退化为无项目记忆，但输出没有充分区分 global-only 和完整项目上下文。
- 工具回执不能证明所有 IDE 已双向连接。
- 最近一次完整周期出现 0 accepted、68 duplicate，说明适配器会重复提交无变化内容。

## 3. 外部实践的取舍

### 3.1 HMS

采用：先规划检索、再组织证据、最后检查完整性。

不采用：独立数据库、独立模型控制器和面向通用问答的完整 HMS 运行栈。

### 3.2 Hindsight

采用：Retain、Recall、Reflect 分离；身份范围先于内容分类；Reflect 不是每次回答前的默认步骤。

不采用：常驻服务和每次调用都经过外部包装器。

来源：https://github.com/vectorize-io/hindsight

### 3.3 OpenViking

采用：L0/L1/L2 渐进加载、稳定摘要优先、按需展开完整证据、服务不可用时 fail-open。

不采用：第二套 Context Database 和自动向每轮用户消息注入动态记忆。

来源：https://github.com/volcengine/OpenViking

### 3.4 Graphiti

采用：事实有效期、事实替代关系、来源 episode、保留完整历史。

不采用：图数据库和自动实体图谱抽取。

来源：https://github.com/getzep/graphiti

### 3.5 claude-mem

采用：SessionStart、checkpoint、Stop/SessionEnd 生命周期和渐进式披露。

不采用：捕获全部工具调用、第二套 worker、第二套向量存储和每步 AI 压缩。

来源：https://github.com/thedotmack/claude-mem

## 4. 设计原则

1. **一个真源**：`AGENTS.md`、`GLOBAL.md`、项目 `STATE.md` 和 append-only events 继续承担唯一真源。
2. **项目优先**：`project_id` 是记忆隔离边界；工具名只是来源，不是独立记忆库。
3. **默认确定性**：问题规划、过滤、去重、时间判断和覆盖检查不调用 LLM。
4. **证据先于结论**：LLM-WorkMem 返回证据包，由当前 IDE 模型形成答案。
5. **稳定上下文优先**：稳定 L0/L1 放在会话前缀；动态证据只在明确 Recall 时加入，保护提示缓存并减少噪声。
6. **审计不能阻断工作**：回执、轨迹和指标写入失败只能降级，不能阻断 Context 或 Recall。
7. **没有证据就说未知**：不以旧事实、相似文本或推断冒充当前事实。
8. **不全量采集聊天**：只保留决定、变更、验证、风险、稳定偏好和 open loop。

## 5. 系统边界

### 5.1 LLM-WorkMem 负责

- 项目身份解析。
- 高价值事件留存和去重。
- 当前状态与历史状态管理。
- 证据检索、组织、排序和覆盖检查。
- IDE/Shell 的上下文交接。
- 工具读写回执、健康状态和检索轨迹。

### 5.2 LLM-WorkMem 不负责

- 生成最终用户回答。
- 保存每个 IDE 的完整对话。
- 解析封闭 IDE 的私有数据库。
- 代替 CBMEM 构建代码图。
- 自动把候选洞察提升为全局原则。
- 在每轮消息前重新注入整套项目记忆。

## 6. 最小架构

```text
IDE / Shell
  -> existing adapter
  -> Retain: high-signal events only
  -> raw/events (append-only evidence)
  -> project STATE / GLOBAL (current truth)
  -> Recall Planner
  -> Evidence Retriever
  -> Evidence Ledger
  -> Recall Verifier
  -> Context Pack
  -> IDE / Shell model

CBMEM only joins Evidence Retriever when the question needs code evidence.
```

只新增两个聚焦模块：

- `lwm/evidence.py`：证据数据合同、状态判定、去重和来源格式。
- `lwm/recall.py`：规划、检索编排、账本组织和覆盖验证。

现有 `lwm/query.py` 保持页面检索职责，不继续膨胀为完整控制器。

## 7. 数据合同

### 7.1 EvidenceItem

```json
{
  "fact_id": "fact-uuid",
  "project_id": "git-...",
  "fact_type": "decision|change|verification|status|preference|open_loop|code",
  "statement": "事实正文",
  "observed_at": "ISO8601",
  "valid_from": "ISO8601|null",
  "valid_to": "ISO8601|null",
  "state": "current|historical|conflicted|unverified",
  "source_event_ids": ["event-uuid"],
  "source_paths": ["path"],
  "verification": ["proof"],
  "confidence": 0.95,
  "supersedes": "fact-id|null",
  "retrieval_reasons": ["project_exact", "latest_verified"]
}
```

### 7.2 RecallPacket

```json
{
  "question": "当前调度为什么失败？",
  "project_id": "git-...",
  "scope": "project|global-only|cross-project",
  "plan": ["project", "current_state", "verification", "conflict"],
  "summary": "供快速判断的确定性摘要",
  "evidence": [],
  "conflicts": [],
  "missing": [],
  "coverage": "complete|partial|insufficient",
  "trace_id": "trace-uuid",
  "token_estimate": 900
}
```

`summary` 只根据选中证据生成模板化摘要，不调用 LLM，不加入证据之外的新判断。

## 8. Recall 执行流程

### 8.1 Project Gate

1. 使用显式 `--project`。
2. 没有显式路径时使用调用者当前工作目录。
3. 通过 Project Registry 解析稳定 `project_id`。
4. 仍无法识别时返回 `scope=global-only` 和显式警告，不伪装成完整项目上下文。

### 8.2 Deterministic Planner

Planner 根据问题词形和调用模式选择以下维度：

- `current_state`：现在、当前、最新、是否仍然。
- `timeline`：何时、上次、之前、之后、相对日期。
- `decision`：为什么选择、为什么更改、方案比较。
- `verification`：是否完成、是否验证、运行是否正常。
- `conflict`：冲突、不同说法、旧规则与新规则。
- `cross_project`：多个项目、反复出现、共同偏好。
- `code`：文件、函数、调用链、代码结构和具体实现。

默认不调用 LLM 生成查询。只有未来真实评估证明确定性 Planner 无法覆盖时，才允许增加可选扩展。

相对日期使用调用时传入的 `now` 和本机时区解析；默认采用系统时区，测试必须固定时间，禁止使用文件修改时间猜测“昨天”或“最近”。

### 8.3 Retrieval Signals

召回组合四类信号，不增加四套服务：

1. 精确项目、事实 ID、文件路径和事件类型。
2. 现有中英文关键词检索。
3. 时间、有效期、verification 和 supersedes 排序。
4. 仅在 `code` 维度启用时调用 CBMEM。

可选语义检索保持关闭，不作为本设计的完成条件。

### 8.4 Evidence Ledger

组织规则：

- 相同 `fact_id` 或幂等键只保留一条。
- `valid_to=null` 且有验证证据的事实优先。
- 被 supersede 的事实保留为 historical，不参与当前状态结论。
- 同一对象存在两个当前值时标记 conflicted，不自行选择。
- 时间问题按事件发生时间排序，不使用文件修改时间代替。
- 代码问题可以附 CBMEM 结果，但不能把代码搜索推断写成已验证运行事实。

### 8.5 Recall Verifier

Verifier 不判断答案文风，只检查证据是否足够：

- 计划要求的维度是否都有证据。
- 每个关键事实是否有来源。
- 当前状态是否混入 historical 事实。
- 是否存在未展示的冲突。
- 是否超过 token budget。

缺失一个非关键维度返回 `partial`；缺失项目身份、当前状态或关键来源时返回 `insufficient`。

## 9. 上下文预算

### 9.1 Session Start

- L0：项目身份、当前目标、最高风险，最多约 300 tokens。
- L1：最近决定、验证和 open loops，最多约 900 tokens。
- 总预算：约 1,200 tokens。

### 9.2 Automatic Recall

- 最多 6 条 EvidenceItem。
- 总预算约 1,200 tokens。
- 使用稳定排序：事实类型、有效状态、时间、fact_id。

### 9.3 Explicit Deep Recall

- 最多 12 条 EvidenceItem。
- 总预算约 3,500 tokens。
- 只有用户或 Agent 明确要求深入查证时启用。

不允许每轮消息自动注入 L2 原始事件。

## 10. Retain 和重复控制

只保留以下事件：

- decision
- change
- verification
- checkpoint
- session_end
- preference
- open_loop
- fact_superseded

不记录普通 prompt、无结果工具调用和重复 session_start。

写入前先计算现有幂等键；同一工具、项目、会话、事件类型和规范化内容未变化时，不再创建新 inbox 文件。周期扫描发现无变化时记录一个周期统计，不重复写 68 条事件。

## 11. 跨工具 Handoff

Handoff 不是新记忆类型，而是 RecallPacket 的固定视图：

- project identity
- current objective
- current status
- latest verified result
- active decisions
- files touched
- open loops
- risks
- source IDs

Adapter 只负责调用和格式适配，不保存自己的 Handoff 副本。另一个 IDE 读取同一 packet 后写真实 read receipt。

## 12. Fail-Open 与健康判定

以下失败不得阻断 Context 或 Recall：

- receipt 写入失败。
- retrieval trace 写入失败。
- CBMEM 暂时不可用，但问题不依赖代码证据。
- 某个非当前 IDE 的 adapter 不可达。

输出继续返回，同时附加 warning，并将健康状态降为 degraded。

只有以下情况阻断项目级 Recall：

- 项目真源不可读。
- 事件或项目状态结构损坏且无法安全跳过。
- 用户明确要求当前状态，但所有候选事实都无来源或互相冲突。

工具健康继续按以下状态展示：

```text
detected -> configured -> reachable -> read_confirmed -> write_confirmed
```

文件存在不能自动升级为 read_confirmed。

## 13. CLI 和 MCP 边界

不新增顶层命令。升级现有接口：

- `lwm hub context`：返回稳定 L0/L1，并自动解析项目。
- `lwm hub retain`：执行高价值事件校验和写前去重。
- `lwm hub recall`：返回 RecallPacket，支持 compact/deep 和 JSON/Markdown。
- `lwm hub reflect`：只产生 candidate。
- `lwm hub health`：展示 Recall、receipt 和项目覆盖的真实状态。

MCP 继续暴露同名能力，不再维护另一套行为逻辑。

## 14. 逐文件实现边界

预计只触及：

- 新增 `lwm/evidence.py`
- 新增 `lwm/recall.py`
- 修改 `lwm/memory_api.py`
- 修改 `lwm/query.py`
- 修改 `lwm/context.py`
- 修改 `lwm/capabilities.py`
- 修改 `lwm/central_cli.py`
- 修改 `lwm/eval.py`
- 修改 `mcp/lwm_server.py`
- 添加对应聚焦测试

不修改 WebUI 视觉、不替换自动化框架、不迁移现有原始数据、不删除现有 wiki 页面。

## 15. 验证设计

### 15.1 单元测试

- `project_path` 真正限制召回范围。
- 当前事实压过被替代事实。
- 冲突事实不会被静默选择。
- 相对时间被锚定到明确区间。
- 重复 EvidenceItem 被去重。
- receipt 写失败时 Context 仍返回。
- CBMEM 失败时非代码 Recall 继续工作。
- token budget 和稳定排序生效。

### 15.2 真实场景评估

建立 18 个固定案例，每类 3 个：

- 当前状态
- 时间线
- 决策原因
- 验证证据
- 冲突处理
- 跨工具 Handoff

每个案例检查 expected fact IDs、state、source、coverage，不再只检查页面 slug。

### 15.3 端到端验收

1. Shell 写入决定，Codex 能读取同一项目证据。
2. Codex 写入验证，Claude Code 能读取当前状态。
3. 旧事实被替代后仍可查询历史，但不会出现在 current summary。
4. 回执目录设为不可写时，Context 正常返回并报告 degraded。
5. 无变化完整周期不再生成重复事件风暴。
6. IDE 不支持 Hook 时状态保持 configured/unverified，不假装双向成功。

## 16. 完成定义

本设计完成后，LLM-WorkMem 必须做到：

- 在正确项目中找到最少必要证据。
- 明确区分当前、历史、冲突和未知。
- 每条关键事实都可以追溯来源。
- 一个 IDE 的有效工作能被另一个 IDE 接续。
- 审计失败不会拖垮核心工作。
- 日常使用不需要用户维护第二套笔记、数据库或后台服务。

这就是 B2 的最终边界：**一个轻量的本地证据控制层，而不是另一个重型 AI 记忆产品。**
