/**
 * Web Crypto API 客户端端到端加密与密钥派生工具库。
 *
 * 遵循 Solana Web3 备份方案规范：
 * 1. 种子来源：用户 Phantom 钱包对规范文本的 ed25519 签名；
 * 2. KDF 派生：通过 PBKDF2 (100,000 次迭代, SHA-256) 对种子派生 AES-256-GCM 密钥；
 * 3. 对称加密：AES-256-GCM，单次随机生成 12 字节 IV（初始化向量），密文前 12 字节为 IV。
 */

export const BACKUP_KDF_SALT = 'llm-workmem-solana-backup-v1';

export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export function base64ToUint8Array(base64: string): Uint8Array {
  const binary = window.atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function stringToUint8Array(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}

export function uint8ArrayToString(bytes: Uint8Array): string {
  return new TextDecoder().decode(bytes);
}

/**
 * 从钱包签名结果通过 PBKDF2 派生 AES-256-GCM 密钥
 */
export async function deriveKeyFromSignature(
  signature: Uint8Array,
  saltStr: string = BACKUP_KDF_SALT
): Promise<CryptoKey> {
  const enc = new TextEncoder();
  // 导入签名作为 PBKDF2 原始主密钥材料
  const baseKey = await window.crypto.subtle.importKey(
    'raw',
    signature as unknown as BufferSource,
    'PBKDF2',
    false,
    ['deriveKey']
  );

  return window.crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: enc.encode(saltStr),
      iterations: 100000,
      hash: 'SHA-256',
    },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * 使用 AES-256-GCM 加密明文字节流。
 * 返回打包后的密文数据包：前 12 字节为 IV，剩余为 Ciphertext + AuthTag。
 */
export async function encryptBytes(
  plainBytes: Uint8Array,
  key: CryptoKey
): Promise<{ iv: Uint8Array; ciphertext: Uint8Array; packed: Uint8Array; packedBase64: string }> {
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  const encryptedBuffer = await window.crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv,
    },
    key,
    plainBytes as unknown as BufferSource
  );

  const ciphertext = new Uint8Array(encryptedBuffer);
  // 打包: [12 bytes IV] + [Ciphertext]
  const packed = new Uint8Array(iv.length + ciphertext.length);
  packed.set(iv, 0);
  packed.set(ciphertext, iv.length);

  return {
    iv,
    ciphertext,
    packed,
    packedBase64: uint8ArrayToBase64(packed),
  };
}

/**
 * 解密数据包：提取前 12 字节 IV，解密剩余密文字节流。
 */
export async function decryptBytes(
  packedBytes: Uint8Array,
  key: CryptoKey
): Promise<Uint8Array> {
  if (packedBytes.length < 13) {
    throw new Error('密文数据包长度异常，无法提取 12 字节 IV');
  }

  const iv = packedBytes.slice(0, 12);
  const ciphertext = packedBytes.slice(12);

  const decryptedBuffer = await window.crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv,
    },
    key,
    ciphertext as unknown as BufferSource
  );

  return new Uint8Array(decryptedBuffer);
}
