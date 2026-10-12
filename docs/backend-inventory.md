# LLM-WorkMem 后端实现清单（源码深盘点）

> 盘点基准：main 分支工作区，2026-10-12。覆盖 `lwm/`（76 模块 / 29,336 行）、`mcp/`、`adapters/hooks/`（23 文件）、`integrations/`。
> 结论先行：**全部 76 个模块均为可运行实现，无 NotImplementedError / 空桩 / TODO 代码标记**；882 个测试函数（96 个测试文件）覆盖各面。真正"未实现"的是文档叙事中的部分能力（见 §7 缺口清单）。

## 1. 入口面（四个真实服务）

| 入口 | 形态 | 启动 | 状态 |
|---|---|---|---|
| `lwm` CLI | Typer CLI，`lwm.cli:main` | `lwm <cmd>` | ✅ 根命令 25 + `hub` 30 + `cbmem` 9 + `raw` 2 |
| MCP stdio 服务器 | JSON-RPC 2.0 over stdio，**不依赖官方 SDK** | `python -m mcp.lwm_server <root>` | ✅ 16 个工具 |
| JSON 网关 | `http.server` ThreadingHTTPServer，`127.0.0.1:8766` | `lwm gateway <root>` | ✅ 30 个端点（`docs/api-contract.md`） |
| HTML 工作台 | `ThreadingHTTPServer`，`127.0.0.1:8765` | `lwm serve <root>` | ✅ 4 类路由（服务端渲染） |

## 2. 捕获层（Capture Plane）

**工具记忆采集 `harvest.py`（1541 行）**
- 12 个源组（`lwm-sources.json` 可追加）：codex、claude-code、cursor、opencode、trae-solo、github-copilot、vscode、kiro、antigravity、minimax、shell、gemini-cli。
- 管线：快照（脱敏）→ `raw/tool-snapshots/<group>/` → 生成 governance/insights/entities 页 → raw sync → compile → analyze → dashboard → llms 导出。
- 运行时安装：`materialize_runtime_layout`、`write_schedule_bundle`（launchd plist 生成+加载）。

**原生生命周期 hooks（`adapters/hooks/`，23 个实现文件）**
- claude-code（settings.json SessionStart/Stop）、codex（hooks.json 4 类事件）、cursor、gemini-cli（+MCP 合并）、antigravity（PreInvocation/Stop + sessions 元数据观察器）、kiro/trae/vscode/minimax（session 观察器）、opencode（TS 插件）。
- 另有 shell hook（zsh preexec/precmd → `raw/shell/<date>.jsonl`）、claude JSONL 会话笔记导入（`session_ingest.py`）。

**IDE 伴侣扩展**：`integrations/ide-companion`（VSIX 打包 + `code/cursor/trae/kiro --install-extension` 安装，`ide_companion.py`）。

## 3. 证据与编译器层（Evidence & Compiler）

| 模块 | 已实现能力 |
|---|---|
| `events.py` | 事件 schema v2：13 种 event_type、8 个必需键、4 档 importance/privacy、16KB 文本截断 |
| `ingest.py` | 准入管道：校验 → 隐私脱敏 → project_id 补全 → 去重 → 项目页追加；四桶（inbox/processed/rejected/failed）+ `.reason` 边车；隐私误杀恢复（默认 dry-run） |
| `privacy.py` | 7 类密钥正则（OpenAI/AWS/GitHub PAT/Slack/JWT/PEM block/KV）→ `<REDACTED>`；敏感路径屏蔽；规则读 `privacy_rules.toml`（自研极简 TOML 解析） |
| `dedup.py` | sha1 去重键 + session 24h 窗口去重；`state/event-index.json` 原子写 |
| `project_memory.py` | `DURABLE_EVENT_TYPES = {decision, bugfix, verification, project_status}`；classify 三态（durable/operational/rejected）；`wiki/projects/<id>.md` 确定性重建（每子弹 `↳ tool · event_id · evidence_path` 溯源）；supersedes 过滤 |
| `project_id.py` | 身份派生：git remote origin → toplevel 路径 → 绝对路径，分别得 `git-/local-/adhoc-<sha1-16>`；`state/project-map.json` |
| `memory_compiler.py`（2062 行） | LLM 候选编译器：10 态状态机；双 provider（Codex CLI 子进程 + OpenAI 兼容 API）；隐私白名单投影 15 字段；每日 50k token 预算（reserve/reconcile）；重试退避 (60,300,1800)s；死信队列；大证据二叉归并分批。**未配 `LWM_ANALYSIS_*` 时静默降级 no-op** |
| `stable_promotion.py` | 全局晋级门禁：≥2 项目 durable（`MIN_PROMOTION_PROJECTS=2`）+ ≥2 项目正向验证 + claim 禁词/密钥过滤 + 无反证；原子写 + `.promotion-backups` 备份 + 审计 jsonl；证据撤回自动回退页 |
| `memory_federation.py` | 跨 Agent 原生记忆联邦（Codex/OpenCode，确定性解析无 LLM）：优先级 opencode=120 > codex=110；superseded/conflicted/stale/archived 判定 + 退休环检测；`release-*.json` 发布与回滚 |
| `structured_candidates.py` | workflow 候选（同任务 ≥3 次）/ relationship 候选（跨 ≥2 项目）；accept 时强制校验 evidence 存在于 processed |
| `conflict.py` / `insights.py` | 跨项目同 tag 决策冲突检测 → `wiki/review/conflict-*.md`；insight 候选 → `candidates-*.md`（纯确定性） |
| `promote.py` | **已退役**：legacy auto-promotion 永远返回 disabled，fail-closed |

## 4. 交付层（Delivery）

- **`context.py` + `hub_service.context_for_tool`**：有界启动上下文（12k 字符上限），按工具渲染 markdown/json。
- **`session_bridge.py`**：JSON-IPC 桥，`context/start/stop` 三阶段，schema v1；proof source 必须 `trusted_host` + host_proof（对照 registry `proof_integrations`，自述"非密码学证明，防伪装"）；`simulate_registry_contract` 全工具契约演练。
- **`lifecycle.py`**：start/stop 幂等（marker 文件 + flock/msvcrt 锁）；stop 时 handoff_summary 边界化（每项 ≤1000 字符 ≤8 项）→ durable 事件 + handoff 创建。
- **`handoff.py`**：跨工具交接包（objective/decisions/changes/verifications/open_questions/next_action）；活跃指针按 (project_id, branch)；supersedes 不匹配响亮失败；ack/close 留痕。
- **`recall.py` + `evidence.py` + `memory_api.py`**：证据召回 B2——7 维问题分解、相对日期窗口、EvidenceItem 去重/仲裁（superseded/conflicted）、coverage 三态（complete/partial/insufficient）+ missing 清单；compact/deep 两档。
- **`behavior_contract.py`**：GLOBAL.md 行为合同版本快照 + SHA-256 校验。

## 5. 控制层（Control）

| 模块 | 已实现能力 |
|---|---|
| `health.py` | 三层快照（infrastructure/data_flow/quality）→ `state/health.json`；healthy/degraded/failed 分级；strict 模式要求 eval 全过 |
| `cycle_receipt.py` | CycleReceiptV2 不可篡改回执（`os.link` 防覆盖）；success / success_with_warnings / failed_core |
| `loop_state.py` | 有界循环状态机，4 退出态；`completed_verified` 强制要求 criteria_met + evidence |
| `closure.py` | 八项闭环门禁（loop/evidence/source/runtime/export/receipt/health/launchd） |
| `runner.py`（851 行） | 一轮完整周期：collector 子进程采集 → shell 清扫 → cbmem 同步 → ingest → 重建项目页 → 候选合成 → 可选分析 → watch 审计 → context 冒烟 → 质量门 → 导出 → 写 V2 回执（含 evidence SHA-256） |
| `supervisor.py` | 6 小时调度（21600s）+ 开机检测；数据属主校验门 |
| `capability_proof.py` | 收据体系：**PROOF = {native-hook, lifecycle-hook, ide-extension, mcp-bridge}** vs **OBSERVATION = {watcher-observed, cli-context, file-probe, explicit-smoke}**；14 天新鲜窗口；POSIX flock / Windows msvcrt 双兼容 |
| `capabilities.py` / `tool_registry.py` | 12 工具注册表 v5（discovery/host_commands/capture_mode/proof_integrations）；probe 区分"已配置"与"真实读写凭证" |
| `lease.py` | 多 Agent 软租约（TTL 600s，force 接管）；无文件锁（有竞态） |
| `lockfile.py` | ingest/cycle 进程锁（O_EXCL + pid 存活 + 陈旧窗口）；cycle_lock 可重入 |
| `queue_compaction.py` | 分析候选队列压缩（保护人工评审，子先于根退役） |

## 6. 备份与 Web3 层（真实度分级）

| 模块 | 真实实现 | 本地模拟 / 部分实现 |
|---|---|---|
| `backup.py` | 本地确定性 tar.gz 备份 + SHA-256；还原 fail-closed + Zip-Slip 防护；compact 模式裁剪至 1800 字节核心文件 | 纯本地，**无上传** |
| `vault.py` | PBKDF2-HMAC-SHA256 100k 轮；原子写；钱包归属删除校验 | **无 JWT 时 CID 是拼接假字符串**（`bafkrei+hash[:48]`），无真实 IPFS/Arweave 上传；**服务端不做加解密**（前端 Web Crypto 产生密文） |
| `solana_storage.py` | **真实** Solana JSON-RPC 验证（getSignatureStatuses + getTransaction、多 RPC 故障转移、验 signer/recipient/memo） | 配额账本与"链上存证"仅本地 JSON 记账，**无链上程序调用/交易构建**；token_mint/treasury 为占位字符串 |
| `webauth.py` | 真实密码学：标准库 RFC 8032 Ed25519 验签 + Base58；PBKDF2 20 万轮；nonce 5 分钟一次性；session 7 天 | 无邮件/找回密码；钱包验证可自动落地 `<addr>@wallet.local` 账户 |

## 7. Wiki 经典模式（Karpathy 模式，全部实现）

`init_scaffold`（wiki 树 + profile）、`compile`（raw→确定性摘要）、`query`（5 档深度检索综合）、`analysis`（链接图：hubs/orphans/broken links）、`eval`（可复现评测套件）、`audit`（统一审计）、`review`（审查队列）、`schema`（frontmatter + 15 种页面类型校验）、`export`（llms.txt/llms-full.txt/llms.json）、`raw_tracker`（SHA-256 漂移检测 files.log）、`watch`（指纹触发增量刷新）、`forget`（事件彻底删除 + 保留策略）。

## 8. CBMEM 代码图谱（外部二进制包装）

`cbmem.py` shell-out `codebase-memory-mcp` 二进制的 7 个命令（index/status/search/architecture/trace/changes/dead_code/semantic）；`cbmem_source.py` 每项目采集快照；`cbmem_bridge.py` 同步注册项目。**二进制缺失时优雅降级**（每项目记 ok=False，不抛异常）。recall 的 CBMEM 证据通道在二进制不可用时仅追加 warning。

## 9. 显式缺口（文档宣称但代码未实现）

1. **团队共享/多用户**：后端无任何多用户模型（`/api/teams` 固定返回空）；federation 仅本机跨 Agent。
2. **订阅计费**：`/api/subscription` 返回静态 4 档定义，无支付/开通逻辑。
3. **IPFS/Arweave 真实上传**：无 Pinata JWT 时 CID 为本地拼接值；无 Arweave 客户端。
4. **链上存证**：仅有 Solana RPC **验签**能力，无发证/锚定交易构建。
5. **服务端加密**：E2EE 加解密在前端，后端只存密文，无解密函数。
6. **session_ingest 摘要步骤**：Claude JSONL → 笔记已实现，"摘要"文档标注 v0.1 范围外。
7. **Kiro/Trae 原生钩子**：有意采用 steering/session-observer 回退（hooks_gen 明示）。
8. **lease 并发**：JSON 读-改-写无文件锁，存在竞态。
9. **insights 7 天窗口**：`within_days` 参数定义未使用（无时间过滤）。
10. **已知文档漂移**：`cbmem_source.py` docstring 声称由 harvest_sources 周期调用（实际唯一调用方是 watch.py）。

## 10. 测试覆盖

96 个测试文件 / 882 个测试函数，覆盖：hub_service、ingest/privacy/dedup、project_memory、compiler（含修复/效率/批次）、stable_promotion、federation、handoff（含并发）、session_bridge、lifecycle、recall/evidence、cycle_receipt/v2 控制面、runner/supervisor 循环、capability_probe、backup/vault/solana_storage、lease、gateway、mcp_server、各 IDE 原生 hook（claude/codex/cursor/gemini/antigravity/opencode）、shell hook、cli 全表面。

## 11. 前端两功能 ↔ 后端映射核对（2026-10-12 实测）

前端 UI 当前 7 个 tab（App.tsx:94-100），按功能归并为用户所述两类；team/plans 为纯演示模块（后端无多用户/计费）。以下映射均在运行中的网关上实测（127.0.0.1:8766）。

### 功能① 整理本地工作流和记忆体

| 前端调用 | 端点 | 后端实现 | 实测 |
|---|---|---|---|
| 项目列表+工作台 | GET /api/projects + /api/context | hub_service.context_for_tool + project-map | ✅ 返回 git-9f1cb19971812dd3 真实项目 |
| 工作方式 | GET /api/behavior + /api/tools/coverage | behavior_show + coverage_report | ✅ |
| 待确认审查 | GET /api/candidates + POST /api/candidates/<id>/review | memory_compiler review_analysis_candidate | ✅ 端点通；**列表为空**——需先跑候选合成（analyze --pending / insights / runner 周期） |
| 历史事件 | GET /api/events | 读 raw/events/inbox+processed | ✅ |
| 搜索/健康 | GET /api/search + /api/health | query + health.collect_and_write | ✅ |

小缺口（非功能缺失）：① “新建项目”为纯本地 UI（后端项目身份由事件自动派生，无创建端点）；② 工作台“交接包”下拉是占位文案——网关**无** `/api/handoff/current` 路由（endpoints.ts 有声明但零调用，CLI/MCP 层有 handoff 能力）。

### 功能② 钱包登录 + 备份/恢复

| 前端调用 | 端点 | 后端实现 | 真实度 |
|---|---|---|---|
| 钱包登录（Phantom/Solflare） | POST /api/auth/wallet/nonce + /verify + GET /me + logout | webauth.py：标准库 Ed25519 验签 + PBKDF2 20 万轮 + nonce 5 分钟 + session 7 天 | ✅ 全真（实测 nonce 正常下发，无 token 访问 /me 正确返回 E_NO_SESSION） |
| 创建加密冷备 | GET /api/backup/bundle?compact=1 → 前端 AES-256-GCM → POST /api/vault/pin_ipfs + /vault/upload → 前端 SPL Memo 分片上链 → POST /api/solana/commit | backup.create_backup_bundle（tar.gz+SHA-256）→ vault.pin_snapshot_ipfs / store_encrypted_snapshot → solana_storage.record_attestation（verify_rpc 真实 RPC 核验） | 本地打包/金库 100% 真；IPFS 有条件真（需 Pinata JWT）；链上存证 = 前端真实广播 + 后端真实验签，但后端账本为本地 JSON |
| 回滚恢复 | RPC 扫链取密文 → GET /api/vault/download → 前端解密 → POST /api/backup/restore | backup.restore_backup_bundle：哈希校验 fail-closed + Zip-Slip 防护 + 原子替换 | ✅ 100% 真 |
| 链上跨设备找回 | GET /api/solana/config + /api/solana/attestations → ColdRestore | solana_storage 配置与存证查询 | ✅（前端真实扫链 getSignaturesForAddress） |
| 配额购买/空投/配置 | POST /api/solana/purchase、/config、GET /api/solana/quota | 前端真实 SOL 转账；后端 RPC 核验 + 本地配额账本 | 交易真、记账本地；Anchor 程序（WORKMEM_PROGRAM_ID）devnet 未部署时自动降级为 SystemProgram.transfer |

### 结论

两大功能**核心链路一一对应且为真实实现**（均已实测端点存活 + 源码核实密码学/备份实现）。差异仅在：演示模块（team/plans）无后端；两个声明未接线的端点（handoff/federation，实测 404 但无调用方）；候选列表需先触发合成；“新建项目”为纯本地交互。协作文档（COLLABORATION-2026-10-12.md）所述“base 分支缺 backup/Web3 模块、登录 UI 被移除”等问题在当前工作树均已存在实现，属分支差异而非缺失。
