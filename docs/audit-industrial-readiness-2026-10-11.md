# LLM-WorkMem 工业级成熟度审计报告

**日期**：2026-10-11
**审计范围**：`lwm/`（Python 后端 76 模块）、`web/src/`（React 前端）、`mcp/`、`adapters/`、`tests/`
**审计问题**：系统是否真正彻底告别 Mock 与演示占位符，形成具备并发防冲突、端到端密文冷备与链上存证锚定的工业级多 Agent 工作记忆底座？

---

## 结论：❌ 尚未达到。三个维度中仅"并发防冲突（数据面）"接近工业级，其余两项存在阻断性缺陷。

| 维度 | 评级 | 一句话结论 |
|---|---|---|
| Mock/演示占位符清除 | ⚠️ 后端干净，**前端残留静默降级路径** | `solana.ts` 在钱包广播失败时伪造 tx_hash 且不报错 |
| 并发防冲突 | ✅ 数据面真实现 / ⚠️ 租约模块自身有竞态 | O_EXCL+PID 检测+平台锁+原子写均为真实实现 |
| 端到端密文冷备 | ⚠️ 链路真实但密钥派生可被降级 | AES-256-GCM 前端真实现，fallback 种子可预测 |
| 链上存证锚定 | ❌ **仅在浏览器钱包场景真实** | 后端从不校验 tx_hash，slot/program_id 为占位值 |

---

## 一、Mock / 演示占位符扫描

**干净的部分**：全仓 `mock|stub|fake|placeholder` 扫描，生产 Python 代码（`lwm/`、`mcp/`、`adapters/`）零命中。所有 mock/fake/stub 均位于 `tests/`（合法测试夹具）；`cbmem_source.py` 中的 `<TODO>` 是用作 TODO 检测器的搜索词，非占位符。

**残留问题（web/src/api/solana.ts）**：

1. **伪造链上凭据（严重）** — `broadcastMemoAttestation()` 第 223-232 行：钱包广播失败时 `catch` 仅 `console.warn`，随后静默返回
   `txHash: 'memo_' + <32字节随机数>` + `slot: 298105200 + random(500)`。
   该伪凭据会被 `POST /api/solana/commit` 登记进后端并扣减配额——**广播失败的"上链"与真实上链在系统内不可区分**，违反 Fail-Closed 原则。
2. **可预测密钥种子** — `signMessageWithWallet()` 第 178-180 行：无钱包插件时以 `SHA-256(消息文本)` 作确定性种子派生 AES 密钥（注释自称"测试种子"），密文可被任何知道消息文本的人解密。
3. **适配层"空则回退 mock"**（`web/src/api/adapters/*`、`web/src/mocks/`）：候选/事件/团队/订阅等 6 处空数据回退演示常量。作为展示策略可接受，但需在 UI 明确标注"演示数据"，当前仅 id 带 `demo-` 前缀。

---

## 二、并发防冲突（数据面合格，租约模块有缺陷）

**真实实现（已核实源码）**：

- `lwm/lockfile.py`：`O_CREAT|O_EXCL` 原子建锁（防 read-then-create 竞态）+ PID 存活检测 + stale 锁清理重试；`ingest_lock` / `cycle_lock` 已接入 `ingest.py`、`runner.py`、`supervisor.py`、`memory_compiler.py` 全部写路径，`LockBusyError` 显式拒绝。
- `lwm/capability_proof.py`：跨平台文件锁（POSIX `fcntl.flock` / Windows `msvcrt.locking`，已修复 Windows 兼容）。
- 原子写贯穿全链：`inbox.py`、`handoff.py`、`cycle_receipt.py`、`memory_federation.py`、`harvest.py`、`behavior_contract.py` 均为 temp + `os.replace`。
- `lwm/conflict.py`：跨项目决策冲突检测（写 `wiki/review/conflict-<date>.md` 供人审）。

**缺陷**：

- **`lwm/lease.py` 自身存在 TOCTOU 竞态**：`acquire_lease` / `release_lease` 是无锁的读-改-写（`_load_leases` → 修改 → `_save_leases`，后者直接 `write_text` 非原子）。两个 Agent 并发申请租约时会双双读到"无租约"而同时获胜——一个防冲突模块自身不防冲突。
- `lockfile` 只保护 ingest/cycle，`lease.py`、`solana_storage.py`、`webauth.py` 的 JSON 状态写入均未纳入锁保护。

---

## 三、端到端密文冷备（链路真实，两处弱点）

**真实部分**：

- 前端 `web/src/utils/crypto.ts`：WebCrypto `AES-256-GCM`（12 字节随机 IV 前置打包）+ `PBKDF2(100k 轮, SHA-256)` 从钱包签名派生密钥——标准实现。
- `web/src/api/storage.ts`：Arweave/Irys 内容寻址上传 + "Local Encrypted Vault" 离线自适应（localStorage 缓存密文）。
- 后端 `lwm/backup.py`：tar.gz 打包 + SHA-256 强校验 + Zip-Slip/软链接路径审计 + 临时目录解压后原子覆盖，设计上加密放在客户端（明文 tar.gz 不出端即可接受）。
- 完整流程 `executeColdBackup()`：bundle → 签名派生密钥 → 本地加密 → 上传 `ar://<id>` → SPL Memo 上链 → 网关登记，六步链路齐备。

**弱点**：

1. 密钥派生 fallback（见第一节第 2 条）使"端到端"在无钱包环境退化为"可预测对称加密"。
2. Local Encrypted Vault 用 localStorage——同源任意 XSS 即可窃取密文，仅够开发联调，不达工业级。
3. 加密/还原链路**无任何自动化测试**（`tests/test_backup.py` 只测明文 tar 的哈希与还原）。

---

## 四、链上存证锚定（最薄弱环节）

- **真实路径仅一条**：浏览器 + Solana 钱包插件 + devnet RPC 可达时，`solana.ts` 走 `TransactionInstruction`(SPL Memo) → `signAndSendTransaction` → `confirmTransaction` → 返回真实 signature/slot。这条路径是真的。
- **后端零验证**：`lwm/solana_storage.py::record_attestation` 只把客户端传来的 `tx_hash` 写进本地 JSON，从不向 RPC 反查签名是否存在、memo 内容是否匹配 snapshot_hash；`slot` 参数缺省硬编码 `298104520`；`program_id`/`token_mint` 是全 1 的占位地址（非已部署程序）。
- **配额/计费为本地账本**：购买、扣减全在 `state/solana_state.json`，与链上转账无勾稽。
- 结果：任何能调网关的进程都可以用编造的 tx_hash 换取"链上不可变存证"记录。**当前实质是"本地 JSON 存证台账"，而非链上锚定。**

---

## 五、通往工业级的差距清单（按优先级）

| # | 修复项 | 位置 | 优先级 |
|---|---|---|---|
| 1 | 删除伪造 txHash fallback：广播失败必须抛错，禁止登记伪凭据 | `web/src/api/solana.ts:223-232` | P0 |
| 2 | 后端登记前向 RPC 校验 tx：签名存在 + memo 含 snapshot_hash + slot 匹配 | `lwm/solana_storage.py` / `gateway.py` | P0 |
| 3 | `lease.py` 写入改原子 + 纳入 `state/locks/` 锁保护，消除 TOCTOU | `lwm/lease.py` | P1 |
| 4 | 密钥派生移除确定性种子 fallback：无钱包时拒绝冷备而非降级 | `web/src/api/solana.ts:178-180` | P1 |
| 5 | 演示回退数据在 UI 显式标注"演示数据" | `web/src/api/adapters/*` | P1 |
| 6 | 为加密冷备 + 存证链路补 e2e 测试（含广播失败路径） | `tests/` | P1 |
| 7 | `solana_state.json` / `webauth.json` 写入原子化并纳入锁 | `lwm/solana_storage.py`, `webauth.py` | P2 |
| 8 | devnet → mainnet/专属集群，占位 program_id 换为真实部署 | `lwm/solana_storage.py` | P2 |

**验证方法说明**：本报告结论全部来自源码级核查（backup.py、solana_storage.py、solana.ts、crypto.ts、storage.ts、lockfile.py、lease.py、conflict.py、gateway.py 全文阅读）+ 全仓模式扫描，未运行链上交易实测（devnet 上链需浏览器钱包签名，超出本次静态审计范围）。
