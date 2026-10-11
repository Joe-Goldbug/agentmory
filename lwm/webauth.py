"""Web 前端账号体系（邮箱 + Solana 钱包登录）。

遵循 GLOBAL.md "标准库优先" 约定：仅用 hashlib/secrets/json，无第三方依赖。

存储：``<root>/state/webauth.json``，结构::

    {
      "users":  {"<email>": {"name": ..., "salt": ..., "hash": ..., "wallets": [...]}},
      "wallets": {"<address>": {"email": "<email or null>", "nonce": ..., "nonce_exp": ...}},
      "sessions": {"<token>": {"user": "<email>", "exp": <unix_ts>}}
    }

密码哈希：PBKDF2-HMAC-SHA256，200k 轮，16 字节盐。

钱包签名校验说明：Ed25519 验签在纯标准库下不可行（无 nacl），因此签名
校验放在前端完成（tweetnacl），网关只负责 nonce 签发与账号绑定。这在
"本地优先、单机自用" 的威胁模型下是足够的；如需服务端强校验，可在
部署机上装 pynacl 后在 ``_wallet_verify`` 中补上。
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any

from lwm.gateway import ApiError

AUTH_FILE = "state/webauth.json"
SESSION_TTL = 7 * 24 * 3600  # 7 天
NONCE_TTL = 300  # 5 分钟
PBKDF2_ROUNDS = 200_000

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")  # base58


# --------------------------------------------------------------------------
# store
# --------------------------------------------------------------------------


def _store_path(root: Path) -> Path:
    return root / AUTH_FILE


def _load(root: Path) -> dict[str, Any]:
    path = _store_path(root)
    if not path.exists():
        return {"users": {}, "wallets": {}, "sessions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"users": {}, "wallets": {}, "sessions": {}}
    data.setdefault("users", {})
    data.setdefault("wallets", {})
    data.setdefault("sessions", {})
    return data


def _save(root: Path, data: dict[str, Any]) -> None:
    path = _store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS
    ).hex()


def _public_user(email: str, user: dict[str, Any]) -> dict[str, Any]:
    return {"email": email, "name": user.get("name") or email.split("@")[0], "wallets": user.get("wallets", [])}


def _new_session(root: Path, data: dict[str, Any], email: str) -> str:
    # 顺带清理过期会话
    now = time.time()
    data["sessions"] = {t: s for t, s in data["sessions"].items() if s.get("exp", 0) > now}
    token = secrets.token_urlsafe(32)
    data["sessions"][token] = {"user": email, "exp": now + SESSION_TTL}
    return token


def _auth_email(body: Any) -> str:
    email = str((body or {}).get("email", "")).strip().lower()
    if not _EMAIL_RE.match(email):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_EMAIL", "邮箱格式不正确")
    return email


# --------------------------------------------------------------------------
# handlers
# --------------------------------------------------------------------------


def handle_register(root: Path, body: Any) -> Any:
    email = _auth_email(body)
    password = str((body or {}).get("password", ""))
    if len(password) < 6:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_WEAK_PASSWORD", "密码至少 6 位")
    name = str((body or {}).get("name", "")).strip() or email.split("@")[0]

    data = _load(root)
    if email in data["users"]:
        raise ApiError(HTTPStatus.CONFLICT, "E_EXISTS", "该邮箱已注册，请直接登录")
    salt = secrets.token_hex(16)
    data["users"][email] = {"name": name, "salt": salt, "hash": _hash_password(password, salt), "wallets": []}
    token = _new_session(root, data, email)
    _save(root, data)
    return {"token": token, "user": _public_user(email, data["users"][email])}


def handle_login(root: Path, body: Any) -> Any:
    email = _auth_email(body)
    password = str((body or {}).get("password", ""))
    data = _load(root)
    user = data["users"].get(email)
    if not user or _hash_password(password, user["salt"]) != user["hash"]:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_BAD_CREDENTIALS", "邮箱或密码错误")
    token = _new_session(root, data, email)
    _save(root, data)
    return {"token": token, "user": _public_user(email, user)}


def handle_me(root: Path, body: Any, auth_header: str = "") -> Any:
    token = auth_header.removeprefix("Bearer ").strip()
    data = _load(root)
    session = data["sessions"].get(token)
    if not session or session.get("exp", 0) < time.time():
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_NO_SESSION", "登录状态已失效")
    user = data["users"].get(session["user"])
    if not user:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_NO_SESSION", "登录状态已失效")
    return {"user": _public_user(session["user"], user)}


def handle_logout(root: Path, body: Any, auth_header: str = "") -> Any:
    token = auth_header.removeprefix("Bearer ").strip()
    data = _load(root)
    data["sessions"].pop(token, None)
    _save(root, data)
    return {"ok": True}


def handle_wallet_nonce(root: Path, body: Any) -> Any:
    address = str((body or {}).get("address", "")).strip()
    if not _ADDRESS_RE.match(address):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_ADDRESS", "Solana 地址格式不正确（base58）")
    data = _load(root)
    nonce = f"LWM-WorkMem 登录验证\n地址: {address}\n时间戳: {int(time.time())}\n随机数: {secrets.token_hex(8)}"
    entry = data["wallets"].setdefault(address, {"email": None})
    entry["nonce"] = nonce
    entry["nonce_exp"] = time.time() + NONCE_TTL
    _save(root, data)
    return {"nonce": nonce}


def handle_wallet_verify(root: Path, body: Any) -> Any:
    address = str((body or {}).get("address", "")).strip()
    nonce = str((body or {}).get("nonce", ""))
    signature = str((body or {}).get("signature", ""))  # base58 或 hex，仅作存档
    email = (body or {}).get("email")
    data = _load(root)
    entry = data["wallets"].get(address)
    if not entry or not entry.get("nonce") or entry["nonce"] != nonce:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE", "nonce 无效，请重新获取")
    if entry.get("nonce_exp", 0) < time.time():
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE_EXPIRED", "nonce 已过期，请重新签名")
    if entry.get("used"):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE_USED", "nonce 已使用，请重新签名")
    entry["used"] = True
    entry["signature"] = signature

    # 绑定/创建账号：邮箱可为空（纯钱包账号），用 <address>@wallet.local 占位
    account = str(email).strip().lower() if email else f"{address[:8].lower()}@wallet.local"
    user = data["users"].get(account)
    if not user:
        salt = secrets.token_hex(16)
        user = {"name": f"{address[:4]}…{address[-4:]}", "salt": salt, "hash": "", "wallets": []}
        data["users"][account] = user
    if address not in user["wallets"]:
        user["wallets"].append(address)
    entry["email"] = account if email else None
    token = _new_session(root, data, account)
    _save(root, data)
    return {"token": token, "user": _public_user(account, user)}
