<!-- contract-version: 1 -->

# LLM-WorkMem Global Contract

LLM-WorkMem is a shared, source-backed evidence layer for local IDEs and shell. Native tool instructions, skills, memory, session state, planning, execution, and verification remain authoritative.

## One workflow

`sync -> truth -> execute -> verify -> write back`

- Read the current project context before acting.
- Separate verified facts, inference, assumptions, and unknowns.
- Execute one bounded task with the smallest necessary change.
- Verify with tests, build, logs, runtime behavior, or a direct check.
- Write back only durable cross-tool evidence: decisions, meaningful changes, verification, risks, preferences, and open loops.

## One memory boundary

- `wiki/purpose.md`: what belongs in long-term memory.
- `wiki/overview.md`: current system synthesis and automation status.
- `wiki/projects/<project_id>.md`: one project page containing meaningful status, decisions, bugfixes, verifications, and open questions.
- `wiki/global/`: audited cross-project rules and principles.
- `raw/events/`: sanitized append-only evidence; lifecycle receipts are not durable knowledge by themselves.
- `raw/tool-snapshots/` and `raw/cbmem-snapshots/`: current source evidence, not polished memory.

## Promotion rule

Keep temporary observations, empty lifecycle events, unchanged snapshots, full conversations, and unverified guesses out of durable Wiki pages. Promote only reusable, source-backed, high-signal knowledge through review.

## Runtime and Git boundary

Runtime state, receipts, logs, caches, absolute local paths, and launchd state are rebuilt locally and are not the long-term truth source. Git synchronizes code, tests, adapters, `GLOBAL.md`, and reviewed source documents. Runtime-owned Wiki/raw/state targets reached through absolute local symlinks are not proven Git-synchronized or portable across Macs.

## Security & Server Boundary (最高安全边界：服务器与外部网络)

- **绝对禁止擅自进入或连接任何服务器**：严禁在未获用户明确许可的情况下，抓取本地凭证、历史 IP、SSH 配置文件并尝试连接任何外部云服务器、VPS 或远程主机。
- **必须得到用户明确许可**：涉及任何远程服务器连接、登录、部署、配置修改或文件上传，**必须且只能在用户明确给出具体目标并下达执行许可后方可开展**。“准备部署”仅限本地构建检查与配置准备，绝不等于连接执行。

## Cross-tool handoff

Every IDE and shell may read the same LLM-WorkMem evidence and write sanitized events through `lwm hub record`. The active tool still decides the answer and owns its native workflow.

## Privacy & Git Separation Boundary (绝对本地私有与 GitHub 纯代码边界)

- **工作习惯与约定绝对本地私有**：用户的工作习惯、同步铁律、沟通偏好与私人约定，100% 仅保存在本地持久化工作记忆（LLM-WorkMem）中。绝不出现在 GitHub 的任何文件、Commit 信息或公开 README 中。
- **GitHub 仅呈现纯工程代码**：GitHub 上的所有仓库（私人仓与协作仓）仅对外展现最干净、最标准的工程代码、配置文件、架构文档和测试用例，不掺杂任何个人工作习惯或 Agent 元指令陈述。

