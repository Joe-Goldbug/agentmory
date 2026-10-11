# LLM-WorkMem 修复验收：2026-10-11

## 结论与边界

本地核心运行、来源审计、项目记忆和统一发布已经通过真实周期。不是“全工具、全语义任务已经完成”。OpenCode/Codex 原生规则和记忆保持权威，LWM 只提供辅助证据与交接，不替代原生安全、执行或技能。

最终运行时：`runtime-20261011T073339Z-d82264fd`。代码提交 `ff3f903`、`d82264f`。非 editable 安装；模块来自本地 Application Support 的 site-packages；sys.path 无 iCloud；源码 manifest 及实际安装 Python 文件均无缺失或哈希差异。

正式验收周期：`cycle-a8505d355bc2`，2026-10-11 15:41:50–15:42:08 +08:00。processed=13，rejected=0，failed=0，core_status=success，overall_status=success，exit_code=0。Analyze errors=0，schema issues=0，review items=0，local/external source gaps=0。CBMEM 两个项目健康。默认 eval 2/2 只是 smoke，不代替产品端到端验收。

## 审计问题对照

| 编号 | 修复与验证 | 尚未证明的边界 |
|---|---|---|
| F01 | 唯一 launchd 服务重新加载；RunAtLoad=true，StartInterval=21600；到期门控、boot ID、睡眠后的轻量补查；已有真实 launchd 到期周期成功 | 未物理重启电脑；LaunchAgent 在用户登录后运行，睡眠中不执行 |
| F02 | UUID 等宿主元数据不再误判为密钥；重审历史拒绝并恢复安全事件；真实密钥事件仍隔离 | 原始拒绝证据未删除；18 个旧索引原件缺失未伪造恢复 |
| F03 | 每轮生命周期幂等；实际结果先落盘、再处理能力收据和交接；修复 1000 字符观察结果被 240 字符交接限制误拒；子事件保留 session_id 和父事件；原生 turn ID 统一 Stop/SessionEnd；AGY 识别真实 step-log 格式，任务 ID 包含会话身份 | AGY R3 成果已原生记录、入库发布并被 OpenCode R12 召回；不等于每个项目与每种宿主都验收 |
| F04 | 区分安装、宿主投递、生命周期收据、有效入库和被其他工具消费；观察器不伪装原生 hook | 所有客户端没有统一冒充 verified |
| F05 | OpenCode 按 turn 标识收集；原生事件与 SDK 兼容；结束前同步原子落盘，异步交接失败仍保留结果；真实 R8 已入库 | 宿主异步结束链未完成的精确根因未宣称已证实 |
| F06 | 保留项目范围、来源和时间；未知项目不升为全局；真实项目隔离测试 | 不把本项目结果推定为其他所有项目成功 |
| F07 | 结构化提取权威 OpenCode/Codex 来源；排除生成镜像回流；支持冲突、显式替代和退休 | 语义建议不是自动批准的新规则 |
| F08 | 开启已有授权的 Codex CLI 分析器；配置失败有恢复入口；真实模型已执行过分析 | 当前每日预算不足，待处理综合没有假报完成 |
| F09 | 完整有界 JSON 请求；覆盖压缩显式记录；超大任务分叶批次和归并树，保留反例分区；摘要 UTF-8 字节限制、反证不变成支持；失败依赖和超限归并明确失败，不无限等待 | 新 map-reduce 在真实模型上的完整语义归并仍待额度恢复；测试使用夹具；完整来源分区不代表逐字全文投递 |
| F10 | 语义种子与完整来源指纹稳定标识；复用未变叶批次；较低预算时重拆不适合的 pending 叶子；无引用旧 reducer 保存为 retired，保留审计；被当前计划重新引用时可恢复 | 不自动恢复 dead-letter 或覆盖人工内容；没有删除历史证据 |
| F11 | 任务、变更、验证、风险分层；幂等更新与重新派生；UTC/+08:00 按时间点排序；验证字段不再预先套用短交接限制；AGY 文件结果去除冗长显示元数据，保留路径、数值和 status unknown；旧记录只重新派生，原件不改 | 派生摘要仍有 480 字符预算和来源链接，不把它说成无限完整副本；原始有界结果另存 |
| F12 | 正向验证与反例共同约束；晋升、撤回、退休闭环；不以“有 verification 字段”当成功 | 全局规则仍需审查，不允许模型静默覆盖人工规则 |
| F13 | 区分 running/failed/stale；最后失败不能被旧成功遮蔽；PID 为空但已加载有效；索引复用；上下文单列带 checked_at/fresh 的运行快照，历史 bugfix 不代表当前健康 | last-attempt 特指失败/警告，最新成功必须读取 latest-cycle；快照不是全客户端或语义综合完成证明 |
| F14 | 增加跨工具、来源、范围、内容和生命周期产品测试；核心修复全套 890 passed；随后新增可选模块启动隔离测试；实际发布的干净 Git 快照 887 passed，Ruff 通过 | 干净快照不含本地未提交备份原型的四项测试；四个既有 forget 警告提示派生页需复核；不是无条件全绿证明 |

## 真实宿主证据

| 宿主 | 本次真实证据 | 状态边界 |
|---|---|---|
| OpenCode | R8 自动注入并读取策略，outbox 已入库；R9 仅凭自动上下文召回 Codex R6。最终 R12 `ses_ed61b7c3effe2ojIQk9t9Kjsm9` 召回 AGY R3 原始事件、路径和 21600/true，且引用来自 opencode:memory 的工作方式；自身 outbox `d1acd86b-3d3e-5dec-8f2b-5b5893ec4561` 自动生成并经最终周期入库 | R10 暴露摘要元数据挤掉数值，R11 暴露高频工具挤掉其他工具；均据真实反例修复，失败记录保留，不覆盖为成功 |
| Codex | R4/R6 真实新会话自动召回 OpenCode R8 最新事件、完整引用 21600/true；R6 `01a1297a-3799-7513-9fc3-455c183c4326` 原生写出成果 `c12055f7-5973-44ef-9d78-c5604c889eec`，已 processed，再被 OpenCode R9 自动召回 | 已实证双向读、原生结果记录、审计入库、发布、另一工具自动消费；不等价全客户端、全部项目实证 |
| Kiro | 本机真实 GUI 模型读取自动 steering/context；实际报告 `4e26a43b-4917-4b5f-ab0f-6766be8ef321` 已 processed 并出现在项目页 | watcher_observed；助手报告标为未验证，不伪装实际成功检查或原生 hook |
| VS Code | 本机真实 Copilot GUI 模型读取 instructions/context；报告 `556b3106-5a27-4b7e-b07e-be0e24da5c03` 已 processed 并发布 | watcher_observed，不等价全扩展全模型验证 |
| AGY/Antigravity | R3 真实会话 `1d7810e0-8fc2-45c9-ad26-cc70f356af95` 原生写出成果 `83ca4b08-a9f4-4d75-b839-a292c525205e`；实际读取结果已 processed、发布，再被 OpenCode R12 自动引用路径及完整策略值 | 已证明本项目的有用成果闭环，不用空生命周期收据冒充成果；原始工具状态仍为 unknown，不自动改成成功 |
| Claude Code | 原生 hooks 和启动读收据存在；真实模型尝试返回 Invalid API key / Not logged in | 登录是当前真实阻塞；未更换密钥、供应商或模型伪造通过 |
| TRAE/TRAE Solo | 保留现有配置和观察链 | 本机未找到可启动应用，本次未做真实宿主验证 |

Cursor、独立 MiniMax 和不存在的独立 Google Gemini CLI 不在此次验收范围；AGY 是实际安装的 Antigravity CLI。

## 日常自动运行

会话原生入口读当前项目紧凑上下文；原生 hooks/plugins 或明确标记的本地观察器收集结果；写入 raw inbox；正式周期审计、隔离异常、构建项目页、生成冲突/综合候选、发布统一记忆。其他工具在新会话或原生规则刷新后读取。已有会话的刷新依宿主能力，不承诺所有正在运行的会话即时更新。

完整整理每六小时；每五分钟只做便宜的 due/状态补查，不反复完整调用模型。睡眠期间不运行，唤醒/登录后补到期工作。安装本地后台服务不需要一直开网页或终端。

截至 15:42 快照，分析主任务 36 个，pending 批次/归并节点 216 个，另有 1 项 analyzed、136 项 retired；retired 不在活跃队列，但原文件及审计仍保留。最终周期 deferred=252。oversized_unbatched=0。可选综合器当天本地记账 16631/20000 tokens；改为按完整请求估算加输出 allowance 预留，不再固定预留 16000。未增加预算或清零计量；Codex CLI 没有上游硬 token cap，真实用量可超过估算，不能把本地预留称为账单硬上限。今天剩余额度仍不足当前完整请求，等待后续到期周期及 UTC 日额度恢复。没有把等待中的历史综合说成已全部处理或批准。

最终 health：2026-10-11 15:42:11 +08:00，healthy、loaded=true、last_exit_code=0、due=false。最终 context 的快照来自该文件，fresh=true、core_status=success、audit_ok=true、issues=0。这是运行层结论，不覆盖客户端登录和语义模型边界。当前成功时间 15:42:08，下一完整周期约 21:42 到期，唤醒/轻量检查可带来分钟级延迟，不承诺秒级准点。

## 最后收口修复与发布边界

- 紧凑上下文按最近一周工具来源保留最新记录，再按时间补齐；高频 Codex 不再独占所有位置，完整来源行随记录一起保留。
- 统一工作流及未解决冲突前置；Markdown 在完整记录之间停止，保留明确省略提示；预算不再把工作方式从末尾悄悄截掉。
- `verification` 字段显示为 `verification evidence`，不因字段名称自动宣称 verified；失败与 unknown 文本保留。
- 干净 Git 快照发现 gateway 顶层强依赖未跟踪的 `lwm/backup.py`，导致核心 CLI 无法启动。已改为实际备份操作时才加载，并增加缺失可选模块的启动回归。
- 本地 `lwm/backup.py` / `tests/test_backup.py` 是其他工作留下的未提交原型，不进入本次发布。审阅发现其恢复函数没有防御 tar 链接，且先删除目标再拷贝，不构成可靠原子恢复；未在真实数据上运行恢复。不要用该原型恢复真实记忆，需单独安全验收。原型文件及其他界面改动保留，没有删除或冒充已经修好。
- GitHub 目标已验证为私人仓 `EthanLau1/LLM-WorkMem`，默认分支 main。本次仅发布修复、测试和此验收记录；不上传 raw、登录凭证、机器专属配置、缓存或无关界面原型。

## 证据位置与保护

运行数据根目录：`~/Library/Application Support/llm-workmem-runtime/llm-workmem`。

- `state/acceptance/2026-10-11/final-system-evidence.json`：当前运行时、配置、周期、队列与项目页摘要。
- `state/acceptance/2026-10-11/{opencode,codex,antigravity,claude-code}-round-*.json`：已执行真实模型验收；失败与未验证保持原状。
- `state/receipts/cycles/cycle-a8505d355bc2.json`：最终运行版本的不可变正式周期收据。
- `raw/events/processed/2026-10-11/fb8b9443-5a96-5018-82c3-18fe0370d0da.json`：OpenCode 原生结果。
- `wiki/projects/git-9f1cb19971812dd3.md`：派生项目记忆，保留事件 ID 与来源。
- runtime 备份 `before-20261011-full-repair.tgz` SHA256 `e48d621850dd0522678eed0974e0d77b9af2107b5b6d90638a6e4732f570eac7`；原生配置另有受限权限备份。

未删除 raw，未重置用户工作，未覆盖 Codex 原生 memories，未改变模型登录配置。运行时保留回滚版本；体积清理不混入本次修复。本记录与修复一起同步私人仓；具体远端提交以 GitHub 和最终同步验证为准。
