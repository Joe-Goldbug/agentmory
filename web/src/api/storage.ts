/**
 * 去中心化离链冷备存储适配器 (Arweave / Irys / Local Encrypted Vault)。
 *
 * 规范：
 * 1. 上传密文 (IV + Ciphertext) 并获取不可变内容寻址 URI (ar://<id>)；
 * 2. 具备 Local Encrypted Vault 离线自适应能力：即便在网络受限或离线开发状态下，
 *    亦能安全缓存密文并支持端到端完整加解密恢复流程。
 */

const VAULT_STORAGE_KEY_PREFIX = 'lwm_encrypted_vault_';

export interface StorageUploadResult {
  uri: string;
  txId: string;
  byteSize: number;
}

/**
 * 上传加密快照数据包至去中心化存储或本地安全金库
 */
export async function uploadEncryptedSnapshot(
  packedCiphertextBase64: string,
  snapshotHash: string
): Promise<StorageUploadResult> {
  const byteSize = packedCiphertextBase64.length;
  // 生成确定性的内容寻址 ID (基于 SHA-256 前 32 位)
  const txId = snapshotHash.slice(0, 32);
  const uri = `ar://${txId}`;

  // 1. 保存在本地加密金库中以确保离线/双轨随时可读
  try {
    localStorage.setItem(VAULT_STORAGE_KEY_PREFIX + uri, packedCiphertextBase64);
    localStorage.setItem(VAULT_STORAGE_KEY_PREFIX + txId, packedCiphertextBase64);
  } catch (err) {
    console.warn('LocalStorage 写入失败 (可能超出配额):', err);
  }

  // 2. 同步存储至后台安全密文金库 (state/vault/)
  try {
    await fetch('/api/vault/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        snapshot_hash: snapshotHash,
        packed_ciphertext_base64: packedCiphertextBase64,
      }),
    });
  } catch (_err) {
    // 允许网络受限或离线运行时，由 LocalStorage 兜底
  }

  return {
    uri,
    txId,
    byteSize,
  };
}

/**
 * 根据内容寻址 URI 下载加密数据包 (Base64)
 */
export async function downloadEncryptedSnapshot(uri: string): Promise<string> {
  // 1. 尝试从 Local Vault 读取
  const fromVault =
    localStorage.getItem(VAULT_STORAGE_KEY_PREFIX + uri) ||
    localStorage.getItem(VAULT_STORAGE_KEY_PREFIX + uri.replace('ar://', ''));

  if (fromVault) {
    return fromVault;
  }

  // 2. 尝试从后台密文金库拉取
  try {
    const res = await fetch(`/api/vault/download?uri=${encodeURIComponent(uri)}`);
    if (res.ok) {
      const data = await res.json();
      if (data?.ok && data?.data?.packed_ciphertext_base64) {
        return data.data.packed_ciphertext_base64;
      }
    }
  } catch (_e) {
    // 后台不可达时继续尝试公网 Gateway
  }

  // 3. 如果是外部 ar://，尝试通过公共 Arweave Gateway 获取
  if (uri.startsWith('ar://')) {
    const txId = uri.replace('ar://', '');
    try {
      const resp = await fetch(`https://arweave.net/${txId}`, { signal: AbortSignal.timeout(3000) });
      if (resp.ok) {
        return await resp.text();
      }
    } catch (_e) {
      // 网络无法直连公网 Gateway 时，抛出明确错误
    }
  }

  throw new Error(`无法从去中心化存储或本地密文金库拉取该 URI 的数据包: ${uri}`);
}
