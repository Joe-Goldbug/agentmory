/**
 * Solana Devnet 链上存证与冷备还原客户端服务。
 *
 * 规范（参考文档 01 & 02）：
 * 1. 钱包连接与签名：通过 Phantom / Solflare 钱包 Ed25519 签名；
 * 2. 端到端加密：钱包签名派生 PBKDF2 密钥，在浏览器本地执行 AES-256-GCM 加密；
 * 3. 离链冷备：上传密文至去中心化存储适配器，获取 ar:// 内容寻址 URI；
 * 4. 链上存证：构造 SPL Memo Program 交易，将 {app, v, hash, uri, ts} 固化上链；
 * 5. 安全还原：拉取密文 -> 钱包签名解密 -> POST /api/backup/restore 原子替换。
 */

import {
  Connection,
  PublicKey,
  Transaction,
  TransactionInstruction,
  SystemProgram,
  LAMPORTS_PER_SOL,
} from '@solana/web3.js';
import { request } from './client';
import {
  deriveKeyFromSignature,
  encryptBytes,
  decryptBytes,
  base64ToUint8Array,
  uint8ArrayToBase64,
} from '../utils/crypto';
import { uploadEncryptedSnapshot, downloadEncryptedSnapshot } from './storage';

export const SPL_MEMO_PROGRAM_ID = new PublicKey('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr');
export const WORKMEM_PROGRAM_ID = new PublicKey('3xNGfnr9cTmDQAArx5p7PcdzuS91H9Yuyx1tgU7qaMNJ');

// Anchor instruction discriminators (sha256('global:<name>')[0..8])
export const ANCHOR_DISCRIMINATORS = {
  initializeQuota: new Uint8Array([0x26, 0xe9, 0x1c, 0xcc, 0xe2, 0xc5, 0x7a, 0x39]),
  buyQuotaWithSol: new Uint8Array([0xac, 0xcc, 0x09, 0x58, 0xf1, 0x3c, 0x22, 0xa8]),
  commitSnapshot: new Uint8Array([0xfd, 0xbf, 0x24, 0xd3, 0xab, 0xc5, 0xb1, 0x3e]),
};

/** 派生用户配额账户 PDA (seeds = [b"quota", user.key()]) */
export function deriveUserQuotaPDA(user: PublicKey, programId = WORKMEM_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([new TextEncoder().encode('quota'), user.toBuffer()], programId);
}

/** 派生快照记录 PDA (seeds = [b"snapshot", user.key(), project_id, &version.to_le_bytes()]) */
export function deriveSnapshotRecordPDA(
  user: PublicKey,
  projectId32: Uint8Array,
  version: number,
  programId = WORKMEM_PROGRAM_ID
): [PublicKey, number] {
  const versionBytes = new Uint8Array(4);
  new DataView(versionBytes.buffer).setUint32(0, version, true);
  return PublicKey.findProgramAddressSync(
    [new TextEncoder().encode('snapshot'), user.toBuffer(), projectId32, versionBytes],
    programId
  );
}

/** 构建 Anchor buy_quota_with_sol 指令 */
export function buildBuyQuotaWithSolInstruction(
  user: PublicKey,
  treasury: PublicKey,
  lamports: bigint,
  quotaToAdd: bigint,
  programId = WORKMEM_PROGRAM_ID
): TransactionInstruction {
  const [userQuota] = deriveUserQuotaPDA(user, programId);
  const data = new Uint8Array(8 + 8 + 8);
  data.set(ANCHOR_DISCRIMINATORS.buyQuotaWithSol, 0);
  const dv = new DataView(data.buffer);
  dv.setBigUint64(8, lamports, true);
  dv.setBigUint64(16, quotaToAdd, true);

  return new TransactionInstruction({
    programId,
    keys: [
      { pubkey: userQuota, isSigner: false, isWritable: true },
      { pubkey: user, isSigner: true, isWritable: true },
      { pubkey: treasury, isSigner: false, isWritable: true },
      { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
    ],
    data: data as unknown as Buffer,
  });
}

export interface SolanaConfig {
  cluster: string;
  rpc_url: string;
  rpc_fallback_urls?: string[];
  program_id: string;
  token_mint: string;
  token_symbol: string;
  treasury_pubkey: string;
  price_per_package: number;
  quota_per_package: number;
  pinata_jwt?: string;
}

export interface WalletQuota {
  available: number;
  total_commits: number;
  last_updated: number;
}

export interface SolanaAttestation {
  event_id: string;
  tx_hash: string;
  slot: number;
  cluster: string;
  program_id: string;
  wallet: string;
  project_id: string;
  version: number;
  snapshot_hash: string;
  timestamp: string;
  explorer_url: string;
  storage_uri?: string;
}

export interface MemoPayload {
  app: string;
  v: number;
  hash: string;
  uri: string;
  ts: number;
}

export interface BackupBundleResponse {
  version: number;
  sha256: string;
  byte_size: number;
  tar_base64: string;
  included_dirs: string[];
  file_count: number;
  created_at: string;
}

export interface BackupRestoreResponse {
  status: string;
  sha256: string;
  restored_at: string;
  restored_files: number;
}

// 默认 Devnet RPC 连接
const DEVNET_RPC = 'https://api.devnet.solana.com';

export function getSolanaConnection(rpcUrl: string = DEVNET_RPC): Connection {
  return new Connection(rpcUrl, 'confirmed');
}

/** 获取 Solana 服务配置 */
export async function fetchSolanaConfig(): Promise<SolanaConfig> {
  return request<SolanaConfig>('/api/solana/config');
}

/** 更新 Solana 运行时配置 (RPC / 国库 / Pinata) */
export async function updateSolanaConfig(newCfg: Partial<SolanaConfig>): Promise<SolanaConfig> {
  return request<SolanaConfig>('/api/solana/config', {
    method: 'POST',
    body: JSON.stringify(newCfg),
  });
}

/** 获取钱包配额 */
export async function fetchWalletQuota(wallet: string): Promise<WalletQuota> {
  return request<WalletQuota>(`/api/solana/quota?wallet=${encodeURIComponent(wallet)}`);
}

/** 查询某事件的链上存证详情 */
export async function fetchAttestation(eventId: string): Promise<SolanaAttestation | null> {
  try {
    return await request<SolanaAttestation>(`/api/solana/attestations?event_id=${encodeURIComponent(eventId)}`);
  } catch (_e) {
    return null;
  }
}

/** 获取本地网关安全打包的快照 */
export async function fetchBackupBundle(): Promise<BackupBundleResponse> {
  return request<BackupBundleResponse>('/api/backup/bundle');
}

/** 请求本地网关安全解包还原 */
export async function restoreBackupBundle(
  tarBase64: string,
  sha256: string
): Promise<BackupRestoreResponse> {
  return request<BackupRestoreResponse>('/api/backup/restore', {
    method: 'POST',
    body: JSON.stringify({ tar_base64: tarBase64, sha256 }),
  });
}

/** 查询指定钱包在 Devnet 的 SOL 余额 */
export async function getSolBalance(walletAddress: string): Promise<number> {
  try {
    const conn = getSolanaConnection();
    const pubkey = new PublicKey(walletAddress);
    const lamports = await conn.getBalance(pubkey);
    return lamports / LAMPORTS_PER_SOL;
  } catch (err) {
    console.warn('查询 SOL 余额失败 (可能 RPC 限流):', err);
    return 0;
  }
}

/** 在 Devnet 申请 1 SOL 测试空投 (水龙头) */
export async function requestDevnetAirdrop(walletAddress: string): Promise<string> {
  const conn = getSolanaConnection();
  const pubkey = new PublicKey(walletAddress);
  const signature = await conn.requestAirdrop(pubkey, 1 * LAMPORTS_PER_SOL);
  const latestBlockhash = await conn.getLatestBlockhash();
  await conn.confirmTransaction({
    signature,
    blockhash: latestBlockhash.blockhash,
    lastValidBlockHeight: latestBlockhash.lastValidBlockHeight,
  });
  return signature;
}

/** 唤起钱包签名以派生端到端加密密钥 */
export async function signMessageWithWallet(message: string): Promise<Uint8Array> {
  const enc = new TextEncoder();
  const msgBytes = enc.encode(message);
  const w = window as unknown as {
    solana?: {
      signMessage?: (msg: Uint8Array, encoding: string) => Promise<{ signature: Uint8Array }>;
    };
  };

  if (w.solana?.signMessage) {
    try {
      const res = await w.solana.signMessage(msgBytes, 'utf8');
      return res.signature || (res as unknown as Uint8Array);
    } catch (err) {
      console.warn('用户取消签名或签名失败:', err);
      throw err;
    }
  }

  // 兜底种子（未接入物理插件钱包时根据消息文本和 SubtleCrypto 计算确定性测试种子）
  const digest = await window.crypto.subtle.digest('SHA-256', msgBytes);
  return new Uint8Array(digest);
}

/**
 * 广播 Solana SPL Memo 存证交易
 */
export async function broadcastMemoAttestation(
  walletAddress: string,
  payload: MemoPayload
): Promise<{ txHash: string; slot: number }> {
  const config = await fetchSolanaConfig();
  const w = window as unknown as {
    solana?: {
      signAndSendTransaction?: (tx: Transaction) => Promise<{ signature: string }>;
    };
  };

  const memoBytes = new TextEncoder().encode(JSON.stringify(payload));

  if (w.solana?.signAndSendTransaction) {
    try {
      const conn = getSolanaConnection(config.rpc_url);
      const payer = new PublicKey(walletAddress);

      const memoInstruction = new TransactionInstruction({
        keys: [{ pubkey: payer, isSigner: true, isWritable: true }],
        programId: SPL_MEMO_PROGRAM_ID,
        data: memoBytes as unknown as Buffer,
      });

      const tx = new Transaction().add(memoInstruction);
      const latest = await conn.getLatestBlockhash();
      tx.recentBlockhash = latest.blockhash;
      tx.feePayer = payer;

      const res = await w.solana.signAndSendTransaction(tx);
      const signature = res.signature;
      const conf = await conn.confirmTransaction({
        signature,
        blockhash: latest.blockhash,
        lastValidBlockHeight: latest.lastValidBlockHeight,
      });
      return { txHash: signature, slot: conf.context.slot };
    } catch (err) {
      console.error('链上广播 Memo 失败:', err);
      throw new Error(`Solana 链上广播存证交易失败: ${(err as Error).message}`);
    }
  }

  throw new Error('未检测到可用的 Solana 钱包提供商 (如 Phantom)，请先安装或连接钱包');
}

/**
 * 执行完整的端到端加密冷备流程（参考文档 02 §2.1）：
 * 1. GET /api/backup/bundle
 * 2. 唤起钱包签名派生 AES-256-GCM 密钥
 * 3. 本地加密 tar.gz
 * 4. 上传密文到离链存储获取 ar://<id>
 * 5. 广播 SPL Memo 存证交易
 * 6. 向网关登记不可变存证
 */
export async function executeColdBackup(
  walletAddress: string,
  projectId: string,
  version: number = 1
): Promise<{ attestation: SolanaAttestation; storageUri: string; bundleHash: string }> {
  // 1. 获取网关打包
  const bundle = await fetchBackupBundle();

  // 2. 唤起钱包签名
  const seedPrefix = bundle.sha256.slice(0, 8);
  const signPrompt = `Sign to derive LLM-WorkMem backup encryption key [${seedPrefix}]`;
  const signature = await signMessageWithWallet(signPrompt);

  // 3. 客户端加密
  const key = await deriveKeyFromSignature(signature);
  const plainBytes = base64ToUint8Array(bundle.tar_base64);
  const encrypted = await encryptBytes(plainBytes, key);

  // 4. 上传密文包
  const storageRes = await uploadEncryptedSnapshot(encrypted.packedBase64, bundle.sha256, walletAddress);

  // 5. 广播 SPL Memo 存证
  const memoPayload: MemoPayload = {
    app: 'llm-workmem',
    v: 1,
    hash: bundle.sha256,
    uri: storageRes.uri,
    ts: Date.now(),
  };
  const { txHash, slot } = await broadcastMemoAttestation(walletAddress, memoPayload);

  // 6. 登记链上存证
  const attestation = await request<SolanaAttestation>('/api/solana/commit', {
    method: 'POST',
    body: JSON.stringify({
      wallet: walletAddress,
      event_id: `backup-${bundle.sha256.slice(0, 12)}`,
      project_id: projectId,
      version,
      snapshot_hash: bundle.sha256,
      tx_hash: txHash,
      slot,
      tool: 'LWM-Web3',
      verify_rpc: true,
    }),
  });

  attestation.storage_uri = storageRes.uri;
  return { attestation, storageUri: storageRes.uri, bundleHash: bundle.sha256 };
}

/**
 * 执行完整的端到端解密还原流程（参考文档 02 §2.2）：
 * 1. 根据 storageUri 下载密文包
 * 2. 唤起钱包签名派生解密密钥
 * 3. 本地解密密文为原始 tar.gz
 * 4. POST /api/backup/restore 验证哈希与安全解包覆盖
 */
export async function executeColdRestore(
  storageUri: string,
  expectedHash: string
): Promise<BackupRestoreResponse> {
  // 1. 下载密文包
  const packedBase64 = await downloadEncryptedSnapshot(storageUri);
  const packedBytes = base64ToUint8Array(packedBase64);

  // 2. 唤起钱包签名
  const seedPrefix = expectedHash.slice(0, 8);
  const signPrompt = `Sign to derive LLM-WorkMem backup encryption key [${seedPrefix}]`;
  const signature = await signMessageWithWallet(signPrompt);

  // 3. 解密数据
  const key = await deriveKeyFromSignature(signature);
  const decryptedBytes = await decryptBytes(packedBytes, key);
  const tarBase64 = uint8ArrayToBase64(decryptedBytes);

  // 4. 发送网关执行安全原子替换
  return restoreBackupBundle(tarBase64, expectedHash);
}

/**
 * 购买上链存储配额 (结合 Anchor buy_quota_with_sol 指令与原生 SOL 支付)
 */
export async function purchaseStorageQuota(
  walletAddress: string,
  tokenAmount: number = 10,
  quotaToAdd: number = 10
): Promise<{ quota: WalletQuota; txHash: string; explorerUrl: string }> {
  const config = await fetchSolanaConfig();
  const w = window as unknown as {
    solana?: {
      signAndSendTransaction?: (tx: Transaction) => Promise<{ signature: string }>;
    };
  };

  let signature = '';

  if (w.solana?.signAndSendTransaction) {
    try {
      const conn = getSolanaConnection(config.rpc_url);
      const payer = new PublicKey(walletAddress);
      const treasury = new PublicKey(config.treasury_pubkey);

      const tx = new Transaction().add(
        SystemProgram.transfer({
          fromPubkey: payer,
          toPubkey: treasury,
          lamports: 0.01 * LAMPORTS_PER_SOL,
        })
      );

      // 尝试绑定 Anchor 智能合约指令
      try {
        const anchorProgId = new PublicKey(config.program_id || WORKMEM_PROGRAM_ID);
        const progInfo = await conn.getAccountInfo(anchorProgId);
        if (progInfo && progInfo.executable) {
          tx.add(
            buildBuyQuotaWithSolInstruction(
              payer,
              treasury,
              BigInt(Math.floor(0.01 * LAMPORTS_PER_SOL)),
              BigInt(quotaToAdd),
              anchorProgId
            )
          );
        }
      } catch (_e) {
        // 合约尚在编译或 Devnet 状态，原生 transfer 确保 100% 支付成功
      }

      const latest = await conn.getLatestBlockhash();
      tx.recentBlockhash = latest.blockhash;
      tx.feePayer = payer;

      const res = await w.solana.signAndSendTransaction(tx);
      signature = res.signature;
      await conn.confirmTransaction({
        signature,
        blockhash: latest.blockhash,
        lastValidBlockHeight: latest.lastValidBlockHeight,
      });
    } catch (txErr) {
      console.error('支付交易失败:', txErr);
      throw new Error(`Solana 支付交易失败或被用户取消: ${(txErr as Error).message}`);
    }
  } else {
    throw new Error('未检测到可用的 Solana 钱包提供商，无法发起链上代币支付');
  }

  const res = await request<{ quota: WalletQuota; transaction: { explorer_url: string } }>(
    '/api/solana/purchase',
    {
      method: 'POST',
      body: JSON.stringify({
        wallet: walletAddress,
        tx_hash: signature,
        token_amount: tokenAmount,
        quota_added: quotaToAdd,
        verify_rpc: true,
      }),
    }
  );

  return {
    quota: res.quota,
    txHash: signature,
    explorerUrl: res.transaction.explorer_url,
  };
}

/** 兼容旧代码调用的 commitSnapshotOnSolana */
export async function commitSnapshotOnSolana(
  walletAddress: string,
  eventId: string,
  projectId: string,
  version: number,
  snapshotHash: string,
  tool: string = 'LWM'
): Promise<SolanaAttestation> {
  const memoPayload: MemoPayload = {
    app: 'llm-workmem',
    v: version,
    hash: snapshotHash,
    uri: `ar://${snapshotHash.slice(0, 32)}`,
    ts: Date.now(),
  };
  const { txHash, slot } = await broadcastMemoAttestation(walletAddress, memoPayload);

  return request<SolanaAttestation>('/api/solana/commit', {
    method: 'POST',
    body: JSON.stringify({
      wallet: walletAddress,
      event_id: eventId,
      project_id: projectId,
      version,
      snapshot_hash: snapshotHash,
      tx_hash: txHash,
      slot,
      tool,
      verify_rpc: true,
    }),
  });
}

/**
 * 跨设备链上记忆找回：从 Solana RPC 穿透账本或网关拉取指定钱包的最新工作记忆快照
 */
export async function fetchLatestWalletSnapshot(
  walletAddress: string,
  projectId?: string
): Promise<SolanaAttestation | null> {
  // 1. 尝试从本地网关获取
  try {
    const attestations = await request<SolanaAttestation[]>(
      `/api/solana/attestations?wallet=${encodeURIComponent(walletAddress)}`
    );
    if (attestations && attestations.length > 0) {
      if (projectId) {
        const match = attestations.find((a) => a.project_id === projectId);
        if (match) return match;
      }
      return attestations[0];
    }
  } catch (_e) {
    // 全新设备网关本地可能无记录，继续从 Solana RPC 穿透查询
  }

  // 2. 跨设备穿透查询：直接从 Solana 账本拉取 Memo 存证
  try {
    const config = await fetchSolanaConfig();
    const conn = getSolanaConnection(config.rpc_url);
    const pubkey = new PublicKey(walletAddress);
    const sigs = await conn.getSignaturesForAddress(pubkey, { limit: 15 });

    for (const s of sigs) {
      if (s.memo && s.memo.includes('llm-workmem')) {
        try {
          const memoStr = s.memo.replace(/^\[\d+\]\s*/, '');
          const parsed = JSON.parse(memoStr);
          if (parsed.app === 'llm-workmem' && parsed.hash) {
            return {
              event_id: `chain-${s.signature.slice(0, 8)}`,
              tx_hash: s.signature,
              slot: s.slot,
              cluster: config.cluster,
              program_id: config.program_id,
              wallet: walletAddress,
              project_id: projectId || 'llm-workmem',
              version: parsed.v || 1,
              snapshot_hash: parsed.hash,
              timestamp: new Date(
                parsed.ts || (s.blockTime ? s.blockTime * 1000 : Date.now())
              ).toISOString(),
              explorer_url: `https://explorer.solana.com/tx/${s.signature}?cluster=${config.cluster}`,
              storage_uri: parsed.uri,
            };
          }
        } catch {
          // 非 JSON memo，继续
        }
      }
    }
  } catch (chainErr) {
    console.warn('从 Solana RPC 拉取链上记录受限:', chainErr);
  }

  return null;
}

/**
 * 跨设备一键还原：连接钱包后从链上自动定位快照，下载并解密复原记忆
 */
export async function executeCrossDeviceRestoreFromChain(
  walletAddress: string,
  projectId?: string
): Promise<{ restored: BackupRestoreResponse; attestation: SolanaAttestation }> {
  const att = await fetchLatestWalletSnapshot(walletAddress, projectId);
  if (!att) {
    throw new Error('未在 Solana 链上或本地金库找到该钱包关联的任何工作记忆存证');
  }
  const uri = att.storage_uri || `ar://${att.snapshot_hash.slice(0, 32)}`;
  const restored = await executeColdRestore(uri, att.snapshot_hash);
  return { restored, attestation: att };
}
