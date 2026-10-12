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
import nacl from 'tweetnacl';
import bs58 from 'bs58';
import { request } from './client';
import { walletNonce, walletVerify, type AuthResult } from './auth';
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
export const ONCHAIN_CHUNK_SIZE = 480;

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
  chunk_tx_hashes?: string[];
}

export interface MemoPayload {
  app: string;
  v: number;
  hash: string;
  uri: string;
  ts: number;
  n?: number;
}

export interface OnChainChunkPayload {
  app: 'llm-workmem-chunk';
  v: number;
  h: string;
  i: number;
  n: number;
  d: string;
}

export interface SolanaWalletProvider {
  isPhantom?: boolean;
  isConnected?: boolean;
  publicKey?: { toString(): string } | null;
  connect: (opts?: { onlyIfTrusted?: boolean }) => Promise<{ publicKey: { toString(): string } }>;
  signMessage: (msg: Uint8Array, encoding?: string) => Promise<{ signature: Uint8Array } | Uint8Array>;
  signTransaction?: (tx: Transaction) => Promise<Transaction>;
  signAllTransactions?: (txs: Transaction[]) => Promise<Transaction[]>;
  signAndSendTransaction?: (tx: Transaction) => Promise<{ signature: string }>;
}

/** 获取浏览器中安装的真实 Solana 钱包插件 (Phantom / Solflare) */
export function getSolanaWalletProvider(): SolanaWalletProvider | null {
  const w = window as unknown as {
    phantom?: { solana?: SolanaWalletProvider };
    solana?: SolanaWalletProvider;
    solflare?: SolanaWalletProvider;
  };
  return w.phantom?.solana ?? w.solana ?? w.solflare ?? null;
}

/** 确保钱包已真实拉起连接，返回钱包插件与真实公钥地址 */
export async function ensureWalletConnected(): Promise<{
  provider: SolanaWalletProvider;
  address: string;
  pubkey: PublicKey;
}> {
  const provider = getSolanaWalletProvider();
  if (!provider) {
    throw new Error('未检测到 Solana 钱包插件（如 Phantom 或 Solflare），请先在浏览器中安装并解锁钱包');
  }
  let address = provider.publicKey?.toString() || '';
  if (!address || !provider.isConnected) {
    const connected = await provider.connect();
    address = connected.publicKey.toString();
  }
  if (!address) {
    throw new Error('未能从钱包获取有效 Solana 公钥地址');
  }
  return { provider, address, pubkey: new PublicKey(address) };
}

/**
 * 真正拉起 Solana 钱包进行连接 + Nonce 挑战签名 + 服务端 Ed25519 验签绑定
 */
export async function connectAndAuthenticateWallet(email?: string): Promise<AuthResult & { address: string }> {
  const { provider, address } = await ensureWalletConnected();
  const { nonce } = await walletNonce(address);
  const msgBytes = new TextEncoder().encode(nonce);
  const sigRes = await provider.signMessage(msgBytes, 'utf8');
  const signature = 'signature' in sigRes ? sigRes.signature : sigRes;
  const pubkeyBytes = bs58.decode(address);
  if (!nacl.sign.detached.verify(msgBytes, signature, pubkeyBytes)) {
    throw new Error('本地 Ed25519 签名自检未通过');
  }
  const authRes = await walletVerify(address, nonce, bs58.encode(signature), email);
  localStorage.setItem('lwm_token', authRes.token);
  return { ...authRes, address };
}

export interface BackupBundleResponse {
  version: number;
  sha256: string;
  byte_size: number;
  tar_base64: string;
  included_dirs: string[];
  file_count: number;
  created_at: string;
  compact?: boolean;
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

/** 获取本地网关安全打包的快照（默认开启 compact 模式以便直接上链存储） */
export async function fetchBackupBundle(compact: boolean = true): Promise<BackupBundleResponse> {
  return request<BackupBundleResponse>(`/api/backup/bundle${compact ? '?compact=1' : ''}`);
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
  if (!walletAddress) return 0;
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
export async function requestDevnetAirdrop(walletAddress?: string): Promise<string> {
  const { address } = walletAddress
    ? { address: walletAddress }
    : await ensureWalletConnected();
  const conn = getSolanaConnection();
  const pubkey = new PublicKey(address);
  const signature = await conn.requestAirdrop(pubkey, 1 * LAMPORTS_PER_SOL);
  const latestBlockhash = await conn.getLatestBlockhash();
  await conn.confirmTransaction({
    signature,
    blockhash: latestBlockhash.blockhash,
    lastValidBlockHeight: latestBlockhash.lastValidBlockHeight,
  });
  return signature;
}

/** 真正唤起 Solana 钱包进行 Ed25519 消息签名以派生端到端加密密钥（严禁伪造 SHA-256 兜底） */
export async function signMessageWithWallet(message: string): Promise<Uint8Array> {
  const { provider } = await ensureWalletConnected();
  const msgBytes = new TextEncoder().encode(message);
  const res = await provider.signMessage(msgBytes, 'utf8');
  return 'signature' in res ? res.signature : res;
}

/**
 * 广播单笔 Solana SPL Memo 存证交易（强制通过已连接钱包真实签名广播）
 */
export async function broadcastMemoAttestation(
  _walletAddress: string,
  payload: MemoPayload
): Promise<{ txHash: string; slot: number; signerAddress: string }> {
  const config = await fetchSolanaConfig();
  const { provider, address, pubkey: payer } = await ensureWalletConnected();
  const conn = getSolanaConnection(config.rpc_url);
  const memoBytes = new TextEncoder().encode(JSON.stringify(payload));

  const memoInstruction = new TransactionInstruction({
    keys: [{ pubkey: payer, isSigner: true, isWritable: true }],
    programId: SPL_MEMO_PROGRAM_ID,
    data: memoBytes as unknown as Buffer,
  });

  const tx = new Transaction().add(memoInstruction);
  const latest = await conn.getLatestBlockhash('confirmed');
  tx.recentBlockhash = latest.blockhash;
  tx.feePayer = payer;

  let signature = '';
  if (provider.signAndSendTransaction) {
    const res = await provider.signAndSendTransaction(tx);
    signature = res.signature;
  } else if (provider.signTransaction) {
    const signed = await provider.signTransaction(tx);
    signature = await conn.sendRawTransaction(signed.serialize());
  } else {
    throw new Error('当前钱包不支持交易签名与广播');
  }

  const conf = await conn.confirmTransaction(
    {
      signature,
      blockhash: latest.blockhash,
      lastValidBlockHeight: latest.lastValidBlockHeight,
    },
    'confirmed'
  );
  return { txHash: signature, slot: conf.context.slot, signerAddress: address };
}

/**
 * 将 AES-256-GCM 加密后的 Agent Memory 密文直接分片写入 Solana Devnet 链上交易 (SPL Memo)
 */
export async function broadcastEncryptedMemoryOnSolana(
  packedCiphertextBase64: string,
  snapshotHash: string,
  version: number = 1,
  fallbackUri?: string
): Promise<{
  txHash: string;
  slot: number;
  chunkTxHashes: string[];
  signerAddress: string;
  onchainUri: string;
}> {
  const config = await fetchSolanaConfig();
  const { provider, address, pubkey: payer } = await ensureWalletConnected();
  const conn = getSolanaConnection(config.rpc_url);

  const chunks: string[] = [];
  for (let i = 0; i < packedCiphertextBase64.length; i += ONCHAIN_CHUNK_SIZE) {
    chunks.push(packedCiphertextBase64.slice(i, i + ONCHAIN_CHUNK_SIZE));
  }

  const hashPrefix = snapshotHash.slice(0, 16);
  const latest = await conn.getLatestBlockhash('confirmed');

  const chunkTxs: Transaction[] = chunks.map((chunkData, idx) => {
    const chunkPayload: OnChainChunkPayload = {
      app: 'llm-workmem-chunk',
      v: 1,
      h: hashPrefix,
      i: idx,
      n: chunks.length,
      d: chunkData,
    };
    const ix = new TransactionInstruction({
      keys: [{ pubkey: payer, isSigner: true, isWritable: true }],
      programId: SPL_MEMO_PROGRAM_ID,
      data: new TextEncoder().encode(JSON.stringify(chunkPayload)) as unknown as Buffer,
    });
    const tx = new Transaction().add(ix);
    tx.recentBlockhash = latest.blockhash;
    tx.feePayer = payer;
    return tx;
  });

  const manifestPayload: MemoPayload = {
    app: 'llm-workmem',
    v: version,
    hash: snapshotHash,
    n: chunks.length,
    uri: fallbackUri || `solana://devnet/memo/${hashPrefix}`,
    ts: Date.now(),
  };
  const manifestIx = new TransactionInstruction({
    keys: [{ pubkey: payer, isSigner: true, isWritable: true }],
    programId: SPL_MEMO_PROGRAM_ID,
    data: new TextEncoder().encode(JSON.stringify(manifestPayload)) as unknown as Buffer,
  });
  const manifestTx = new Transaction().add(manifestIx);
  manifestTx.recentBlockhash = latest.blockhash;
  manifestTx.feePayer = payer;

  const chunkTxHashes: string[] = [];
  let manifestSig = '';

  // 优先使用 signAllTransactions 一次性拉起钱包完成所有分片与主存证签名
  if (provider.signAllTransactions) {
    const allSigned = await provider.signAllTransactions([...chunkTxs, manifestTx]);
    const signedChunks = allSigned.slice(0, chunkTxs.length);
    const signedManifest = allSigned[allSigned.length - 1];

    for (const stx of signedChunks) {
      const sig = await conn.sendRawTransaction(stx.serialize(), { skipPreflight: false });
      chunkTxHashes.push(sig);
    }
    manifestSig = await conn.sendRawTransaction(signedManifest.serialize(), { skipPreflight: false });
  } else if (provider.signAndSendTransaction) {
    for (const ctx of chunkTxs) {
      const res = await provider.signAndSendTransaction(ctx);
      chunkTxHashes.push(res.signature);
    }
    const mRes = await provider.signAndSendTransaction(manifestTx);
    manifestSig = mRes.signature;
  } else {
    throw new Error('当前 Solana 钱包不支持交易签名');
  }

  const conf = await conn.confirmTransaction(
    {
      signature: manifestSig,
      blockhash: latest.blockhash,
      lastValidBlockHeight: latest.lastValidBlockHeight,
    },
    'confirmed'
  );

  const onchainUri = `solana://devnet/tx/${manifestSig}`;
  return {
    txHash: manifestSig,
    slot: conf.context.slot,
    chunkTxHashes,
    signerAddress: address,
    onchainUri,
  };
}

/**
 * 直接从 Solana Devnet 区块链交易 (SPL Memo 分片) 中拉取并重组加密的 Agent Memory 密文
 */
export async function fetchEncryptedMemoryFromSolanaChain(
  walletAddress: string,
  expectedHash: string,
  chunkTxHashes?: string[]
): Promise<string | null> {
  try {
    const config = await fetchSolanaConfig();
    const conn = getSolanaConnection(config.rpc_url);
    const hashPrefix = expectedHash.slice(0, 16);
    const chunkMap = new Map<number, string>();
    let totalExpected = 0;

    const tryParseMemoString = (rawMemo: string) => {
      const clean = rawMemo.replace(/^\[\d+\]\s*/, '').trim();
      try {
        const obj = JSON.parse(clean);
        if (obj && obj.app === 'llm-workmem-chunk' && obj.h === hashPrefix && typeof obj.i === 'number') {
          chunkMap.set(obj.i, String(obj.d || ''));
          if (typeof obj.n === 'number' && obj.n > 0) {
            totalExpected = obj.n;
          }
        }
      } catch {
        // 忽略非 JSON Memo
      }
    };

    // 1. 若已知分片交易哈希列表，直接按交易哈希从 Solana RPC 读取
    if (chunkTxHashes && chunkTxHashes.length > 0) {
      const parsedTxs = await conn.getParsedTransactions(chunkTxHashes, {
        maxSupportedTransactionVersion: 0,
        commitment: 'confirmed',
      });
      for (const ptx of parsedTxs) {
        if (!ptx?.transaction?.message?.instructions) continue;
        for (const ix of ptx.transaction.message.instructions) {
          if ('parsed' in ix && typeof ix.parsed === 'string') {
            tryParseMemoString(ix.parsed);
          }
        }
      }
    }

    // 2. 通过钱包地址扫描 Solana 账本历史签名列表中的 Memo
    if ((totalExpected === 0 || chunkMap.size < totalExpected) && walletAddress) {
      const pubkey = new PublicKey(walletAddress);
      const sigs = await conn.getSignaturesForAddress(pubkey, { limit: 50 }, 'confirmed');
      const sigsToFetch: string[] = [];
      for (const s of sigs) {
        if (s.memo && s.memo.includes(hashPrefix)) {
          tryParseMemoString(s.memo);
          sigsToFetch.push(s.signature);
        }
      }
      if ((totalExpected === 0 || chunkMap.size < totalExpected) && sigsToFetch.length > 0) {
        const parsedTxs = await conn.getParsedTransactions(sigsToFetch, {
          maxSupportedTransactionVersion: 0,
          commitment: 'confirmed',
        });
        for (const ptx of parsedTxs) {
          if (!ptx?.transaction?.message?.instructions) continue;
          for (const ix of ptx.transaction.message.instructions) {
            if ('parsed' in ix && typeof ix.parsed === 'string') {
              tryParseMemoString(ix.parsed);
            }
          }
        }
      }
    }

    if (totalExpected > 0 && chunkMap.size === totalExpected) {
      const ordered: string[] = [];
      for (let i = 0; i < totalExpected; i++) {
        const part = chunkMap.get(i);
        if (part === undefined) return null;
        ordered.push(part);
      }
      return ordered.join('');
    }
  } catch (err) {
    console.warn('从 Solana Devnet 账本直接读取加密记忆分片失败:', err);
  }
  return null;
}

/**
 * 执行完整的端到端加密与 Solana Devnet 链上真实存储流程：
 * 1. 确保钱包已真实连接并获取公钥
 * 2. GET /api/backup/bundle?compact=1 获取核心记忆归档
 * 3. 唤起钱包 Ed25519 签名派生 AES-256-GCM 密钥并加密归档
 * 4. 将加密密文分片直接广播至 Solana Devnet 区块链 (SPL Memo 交易组)
 * 5. 同步上传去中心化冗余镜像并向网关登记链上真实存证
 */
export async function executeColdBackup(
  _walletAddress: string,
  projectId: string,
  version: number = 1
): Promise<{ attestation: SolanaAttestation; storageUri: string; bundleHash: string }> {
  const { address: realWallet } = await ensureWalletConnected();

  // 1. 获取网关紧凑打包
  const bundle = await fetchBackupBundle(true);

  // 2. 真实唤起钱包签名派生密钥
  const seedPrefix = bundle.sha256.slice(0, 8);
  const signPrompt = `Sign to derive LLM-WorkMem backup encryption key [${seedPrefix}]`;
  const signature = await signMessageWithWallet(signPrompt);

  // 3. 客户端浏览器本地 AES-256-GCM 加密
  const key = await deriveKeyFromSignature(signature);
  const plainBytes = base64ToUint8Array(bundle.tar_base64);
  const encrypted = await encryptBytes(plainBytes, key);

  // 4. 辅助上传至 IPFS / 加密金库
  const storageRes = await uploadEncryptedSnapshot(encrypted.packedBase64, bundle.sha256, realWallet);

  // 5. 将加密后的 Agent Memory 密文直接写入 Solana Devnet 区块链
  const { txHash, slot, chunkTxHashes, onchainUri } = await broadcastEncryptedMemoryOnSolana(
    encrypted.packedBase64,
    bundle.sha256,
    version,
    storageRes.uri
  );

  // 6. 向网关登记链上存证（开启 RPC 链上真实交易核验）
  const attestation = await request<SolanaAttestation>('/api/solana/commit', {
    method: 'POST',
    body: JSON.stringify({
      wallet: realWallet,
      event_id: `backup-${bundle.sha256.slice(0, 12)}`,
      project_id: projectId,
      version,
      snapshot_hash: bundle.sha256,
      tx_hash: txHash,
      slot,
      chunk_tx_hashes: chunkTxHashes,
      tool: 'LWM-Web3',
      verify_rpc: true,
    }),
  });

  attestation.storage_uri = onchainUri;
  attestation.chunk_tx_hashes = chunkTxHashes;
  return { attestation, storageUri: onchainUri, bundleHash: bundle.sha256 };
}

/**
 * 执行完整的端到端解密还原流程：
 * 1. 优先直接从 Solana Devnet 区块链分片交易提取加密记忆（若无链上分片则从去中心化网关拉取）
 * 2. 唤起钱包签名派生解密密钥
 * 3. 本地解密密文为原始 tar.gz
 * 4. POST /api/backup/restore 验证 SHA-256 哈希与安全解包覆盖
 */
export async function executeColdRestore(
  storageUri: string,
  expectedHash: string,
  walletAddress?: string,
  chunkTxHashes?: string[]
): Promise<BackupRestoreResponse> {
  const { address: realWallet } = await ensureWalletConnected();
  const targetWallet = walletAddress || realWallet;

  // 1. 优先从 Solana Devnet 链上交易直接读取密文
  let packedBase64 = await fetchEncryptedMemoryFromSolanaChain(
    targetWallet,
    expectedHash,
    chunkTxHashes
  );
  if (!packedBase64) {
    packedBase64 = await downloadEncryptedSnapshot(storageUri);
  }
  const packedBytes = base64ToUint8Array(packedBase64);

  // 2. 真实唤起钱包签名派生解密密钥
  const seedPrefix = expectedHash.slice(0, 8);
  const signPrompt = `Sign to derive LLM-WorkMem backup encryption key [${seedPrefix}]`;
  const signature = await signMessageWithWallet(signPrompt);

  // 3. 浏览器本地 AES-256-GCM 解密
  const key = await deriveKeyFromSignature(signature);
  const decryptedBytes = await decryptBytes(packedBytes, key);
  const tarBase64 = uint8ArrayToBase64(decryptedBytes);

  // 4. 发送网关执行 SHA-256 校验与安全原子替换
  return restoreBackupBundle(tarBase64, expectedHash);
}

/**
 * 购买上链存储配额 (真实拉起钱包签名原生 SOL 转账 + Anchor 指令并在服务端通过 RPC 核验交易)
 */
export async function purchaseStorageQuota(
  _walletAddress: string,
  tokenAmount: number = 10,
  quotaToAdd: number = 10
): Promise<{ quota: WalletQuota; txHash: string; explorerUrl: string }> {
  const config = await fetchSolanaConfig();
  const { provider, address: realWallet, pubkey: payer } = await ensureWalletConnected();

  let signature = '';
  try {
    const conn = getSolanaConnection(config.rpc_url);
    const treasury = new PublicKey(config.treasury_pubkey);

    const tx = new Transaction().add(
      SystemProgram.transfer({
        fromPubkey: payer,
        toPubkey: treasury,
        lamports: Math.floor(0.01 * LAMPORTS_PER_SOL),
      })
    );

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
      // Devnet 上若未部署自定义合约程序，SystemProgram.transfer 原生转账真实执行并由后端 RPC 核验
    }

    const latest = await conn.getLatestBlockhash('confirmed');
    tx.recentBlockhash = latest.blockhash;
    tx.feePayer = payer;

    if (provider.signAndSendTransaction) {
      const res = await provider.signAndSendTransaction(tx);
      signature = res.signature;
    } else if (provider.signTransaction) {
      const signed = await provider.signTransaction(tx);
      signature = await conn.sendRawTransaction(signed.serialize());
    } else {
      throw new Error('当前钱包不支持交易签名');
    }

    await conn.confirmTransaction(
      {
        signature,
        blockhash: latest.blockhash,
        lastValidBlockHeight: latest.lastValidBlockHeight,
      },
      'confirmed'
    );
  } catch (txErr) {
    console.error('支付交易失败:', txErr);
    throw new Error(`Solana 支付交易失败或被用户取消: ${(txErr as Error).message}`);
  }

  const res = await request<{ quota: WalletQuota; transaction: { explorer_url: string } }>(
    '/api/solana/purchase',
    {
      method: 'POST',
      body: JSON.stringify({
        wallet: realWallet,
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

/** 将单条工作记忆事件直接固化至 Solana Devnet 链上 */
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
    uri: `solana://devnet/memo/${snapshotHash.slice(0, 16)}`,
    ts: Date.now(),
  };
  const { txHash, slot, signerAddress } = await broadcastMemoAttestation(walletAddress, memoPayload);

  return request<SolanaAttestation>('/api/solana/commit', {
    method: 'POST',
    body: JSON.stringify({
      wallet: signerAddress,
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
 * 跨设备链上记忆找回：直接从 Solana Devnet 账本或网关拉取指定钱包的最新工作记忆快照
 */
export async function fetchLatestWalletSnapshot(
  walletAddress: string,
  projectId?: string
): Promise<SolanaAttestation | null> {
  // 1. 优先直接从 Solana Devnet 账本查询最新链上存证
  try {
    const config = await fetchSolanaConfig();
    const conn = getSolanaConnection(config.rpc_url);
    const pubkey = new PublicKey(walletAddress);
    const sigs = await conn.getSignaturesForAddress(pubkey, { limit: 30 }, 'confirmed');

    for (const s of sigs) {
      if (s.memo && s.memo.includes('"app":"llm-workmem"')) {
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
              storage_uri: parsed.uri || `solana://devnet/tx/${s.signature}`,
            };
          }
        } catch {
          // 非主存证 JSON memo，继续
        }
      }
    }
  } catch (chainErr) {
    console.warn('从 Solana RPC 拉取链上记录受限:', chainErr);
  }

  // 2. 尝试从网关存证记录读取
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
    // 忽略
  }

  return null;
}

/**
 * 跨设备一键还原：真实连接钱包后从 Solana Devnet 链上自动定位快照与分片密文，钱包签名解密并复原记忆
 */
export async function executeCrossDeviceRestoreFromChain(
  walletAddress?: string,
  projectId?: string
): Promise<{ restored: BackupRestoreResponse; attestation: SolanaAttestation }> {
  const { address: realWallet } = await ensureWalletConnected();
  const targetWallet = walletAddress || realWallet;
  const att = await fetchLatestWalletSnapshot(targetWallet, projectId);
  if (!att) {
    throw new Error('未在 Solana Devnet 链上找到该钱包关联的任何工作记忆存证');
  }
  const uri = att.storage_uri || `solana://devnet/tx/${att.tx_hash}`;
  const restored = await executeColdRestore(uri, att.snapshot_hash, targetWallet, att.chunk_tx_hashes);
  return { restored, attestation: att };
}
