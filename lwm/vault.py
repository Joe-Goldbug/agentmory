"""End-to-End Encrypted Backup Vault (Standard Library Only).

遵循 GLOBAL.md "标准库优先、最小可用 Diff、严禁过度抽象" 原则。
仅使用标准库：base64, hashlib, json, os, pathlib, tempfile, time, datetime。

架构契约与 E2EE 规范：
1. 密钥所有权：端到端加密体系中，主密钥材料由客户端（Phantom 钱包 Ed25519 签名）掌握；
   服务端/网关仅负责密文金库存储、完整性防篡改审计与内容寻址路由，绝不触碰用户明文密钥；
2. 密钥派生：PBKDF2-HMAC-SHA256 (100,000 次迭代, salt='llm-workmem-solana-backup-v1', 32 字节输出)；
3. 密文格式：packed = [12 字节 IV] + [AES-256-GCM 密文与 AuthTag]，以 Base64 编码在通道传输；
4. 金库存储：<root>/state/vault/<tx_id>.enc 与 <tx_id>.meta.json，原子写入并由 index.json 索引。
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

VAULT_DIR = "state/vault"
DEFAULT_KDF_SALT = "llm-workmem-solana-backup-v1"
MIN_CIPHERTEXT_BYTES = 13  # 12 字节 IV + 至少 1 字节数据


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _vault_dir(root: Path) -> Path:
    p = root / VAULT_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_path(root: Path) -> Path:
    return _vault_dir(root) / "index.json"


def _atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with open(fd, mode, encoding=encoding) as f:
            f.write(content)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _load_index(root: Path) -> dict[str, Any]:
    idx_file = _index_path(root)
    if not idx_file.is_file():
        return {"snapshots": {}}
    try:
        data = json.loads(idx_file.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "snapshots" in data:
            return data
    except (OSError, ValueError):
        pass
    return {"snapshots": {}}


def _save_index(root: Path, index: dict[str, Any]) -> None:
    _atomic_write(
        _index_path(root),
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
    )


def derive_key_from_seed(
    seed: bytes | str,
    salt: str = DEFAULT_KDF_SALT,
    iterations: int = 100000,
) -> bytes:
    """标准 PBKDF2-HMAC-SHA256 密钥派生，与前端 Web Crypto 完全对齐。"""
    if isinstance(seed, str):
        seed_bytes = seed.encode("utf-8")
    else:
        seed_bytes = seed
    salt_bytes = salt.encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", seed_bytes, salt_bytes, iterations, dklen=32)


def store_encrypted_snapshot(
    root: Path,
    *,
    snapshot_hash: str,
    packed_ciphertext_base64: str,
    wallet: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """验证并持久化存储端到端密文快照到本地安全金库。"""
    clean_hash = snapshot_hash.strip().lower()
    if not clean_hash or len(clean_hash) < 16:
        raise ValueError("无效的快照哈希 (snapshot_hash)")

    b64_str = packed_ciphertext_base64.strip()
    try:
        raw_bytes = base64.b64decode(b64_str)
    except Exception as exc:
        raise ValueError(f"Base64 密文解码失败: {exc}") from exc

    if len(raw_bytes) < MIN_CIPHERTEXT_BYTES:
        raise ValueError(
            f"密文数据包长度异常 ({len(raw_bytes)} 字节)，小于最小安全长度 (12 字节 IV + 载荷)"
        )

    # 确定性永久寻址 ID
    tx_id = clean_hash[:32]
    uri = f"ar://{tx_id}"
    sha256_checksum = hashlib.sha256(raw_bytes).hexdigest()

    v_dir = _vault_dir(root)
    enc_path = v_dir / f"{tx_id}.enc"
    meta_path = v_dir / f"{tx_id}.meta.json"

    meta_payload = {
        "tx_id": tx_id,
        "uri": uri,
        "snapshot_hash": clean_hash,
        "sha256": sha256_checksum,
        "byte_size": len(raw_bytes),
        "wallet": wallet.strip(),
        "created_at": _now_iso(),
        "metadata": metadata or {},
    }

    _atomic_write(enc_path, b64_str + "\n")
    _atomic_write(meta_path, json.dumps(meta_payload, ensure_ascii=False, indent=2) + "\n")

    index = _load_index(root)
    index["snapshots"][tx_id] = {
        "tx_id": tx_id,
        "uri": uri,
        "snapshot_hash": clean_hash,
        "sha256": sha256_checksum,
        "byte_size": len(raw_bytes),
        "wallet": wallet.strip(),
        "created_at": meta_payload["created_at"],
    }
    _save_index(root, index)

    return meta_payload


def get_encrypted_snapshot(
    root: Path,
    uri_or_hash: str,
) -> dict[str, Any] | None:
    """按 URI 或快照哈希获取密文数据包及元数据。"""
    raw = uri_or_hash.strip()
    if raw.startswith("ar://"):
        tx_id = raw[len("ar://") :]
    else:
        tx_id = raw[:32].lower()

    v_dir = _vault_dir(root)
    enc_path = v_dir / f"{tx_id}.enc"
    meta_path = v_dir / f"{tx_id}.meta.json"

    if not enc_path.is_file():
        return None

    try:
        ciphertext_b64 = enc_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    return {
        "tx_id": tx_id,
        "uri": f"ar://{tx_id}",
        "packed_ciphertext_base64": ciphertext_b64,
        "meta": meta,
    }


def list_encrypted_snapshots(
    root: Path,
    wallet: str | None = None,
) -> list[dict[str, Any]]:
    """列出金库中已归档的密文快照列表（支持钱包地址筛选）。"""
    index = _load_index(root)
    items = list(index.get("snapshots", {}).values())
    if wallet and wallet.strip():
        target_wallet = wallet.strip().lower()
        items = [i for i in items if str(i.get("wallet", "")).lower() == target_wallet]
    return sorted(items, key=lambda x: str(x.get("created_at", "")), reverse=True)


def delete_encrypted_snapshot(
    root: Path,
    uri_or_hash: str,
    wallet: str | None = None,
) -> bool:
    """从金库中安全删除指定快照。"""
    raw = uri_or_hash.strip()
    tx_id = raw[len("ar://") :] if raw.startswith("ar://") else raw[:32].lower()

    v_dir = _vault_dir(root)
    enc_path = v_dir / f"{tx_id}.enc"
    meta_path = v_dir / f"{tx_id}.meta.json"

    if not enc_path.is_file() and not meta_path.is_file():
        return False

    if wallet and wallet.strip():
        target_wallet = wallet.strip().lower()
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                meta = {}
            if meta.get("wallet") and str(meta.get("wallet", "")).lower() != target_wallet:
                raise PermissionError("无权删除非当前钱包所有的快照")

    for p in (enc_path, meta_path):
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass

    index = _load_index(root)
    if tx_id in index.get("snapshots", {}):
        del index["snapshots"][tx_id]
        _save_index(root, index)

    return True


__all__ = [
    "DEFAULT_KDF_SALT",
    "VAULT_DIR",
    "delete_encrypted_snapshot",
    "derive_key_from_seed",
    "get_encrypted_snapshot",
    "list_encrypted_snapshots",
    "store_encrypted_snapshot",
]
