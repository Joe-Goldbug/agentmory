#!/usr/bin/env bash
# ==============================================================================
# LLM-WorkMem Solana Devnet 合约构建与一键部署脚本
# 运行环境：Linux / macOS / WSL2 (Ubuntu)
# 依赖：Solana CLI (>= 1.18), Anchor CLI (0.30.1), Rust (>= 1.75)
# ==============================================================================

set -euo pipefail

echo "==> 1. 检查开发环境..."
command -v solana >/dev/null 2>&1 || { echo "错误: 未找到 solana CLI，请先安装: sh -c \"\$(curl -sSfL https://release.anza.xyz/stable/install)\""; exit 1; }
command -v anchor >/dev/null 2>&1 || { echo "错误: 未找到 anchor CLI，请先安装: cargo install --git https://github.com/coral-xyz/anchor avm --locked --force && avm install 0.30.1 && avm use 0.30.1"; exit 1; }

echo "==> 2. 配置 Solana 网络为 Devnet..."
solana config set --url https://api.devnet.solana.com

WALLET_PATH="${HOME}/.config/solana/id.json"
if [ ! -f "$WALLET_PATH" ]; then
    echo "==> 未找到默认钱包，正在创建测试钱包: $WALLET_PATH"
    mkdir -p "$(dirname "$WALLET_PATH")"
    solana-keygen new --no-bip39-passphrase -o "$WALLET_PATH"
fi

PUBKEY=$(solana-keygen pubkey "$WALLET_PATH")
echo "钱包地址: $PUBKEY"

BALANCE=$(solana balance "$PUBKEY" | awk '{print $1}')
echo "当前 Devnet 余额: $BALANCE SOL"

if (( $(echo "$BALANCE < 2.0" | bc -l) )); then
    echo "==> 申请 Devnet 2 SOL 测试空投..."
    solana airdrop 2 "$PUBKEY" || echo "警告: 空投请求未直接成功，若余额充足可继续"
fi

echo "==> 3. 编译 Anchor 合约 (生成 target/deploy/workmem_storage.so)..."
anchor build

PROGRAM_KEYPAIR="target/deploy/workmem_storage-keypair.json"
if [ ! -f "$PROGRAM_KEYPAIR" ]; then
    echo "错误: 未找到编译生成的 program keypair: $PROGRAM_KEYPAIR"
    exit 1
fi

PROGRAM_ID=$(solana-keygen pubkey "$PROGRAM_KEYPAIR")
echo "=========================================================="
echo "🎯 合约 Program ID: $PROGRAM_ID"
echo "=========================================================="

echo "==> 4. 同步 Program ID 到 lib.rs 与 Anchor.toml..."
sed -i.bak "s/declare_id!(\"[^\"]*\")/declare_id!(\"$PROGRAM_ID\")/g" src/lib.rs && rm -f src/lib.rs.bak
sed -i.bak "s/workmem_storage = \"[^\"]*\"/workmem_storage = \"$PROGRAM_ID\"/g" Anchor.toml && rm -f Anchor.toml.bak

echo "==> 5. 重新生成并部署..."
anchor build
anchor deploy --provider.cluster devnet

echo "=========================================================="
echo "✅ 部署成功！"
echo "Explorer: https://explorer.solana.com/address/${PROGRAM_ID}?cluster=devnet"
echo "请将该 Program ID 更新到前端与后端的配置中。"
echo "=========================================================="
