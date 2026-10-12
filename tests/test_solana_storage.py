"""Tests for Solana storage state and gateway integration."""

from __future__ import annotations

from pathlib import Path
import pytest
from lwm import solana_storage


def test_solana_config_defaults_and_update(tmp_path: Path) -> None:
    cfg = solana_storage.get_solana_config(tmp_path)
    assert cfg["cluster"] == "devnet"
    assert "WMEM" in cfg["token_symbol"]
    assert cfg["price_per_package"] == 10
    assert cfg["quota_per_package"] == 10

    # 更新配置
    updated = solana_storage.update_solana_config(
        tmp_path,
        {"rpc_url": "https://custom.helius-rpc.com/?api-key=test", "treasury_pubkey": "custom_treasury_123"},
    )
    assert updated["rpc_url"] == "https://custom.helius-rpc.com/?api-key=test"
    assert updated["treasury_pubkey"] == "custom_treasury_123"

    # 再次读取验证持久化
    refetched = solana_storage.get_solana_config(tmp_path)
    assert refetched["rpc_url"] == "https://custom.helius-rpc.com/?api-key=test"


def test_wallet_initial_quota_and_purchase(tmp_path: Path) -> None:
    wallet = "7xKXtg9P4WMEMdemoDevnetWallet111111111111111"
    quota = solana_storage.get_wallet_quota(tmp_path, wallet)
    assert quota["available"] == 3  # 新钱包测试赠送 3 次
    assert quota["total_commits"] == 0

    # 购买 10 次配额
    res = solana_storage.record_quota_purchase(
        tmp_path,
        wallet,
        tx_hash="tx_test_purchase_signature_123",
        token_amount=10,
        quota_added=10,
    )
    assert res["quota"]["available"] == 13
    assert "explorer.solana.com" in res["transaction"]["explorer_url"]


def test_record_attestation_and_deduct_quota(tmp_path: Path) -> None:
    wallet = "7xKXtg9P4WMEMdemoDevnetWallet111111111111111"
    # 初始化配额 (3 次)
    _ = solana_storage.get_wallet_quota(tmp_path, wallet)

    # 记录存证
    att = solana_storage.record_attestation(
        tmp_path,
        wallet=wallet,
        event_id="evt-001",
        project_id="git-test-proj-hash",
        version=1,
        snapshot_hash="sha256-hash-of-snapshot",
        tx_hash="tx_test_snapshot_commit_456",
        slot=298104520,
    )

    assert att["event_id"] == "evt-001"
    assert att["slot"] == 298104520
    assert "explorer.solana.com" in att["explorer_url"]

    # 验证配额已扣除 (3 - 1 = 2)
    current_quota = solana_storage.get_wallet_quota(tmp_path, wallet)
    assert current_quota["available"] == 2
    assert current_quota["total_commits"] == 1

    # 获取该事件的存证
    saved = solana_storage.get_attestation(tmp_path, "evt-001")
    assert saved is not None
    assert saved["tx_hash"] == "tx_test_snapshot_commit_456"


def test_verify_solana_tx_format_validation() -> None:
    import pytest

    with pytest.raises(ValueError, match="无效的 Solana 交易哈希格式"):
        solana_storage.verify_solana_tx_on_chain("")

    with pytest.raises(ValueError, match="无效的 Solana 交易哈希格式"):
        solana_storage.verify_solana_tx_on_chain("short_hash")


def test_verify_solana_tx_mocked_rpc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import io
    import json
    import urllib.request

    valid_tx = "5eHqP9x7Z2L6jK8wY3nM5vQ8xT4rW2yU1oP9sK6jL3mN7vQ8xT4rW2yU1oP9sK6j"

    class FakeResponse:
        def __init__(self, data: dict):
            self._bytes = json.dumps(data).encode("utf-8")

        def read(self) -> bytes:
            return self._bytes

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    # 1. 模拟链上成功确认
    def fake_urlopen_success(req, timeout=6.0):
        return FakeResponse({
            "jsonrpc": "2.0",
            "result": {
                "value": [
                    {
                        "slot": 301294812,
                        "confirmationStatus": "finalized",
                        "err": None,
                    }
                ]
            },
            "id": 1,
        })

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_success)

    res = solana_storage.verify_solana_tx_on_chain(valid_tx)
    assert res["verified"] is True
    assert res["slot"] == 301294812
    assert res["confirmation_status"] == "finalized"

    # 记录存证时开启 verify_rpc=True，自动填充真实 slot
    _ = solana_storage.get_wallet_quota(tmp_path, "wallet1")
    att = solana_storage.record_attestation(
        tmp_path,
        wallet="wallet1",
        event_id="evt-rpc-verified",
        project_id="proj-1",
        version=1,
        snapshot_hash="hash-1234567890abcdef",
        tx_hash=valid_tx,
        verify_rpc=True,
    )
    assert att["slot"] == 301294812

    # 2. 模拟链上交易报错 (err != None)
    def fake_urlopen_err(req, timeout=6.0):
        return FakeResponse({
            "jsonrpc": "2.0",
            "result": {
                "value": [
                    {
                        "slot": 301294813,
                        "confirmationStatus": "processed",
                        "err": {"InstructionError": [0, "Custom: 1"]},
                    }
                ]
            },
            "id": 1,
        })

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_err)
    with pytest.raises(ValueError, match="链上交易执行失败"):
        solana_storage.verify_solana_tx_on_chain(valid_tx)


def test_ed25519_wallet_verify_accepts_valid_and_rejects_forged(tmp_path: Path) -> None:
    import hashlib
    from lwm import webauth
    from lwm.gateway import ApiError

    def b58encode(b: bytes) -> str:
        alphabet = webauth._B58_ALPHABET
        n = int.from_bytes(b, "big")
        chars = []
        while n > 0:
            n, r = divmod(n, 58)
            chars.append(alphabet[r])
        pad = len(b) - len(b.lstrip(b"\x00"))
        return "1" * pad + "".join(reversed(chars))

    # 使用 RFC 8032 Ed25519 标准算法由 32 字节私钥种子生成公钥与签名
    seed = bytes(range(1, 33))
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    pubkey_bytes = webauth._encode_point(webauth._scalarmult(webauth._ED_B, a))
    address = b58encode(pubkey_bytes)

    nonce_res = webauth.handle_wallet_nonce(tmp_path, {"address": address})
    nonce = nonce_res["nonce"]
    msg = nonce.encode("utf-8")

    # 伪造签名必须被 401 E_BAD_SIGNATURE 拒绝，且不能消耗 nonce
    forged_sig = b58encode(b"\x01" * 64)
    with pytest.raises(ApiError) as exc_info:
        webauth.handle_wallet_verify(
            tmp_path,
            {"address": address, "nonce": nonce, "signature": forged_sig},
        )
    assert exc_info.value.code == "E_BAD_SIGNATURE"

    # 真实 Ed25519 签名必须通过验证并返回会话 token 与绑定钱包
    r = int.from_bytes(hashlib.sha512(h[32:] + msg).digest(), "little") % webauth._ED_L
    r_bytes = webauth._encode_point(webauth._scalarmult(webauth._ED_B, r))
    k = int.from_bytes(hashlib.sha512(r_bytes + pubkey_bytes + msg).digest(), "little") % webauth._ED_L
    s = (r + k * a) % webauth._ED_L
    real_sig = b58encode(r_bytes + s.to_bytes(32, "little"))

    verified = webauth.handle_wallet_verify(
        tmp_path,
        {"address": address, "nonce": nonce, "signature": real_sig},
    )
    assert "token" in verified
    assert address in verified["user"]["wallets"]


