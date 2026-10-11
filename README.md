# llm-workmem

<p align="center">
  <img src="assets/logo.svg" alt="llm-workmem" width="480" /><br />
  <sub>Universal Cross-Agent Working Memory, Knowledge Management & Backup System</sub><br />
  <sub>跨 Agent 统一工作记忆与知识管理和备份系统</sub>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)](pyproject.toml)

> **Bilingual Documentation / 中英文双语对照文档**
> An LLM working memory, knowledge management, and decentralized backup platform that evolves with you. Originating from [Karpathy's LLM-WorkMem philosophy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), `llm-workmem` has evolved into a comprehensive **cross-agent working memory, task handoff, evidence federation, and seamless Web2-Web3 blockchain backup engine** designed for modern AI engineering workflows.
> 一个与你共同演进的 LLM 工作记忆、知识管理与去中心化备份系统。源自 [Karpathy 的 LLM-WorkMem 哲学](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)，现已全面升级为面向现代 AI 编程工作流的**跨 Agent 工作记忆、任务交接（Handoff）、证据联邦与 Web2-Web3 丝滑无瑕区块链备份引擎**。

---

## 1. Overview / 系统概览

**[EN]** Modern software engineering frequently spans multiple AI tools: you brainstorm or plan in **Claude Code** or **Codex**, implement components in **Antigravity**, **Cursor**, or **Trae**, run autonomous tasks in **OpenCode** or **Kiro**, and inspect terminal pipelines via **Zsh**.
**[ZH]** 在现代 AI 辅助研发中，开发者通常在多个工具与环境中频繁切换：使用 **Claude Code** 或 **Codex** 进行架构设计与计划，在 **Antigravity**、**Cursor** 或 **Trae** 中编写代码，通过 **OpenCode** 或 **Kiro** 执行自动化 Agent 任务，并在 **Zsh** 交互式终端中运行验证流水线。

---

**[EN]** However, modern multi-agent development faces three critical pain points:
1. **Isolated Memory Silos**: Previous decisions, bugfixes, and verifications are lost across session restarts. Passing a task between AI agents requires manually copying conversation snippets.
2. **Context Degradation & Hallucinations**: Unstructured memory dumps cause prompt bloat, security token leaks, and conflicting assumptions.
3. **Fragile Backup & Tamper Vulnerability**: Critical engineering decisions, architectural trade-offs, and verification proofs reside solely in ephemeral local disks or centralized cloud silos, vulnerable to accidental loss, silent corruption, or vendor lock-in.

**[ZH]** 然而，现代多 Agent 协同研发面临三大核心痛点：
1. **记忆孤岛与上下文断裂**：会话重启后，历史决定、Bugfix 修复经验与验证结果丢失；跨 Agent 交接任务需手动复制粘贴对话记录。
2. **非结构化膨胀与幻觉失真**：非结构化记忆倾倒导致 Prompt 窗口迅速耗尽、秘钥泄露以及前后逻辑矛盾。
3. **单点备份脆弱与篡改风险**：关键工程决策、架构选型与验证证据仅存在于易失的本地磁盘或中心化云存储中，极易因误删、静默损坏或平台锁定而永久丢失。

---

**[EN]** **`llm-workmem` solves this by providing a universal working memory backbone with seamless Web2-Web3 multi-tier backup and cryptographic provenance.**
**[ZH]** **`llm-workmem` 为所有本地 AI 编程工具提供统一的工作记忆中枢，并融合 Web2-Web3 丝滑无瑕的多级备份与去中心化可信验证。**

---

### Core Operating Principles / 核心设计原则

1. **Auxiliary Evidence Layer / 辅助证据层**
   - **[EN]** `llm-workmem` injects verified context, project memory, active handoffs, and behavior guidelines into agents at session startup. It **never replaces or overrides** each agent's native tools, instructions, skills, planning, execution, or verification workflows. Native workflows always remain authoritative.
   - **[ZH]** `llm-workmem` 在会话启动时向各 Agent 注入项目记忆、行为规范、活跃任务交接与联邦知识。它**绝不取代或重写**各工具原生的工具集、技能、计划、执行、验证或内部记忆机制（各工具原生工作流保持最高权威）。

2. **Truthful Core / 真实核心**
   - **[EN]** Only structured decisions, verified bugfixes, and concrete outcomes are admitted into long-term project memory. Operational noise, raw prompt transcripts, command-only chatter, and environment dumps are rejected.
   - **[ZH]** 仅允许结构化的工程决策（Decisions）、变更（Changes）、验证结果（Verifications）与开放问题（Open Questions）进入长期记忆。命令回显、完整 Prompt、对话废话与环境转录被自动识别为操作噪音并剔除。

3. **Strict Proof Verification / 真实凭证严格审计**
   - **[EN]** Having a configuration file or observation log is not treated as bidirectional integration proof. The system explicitly distinguishes between `instruction-only`, `watcher-observed`, and `native-hook` verified receipts.
   - **[ZH]** 配置文件存在或本地文件观察不等于双向集成完成。系统严格区分“仅生成指令”（instruction-only）、“观察器捕获”（watcher-observed）与“宿主原生 Hook 验证回执”（native-hook verified proof）。

4. **Zero-Trust Privacy & Quarantine / 零信任隐私与安全隔离**
   - **[EN]** Automated secret and token scrubbing runs on every ingested event (`privacy.py`). Sensitive keys never enter project memory or external backup payloads. Questionable events are quarantined with safe recovery workflows.
   - **[ZH]** 所有摄入事件必须经过自动化秘钥脱敏与隐私扫描（`privacy.py`）。敏感凭证绝不进入长期记忆或备份载荷；高风险事件自动进入隔离区，提供安全的审查恢复链路。

5. **Seamless Web2-Web3 Hybrid Backup / Web2-Web3 丝滑无瑕双引擎备份**
   - **[EN]** **Zero Web3 Friction for Everyday Coding**: Developers use local IDEs and CLI tools with sub-millisecond latency without requiring crypto wallets, gas tokens, or transaction popups during daily coding sessions.
   - **[ZH]** **日常研发零 Web3 阻碍**：开发者在本地 IDE 和终端中编码时享受亚毫秒级瞬时响应，绝不弹出钱包签名或要求强制 Gas，保持最纯粹的本地高效体验。
   - **[EN]** **Decentralized Permanence & Cryptographic Anchoring**: When backup is triggered, the system asynchronously snapshots admitted memories, computes Merkle root proofs, and anchors receipts to blockchain registries (EVM / L2s) while storing tamper-proof archives on decentralized storage (Arweave / IPFS / Filecoin).
   - **[ZH]** **去中心化永久存储与链上可信锚定**：备份触发时，系统异步生成确定性快照，计算 Merkle 树根哈希，将不可变回执锚定到区块链合约（EVM / L2 等），并将脱敏归档备份至去中心化永存网络（Arweave / IPFS / Filecoin），实现不可篡改、可跨团队溯源的永恒工程资产备份。

---

## 2. System Architecture / 系统架构

`llm-workmem` is organized into five decoupled architectural planes / 采用高度解耦的五层统一架构设计:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CAPTURE PLANE / 捕获层                          │
│   IDE Lifecycle Hooks │ Shared Session Bridge │ Companion Extensions │ Shell Hook  │
│   (Codex, Claude, AGY, Gemini, Kiro, Trae, MiniMax, VS Code, Cursor, Zsh)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Raw Events / 原始事件 (raw/events/inbox/)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 EVIDENCE & COMPILER PLANE / 证据与编译器层                  │
│  Deterministic Admission (classify_event) ──► Privacy Filter (privacy.py)   │
│  Project Memory Rebuilder                 ──► Provenance Linker             │
│  Memory Federation (Cross-Agent Release)  ──► Compiler & Token Budgeting    │
│  Candidate Review Queue                   ──► Stable Promotion Gate         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Verified Memory & Handoffs / 验证记忆与交接包
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DELIVERY PLANE / 交付层                         │
│  Bounded Startup Context (<12k chars) │ Active Task Handoff (Cross-Tool)    │
│  Canonical Behavior Contract (GLOBAL) │ Evidence Recall B2 (Progressive)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▲
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                             CONTROL PLANE / 控制层                          │
│  6-Hour Supervisor (Launchd) │ Immutable Cycle Receipts │ Closure Gate      │
│  Tool Capability Probing     │ Strict Health Audit      │ CBMEM Code Graph  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Verified Snapshots & Merkle Roots / 验证快照与根哈希
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  BACKUP & DECENTRALIZED PLANE / 备份与去中心化层            │
│  Web2 Deterministic Snapshots        ──► Local Receipts (.promotion-backups)│
│  Decentralized Archival (IPFS/Arweave)──► Permanent Content Addressing     │
│  On-Chain State Anchoring (EVM/L2)   ──► Verifiable Merkle Root Registry    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Capture Plane / 捕获层
- **Universal Session Bridge (`lwm hub bridge`) / 统一会话桥接器**:
  - **[EN]** Standard JSON interface supporting `context`, `start`, and `stop` phases across IDEs and CLIs.
  - **[ZH]** 标准 JSON IPC 接口，统一处理各 IDE 与 CLI 的 `context`、`start` 和 `stop` 生命周期阶段。
- **Native Lifecycle Hooks / 原生生命周期 Hooks**:
  - **[EN]** Real lifecycle integrations for Claude Code, OpenAI Codex, Antigravity, Gemini CLI, and Zsh shell.
  - **[ZH]** 深度对接 Claude Code、Codex、Antigravity、Gemini CLI 及 Zsh 终端生命周期事件。
- **IDE Companion Extensions / IDE Companion 伴侣扩展**:
  - **[EN]** Host-tailored packages for VS Code, Trae, Kiro, and Cursor.
  - **[ZH]** 为 VS Code、Trae、Kiro 和 Cursor 提供宿主兼容包。
- **Project Identity Resolution / 项目身份严格解析**:
  - **[EN]** Canonical Git root hashing (`id=git-<hash>`), ensuring events map to real workspace boundaries regardless of directory aliasing or symlinks.
  - **[ZH]** 基于 Git 仓库根目录哈希（`id=git-<hash>`）确定项目边界，彻底解决软链接和目录间接引用引起的记忆混淆。

### 2. Evidence & Compiler Plane / 证据与编译器层
- **Truthful Core Admission (`lwm hub ingest`) / 真实核心准入**:
  - **[EN]** Sorts incoming events into `durable` (structured decisions, changes, verifications, risks), `operational` (lifecycle notices, commands), or `rejected`.
  - **[ZH]** 将输入事件严格分类为 `durable`（可沉淀工程事实）、`operational`（生命周期/命令等运行噪音）或 `rejected`。
- **Project Memory Engine (`lwm hub rebuild-projects`, `lwm hub reflect`) / 项目记忆确定性重建**:
  - **[EN]** Deterministically rebuilds project pages (`Recent Decisions`, `Recent Bugfixes`, `Verifications`, `Open Questions`) with exact event provenance links.
  - **[ZH]** 依据摄入事件自动生成项目状态页（近期决策、Bugfix、验证记录与遗留问题），每条记忆均带有精确到文件与 UUID 的证据链链接。
- **Unified Native Memory Federation (`lwm hub federation`) / 统一原生记忆联邦**:
  - **[EN]** Compiles and reconciles workflow memory from disparate agent sources (e.g. OpenCode `MEMORY.md`, Codex, Claude Code, Antigravity) into immutable, timestamped releases (`release-*.json`).
  - **[ZH]** 将分散在 OpenCode（`MEMORY.md`）、Codex、Claude Code、Antigravity 中的原生记忆统一抽取、去重并解决冲突，生成带时间戳的不可变发布版本（`release-*.json`）。
- **Memory Compiler (`lwm hub analyze --pending`) / LLM 记忆编译器**:
  - **[EN]** Optional, token-budgeted LLM analysis identifying recurring workflows, relationships, and contradictions across projects without altering raw events.
  - **[ZH]** 基于每日 Token 预算与重试状态机，分析多项目间的复用工作流与模式，生成结构化候选对象（`candidates-*.md`）。
- **Stable Promotion Gate (`lwm hub promote-analysis`) / 稳定晋级门禁**:
  - **[EN]** Enforces multi-project backing (`>= 2 projects`) and verified test outcomes before promoting candidates to global principles (`wiki/global/*.md`). Automatically retracts pages if backing evidence is retired or contradicted.
  - **[ZH]** 严格要求跨至少两个不同项目（`MIN_PROMOTION_PROJECTS >= 2`）并具备正面验证结果才可晋级为全局规则（`wiki/global/*.md`）；当下游证据撤回或被推翻时，自动触发版本回退与撤回。

### 3. Delivery Plane / 交付层
- **Bounded Startup Context (`lwm hub context`) / 受限启动上下文**:
  - **[EN]** Injects structured context tailored to the active tool at startup within a strict budget (max 12,000 chars), preventing context window exhaustion.
  - **[ZH]** 启动时根据激活工具组装上限 12,000 字符的精炼上下文，杜绝 Prompt 溢出。
- **Cross-Agent Task Handoff (`lwm hub handoff-*`) / 跨 Agent 任务交接**:
  - **[EN]** Transfers ongoing task state (`task_id`, `objective`, `current_state`, `decisions`, `changes`, `verifications`, `next_action`) seamlessly from one agent to another.
  - **[ZH]** 在工具退出时固化当前任务目标、当前状态、决定、变更、验证和下一步行动（`next_action`），供下一个启动的工具接力执行。
- **Evidence Recall B2 (`lwm hub recall`) / 确定性证据召回**:
  - **[EN]** Progressive, deterministic evidence retrieval returning project-scoped evidence packets rather than raw keyword hits.
  - **[ZH]** 渐进式确定性检索，返回包含检索计划、证据来源、多维覆盖与缺失项的项目级证据包。
- **Canonical Behavior Contract (`GLOBAL.md` & `lwm hub behavior`) / 统一行为合同**:
  - **[EN]** Machine-verified SHA-256 engineering behavior baseline shared across all tools.
  - **[ZH]** 全局统一的个人工程行为规范，经由 SHA-256 哈希比对与版本快照验证（`lwm hub behavior`）。

### 4. Control Plane / 控制层
- **Single Scheduled Supervisor (`lwm hub run-supervisor`) / 统一 Supervisor 调度守护**:
  - **[EN]** Single launchd job executing collection, admission, compile, export, and health checks every 6 hours or on login.
  - **[ZH]** 每 6 小时或开机时自动执行采集、摄入、重建、候选生成、审查导出与审计。
- **Immutable Cycle Receipts (`CycleReceiptV2`) / 不可变周期回执**:
  - **[EN]** Each execution cycle records an immutable snapshot with source-level isolation (`ok`, `warning`, `degraded`, `quality_warning`, `failed_core`).
  - **[ZH]** 每次运行均产出隔离不可变回执，明确划分 `ok`、`warning`、`degraded`、`quality_warning` 与 `failed_core`。
- **Loop Engineering & Closure Gate (`lwm hub closure`) / 闭环工程门禁**:
  - **[EN]** Inspects external verification proof before allowing tasks to declare completion.
  - **[ZH]** 外部客观证据不足时拒绝标记任务闭环，阻断未验证完成。
- **Tool Registry & Coverage Probe (`lwm hub tools probe`, `lwm hub coverage`) / 工具能力探查与覆盖**:
  - **[EN]** Audits real integration status across all tools.
  - **[ZH]** 查看各工具双向读写与凭证覆盖报告，严查真实集成状态。
- **Codebase Memory (`lwm cbmem`) / 代码库图谱记忆**:
  - **[EN]** Integrates deep AST code-graph analysis via [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp).
  - **[ZH]** 通过 AST 和代码图谱分析深入解析代码调用关系与架构结构。

### 5. Backup & Decentralized Plane / 备份与去中心化层
- **Web2 Deterministic Local Backups / Web2 确定性本地快照**:
  - **[EN]** Generates atomic, compressed tarballs of admitted memories, cycle receipts, and global principles into `.promotion-backups` and `state/backups/`.
  - **[ZH]** 自动生成已准入记忆、周期回执与全局原则的原子级压缩快照包，存储于本地安全备份目录。
- **Decentralized Archival (Arweave / IPFS / Filecoin) / 去中心化永久存储**:
  - **[EN]** Content-addressed, permanent decentralized storage ensuring that federated memory releases cannot be deleted or corrupted by any single entity.
  - **[ZH]** 基于内容寻址的去中心化永存方案，确保经过审查的联邦发布与全局工程原则具备防单点灾难的永恒存储能力。
- **On-Chain Cryptographic Anchoring (EVM / L2s) / 链上可信状态锚定**:
  - **[EN]** Calculates Merkle trees over `CycleReceiptV2` batches and commits Merkle root state hashes to smart contract registries for zero-knowledge verifiable provenance across cross-organizational agent teams.
  - **[ZH]** 对周期回执与记忆快照计算 Merkle 树，将状态根哈希提交至智能合约注册表，为跨组织或跨设备的分布式 AI 团队提供零知识可验证的防篡改证明。

---

## 3. Multi-Agent Ecosystem Matrix / 跨 Agent 工具生态矩阵

| Tool / Host (工具宿主) | Primary Surface (交互形态) | Capture Method (采集机制) | Delivery Method (交付机制) | Verification Proof Level (凭证验证等级) |
|---|---|---|---|---|
| **Anthropic Claude Code** | CLI / Agent | SessionStart / Stop native hooks | `CLAUDE.md` + Hook Context | Verified Native Proof (`claude-code-hook`) / 经测试宿主凭证 |
| **OpenAI Codex** | CLI / IDE | `SessionStart`/`SessionEnd` hook | `hooks.json` + `AGENTS.md` | Verified Native Proof (`codex-hook`) / 经测试宿主凭证 |
| **OpenCode** | CLI / Agent | Plugin lifecycle + write-back | `AGENTS.md` + Plugin Bridge | Verified Native Proof (`opencode-plugin`) / 经测试宿主凭证 |
| **Google Antigravity (AGY)** | IDE / Agent | PreInvocation / Stop hooks + MCP | `.agents/AGENTS.md` + Hooks | Native Hook Contract + Observer / 原生 Hook 契约 + 观察器备选 |
| **AWS Kiro** | IDE | Session / steering adapter | Companion Extension + Steering | Companion Verified Proof (`kiro-extension`) / Companion 宿主凭证 |
| **ByteDance Trae** | IDE | Attach / session adapter | Companion Extension + `.traerules` | Companion Verified Proof (`trae-extension`) / Companion 宿主凭证 |
| **MiniMax** | Desktop / CLI | Registered MCP bridge + wrapper | Runtime SQLite + Shell Context | Registered MCP Bridge (`minimax-mcp`) / 注册 MCP 桥接凭证 |
| **VS Code / Copilot** | IDE | Session & task observer | Companion Extension + Rules | Companion Verified Proof (`vscode-extension`) / Companion 宿主凭证 |
| **Cursor** | IDE | Rules (`.mdc`) + shell lifecycle | `.cursor/rules/llm-workmem.mdc` | Companion / Shell Lifecycle / 扩展与终端备选 |
| **Gemini CLI** | CLI | SessionStart/End native hook | `GEMINI.md` + Settings Hook | Native Hook Contract + MCP Bridge / 原生 Hook 契约 + MCP 桥接 |
| **Zsh Interactive Shell** | Terminal (终端) | `preexec` / `precmd` shell hook | Dynamic context CLI (`lwm-context`) | Verified Native Proof (`shell-hook`) / 经测试终端凭证 |

> **Proof vs. Observation / 真实凭证与观察器区别**:
> **[EN]** An installed rule or configuration file alone only indicates configuration presence. Verified status (`supported`) requires an authentic runtime receipt (`native-hook`, `host-reported`, or companion verification).
> **[ZH]** 仅安装配置文件仅代表已配置，并不代表集成已实际打通。只有经由真实运行时产生的 Hook 或扩展回执才能被标记为经测试凭证。

---

## 4. Installation & Setup / 安装与快速上手

### Requirements / 环境要求
- **Python**: `>= 3.11`
- **Package Manager / 包管理器**: [uv](https://docs.astral.sh/uv/) (recommended / 推荐) or standard `pip`
- **OS / 操作系统**: macOS / Linux

### 1. Install CLI / 安装命令行工具

```bash
# Using uv (recommended) / 使用 uv (推荐)
uv tool install .
# Or local editable install / 或本地可编辑开发安装:
uv pip install -e ".[dev]"

# Or standard pip / 或使用标准 pip:
pip install .
```

Verify / 验证安装:
```bash
lwm --version
```

### 2. Configure Workstation / 初始化工作站环境

```bash
# 1. Set the LLM-WorkMem data root / 设置持久化工作记忆数据根目录
export LWM_ROOT="/path/to/LLM-WorkMem"

# 2. Preview global installation (dry run) / 预览将要安装的适配器 (dry-run)
lwm install-global "$LWM_ROOT" --dry-run

# 3. Apply global adapter installations / 正式安装各 IDE/CLI 的全局入口
lwm install-global "$LWM_ROOT"

# 4. Generate native hooks for supported IDEs / 为支持的 IDE 生成原生 Hook 配置
lwm hub install-ide-hooks "$LWM_ROOT"

# 5. Install shell hook into ~/.zshrc / 向 ~/.zshrc 安装终端生命周期捕获 Hook
lwm hub install-shell-hook "$LWM_ROOT"
```

### 3. Verify Integrations / 验证工具集成与覆盖率

```bash
# Probe tool discovery & collector status / 查看本地工具发现与采集器就绪情况
lwm hub tools probe --root "$LWM_ROOT"

# Check bidirectional read/write coverage report / 查看各工具双向读写与凭证覆盖报告
lwm hub coverage --root "$LWM_ROOT"
```

### 4. Install Codebase Memory (Optional) / 安装代码库图谱记忆（可选）

```bash
bash automation/install-cbmem.sh
lwm cbmem doctor
```

---

## 5. Core Workflows / 核心工作流与实战指南

### Workflow 1: Session Startup & Context Injection / 会话启动与上下文注入

**[EN]** When an AI agent launches in a project directory, it requests bounded context via the shared bridge:
**[ZH]** 当任何 AI 工具在项目目录下启动时，通过统一会话桥请求当前项目的精简上下文：

```bash
# Markdown format (for direct prompt injection) / Markdown 格式 (供直接 Prompt 注入)
lwm hub context --tool claude-code --project "$PWD"

# JSON format (for programmatic IDE integrations) / JSON 格式 (供 IDE 插件解析)
lwm hub context --tool codex --project "$PWD" --format json
```

---

### Workflow 2: Cross-Agent Task Handoff / 跨 Agent 任务交接实战

#### Step A: Tool A Completes its Turn and Leaves a Handoff / 工具 A 阶段完成，提交交接包
```bash
lwm hub bridge-stop \
  --tool codex \
  --project "$PWD" \
  --task-id "task-auth-migration" \
  --task "Implemented token validation middleware" \
  --handoff-json '{
    "task_id": "task-auth-migration",
    "objective": "Migrate session tokens to JWT verification",
    "current_state": "Middleware written, test suite failing on edge case",
    "decisions": ["Use HS256 for internal service tokens"],
    "changes": ["src/auth/jwt.py", "tests/test_jwt.py"],
    "verifications": ["pytest tests/test_jwt.py -k test_valid_token PASSED"],
    "risks": ["Clock skew on distributed nodes"],
    "open_questions": ["What is the expiration window for refresh tokens?"],
    "next_action": "Fix clock skew tolerance in token validator"
  }' \
  --root "$LWM_ROOT"
```

#### Step B: Tool B Launches and Picks Up the Work / 工具 B 启动并接手工作
```bash
lwm hub handoff ack --handoff-id "<handoff_id>" --target-tool antigravity --root "$LWM_ROOT"
```

#### Step C: Final Verification and Handoff Closure / 最终验证完成，关闭交接
```bash
lwm hub handoff close --handoff-id "<handoff_id>" --root "$LWM_ROOT"
```

---

### Workflow 3: Submitting Work Events & Ingestion / 提交工作事件与记忆摄入

```bash
# Submit structured work / 提交结构化工作事实
lwm hub record \
  --tool shell \
  --project "$PWD" \
  --task "Fix memory compiler token budgeting" \
  --decision "Enforce daily token limit with reserve/reconcile pattern" \
  --change "lwm/memory_compiler.py" \
  --verification "pytest tests/test_analysis_compiler.py PASSED" \
  --tag "stable-claim" \
  --root "$LWM_ROOT"

# Ingest events into processed store / 执行摄入与项目记忆重建
lwm hub ingest "$LWM_ROOT"
```

---

### Workflow 4: Memory Compilation & Promotion / 记忆编译与稳定晋级

```bash
# 1. Run optional LLM analysis on pending durable events / 运行离线 LLM 候选分析
lwm hub analyze --pending --root "$LWM_ROOT"

# 2. Review a candidate / 审查分析候选 (accept | reject | promote)
lwm hub review-analysis <candidate_id> --decision accept --root "$LWM_ROOT"

# 3. Explicitly promote to wiki/global/ / 跨双项目验证后，晋级为全局规则
lwm hub promote-analysis <candidate_id> --root "$LWM_ROOT"

# 4. Compile native memories into unified release / 编译各 Agent 原生记忆为统一发布
lwm hub federation compile --root "$LWM_ROOT"
```

---

### Workflow 5: Evidence Recall B2 / 确定性证据召回 B2

```bash
# Compact recall / 精简模式召回
lwm hub recall "What was verified regarding memory compiler token limits?" \
  --project "$PWD" \
  --root "$LWM_ROOT"

# Deep audit formatted in Markdown / 深度审计模式输出 Markdown
lwm hub recall "Trace all architectural decisions on tool adapters" \
  --project "$PWD" \
  --mode deep \
  --format markdown \
  --root "$LWM_ROOT"
```

---

### Workflow 6: Multi-Tier Backup & Web2-Web3 Anchoring / 多级备份与 Web2-Web3 锚定实战

**[EN]** Safeguard engineering memory across local snapshots, decentralized storage, and on-chain verification without interrupting daily coding:
**[ZH]** 在不干扰日常编码流畅度的前提下，为工程记忆提供本地快照、去中心化永存与链上可信验证：

```bash
# 1. Create a local deterministic backup snapshot / 创建本地确定性备份快照
lwm hub backup create --root "$LWM_ROOT"

# 2. Asynchronously export sanitized snapshot to decentralized storage / 异步归档至去中心化永存
lwm hub backup sync --provider arweave --root "$LWM_ROOT"

# 3. Anchor latest cycle Merkle root on-chain / 将最新周期 Merkle 根锚定到区块链合约
lwm hub backup anchor --network evm --root "$LWM_ROOT"

# 4. Verify cryptographic integrity against on-chain root / 校验本地快照与链上锚定的一致性
lwm hub backup verify --root "$LWM_ROOT"
```

---

### Workflow 7: Health & Closure Gate / 系统健康与闭环审计

```bash
# Full system health snapshot / 系统多维度健康度快照
lwm hub health "$LWM_ROOT"

# Check evidence closure gates / 检查当前工作循环是否具备充分客观证据闭环
lwm hub closure "$LWM_ROOT"

# Verify immutable cycle receipt / 校验特定周期的不可变回执
lwm hub verify-cycle --root "$LWM_ROOT"
```

---

## 6. Classic Knowledge Wiki & Skill / 经典知识库模式与 Agent Skill

<p align="center">
  <img src="assets/flow.svg" alt="wiki-flow" width="600" /><br />
</p>

**[EN]** For users who also use LLM-WorkMem as a classic personal knowledge base, the original Karpathy workflow remains fully supported via `skills/llm-workmem/` (`INIT`, `INGEST`, `QUERY`, `UPDATE`, `LINT`).
**[ZH]** 对于希望保留经典个人知识库玩法的用户，原版 Karpathy 模式依旧通过 `skills/llm-workmem/` 得到完整支持（包含 `INIT`、`INGEST`、`QUERY`、`UPDATE`、`LINT`）。

```bash
# Initialize wiki workspace / 初始化 Wiki 目录骨架
lwm init --profile personal wiki/my-notes

# Compile raw sources into Markdown / 将 raw 原始资料编译为确定性总结页
lwm compile wiki/my-notes

# Query wiki with hierarchical synthesis / 执行层次化知识查询
lwm query "Summarize key findings" --wiki wiki/my-notes

# Export agent context (llms.txt, llms-full.txt, llms.json) / 导出 AI 可消费格式
lwm export wiki/my-notes

# Launch desktop-like local web workspace / 启动本地浏览器工作台
lwm serve wiki/my-notes
```

---

## 7. CLI Command Quick Reference / CLI 命令速查手册

### Central Hub Commands (`lwm hub ...`) / 核心 Hub 命令

| Command (命令) | Description / 说明 |
|---|---|
| `lwm hub context` | Render bounded per-tool context / 输出指定工具在指定项目的启动上下文 |
| `lwm hub bridge` | Universal JSON session bridge for IDEs & CLIs / 面向 IDE 与 CLI 的统一 JSON 会话桥 |
| `lwm hub bridge-stop` | Shell-friendly structured stop & handoff / Shell 友好的会话退出与交接包装命令 |
| `lwm hub record` | Submit structured work event into `raw/events/inbox/` / 提交结构化工作事件 |
| `lwm hub ingest` | Process inbox events & update project memory / 确定性处理 inbox 事件并更新项目记忆 |
| `lwm hub recall` | Evidence Recall B2: progressive deterministic retrieval / 证据召回 B2：渐进式确定性检索 |
| `lwm hub handoff create` | Create a cross-tool handoff packet / 创建跨工具任务交接包 |
| `lwm hub handoff current` | View the currently active handoff for a project / 查看指定项目当前活跃交接包 |
| `lwm hub handoff ack` | Acknowledge that a target tool has loaded the handoff / 记录目标工具已接手交接包 |
| `lwm hub handoff close` | Mark a handoff closed upon task completion / 任务完成后关闭交接包 |
| `lwm hub federation compile` | Compile unified native-memory release / 编译跨 Agent 原生记忆为统一发布版本 |
| `lwm hub federation restore` | Roll back to a previous unified memory release / 回退至指定的历史联邦记忆发布版本 |
| `lwm hub backup create` | Create atomic deterministic backup snapshot / 创建本地原子确定性备份快照 |
| `lwm hub backup sync` | Asynchronously sync backup to decentralized storage / 异步同步备份至去中心化永存网络 |
| `lwm hub backup anchor` | Anchor cycle Merkle root proof to blockchain / 将周期 Merkle 根证明锚定至区块链 |
| `lwm hub backup verify` | Cryptographically verify local backup against on-chain proof / 校验本地备份与链上存证一致性 |
| `lwm hub analyze --pending` | Execute LLM memory compiler analysis / 执行 LLM 内存编译器候选分析 |
| `lwm hub review-analysis` | Review an analysis candidate (`accept`/`reject`/`promote`) / 审查分析候选 |
| `lwm hub promote-analysis` | Promote accepted candidate through multi-project gates / 晋级候选至全局知识库 |
| `lwm hub tools list / probe` | List discovered tools & probe collectors / 列出已发现工具并探查采集器可用性 |
| `lwm hub coverage` | Output integration & proof coverage report / 输出双向集成与凭证覆盖状态报告 |
| `lwm hub health` | Multi-dimensional health snapshot / 多维度健康度快照 |
| `lwm hub closure` | Check if latest loop has sufficient evidence to close / 检查工作循环是否达到闭环证据要求 |
| `lwm hub behavior show/verify` | Inspect & verify canonical `GLOBAL.md` / 查看并校验权威行为合同 `GLOBAL.md` |
| `lwm hub install-ide-hooks` | Generate native lifecycle hook configurations / 为各 IDE 生成原生 Hook 配置文件 |
| `lwm hub install-shell-hook` | Install or update Zsh shell lifecycle hook / 安装或刷新 Zsh 终端生命周期 Hook |
| `lwm hub rebuild-projects` | Rebuild project memory pages from raw events / 从原始事件确定性重建项目记忆页 |
| `lwm hub forget` | Completely remove an event and its page references / 彻底删除指定事件与页面索引 |
| `lwm hub recover-privacy` | Re-evaluate quarantined privacy events / 依据当前规则重新评估被隔离的隐私事件 |

### Root CLI Commands (`lwm ...`) / 基础根命令

| Command (命令) | Description / 说明 |
|---|---|
| `lwm install-global` | Install user-level global adapters & entrypoints / 安装全局适配器与接入点 |
| `lwm attach` | Attach per-tool context entrypoints into a project / 为项目安装各工具的上下文入口 |
| `lwm cbmem` | Codebase memory commands (`doctor`, `index`, `search`, `architecture`, `trace`) / 代码库图谱记忆命令 |
| `lwm init` | Scaffold a new wiki tree / 初始化 Wiki 目录骨架 |
| `lwm compile` | Compile raw input sources into Markdown summaries / 将原始输入编译为结构化总结 |
| `lwm query` | Search and synthesize knowledge from the wiki / 检索与合成知识库内容 |
| `lwm harvest` | Snapshot tool-memory sources into `raw/` / 将外部工具记忆快照进 `raw/` |
| `lwm watch` | Detect source drift & trigger incremental refreshes / 监控文件变更并自动增量刷新 |
| `lwm export` | Generate `llms.txt`, `llms-full.txt`, and `llms.json` / 导出 AI 可消费文件 |
| `lwm audit` | Run unified health audit (analysis + schema + review + eval) / 运行综合健康审计 |
| `lwm eval` | Run reproducible query eval suite / 执行预置查询评测套件 |
| `lwm schedule` | Generate launchd supervisor bundle / 生成 launchd 定时调度配置包 |
| `lwm dashboard` | Generate desktop-style HTML dashboard snapshot / 生成桌面式 HTML 总览报告 |
| `lwm serve` | Run live local workspace in the browser / 启动本地浏览器工作台 |

---

## 8. Configuration & Governance / 配置文件与系统治理

### Behavior Contract (`GLOBAL.md`) / 行为合同规范
**[EN]** `GLOBAL.md` serves as the authoritative, human-reviewed engineering behavior baseline across all tools (verified via SHA-256 and versioned snapshots). It strictly enforces: minimal diffs, standard library preference, verification before action, non-destructive safety, and 100% local privacy for personal habits (keeping GitHub pure engineering code).
**[ZH]** `GLOBAL.md` 是全局统一、经过人工审阅的个人工程行为底线（通过 SHA-256 哈希与版本快照验证）。强制要求：最小化变更、标准库优先、行动前验证、严格非破坏性安全保障，以及个人工作习惯绝对本地私有（GitHub 仅呈现纯工程代码与文档）。

### Privacy Rules (`privacy_rules.toml`) / 隐私与脱敏规则
**[EN]** All ingested events are sanitized against `privacy_rules.toml` (scrubbing API keys, tokens, credentials, and sensitive local paths). High-risk items enter quarantine and never enter project pages or backup payloads.
**[ZH]** 所有摄入系统的事件均会依据 `privacy_rules.toml` 自动脱敏（过滤 API Keys、Tokens、凭据及敏感本地路径）。高风险事件自动进入安全隔离区，严禁写入项目页或外部备份载荷。

### Memory Compiler & Backup Settings / 内存编译器与备份环境配置
```bash
# Optional LLM Memory Compiler / 可选离线 LLM 编译器
export LWM_ANALYSIS_ENABLED=1
export LWM_ANALYSIS_BASE_URL="https://api.openai.com/v1"
export LWM_ANALYSIS_API_KEY="your-api-key"
export LWM_ANALYSIS_MODEL="gpt-4o-mini"
export LWM_ANALYSIS_DAILY_TOKEN_BUDGET=50000

# Optional Web3 & Decentralized Backup / 可选 Web3 去中心化备份设置
export LWM_BACKUP_ENABLED=0
export LWM_BACKUP_STORAGE_PROVIDER="arweave"   # arweave | ipfs | filecoin
export LWM_BACKUP_GATEWAY_URL="https://arweave.net"
export LWM_BACKUP_ANCHOR_NETWORK="arbitrum"    # ethereum | arbitrum | polygon | solana
```
> **[EN]** If no external LLM or Web3 endpoint is configured, `llm-workmem` operates completely deterministically and locally with zero degradation to core features.
> **[ZH]** 若未配置外部 LLM 或 Web3 节点，系统将完全以纯本地确定性模式平稳运行，核心功能不受任何降级影响。

---

## 9. License / 开源许可证

This project is licensed under the [MIT License](LICENSE) / 本项目基于 [MIT 许可证](LICENSE) 开源。
