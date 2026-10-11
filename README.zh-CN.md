# llm-workmem

> **最新备份设计（2026-10-11）**：Team 与企业可选 LWM 公司托管、受支持的去中心化存储或双副本，链上存证独立选择。以 [最新战略](docs/business_plan/WEB2_WEB3_BACKUP_STRATEGY_AND_TOKENOMICS.md) 替代下文旧备份、合规与金融结论。下文相关 CLI 示例、性能和 Web3 功能描述须经实现与恢复验证后，才能作为已上线能力；不构成永久保存或合规保证。

<p align="center">
  <img src="assets/logo.svg" alt="llm-workmem" width="480" /><br />
  <sub>跨 Agent 统一工作记忆与知识管理和备份系统</sub>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)](pyproject.toml)

LLM-WorkMem 的产品方向是跨 Agent 统一工作记忆、知识管理与备份系统，整合有来源的任务交接、可恢复加密备份和可选独立验真。具体功能可用性以实现和验收记录为准。

[English Documentation](README.md)

---

## 核心定位与设计哲学

在现代 AI 辅助研发中，开发者通常在多个工具与环境中频繁切换：使用 **Claude Code** 或 **Codex** 进行架构设计与计划，在 **Antigravity**、**Cursor** 或 **Trae** 中编写代码，通过 **OpenCode** 或 **Kiro** 执行自动化 Agent 任务，并在 **Zsh** 交互式终端中运行验证流水线。

然而，现代多 Agent 协同研发面临三大核心痛点：
1. **记忆孤岛与上下文断裂**：会话重启后，历史决定、Bugfix 修复经验与验证结果丢失；跨 Agent 交接任务需手动复制粘贴对话记录。
2. **非结构化膨胀与幻觉失真**：非结构化记忆倾倒导致 Prompt 窗口迅速耗尽、秘钥泄露以及前后逻辑矛盾。
3. **单点备份脆弱与篡改风险**：关键工程决策、架构选型与验证证据仅存在于易失的本地磁盘或中心化云存储中，极易因误删、静默损坏或平台锁定而永久丢失。

**`llm-workmem` 为所有本地 AI 编程工具提供统一的工作记忆中枢，并融合 Web2-Web3 丝滑无瑕的多级备份与去中心化可信验证。**

### 核心设计原则

1. **辅助证据层（Auxiliary Evidence Layer）**：`llm-workmem` 在会话启动时向各 Agent 注入项目记忆、行为规范、活跃任务交接与联邦知识。它**绝不取代或重写**各工具原生的工具集、技能、计划、执行、验证或内部记忆机制（各工具原生工作流保持最高权威）。
2. **真实核心（Truthful Core）**：仅允许结构化的工程决策（Decisions）、变更（Changes）、验证结果（Verifications）与开放问题（Open Questions）进入长期记忆。命令回显、完整 Prompt、对话废话与环境转录被自动识别为操作噪音并剔除。
3. **真实凭证严格审计（Strict Proof Verification）**：配置文件存在或本地文件观察不等于双向集成完成。系统严格区分“仅生成指令”（instruction-only）、“观察器捕获”（watcher-observed）与“宿主原生 Hook 验证回执”（native-hook verified proof）。
4. **零信任隐私与安全隔离（Zero-Trust Privacy & Quarantine）**：所有摄入事件必须经过自动化秘钥脱敏与隐私扫描（`privacy.py`）。敏感凭证绝不进入长期记忆或备份载荷；高风险事件自动进入隔离区，提供安全的审查恢复链路。
5. **Web2-Web3 丝滑无瑕双引擎备份（Seamless Web2-Web3 Hybrid Backup）**：
   - **日常研发零 Web3 阻碍**：开发者在本地 IDE 和终端中编码时享受亚毫秒级瞬时响应，绝不弹出钱包签名或要求强制 Gas，保持最纯粹的本地高效体验。
   - **去中心化永久存储与链上可信锚定**：备份触发时，系统异步生成确定性快照，计算 Merkle 树根哈希，将不可变回执锚定到区块链合约（EVM / L2 等），并将脱敏归档备份至去中心化永存网络（Arweave / IPFS / Filecoin），实现不可篡改、可跨团队溯源的永恒工程资产备份。

---

## 系统架构（五层统一架构）

`llm-workmem` 采用高度解耦的五层统一架构设计：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             捕获层 (CAPTURE PLANE)                          │
│   IDE 生命周期 Hook │ 统一会话桥 (Bridge) │ 宿主 Companion 扩展 │ 终端 Hook │
│   (Codex, Claude, AGY, Gemini, Kiro, Trae, MiniMax, VS Code, Cursor, Zsh)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 原始事件 (raw/events/inbox/)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       证据与编译器层 (EVIDENCE & COMPILER)                  │
│  确定性准入分类 (classify_event)     ──► 隐私与秘钥过滤 (privacy.py)         │
│  项目记忆确定性重建 (project_memory) ──► 证据链溯源绑定                     │
│  跨 Agent 记忆联邦 (Federation)      ──► LLM 编译器与每日 Token 预算控制    │
│  候选审查队列 (review/)              ──► 稳定晋级门禁 (Stable Promotion)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 验证后的记忆与交接包
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             交付层 (DELIVERY PLANE)                         │
│  受限启动上下文 (Context <= 12k 字符) │ 跨 Agent 任务交接 (Handoff Packet)  │
│  统一行为合同 (GLOBAL.md 验证快照)   │ 确定性证据召回 (Evidence Recall B2)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       ▲
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                             控制层 (CONTROL PLANE)                          │
│  6小时 Supervisor 调度守护 (Launchd) │ 不可变周期回执 (CycleReceiptV2)      │
│  工具能力真实探查 (Tools Probe)      │ 严格健康审计 (Health) 与闭环门禁     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 验证快照与 Merkle 根哈希
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    备份与去中心化层 (BACKUP & DECENTRALIZED)                │
│  Web2 确定性本地快照                 ──► 本地安全备份 (.promotion-backups)  │
│  去中心化永久存储 (IPFS / Arweave)   ──► 内容寻址防单点篡改                 │
│  链上可信状态锚定 (EVM / L2)         ──► Merkle 根零知识与跨团队可验证存证  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. 捕获层（Capture Plane）
- **统一会话桥接器（`lwm hub bridge`）**：标准 JSON IPC 接口，统一处理各 IDE 与 CLI 的 `context`、`start` 和 `stop` 生命周期阶段。
- **原生生命周期 Hooks**：深度对接 Claude Code、Codex、Antigravity、Gemini CLI 及 Zsh 终端生命周期事件。
- **IDE Companion 扩展**：为 VS Code、Trae、Kiro 和 Cursor 提供宿主兼容包。
- **项目身份严格解析**：基于 Git 仓库根目录哈希（`id=git-<hash>`）确定项目边界，彻底解决软链接和目录间接引用引起的记忆混淆。

### 2. 证据与编译器层（Evidence & Compiler Plane）
- **真实核心准入（`lwm hub ingest`）**：将输入事件严格分类为 `durable`（可沉淀工程事实）、`operational`（生命周期/命令等运行噪音）或 `rejected`。
- **项目记忆确定性重建（`lwm hub rebuild-projects` / `reflect`）**：依据摄入事件自动生成项目状态页（近期决策、Bugfix、验证记录与遗留问题），每条记忆均带有精确到文件与 UUID 的证据链链接。
- **统一原生记忆联邦（`lwm hub federation`）**：将 OpenCode（`MEMORY.md`）、Codex、Claude Code、Antigravity 等来源的原生记忆抽取、去重，按明确的优先级与替代规则处理，标记未解决的冲突候选并生成带时间戳的发布版本（`release-*.json`）；这不等于自动理解和解决所有语义冲突。
- **记忆审核与更新**：审核接口支持接受、拒绝或晋级分析候选；记忆联邦区分有效、冲突、陈旧和已被替代的记录，明确的来源更新可替代旧记录。这里管理的是共享记忆，不是自动修复项目代码，也不保证判断每条说法的真伪。独立 HTML 的采纳／撤回交互仅为演示，不写入真实后台，也不证明所有 IDE 会立即撤销已读取的内容。
- **LLM 记忆编译器（`lwm hub analyze --pending`）**：基于每日 Token 预算与重试状态机，分析多项目间的复用工作流与模式，生成结构化候选对象（`candidates-*.md`）。
- **稳定晋级门禁（`lwm hub promote-analysis`）**：严格要求跨至少两个不同项目（`MIN_PROMOTION_PROJECTS >= 2`）并具备正面验证结果才可晋级为全局规则（`wiki/global/*.md`）；当下游证据撤回或被推翻时，自动触发版本回退与撤回。

### 3. 交付层（Delivery Plane）
- **受限启动上下文（`lwm hub context`）**：启动时根据激活工具组装上限 12,000 字符的精炼上下文，杜绝 Prompt 溢出。
- **跨 Agent 任务交接（`lwm hub handoff-*`）**：在工具退出时固化当前任务目标、当前状态、决定、变更、验证和下一步行动（`next_action`），供下一个启动的工具接力执行。
- **证据召回 B2（`lwm hub recall`）**：渐进式确定性检索，返回包含检索计划、证据来源、多维覆盖与缺失项的项目级证据包。
- **统一行为合同（`GLOBAL.md`）**：全局统一的个人工程行为规范，经由 SHA-256 哈希比对与版本快照验证（`lwm hub behavior`）。

### 4. 控制层（Control Plane）
- **统一 Supervisor 守护（`lwm hub run-supervisor`）**：每 6 小时或开机时自动执行采集、摄入、重建、候选生成、审查导出与审计。
- **不可变周期回执（`CycleReceiptV2`）**：每次运行均产出隔离不可变回执，明确划分 `ok`、`warning`、`degraded`、`quality_warning` 与 `failed_core`。
- **闭环工程门禁（`lwm hub closure`）**：外部客观证据不足时拒绝标记任务闭环，阻断未验证完成。
- **代码库记忆集成（`lwm cbmem`）**：通过 AST 和代码图谱分析深入解析代码调用关系与架构结构。

### 5. 备份与去中心化层（Backup & Decentralized Plane）
- **Web2 确定性本地快照**：自动生成已准入记忆、周期回执与全局原则的原子级压缩快照包，存储于本地安全备份目录。
- **去中心化永久存储（Arweave / IPFS / Filecoin）**：基于内容寻址的去中心化永存方案，确保经过审查的联邦发布与全局工程原则具备防单点灾难的永恒存储能力。
- **链上可信状态锚定（EVM / L2 等）**：对周期回执与记忆快照计算 Merkle 树，将状态根哈希提交至智能合约注册表，为跨组织或跨设备的分布式 AI 团队提供零知识可验证的防篡改证明。

---

## 跨 Agent 工具生态矩阵

`llm-workmem` 原生支持 11 种主流 AI 研发工具与环境：

| 工具 / 宿主 | 交互形态 | 采集机制 | 交付机制 | 凭证验证等级 (Proof Level) |
|---|---|---|---|---|
| **Anthropic Claude Code** | CLI / Agent | SessionStart / Stop 原生 Hook | `CLAUDE.md` + Hook Context | 经测试宿主凭证 (`claude-code-hook`) |
| **OpenAI Codex** | CLI / IDE | `SessionStart`/`SessionEnd` Hook | `hooks.json` + `AGENTS.md` | 经测试宿主凭证 (`codex-hook`) |
| **OpenCode** | CLI / Agent | 插件生命周期 + 结构化写回 | `AGENTS.md` + 插件桥接 | 经测试宿主凭证 (`opencode-plugin`) |
| **Google Antigravity (AGY)** | IDE / Agent | PreInvocation / Stop Hook + MCP | `.agents/AGENTS.md` + Hooks | 原生 Hook 契约 + 观察器备选 |
| **AWS Kiro** | IDE | 会话 / 导向适配器 (Steering) | Companion 扩展 + Steering | Companion 宿主凭证 (`kiro-extension`) |
| **ByteDance Trae** | IDE | Attach / 会话适配器 | Companion 扩展 + `.traerules` | Companion 宿主凭证 (`trae-extension`) |
| **MiniMax** | 桌面端 / CLI | 注册 MCP 桥接器 + Shell 包装 | 运行时 SQLite + Shell Context | 注册 MCP 桥接凭证 (`minimax-mcp`) |
| **VS Code / Copilot** | IDE | 任务与会话观察器 | Companion 扩展 + 用户指令 | Companion 宿主凭证 (`vscode-extension`) |
| **Cursor** | IDE | 规则系统 (`.mdc`) + Shell 周期 | `.cursor/rules/llm-workmem.mdc` | Companion / Shell 生命周期备选 |
| **Gemini CLI** | CLI | SessionStart/End 原生 Hook | `GEMINI.md` + 设置 Hook | 原生 Hook 契约 + MCP 桥接 |
| **Zsh 交互式终端** | 终端命令行 | `preexec` / `precmd` Shell Hook | 动态上下文命令 (`lwm-context`) | 经测试终端凭证 (`shell-hook`) |

> **提示**：安装了配置文件不等于双向集成已打通。通过 `lwm hub tools probe` 和 `lwm hub coverage` 可以实时查看各工具的实际运行状态（区分已配置、宿主存在与真实读写 Proof）。

---

## 安装与快速上手

### 环境要求
- **Python**: `>= 3.11`
- **包管理器**: 推荐 [uv](https://docs.astral.sh/uv/)，亦可使用标准 `pip`
- **操作系统**: macOS / Linux

### 1. 安装 CLI

推荐使用 `uv` 安装：
```bash
uv tool install .
# 或者在本地开发模式下安装：
uv pip install -e ".[dev]"
```

或使用标准 `pip`：
```bash
pip install .
```

检查版本：
```bash
lwm --version
```

### 2. 初始化工作站环境

设置持久化工作记忆的数据根目录并安装全局适配器：

```bash
# 1. 设置工作记忆根目录
export LWM_ROOT="/path/to/LLM-WorkMem"

# 2. 预览将要安装的适配器与规则文件 (dry-run)
lwm install-global "$LWM_ROOT" --dry-run

# 3. 正式安装各 IDE / CLI 的全局入口
lwm install-global "$LWM_ROOT"

# 4. 为支持的 IDE 生成原生 Hook 配置文件
lwm hub install-ide-hooks "$LWM_ROOT"

# 5. 向 ~/.zshrc 安装终端生命周期捕获 Hook
lwm hub install-shell-hook "$LWM_ROOT"
```

### 3. 验证工具覆盖状态

```bash
# 查看本地各工具的发现状态与采集器就绪情况
lwm hub tools probe --root "$LWM_ROOT"

# 查看各工具双向读写与凭证覆盖报告
lwm hub coverage --root "$LWM_ROOT"
```

### 4. 安装代码库图谱记忆（可选）

如需启用针对项目目录的深度 AST 结构与调用图分析：

```bash
bash automation/install-cbmem.sh
lwm cbmem doctor
```

---

## 核心工作流与实战指南

### 1. 会话启动与上下文注入

当任何 AI 工具在项目目录下启动时，自动或手动请求当前项目的精简上下文：

```bash
# 生成 Markdown 格式（供 Prompt 或指令文件加载）
lwm hub context --tool claude-code --project "$PWD"

# 生成 JSON 格式（供 IDE 插件解析）
lwm hub context --tool codex --project "$PWD" --format json
```

### 2. 跨 Agent 任务交接实战

在不同工具之间协同工作时（例如：在 Codex 中完成部分任务后交由 Antigravity 或 Claude Code 继续）：

#### 步骤 A：工具 A 完成当前阶段，记录交接包
```bash
lwm hub bridge-stop \
  --tool codex \
  --project "$PWD" \
  --task-id "task-auth-migration" \
  --task "完成 JWT 校验中间件编写" \
  --handoff-json '{
    "task_id": "task-auth-migration",
    "objective": "将会话 Token 迁移至 JWT 校验",
    "current_state": "中间件编写完毕，单元测试在边界用例失败",
    "decisions": ["内部服务采用 HS256 签名算法"],
    "changes": ["src/auth/jwt.py", "tests/test_jwt.py"],
    "verifications": ["pytest tests/test_jwt.py -k test_valid_token 通过"],
    "risks": ["分布式节点存在时间漂移风险"],
    "open_questions": ["Refresh Token 的有效期窗口确定为多久？"],
    "next_action": "在 Token 校验器中增加时间漂移容差逻辑"
  }' \
  --root "$LWM_ROOT"
```

#### 步骤 B：工具 B 启动并接手工作
```bash
lwm hub handoff ack --handoff-id "<handoff_id>" --target-tool antigravity --root "$LWM_ROOT"
```

#### 步骤 C：任务最终验证完成，关闭交接
```bash
lwm hub handoff close --handoff-id "<handoff_id>" --root "$LWM_ROOT"
```

### 3. 提交工作事件与记忆摄入

```bash
# 提交结构化事实
lwm hub record \
  --tool shell \
  --project "$PWD" \
  --task "修复内存编译器 Token 预算控制" \
  --decision "采用预扣除与对账机制控制每日 Token 预算" \
  --change "lwm/memory_compiler.py" \
  --verification "pytest tests/test_analysis_compiler.py 通过" \
  --tag "stable-claim" \
  --root "$LWM_ROOT"

# 执行摄入与项目记忆重建
lwm hub ingest "$LWM_ROOT"
```

### 4. 记忆编译与稳定晋级

```bash
# 1. 对待处理的长期事件运行离线 LLM 分析
lwm hub analyze --pending --root "$LWM_ROOT"

# 2. 人工审查候选模式（接受、拒绝或直接晋级）
lwm hub review-analysis <candidate_id> --decision accept --root "$LWM_ROOT"

# 3. 经过双项目验证后，显式晋级为全局知识
lwm hub promote-analysis <candidate_id> --root "$LWM_ROOT"

# 4. 编译各 Agent 的原生记忆为统一发布版本
lwm hub federation compile --root "$LWM_ROOT"
```

### 5. 证据召回 B2（Evidence Recall B2）

```bash
# 精简模式召回
lwm hub recall "本项目最近关于内存编译器的 Token 上限是如何验证的？" \
  --project "$PWD" \
  --root "$LWM_ROOT"

# 深度审计模式并输出 Markdown
lwm hub recall "梳理本项目所有关于适配器架构的设计决定" \
  --project "$PWD" \
  --mode deep \
  --format markdown \
  --root "$LWM_ROOT"
```

### 6. 多级备份与 Web2-Web3 锚定实战

在不干扰日常编码流畅度的前提下，为工程记忆提供本地快照、去中心化永存与链上可信验证：

```bash
# 1. 创建本地确定性备份快照
lwm hub backup create --root "$LWM_ROOT"

# 2. 异步归档脱敏快照至去中心化永存网络 (Arweave / IPFS / Filecoin)
lwm hub backup sync --provider arweave --root "$LWM_ROOT"

# 3. 将最新周期 Merkle 根锚定到区块链合约
lwm hub backup anchor --network evm --root "$LWM_ROOT"

# 4. 密码学校验本地快照与链上锚定的一致性
lwm hub backup verify --root "$LWM_ROOT"
```

### 7. 健康监控与闭环审计

```bash
# 系统全面健康度快照
lwm hub health "$LWM_ROOT"

# 检查当前工程循环是否具备充分客观证据闭环
lwm hub closure "$LWM_ROOT"

# 校验特定周期的不可变回执
lwm hub verify-cycle --root "$LWM_ROOT"
```

---

## 经典知识库模式与 Agent Skill

对于希望保留 Karpathy 原版纯 Markdown 个人知识库玩法的用户，`llm-workmem` 依旧提供完整的支持：

<p align="center">
  <img src="assets/flow.svg" alt="wiki-flow" width="600" /><br />
</p>

### 知识库常用命令
```bash
# 初始化个人知识库目录树
lwm init --profile personal wiki/my-notes

# 将 raw/ 目录下的原始资料编译为确定性总结页
lwm compile wiki/my-notes

# 执行层次化知识查询
lwm query "总结核心观点" --wiki wiki/my-notes

# 导出 AI 可消费格式 (llms.txt, llms-full.txt, llms.json)
lwm export wiki/my-notes

# 启动本地 Web 工作台
lwm serve wiki/my-notes
```

---

## CLI 命令速查手册

### Central Hub 命令（`lwm hub ...`）

| 子命令 | 说明 |
|---|---|
| `lwm hub context` | 输出指定工具在指定项目的启动上下文（`--format markdown` 或 `json`） |
| `lwm hub bridge` | 面向 IDE 与 CLI 的统一 JSON 会话桥接器 |
| `lwm hub bridge-stop` | Shell 友好的会话退出与 Handoff 提交包装命令 |
| `lwm hub record` | 提交一条结构化工作事件到 `raw/events/inbox/` |
| `lwm hub ingest` | 确定性处理 inbox 事件并更新项目记忆 |
| `lwm hub recall` | 证据召回 B2：渐进式确定性检索 |
| `lwm hub handoff create` | 创建跨工具任务交接包 |
| `lwm hub handoff current` | 查看指定项目的当前活跃交接包 |
| `lwm hub handoff ack` | 记录目标工具已接手交接包 |
| `lwm hub handoff close` | 任务完成后关闭交接包 |
| `lwm hub federation compile` | 编译跨 Agent 原生记忆为统一发布版本 |
| `lwm hub federation restore` | 回退至指定的历史联邦记忆发布版本 |
| `lwm hub backup create` | 创建本地原子确定性备份快照 |
| `lwm hub backup sync` | 异步同步备份至去中心化永存网络 |
| `lwm hub backup anchor` | 将周期 Merkle 根证明锚定至区块链智能合约 |
| `lwm hub backup verify` | 密码学校验本地备份与链上存证一致性 |
| `lwm hub analyze --pending` | 执行 LLM 内存编译器候选分析 |
| `lwm hub review-analysis` | 审查分析候选（`accept` / `reject` / `promote`） |
| `lwm hub promote-analysis` | 将已接受的候选通过多项目凭证门禁晋级至 `wiki/global/` |
| `lwm hub tools list / probe` | 列出已发现工具并探查采集器可用性 |
| `lwm hub coverage` | 输出双向集成与凭证覆盖状态报告 |
| `lwm hub health` | 多维度健康度快照（基础设施、数据流、周期状态、质量） |
| `lwm hub closure` | 检查当前工作循环是否达到闭环证据要求 |
| `lwm hub behavior show / verify` | 查看并校验权威行为合同 `GLOBAL.md` |
| `lwm hub install-ide-hooks` | 为各 IDE 生成原生 Hook 配置文件 |
| `lwm hub install-shell-hook` | 安装或刷新 Zsh 终端生命周期 Hook |
| `lwm hub rebuild-projects` | 从已准入的原始事件确定性重建所有项目记忆页 |
| `lwm hub forget` | 从事件存储与项目页中彻底删除指定的事件 |
| `lwm hub recover-privacy` | 依据当前脱敏规则重新评估被隔离的隐私事件 |

### 根命令（`lwm ...`）

| 命令 | 说明 |
|---|---|
| `lwm install-global` | 为当前用户安装全局适配器与接入点 |
| `lwm attach` | 为特定项目目录安装各工具的上下文入口 |
| `lwm cbmem` | 代码库图谱记忆命令（`doctor`, `index`, `search`, `architecture`, `trace` 等） |
| `lwm init` | 初始化 Wiki 目录骨架 |
| `lwm compile` | 将原始输入文件编译为结构化 Markdown |
| `lwm query` | 检索与合成知识库内容 |
| `lwm harvest` | 将外部工具记忆快照进 `raw/` 目录并更新总结 |
| `lwm watch` | 监控文件变更并自动增量刷新 |
| `lwm export` | 导出 `llms.txt`、`llms-full.txt` 和 `llms.json` |
| `lwm audit` | 运行综合健康审计（结构、模式、审查队列、查询评测） |
| `lwm eval` | 执行预置查询评测套件 |
| `lwm schedule` | 生成 launchd 定时调度配置包 |
| `lwm dashboard` | 生成桌面式 HTML 总览报告 |
| `lwm serve` | 启动本地浏览器工作台 |

---

## 配置文件与系统治理

### 行为合同（`GLOBAL.md`）
`GLOBAL.md` 是全局统一、经过人工审阅的个人工程行为底线：
- 坚持长期合作伙伴思维，透明沟通配置与代码；
- 行动前必须核实真实文件、真实环境与边界；
- 坚持极简代码哲学（最小完整变更、标准库优先、避免无用抽象）；
- 严格的非破坏性操作保障（严禁未经明确授权的删库或强推）；
- **工作习惯与约定绝对本地私有**：个人工作习惯仅保存在本地工作记忆中，GitHub 仓库仅对外展现最纯净标准的工程代码与架构文档。

### 隐私过滤规则（`privacy_rules.toml`）
所有摄入系统的事件均会执行隐私规则匹配：
- 秘钥模式自动过滤（API Keys、GitHub Token、AWS 秘钥等）；
- 绝对敏感路径自动脱敏；
- 包含不可脱敏机密的事件自动进入安全隔离区，严禁写入项目页或外部备份载荷。

### 内存编译器与备份环境配置
```bash
# 可选离线 LLM 编译器
export LWM_ANALYSIS_ENABLED=1
export LWM_ANALYSIS_BASE_URL="https://api.openai.com/v1"
export LWM_ANALYSIS_API_KEY="your-api-key"
export LWM_ANALYSIS_MODEL="gpt-4o-mini"
export LWM_ANALYSIS_DAILY_TOKEN_BUDGET=50000

# 可选 Web3 去中心化备份设置
export LWM_BACKUP_ENABLED=0
export LWM_BACKUP_STORAGE_PROVIDER="arweave"   # arweave | ipfs | filecoin
export LWM_BACKUP_GATEWAY_URL="https://arweave.net"
export LWM_BACKUP_ANCHOR_NETWORK="arbitrum"    # ethereum | arbitrum | polygon | solana
```
> 若未配置外部 LLM 或 Web3 节点，系统将完全以纯本地确定性模式平稳运行，核心功能不受任何降级影响。

---

## 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
