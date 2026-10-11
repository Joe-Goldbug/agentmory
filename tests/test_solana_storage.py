"""Tests for Solana storage state and gateway integration."""

from __future__ import annotations

from pathlib import Path
from lwm import solana_storage


def test_solana_config_defaults(tmp_path: Path) -> None:
    cfg = solana_storage.get_solana_config(tmp_path)
    assert cfg["cluster"] == "devnet"
    assert "WMEM" in cfg["token_symbol"]
    assert cfg["price_per_package"] == 10
    assert cfg["quota_per_package"] == 10


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
