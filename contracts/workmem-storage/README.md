# WorkMem Storage Solana Anchor Program

本智能合约负责 `llm-workmem` 在 Solana 区块链上的**去中心化存储付费结算与不可变工作记忆存证**。

---

## 核心设计与数据架构

1. **付费额度 PDA (`b"quota", user.key()`)**：
   - 记录用户购买的可用提交次数（`available_commits`）、累计提交次数（`total_commits`）与最后操作时间戳。
   - 支持两种支付通道：
     - `buy_quota_with_sol`: 开发者直接使用原生 SOL（Lamports）向国库支付购买额度（无摩擦首选）。
     - `buy_quota_with_tokens`: 使用生态 SPL Token 支付。

2. **不可变存证 PDA (`b"snapshot", user.key(), project_id, version.to_le_bytes()`)**：
   - 每次提交快照（`commit_snapshot`）扣减 1 次配额。
   - 链上不可篡改记录：
     - `project_id`: Git 根目录 SHA-256 派生识别码 (32 字节)
     - `version`: 快照版本号 (u32)
     - `snapshot_hash`: 工作记忆打包证据的 SHA-256 哈希 (32 字节)
     - `encrypted_uri`: 去中心化永久存储 URI（如 `ar://<tx_id>` 或 `ipfs://<cid>`）
     - `tool`: 产生该记忆的 AI Agent 标识（如 `Claude Code`, `AGY`, `Cursor`）
     - `timestamp`: 链上可信时间戳

---

## 一键部署至 Solana Devnet

### 前置要求
- Linux / macOS / WSL2 (Ubuntu)
- [Rust & Cargo](https://rustup.rs/) (>= 1.75)
- [Solana CLI](https://docs.solanalabs.com/cli/install) (>= 1.18)
- [Anchor CLI](https://www.anchor-lang.com/docs/installation) (0.30.1)

### 执行脚本
在当前目录运行：
```bash
chmod +x deploy.sh
./deploy.sh
```

### 手动部署流程
```bash
# 1. 切换到 Devnet
solana config set --url https://api.devnet.solana.com

# 2. 编译合约并获取 Program ID
anchor build
solana-keygen pubkey target/deploy/workmem_storage-keypair.json

# 3. 将输出的 Program ID 填入 src/lib.rs (declare_id!) 和 Anchor.toml
# 4. 重新构建并部署
anchor build
anchor deploy --provider.cluster devnet
```
