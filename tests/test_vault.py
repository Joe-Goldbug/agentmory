"""Tests for End-to-End Encrypted Backup Vault (lwm/vault.py)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import pytest

from lwm import vault


def test_derive_key_from_seed_length_and_determinism() -> None:
    seed1 = b"phantom_wallet_ed25519_signature_test_1"
    key1 = vault.derive_key_from_seed(seed1)
    assert len(key1) == 32

    # Deterministic output
    key2 = vault.derive_key_from_seed(seed1)
    assert key1 == key2

    # Different seed yields different key
    seed2 = b"phantom_wallet_ed25519_signature_test_2"
    assert vault.derive_key_from_seed(seed2) != key1


def test_store_and_get_encrypted_snapshot(tmp_path: Path) -> None:
    # 模拟客户端 Web Crypto 生成的数据包: 12 字节 IV + 密文
    fake_payload = b"123456789012" + b"encrypted_aes_gcm_ciphertext_data"
    b64_payload = base64.b64encode(fake_payload).decode("ascii")
    snapshot_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    wallet = "7xKXtg9P4WMEMdemoDevnetWallet111111111111111"

    meta = vault.store_encrypted_snapshot(
        tmp_path,
        snapshot_hash=snapshot_hash,
        packed_ciphertext_base64=b64_payload,
        wallet=wallet,
        metadata={"project_id": "test-p1", "version": 2},
    )

    tx_id = snapshot_hash[:32]
    assert meta["tx_id"] == tx_id
    assert meta["uri"] == f"ar://{tx_id}"
    assert meta["byte_size"] == len(fake_payload)
    assert meta["wallet"] == wallet

    # 磁盘文件落盘验证
    enc_file = tmp_path / "state" / "vault" / f"{tx_id}.enc"
    meta_file = tmp_path / "state" / "vault" / f"{tx_id}.meta.json"
    assert enc_file.is_file()
    assert meta_file.is_file()

    # 按 URI 读取
    retrieved_by_uri = vault.get_encrypted_snapshot(tmp_path, f"ar://{tx_id}")
    assert retrieved_by_uri is not None
    assert retrieved_by_uri["packed_ciphertext_base64"] == b64_payload
    assert retrieved_by_uri["meta"]["metadata"]["project_id"] == "test-p1"

    # 按完整 Hash 读取
    retrieved_by_hash = vault.get_encrypted_snapshot(tmp_path, snapshot_hash)
    assert retrieved_by_hash is not None
    assert retrieved_by_hash["tx_id"] == tx_id


def test_store_rejects_invalid_or_truncated_ciphertext(tmp_path: Path) -> None:
    valid_hash = "abcdef0123456789abcdef0123456789"

    # 非法 Base64
    with pytest.raises(ValueError, match="Base64 密文解码失败"):
        vault.store_encrypted_snapshot(
            tmp_path,
            snapshot_hash=valid_hash,
            packed_ciphertext_base64="not_base64!@@#$",
        )

    # 截断数据 (小于 13 字节)
    truncated = base64.b64encode(b"too_short").decode("ascii")
    with pytest.raises(ValueError, match="密文数据包长度异常"):
        vault.store_encrypted_snapshot(
            tmp_path,
            snapshot_hash=valid_hash,
            packed_ciphertext_base64=truncated,
        )


def test_list_and_delete_encrypted_snapshots(tmp_path: Path) -> None:
    payload1 = base64.b64encode(b"1234567890123payload1").decode("ascii")
    payload2 = base64.b64encode(b"1234567890123payload2").decode("ascii")

    w1 = "wallet_user_1"
    w2 = "wallet_user_2"

    vault.store_encrypted_snapshot(
        tmp_path,
        snapshot_hash="11111111111111111111111111111111",
        packed_ciphertext_base64=payload1,
        wallet=w1,
    )
    vault.store_encrypted_snapshot(
        tmp_path,
        snapshot_hash="22222222222222222222222222222222",
        packed_ciphertext_base64=payload2,
        wallet=w2,
    )

    all_items = vault.list_encrypted_snapshots(tmp_path)
    assert len(all_items) == 2

    w1_items = vault.list_encrypted_snapshots(tmp_path, wallet=w1)
    assert len(w1_items) == 1
    assert w1_items[0]["tx_id"] == "11111111111111111111111111111111"

    # 越权删除拒绝
    with pytest.raises(PermissionError, match="无权删除"):
        vault.delete_encrypted_snapshot(
            tmp_path, "11111111111111111111111111111111", wallet=w2
        )

    # 正常删除
    assert vault.delete_encrypted_snapshot(
        tmp_path, "11111111111111111111111111111111", wallet=w1
    )
    assert vault.get_encrypted_snapshot(tmp_path, "11111111111111111111111111111111") is None
    assert len(vault.list_encrypted_snapshots(tmp_path)) == 1
