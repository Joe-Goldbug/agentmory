"""Solana Devnet 链上存证与代币配额状态管理（标准库优先）。

遵循 GLOBAL.md "标准库优先" 原则：仅使用 json / pathlib / time / hashlib。

存储路径：``<root>/state/solana_state.json``
结构::
    {
      "config": {
        "cluster": "devnet",
        "rpc_url": "https://api.devnet.solana.com",
        "program_id": "WMEMs11111111111111111111111111111111111111",
        "token_mint": "DevWMEMMint11111111111111111111111111111111",
        "token_symbol": "WMEM",
        "treasury_pubkey": "WMEMTReasury11111111111111111111111111111111",
        "price_per_package": 10,
        "quota_per_package": 10
      },
      "quotas": {
        "<wallet_address>": {
          "available": 10,
          "total_commits": 0,
          "last_updated": 1728641774
        }
      },
      "attestations": {
        "<event_or_snapshot_id>": {
          "tx_hash": "...",
          "slot": 298102301,
          "cluster": "devnet",
          "program_id": "...",
          "wallet": "...",
          "project_id": "...",
          "version": 1,
          "snapshot_hash": "...",
          "timestamp": "2026-10-11T10:16:00Z",
          "explorer_url": "https://explorer.solana.com/tx/.../?cluster=devnet"
        }
      },
      "transactions": [...]
    }
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOLANA_STATE_FILE = "state/solana_state.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "cluster": "devnet",
    "rpc_url": "https://api.devnet.solana.com",
    "program_id": "WMEMs11111111111111111111111111111111111111",
    "token_mint": "DevWMEMMint11111111111111111111111111111111",
    "token_symbol": "$WMEM",
    "treasury_pubkey": "WMEMTReasury11111111111111111111111111111111",
    "price_per_package": 10,  # 10 $WMEM 或 0.05 SOL
    "quota_per_package": 10,  # 可获得 10 次链上不可变存证
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _store_path(root: Path) -> Path:
    return root / SOLANA_STATE_FILE


def _load(root: Path) -> dict[str, Any]:
    path = _store_path(root)
    if not path.exists():
        return {
            "config": dict(DEFAULT_CONFIG),
            "quotas": {},
            "attestations": {},
            "transactions": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {
            "config": dict(DEFAULT_CONFIG),
            "quotas": {},
            "attestations": {},
            "transactions": [],
        }
    data.setdefault("config", dict(DEFAULT_CONFIG))
    data.setdefault("quotas", {})
    data.setdefault("attestations", {})
    data.setdefault("transactions", [])
    return data


def _save(root: Path, data: dict[str, Any]) -> None:
    path = _store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_solana_config(root: Path) -> dict[str, Any]:
    data = _load(root)
    return data.get("config", DEFAULT_CONFIG)


def get_wallet_quota(root: Path, wallet: str) -> dict[str, Any]:
    """获取指定钱包的链上存储配额状态；新钱包默认赠送 3 次测试体验额度。"""
    wallet = wallet.strip()
    data = _load(root)
    quotas = data["quotas"]
    if wallet not in quotas:
        # 新连接的测试网钱包默认赠送 3 次测试上链存证额度
        quotas[wallet] = {
            "available": 3,
            "total_commits": 0,
            "last_updated": time.time(),
        }
        _save(root, data)
    return quotas[wallet]


def record_quota_purchase(
    root: Path,
    wallet: str,
    tx_hash: str,
    token_amount: int,
    quota_added: int,
) -> dict[str, Any]:
    """记录用户使用 SPL Token 购买上链存储额度。"""
    wallet = wallet.strip()
    data = _load(root)
    quotas = data["quotas"]
    current = quotas.get(
        wallet,
        {"available": 0, "total_commits": 0, "last_updated": time.time()},
    )
    current["available"] = int(current.get("available", 0)) + int(quota_added)
    current["last_updated"] = time.time()
    quotas[wallet] = current

    tx_record = {
        "tx_hash": tx_hash,
        "type": "purchase",
        "wallet": wallet,
        "token_amount": token_amount,
        "quota_added": quota_added,
        "timestamp": _now_iso(),
        "explorer_url": f"https://explorer.solana.com/tx/{tx_hash}?cluster=devnet",
    }
    data["transactions"].append(tx_record)
    _save(root, data)
    return {"quota": current, "transaction": tx_record}


def record_attestation(
    root: Path,
    wallet: str,
    event_id: str,
    project_id: str,
    version: int,
    snapshot_hash: str,
    tx_hash: str,
    slot: int | None = None,
) -> dict[str, Any]:
    """记录一次工作记忆快照上链存证，扣减 1 次配额。"""
    wallet = wallet.strip()
    data = _load(root)
    quotas = data["quotas"]
    current = quotas.get(
        wallet,
        {"available": 0, "total_commits": 0, "last_updated": time.time()},
    )
    if current.get("available", 0) <= 0:
        raise ValueError("当前钱包链上存证配额不足，请先支付代币充值")

    current["available"] -= 1
    current["total_commits"] = current.get("total_commits", 0) + 1
    current["last_updated"] = time.time()
    quotas[wallet] = current

    explorer_url = f"https://explorer.solana.com/tx/{tx_hash}?cluster=devnet"
    attestation = {
        "event_id": event_id,
        "tx_hash": tx_hash,
        "slot": slot or 298104520,
        "cluster": "devnet",
        "program_id": data["config"]["program_id"],
        "wallet": wallet,
        "project_id": project_id,
        "version": version,
        "snapshot_hash": snapshot_hash,
        "timestamp": _now_iso(),
        "explorer_url": explorer_url,
    }
    data["attestations"][event_id] = attestation

    tx_record = {
        "tx_hash": tx_hash,
        "type": "commit_snapshot",
        "wallet": wallet,
        "event_id": event_id,
        "project_id": project_id,
        "timestamp": _now_iso(),
        "explorer_url": explorer_url,
    }
    data["transactions"].append(tx_record)
    _save(root, data)
    return attestation


def get_attestation(root: Path, event_id: str) -> dict[str, Any] | None:
    data = _load(root)
    return data["attestations"].get(event_id)


def list_attestations(root: Path, wallet: str | None = None) -> list[dict[str, Any]]:
    data = _load(root)
    items = list(data["attestations"].values())
    if wallet:
        items = [i for i in items if i.get("wallet") == wallet]
    return sorted(items, key=lambda x: str(x.get("timestamp", "")), reverse=True)
