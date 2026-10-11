"""Tests for gateway /api/backup/* and /api/leases/* endpoints."""

from __future__ import annotations

from pathlib import Path

from lwm.gateway import _dispatch


def test_gateway_backup_bundle_and_restore(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "note.md").write_text("hello gateway backup", encoding="utf-8")

    # 1. GET /api/backup/bundle
    bundle = _dispatch(tmp_path, "GET", "/api/backup/bundle", {}, None)
    assert bundle["version"] == 1
    assert bundle["sha256"]
    assert bundle["tar_base64"]

    # 2. 破坏文件
    (wiki_dir / "note.md").write_text("broken", encoding="utf-8")

    # 3. POST /api/backup/restore
    res = _dispatch(
        tmp_path,
        "POST",
        "/api/backup/restore",
        {},
        {"tar_base64": bundle["tar_base64"], "sha256": bundle["sha256"]},
    )
    assert res["status"] == "success"

    # 4. 验证恢复
    assert (wiki_dir / "note.md").read_text(encoding="utf-8") == "hello gateway backup"


def test_gateway_leases_flow(tmp_path: Path) -> None:
    # 1. 申请租约
    acq = _dispatch(
        tmp_path,
        "POST",
        "/api/leases/acquire",
        {},
        {"project_id": "proj-gw", "agent_name": "Antigravity", "objective": "网关测试"},
    )
    assert acq["ok"] is True
    assert acq["conflict"] is False

    # 2. 查询活跃租约
    active = _dispatch(tmp_path, "GET", "/api/leases/active", {"project_id": ["proj-gw"]}, None)
    assert active is not None
    assert active["agent_name"] == "Antigravity"

    # 3. 列出所有租约
    leases_list = _dispatch(tmp_path, "GET", "/api/leases", {}, None)
    assert len(leases_list) == 1
    assert leases_list[0]["project_id"] == "proj-gw"

    # 4. 释放租约
    rel = _dispatch(
        tmp_path,
        "POST",
        "/api/leases/release",
        {},
        {"project_id": "proj-gw", "lease_id": acq["lease_id"]},
    )
    assert rel["ok"] is True
    assert rel["released"] is True


def test_gateway_vault_and_subscription_flow(tmp_path: Path) -> None:
    import base64

    # 1. /api/subscription returns 4 tiers
    plans = _dispatch(tmp_path, "GET", "/api/subscription", {}, None)
    assert len(plans) == 4
    plan_names = [p["name"] for p in plans]
    assert plan_names == ["Local", "Personal", "Pro", "Team"]

    # 2. POST /api/vault/upload
    fake_payload = b"1234567890123" + b"ciphertext_bytes_here"
    b64_str = base64.b64encode(fake_payload).decode("ascii")
    upload_res = _dispatch(
        tmp_path,
        "POST",
        "/api/vault/upload",
        {},
        {
            "snapshot_hash": "aabbccddeeff00112233445566778899",
            "packed_ciphertext_base64": b64_str,
            "wallet": "7xKXdemoWallet",
        },
    )
    assert upload_res["uri"] == "ar://aabbccddeeff00112233445566778899"

    # 3. GET /api/vault/download
    download_res = _dispatch(
        tmp_path,
        "GET",
        "/api/vault/download",
        {"uri": ["ar://aabbccddeeff00112233445566778899"]},
        None,
    )
    assert download_res["packed_ciphertext_base64"] == b64_str

    # 4. GET /api/vault/list
    vault_list = _dispatch(
        tmp_path,
        "GET",
        "/api/vault/list",
        {"wallet": ["7xKXdemoWallet"]},
        None,
    )
    assert len(vault_list) == 1
    assert vault_list[0]["tx_id"] == "aabbccddeeff00112233445566778899"

