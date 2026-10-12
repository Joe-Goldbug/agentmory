"""Web 前端账号体系（邮箱 + Solana 钱包登录）。

遵循 GLOBAL.md "标准库优先" 约定：仅用 hashlib/secrets/json，无第三方依赖。

存储：``<root>/state/webauth.json``，结构::

    {
      "users":  {"<email>": {"name": ..., "salt": ..., "hash": ..., "wallets": [...]}},
      "wallets": {"<address>": {"email": "<email or null>", "nonce": ..., "nonce_exp": ...}},
      "sessions": {"<token>": {"user": "<email>", "exp": <unix_ts>}}
    }

密码哈希：PBKDF2-HMAC-SHA256，200k 轮，16 字节盐。
钱包签名校验：服务端采用纯标准库 RFC 8032 Ed25519 椭圆曲线验签与 Base58 解码，
对 Phantom / Solflare 钱包针对 Nonce 的签名进行严格密码学核验。
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

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_ED_P = 2**255 - 19
_ED_L = 2**252 + 27742317777372353535851937790883648493
_ED_D = (-121665 * pow(121666, _ED_P - 2, _ED_P)) % _ED_P
_ED_I = pow(2, (_ED_P - 1) // 4, _ED_P)


def b58decode(s: str) -> bytes:
    """标准 Base58 解码（Solana 地址与签名格式）。"""
    clean = s.strip()
    if not clean:
        raise ValueError("空 Base58 字符串")
    num = 0
    for ch in clean:
        idx = _B58_ALPHABET.find(ch)
        if idx < 0:
            raise ValueError(f"非法 Base58 字符: {ch}")
        num = num * 58 + idx
    pad = 0
    for ch in clean:
        if ch == "1":
            pad += 1
        else:
            break
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big") if num > 0 else b""
    return b"\x00" * pad + raw


def _ed_xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_ED_D * y * y + 1, _ED_P - 2, _ED_P) % _ED_P
    x = pow(xx, (_ED_P + 3) // 8, _ED_P)
    if (x * x - xx) % _ED_P != 0:
        x = (x * _ED_I) % _ED_P
    if x % 2 != 0:
        x = _ED_P - x
    return x


_ED_BY = 4 * pow(5, _ED_P - 2, _ED_P) % _ED_P
_ED_BX = _ed_xrecover(_ED_BY)
_ED_B = (_ED_BX % _ED_P, _ED_BY % _ED_P, 1, (_ED_BX * _ED_BY) % _ED_P)


def _edwards_add(
    pt1: tuple[int, int, int, int], pt2: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    x1, y1, z1, t1 = pt1
    x2, y2, z2, t2 = pt2
    a = (y1 - x1) * (y2 - x2) % _ED_P
    b = (y1 + x1) * (y2 + x2) % _ED_P
    c = t1 * 2 * _ED_D * t2 % _ED_P
    d = z1 * 2 * z2 % _ED_P
    e = (b - a) % _ED_P
    f = (d - c) % _ED_P
    g = (d + c) % _ED_P
    h = (b + a) % _ED_P
    return (e * f % _ED_P, g * h % _ED_P, f * g % _ED_P, e * h % _ED_P)


def _scalarmult(pt: tuple[int, int, int, int], e: int) -> tuple[int, int, int, int]:
    res = (0, 1, 1, 0)
    cur = pt
    while e > 0:
        if e & 1:
            res = _edwards_add(res, cur)
        cur = _edwards_add(cur, cur)
        e >>= 1
    return res


def _decode_point(b: bytes) -> tuple[int, int, int, int]:
    if len(b) != 32:
        raise ValueError("Ed25519 坐标点必须为 32 字节")
    unpacked = int.from_bytes(b, "little")
    sign = (unpacked >> 255) & 1
    y = unpacked & ((1 << 255) - 1)
    if y >= _ED_P:
        raise ValueError("y 坐标超出有限域范围")
    x = _ed_xrecover(y)
    if (x * x) % _ED_P != (y * y - 1) * pow(_ED_D * y * y + 1, _ED_P - 2, _ED_P) % _ED_P:
        raise ValueError("坐标点不在 Ed25519 曲线上")
    if x == 0 and sign == 1:
        raise ValueError("非法 x=0 符号位")
    if (x & 1) != sign:
        x = _ED_P - x
    return (x, y, 1, (x * y) % _ED_P)


def _encode_point(pt: tuple[int, int, int, int]) -> bytes:
    x, y, z, _ = pt
    zi = pow(z, _ED_P - 2, _ED_P)
    x = (x * zi) % _ED_P
    y = (y * zi) % _ED_P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def verify_ed25519_signature(pubkey_bytes: bytes, message: bytes, sig_bytes: bytes) -> bool:
    """RFC 8032 标准 Ed25519 签名验证（纯标准库实现）。"""
    try:
        if len(pubkey_bytes) != 32 or len(sig_bytes) != 64:
            return False
        r_bytes = sig_bytes[:32]
        s_int = int.from_bytes(sig_bytes[32:], "little")
        if s_int >= _ED_L:
            return False
        a_pt = _decode_point(pubkey_bytes)
        r_pt = _decode_point(r_bytes)
        k = int.from_bytes(hashlib.sha512(r_bytes + pubkey_bytes + message).digest(), "little") % _ED_L
        lhs = _scalarmult(_ED_B, s_int)
        rhs = _edwards_add(r_pt, _scalarmult(a_pt, k))
        return _encode_point(lhs) == _encode_point(rhs)
    except Exception:
        return False


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
    try:
        pubkey_bytes = b58decode(address)
        if len(pubkey_bytes) != 32:
            raise ValueError("Solana 公钥解码后必须为 32 字节")
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_ADDRESS", f"Solana 公钥无效: {exc}") from exc
    data = _load(root)
    nonce = f"LWM-WorkMem 登录验证\n地址: {address}\n时间戳: {int(time.time())}\n随机数: {secrets.token_hex(8)}"
    entry = data["wallets"].setdefault(address, {"email": None})
    entry["nonce"] = nonce
    entry["nonce_exp"] = time.time() + NONCE_TTL
    entry["used"] = False
    _save(root, data)
    return {"nonce": nonce}


def _decode_signature_bytes(signature: str) -> bytes:
    clean = signature.strip()
    if not clean:
        raise ValueError("签名为空")
    if len(clean) == 128 and all(c in "0123456789abcdefABCDEF" for c in clean):
        return bytes.fromhex(clean)
    return b58decode(clean)


def handle_wallet_verify(root: Path, body: Any, auth_header: str = "") -> Any:
    address = str((body or {}).get("address", "")).strip()
    nonce = str((body or {}).get("nonce", ""))
    signature = str((body or {}).get("signature", "")).strip()
    email = (body or {}).get("email")

    if not _ADDRESS_RE.match(address):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_ADDRESS", "Solana 地址格式不正确")
    if not signature:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_BAD_SIGNATURE", "缺少钱包 Ed25519 签名")

    data = _load(root)
    entry = data["wallets"].get(address)
    if not entry or not entry.get("nonce") or entry["nonce"] != nonce:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE", "nonce 无效，请重新获取")
    if entry.get("nonce_exp", 0) < time.time():
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE_EXPIRED", "nonce 已过期，请重新签名")
    if entry.get("used"):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_NONCE_USED", "nonce 已使用，请重新签名")

    try:
        pubkey_bytes = b58decode(address)
        sig_bytes = _decode_signature_bytes(signature)
    except ValueError as exc:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_BAD_SIGNATURE", f"签名或公钥编码格式非法: {exc}") from exc

    if not verify_ed25519_signature(pubkey_bytes, nonce.encode("utf-8"), sig_bytes):
        raise ApiError(HTTPStatus.UNAUTHORIZED, "E_BAD_SIGNATURE", "钱包 Ed25519 签名密码学核验失败")

    entry["used"] = True
    entry["signature"] = signature

    # 若当前请求带有已登录的 Bearer token，优先将该验证通过的钱包绑定到当前登录账户
    session_account = None
    if auth_header:
        token_in = auth_header.removeprefix("Bearer ").strip()
        sess = data["sessions"].get(token_in)
        if sess and sess.get("exp", 0) > time.time() and sess.get("user") in data["users"]:
            session_account = sess["user"]

    account = (
        session_account
        or (str(email).strip().lower() if email else None)
        or entry.get("email")
        or f"{address[:8].lower()}@wallet.local"
    )
    user = data["users"].get(account)
    if not user:
        salt = secrets.token_hex(16)
        user = {"name": f"{address[:4]}…{address[-4:]}", "salt": salt, "hash": "", "wallets": []}
        data["users"][account] = user
    if address not in user["wallets"]:
        user["wallets"].append(address)
    entry["email"] = account
    token = _new_session(root, data, account)
    _save(root, data)
    return {"token": token, "user": _public_user(account, user)}

