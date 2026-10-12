"""Minimal JSON gateway over the LLM-WorkMem hub (standard library only).

Why this exists
---------------
The browser cannot call the CLI, the ``hub bridge`` JSON-IPC or the MCP stdio
server. ``lwm serve`` is the only HTTP surface but it renders *HTML* and has
no ``/api/*`` routes. This module adds the missing JSON transport so the
``web/`` frontend can read the same data the CLI already produces.

Design constraints (mirrors ``lwm/dashboard.py::serve_wiki`` and honours the
``GLOBAL.md`` "standard library first, no useless abstraction" contract):

* no third-party web framework — ``http.server`` only;
* no new business logic — every route wraps an existing ``lwm/`` function;
* local-first: binds ``127.0.0.1`` by default, **no authentication**.

Response envelope (defined in ``docs/api-contract.md``)::

    {"ok": true,  "data": <payload>}
    {"ok": false, "error": {"code": ..., "message": ..., "detail": ...}}
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from lwm import health as lwm_health
from lwm import hub_service, memory_compiler

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766  # 8765 is taken by `lwm serve`

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


class ApiError(Exception):
    """带 HTTP 语义的业务异常（区别于 ValueError 的参数校验失败）。"""

    def __init__(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.detail = detail


def _json_default(value: Any) -> Any:
    """Make dataclasses / Paths / tuples JSON-serialisable."""
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"not JSON serialisable: {type(value)!r}")


def _events_dirs(root: Path) -> list[Path]:
    return [
        d
        for d in (
            root / "raw" / "events" / "inbox",
            root / "raw" / "events" / "processed",
        )
        if d.is_dir()
    ]


def _load_events(root: Path, limit: int, project_id: str | None) -> list[dict[str, Any]]:
    """Read event JSON straight from the evidence store (newest first)."""
    files = [
        p
        for d in _events_dirs(root)
        for p in sorted(d.rglob("*.json"), reverse=True)
    ]
    events: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        if project_id and payload.get("project_id") != project_id:
            continue
        payload.setdefault("event_id", path.stem)
        events.append(payload)
        if len(events) >= limit:
            break
    return events


def _project_titles(root: Path) -> dict[str, str]:
    """project_id -> last known task (from wiki/project/*.md front matter)."""
    titles: dict[str, str] = {}
    for page in (root / "wiki" / "projects").glob("*.md"):
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"^Last task:\s*(.+)$", text, flags=re.MULTILINE)
        if match:
            titles[page.stem] = match.group(1).strip()
    return titles


def _status_payload(root: Path) -> dict[str, Any]:
    snapshot = lwm_health.collect_and_write(root.resolve(), strict=False)
    return {
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "infrastructure": snapshot.infrastructure,
        "data_flow": snapshot.data_flow,
        "cycle": snapshot.cycle,
        "inbox_counts": snapshot.inbox_counts,
        "quality": snapshot.quality,
        "monthly_events": _monthly_event_count(root),
        "token_budget_used_percent": None,  # 需 LWM_ANALYSIS_* 启用后统计，见契约 §1.1
    }


def _monthly_event_count(root: Path) -> int:
    """Approximate "events retained this month" (the demo's savings metric has
    no backend equivalent — see docs/frontend-demo-integration.md §3.1⑧)."""
    prefix = datetime.now().strftime("%Y-%m")
    total = 0
    for directory in _events_dirs(root):
        month_dir = directory / prefix
        if month_dir.is_dir():
            total += len(list(month_dir.glob("*.json")))
    return total


# --------------------------------------------------------------------------
# route handlers — each wraps an existing lwm/ function
# --------------------------------------------------------------------------


def _handle_health(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    return _status_payload(root)


def _handle_projects(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    mapping: dict[str, str] = {}
    map_path = root / "state" / "project-map.json"
    if map_path.is_file():
        try:
            mapping = json.loads(map_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            mapping = {}

    titles = _project_titles(root)
    ids = sorted(set(mapping.values()) | set(titles))
    return [
        {
            "project_id": pid,
            "title": titles.get(pid, f"Project {pid}"),
            "tag": "",
            "path": next((p for p, i in mapping.items() if i == pid), ""),
        }
        for pid in ids
    ]


def _handle_context(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    tool = (params.get("tool") or ["codex"])[0]
    project = (params.get("project") or [None])[0]
    if not project:
        raise ValueError("missing required query parameter: project")
    limit = int((params.get("limit") or ["6"])[0])
    report, _receipt = hub_service.context_for_tool(
        root.resolve(), tool=tool, project_path=project, limit=limit
    )
    return report.data


def _handle_behavior(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    data = hub_service.behavior_show(root)
    # 前端按 path/version/sha256/body 消费；status=missing 时 body 为空串
    return {
        "path": data.get("path", "GLOBAL.md"),
        "version": data.get("version", "unknown"),
        "sha256": data.get("sha256", ""),
        "status": data.get("status", "missing"),
        "body": data.get("text") or data.get("body") or "",
    }


def _handle_events(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    limit = int((params.get("limit") or ["50"])[0])
    project = (params.get("project") or [None])[0]
    return _load_events(root, limit, project)


def _handle_tools(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    return hub_service.list_tools(root, home=Path.home())


def _handle_coverage(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    """Map ``hub_service.coverage_report`` onto the contract's proof levels.

    Real payload keys (verified): tool_id, status, capture_status,
    delivery_status, read_status, write_status, last_capture_at, last_read_at,
    last_write_at, gaps, status_reason.
    """
    report = hub_service.coverage_report(root, home=Path.home())
    rows = []
    for payload in report.values():
        rows.append(
            {
                "tool": payload.get("tool_id", "unknown"),
                "proof_level": _proof_level(payload),
                "last_seen": (
                    payload.get("last_capture_at")
                    or payload.get("last_read_at")
                    or payload.get("last_write_at")
                    or ""
                ),
                "readable": str(payload.get("read_status") or "missing") != "missing",
                "writable": str(payload.get("write_status") or "missing") != "missing",
                "status_reason": payload.get("status_reason", ""),
                "gaps": list(payload.get("gaps") or []),
            }
        )
    return rows


def _proof_level(payload: dict[str, Any]) -> str:
    """三级 Proof：native-hook / watcher-observed / configured / none。

    必须**精确匹配**：``delivery_status`` 可能是 ``configured_unverified``，
    其中含子串 "verified"，用 `in` 判断会误判为最高等级。
    """
    read = str(payload.get("read_status") or "").lower()
    write = str(payload.get("write_status") or "").lower()
    capture = str(payload.get("capture_status") or "").lower()
    delivery = str(payload.get("delivery_status") or "").lower()

    if read == "verified" or write == "verified":
        return "native-hook"
    if capture == "ok" or read == "observed" or write == "observed":
        return "watcher-observed"
    if delivery.startswith("configured") or capture == "awaiting_first_event":
        return "configured"
    return "none"


def _handle_probe(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    # 探查无副作用，等价于重新计算一次覆盖报告
    return _handle_coverage(root, params, body)


def _handle_candidates(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    """Pending review candidates.

    ``memory_compiler`` writes candidates under ``state/analysis/candidates``.
    The compiler needs LWM_ANALYSIS_* to synthesise *new* candidates; without
    them the directory is simply empty, which is a valid (empty) response.
    """
    directory = root / memory_compiler.ANALYSIS_DIR
    if not directory.is_dir():
        return []
    rows = []
    for path in sorted(directory.glob("*.md"), reverse=True):
        text = path.read_text(encoding="utf-8")
        rows.append(
            {
                "id": path.stem,
                "kind": _infer_kind(text),
                "title": _first_heading(text) or path.stem,
                "summary": _summary(text),
                "source_tool": _meta(text, "source_tool") or "unknown",
                "created_at": _meta(text, "created_at") or "",
            }
        )
    return rows


def _handle_review(root: Path, candidate_id: str, body: Any) -> Any:
    if not isinstance(body, dict) or "decision" not in body:
        raise ValueError("missing required field: decision")
    decision = str(body["decision"])
    if decision not in {"accept", "reject", "promote"}:
        raise ValueError("decision must be one of: accept, reject, promote")
    try:
        result = hub_service.review_analysis(
            root.resolve(), candidate_id, decision=decision
        )
    except FileNotFoundError as exc:
        raise ApiError(
            HTTPStatus.NOT_FOUND, "E_NOT_FOUND", f"candidate not found: {candidate_id}"
        ) from exc
    return {"id": candidate_id, "decision": decision, "result": result}


def _handle_search(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    query = ((params.get("q") or [""])[0]).strip()
    if not query:
        return []
    lowered = query.lower()
    hits: list[dict[str, str]] = []

    for page in sorted((root / "wiki" / "projects").glob("*.md")):
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if lowered in line.lower() and line.strip():
                hits.append(
                    {
                        "title": page.stem,
                        "snippet": line.strip()[:160],
                        "pagePath": f"projects/{page.stem}",
                    }
                )
                break
    for event in _load_events(root, limit=50, project_id=None)[:20]:
        task = str(event.get("task") or "")
        if lowered in task.lower():
            hits.append(
                {
                    "title": task,
                    "snippet": f"{event.get('tool', '')} · {event.get('timestamp', '')}",
                    "pagePath": f"events/{event.get('event_id', '')}",
                }
            )
    return hits[:20]


def _handle_teams(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    # 无多用户模型（federation 是本机跨 Agent，不是团队）—— 见集成文档 §3.1⑥
    return {"available": False, "members": []}


def _handle_subscription(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    # 按照商业化产品定价规范提供 4 档订阅方案定义
    return [
        {
            "name": "Local",
            "price": "免费",
            "desc": "¥0 / 月",
            "target": "本地优先：数据留在你自己的机器上",
            "features": ["本地记忆", "基础工具连接", "查看来源", "手动导出"],
            "buttonText": "当前套餐",
            "highlight": False,
            "disabled": True,
        },
        {
            "name": "Personal",
            "price": "¥39",
            "desc": "¥39 / 月",
            "target": "工作不丢、换电脑能继续、少维护",
            "features": ["加密云备份", "跨设备同步", "版本恢复", "自动整理额度", "运行异常提醒"],
            "buttonText": "升级 Personal",
            "highlight": True,
            "disabled": False,
        },
        {
            "name": "Pro",
            "price": "¥89",
            "desc": "¥89 / 月",
            "target": "多个项目和多个工具之间更可靠地衔接",
            "features": ["Personal 全部功能", "更多语义整理额度", "跨项目经验综合", "冲突与影响分析"],
            "buttonText": "升级 Pro",
            "highlight": False,
            "disabled": False,
        },
        {
            "name": "Team",
            "price": "¥69",
            "desc": "¥69 / 人 / 月起 (3人起)",
            "target": "团队不用反复传背景，也能控制谁写入什么",
            "features": ["共享项目记忆", "成员权限管理", "审批与审计日志", "团队交接流水线"],
            "buttonText": "联系团队版",
            "highlight": False,
            "disabled": False,
        },
    ]


# --- small markdown helpers (candidates live as Markdown, not JSON) ---


def _first_heading(text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _summary(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return " ".join(lines[:3])[:300]


def _meta(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _infer_kind(text: str) -> str:
    lowered = text.lower()
    if "conflict" in lowered:
        return "conflict"
    if "outdated" in lowered or "stale" in lowered:
        return "outdated"
    return "rule"


def _handle_solana_config(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import solana_storage
    return solana_storage.get_solana_config(root)


def _handle_solana_config_update(root: Path, body: Any) -> Any:
    from lwm import solana_storage
    new_cfg = body or {}
    if not isinstance(new_cfg, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "配置格式须为 JSON 对象")
    return solana_storage.update_solana_config(root, new_cfg)


def _handle_solana_quota(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import solana_storage
    wallet = ((params.get("wallet") or [""])[0]).strip()
    if not wallet:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_WALLET", "缺少 wallet 参数")
    return solana_storage.get_wallet_quota(root, wallet)


def _handle_solana_attestations(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import solana_storage
    wallet = ((params.get("wallet") or [""])[0]).strip()
    event_id = ((params.get("event_id") or [""])[0]).strip()
    if event_id:
        res = solana_storage.get_attestation(root, event_id)
        if not res:
            raise ApiError(HTTPStatus.NOT_FOUND, "E_NOT_FOUND", "未找到该事件的链上存证")
        return res
    return solana_storage.list_attestations(root, wallet or None)


def _handle_solana_verify(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import solana_storage
    tx_hash = ((params.get("tx_hash") or [""])[0]).strip()
    if not tx_hash:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 tx_hash 参数")
    config = solana_storage.get_solana_config(root)
    rpc_url = config.get("rpc_url", solana_storage.DEFAULT_CONFIG["rpc_url"])
    try:
        return solana_storage.verify_solana_tx_on_chain(tx_hash, rpc_url=rpc_url)
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_VERIFICATION_FAILED", str(exc)) from exc


def _handle_solana_purchase(root: Path, body: Any) -> Any:
    from lwm import solana_storage
    wallet = str((body or {}).get("wallet", "")).strip()
    tx_hash = str((body or {}).get("tx_hash", "")).strip()
    token_amount = int((body or {}).get("token_amount", 10))
    quota_added = int((body or {}).get("quota_added", 10))
    config = solana_storage.get_solana_config(root)
    default_verify = bool(config.get("enforce_rpc_verification", True))
    verify_rpc = bool((body or {}).get("verify_rpc", default_verify))
    if not wallet or not tx_hash:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 wallet 或 tx_hash")
    try:
        return solana_storage.record_quota_purchase(
            root, wallet, tx_hash, token_amount, quota_added, verify_rpc=verify_rpc
        )
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_PURCHASE_FAILED", str(exc)) from exc


def _handle_solana_commit(root: Path, body: Any) -> Any:
    from lwm import solana_storage
    wallet = str((body or {}).get("wallet", "")).strip()
    event_id = str((body or {}).get("event_id", "")).strip()
    project_id = str((body or {}).get("project_id", "")).strip()
    version = int((body or {}).get("version", 1))
    snapshot_hash = str((body or {}).get("snapshot_hash", "")).strip()
    tx_hash = str((body or {}).get("tx_hash", "")).strip()
    slot = (body or {}).get("slot")
    chunk_tx_hashes = (body or {}).get("chunk_tx_hashes")
    config = solana_storage.get_solana_config(root)
    default_verify = bool(config.get("enforce_rpc_verification", True))
    verify_rpc = bool((body or {}).get("verify_rpc", default_verify))
    if not wallet or not event_id or not snapshot_hash or not tx_hash:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少必要参数")
    try:
        return solana_storage.record_attestation(
            root,
            wallet,
            event_id,
            project_id,
            version,
            snapshot_hash,
            tx_hash,
            slot,
            verify_rpc=verify_rpc,
            chunk_tx_hashes=chunk_tx_hashes,
        )
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_QUOTA_EXCEEDED", str(exc)) from exc


def _handle_vault_upload(root: Path, body: Any) -> Any:
    from lwm import vault
    payload = body or {}
    snapshot_hash = str(payload.get("snapshot_hash", "")).strip()
    packed_b64 = str(payload.get("packed_ciphertext_base64", "")).strip()
    wallet = str(payload.get("wallet", "")).strip()
    metadata = payload.get("metadata")
    if not snapshot_hash or not packed_b64:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 snapshot_hash 或 packed_ciphertext_base64")
    try:
        return vault.store_encrypted_snapshot(
            root,
            snapshot_hash=snapshot_hash,
            packed_ciphertext_base64=packed_b64,
            wallet=wallet,
            metadata=metadata,
        )
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_VAULT_ERROR", str(exc)) from exc


def _handle_vault_pin_ipfs(root: Path, body: Any) -> Any:
    from lwm import solana_storage, vault
    payload = body or {}
    snapshot_hash = str(payload.get("snapshot_hash", "")).strip()
    packed_b64 = str(payload.get("packed_ciphertext_base64", "")).strip()
    wallet = str(payload.get("wallet", "")).strip()
    metadata = payload.get("metadata")
    cfg = solana_storage.get_solana_config(root)
    pinata_jwt = cfg.get("pinata_jwt")
    if not snapshot_hash or not packed_b64:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 snapshot_hash 或 packed_ciphertext_base64")
    try:
        return vault.pin_snapshot_ipfs(
            root,
            snapshot_hash=snapshot_hash,
            packed_ciphertext_base64=packed_b64,
            wallet=wallet,
            metadata=metadata,
            pinata_jwt=pinata_jwt,
        )
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_VAULT_ERROR", str(exc)) from exc


def _handle_vault_download(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import vault
    uri = ((params.get("uri") or [""])[0]).strip()
    snapshot_hash = ((params.get("snapshot_hash") or [""])[0]).strip()
    target = uri or snapshot_hash
    if not target:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 uri 或 snapshot_hash 参数")
    res = vault.get_encrypted_snapshot(root, target)
    if not res:
        raise ApiError(HTTPStatus.NOT_FOUND, "E_NOT_FOUND", "未找到指定快照密文")
    return res


def _handle_vault_list(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import vault
    wallet = ((params.get("wallet") or [""])[0]).strip()
    return vault.list_encrypted_snapshots(root, wallet or None)


def _handle_backup_bundle(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import backup

    compact_param = ((params.get("compact") or [""])[0]).strip().lower()
    compact = compact_param in ("1", "true", "yes")
    return backup.create_backup_bundle(root, compact=compact)


def _handle_backup_restore(root: Path, body: Any) -> Any:
    from lwm import backup

    payload = body or {}
    tar_b64 = str(payload.get("tar_base64", "")).strip()
    sha256 = str(payload.get("sha256", "")).strip()
    if not tar_b64 or not sha256:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 tar_base64 或 sha256")
    try:
        return backup.restore_backup_bundle(root, tar_b64, sha256)
    except PermissionError as exc:
        raise ApiError(HTTPStatus.FORBIDDEN, "E_ZIP_SLIP", str(exc)) from exc
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_RESTORE_FAILED", str(exc)) from exc


def _handle_leases_active(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import lease

    project_id = (params.get("project_id") or [""])[0]
    return lease.get_active_lease(root, project_id)


def _handle_leases_list(root: Path, params: dict[str, list[str]], body: Any) -> Any:
    from lwm import lease

    return lease.list_active_leases(root)


def _handle_leases_acquire(root: Path, body: Any) -> Any:
    from lwm import lease

    payload = body or {}
    project_id = str(payload.get("project_id", "")).strip()
    agent_name = str(payload.get("agent_name", "")).strip()
    objective = str(payload.get("objective", "")).strip()
    ttl = int(payload.get("ttl_seconds", lease.DEFAULT_TTL_SECONDS))
    force = bool(payload.get("force", False))
    if not project_id or not agent_name:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 project_id 或 agent_name")
    return lease.acquire_lease(root, project_id, agent_name, objective, ttl, force)


def _handle_leases_release(root: Path, body: Any) -> Any:
    from lwm import lease

    payload = body or {}
    project_id = str(payload.get("project_id", "")).strip()
    lease_id = payload.get("lease_id")
    if not project_id:
        raise ApiError(HTTPStatus.BAD_REQUEST, "E_BAD_PARAMS", "缺少 project_id")
    return lease.release_lease(root, project_id, lease_id)


# --------------------------------------------------------------------------
# routing table
# --------------------------------------------------------------------------

ROUTES: dict[str, Callable[[Path, dict[str, list[str]], Any], Any]] = {
    "/api/health": _handle_health,
    "/api/projects": _handle_projects,
    "/api/context": _handle_context,
    "/api/behavior": _handle_behavior,
    "/api/events": _handle_events,
    "/api/tools": _handle_tools,
    "/api/tools/probe": _handle_probe,
    "/api/tools/coverage": _handle_coverage,
    "/api/candidates": _handle_candidates,
    "/api/search": _handle_search,
    "/api/teams": _handle_teams,
    "/api/subscription": _handle_subscription,
    "/api/solana/config": _handle_solana_config,
    "/api/solana/quota": _handle_solana_quota,
    "/api/solana/attestations": _handle_solana_attestations,
    "/api/solana/verify": _handle_solana_verify,
    "/api/vault/download": _handle_vault_download,
    "/api/vault/list": _handle_vault_list,
    "/api/backup/bundle": _handle_backup_bundle,
    "/api/leases/active": _handle_leases_active,
    "/api/leases": _handle_leases_list,
}

REVIEW_PREFIX = "/api/candidates/"
REVIEW_SUFFIX = "/review"


def _dispatch(
    root: Path,
    method: str,
    path: str,
    params: dict[str, list[str]],
    body: Any,
    auth_header: str = "",
) -> Any:
    if method == "POST" and path.startswith(REVIEW_PREFIX) and path.endswith(REVIEW_SUFFIX):
        candidate_id = unquote(path[len(REVIEW_PREFIX) : -len(REVIEW_SUFFIX)])
        return _handle_review(root, candidate_id, body)
    if method == "POST" and path == "/api/solana/config":
        return _handle_solana_config_update(root, body)
    if method == "POST" and path == "/api/vault/pin_ipfs":
        return _handle_vault_pin_ipfs(root, body)
    if method == "POST" and path == "/api/solana/purchase":
        return _handle_solana_purchase(root, body)
    if method == "POST" and path == "/api/solana/commit":
        return _handle_solana_commit(root, body)
    if method == "POST" and path == "/api/vault/upload":
        return _handle_vault_upload(root, body)
    if method == "POST" and path == "/api/backup/restore":
        return _handle_backup_restore(root, body)
    if method == "POST" and path == "/api/leases/acquire":
        return _handle_leases_acquire(root, body)
    if method == "POST" and path == "/api/leases/release":
        return _handle_leases_release(root, body)
    # webauth 依赖本模块的 ApiError，延迟导入避免循环
    from lwm import webauth

    if method == "POST" and path == "/api/auth/register":
        return webauth.handle_register(root, body)
    if method == "POST" and path == "/api/auth/login":
        return webauth.handle_login(root, body)
    if method == "POST" and path == "/api/auth/wallet/nonce":
        return webauth.handle_wallet_nonce(root, body)
    if method == "POST" and path == "/api/auth/wallet/verify":
        return webauth.handle_wallet_verify(root, body, auth_header)
    if method == "GET" and path == "/api/auth/me":
        return webauth.handle_me(root, body, auth_header)
    if method == "POST" and path == "/api/auth/logout":
        return webauth.handle_logout(root, body, auth_header)
    handler = ROUTES.get(path)
    if handler is None:
        raise KeyError(path)
    return handler(root, params, body)


def make_handler(root: Path) -> type[BaseHTTPRequestHandler]:
    class GatewayHandler(BaseHTTPRequestHandler):
        server_version = "lwm/gateway"
        protocol_version = "HTTP/1.1"

        # ---- transport ----

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _ok(self, data: Any) -> None:
            self._send_json(HTTPStatus.OK, {"ok": True, "data": data})

        def _fail(self, status: HTTPStatus, code: str, message: str, detail: Any = None) -> None:
            self._send_json(status, {"ok": False, "error": {"code": code, "message": message, "detail": detail}})

        def _read_body(self) -> Any:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return None
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except ValueError:
                return None

        def _serve(self, method: str) -> None:
            # http.server 按 ISO-8859-1 解码请求行，中文 query 会变乱码，
            # 需还原字节后按 UTF-8 重新解码，否则 /api/search?q=中文 永远搜不到。
            try:
                raw_path = self.path.encode("iso-8859-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                raw_path = self.path
            parsed = urlparse(raw_path)
            params = parse_qs(parsed.query)
            body = self._read_body() if method == "POST" else None
            # 候选 id 可能含中文/空格，同样按 UTF-8 还原
            path = unquote(parsed.path)
            try:
                data = _dispatch(root, method, path, params, body, self.headers.get("Authorization", ""))
            except KeyError:
                self._fail(HTTPStatus.NOT_FOUND, "E_NOT_FOUND", f"no route for {path}")
                return
            except ApiError as exc:
                self._fail(exc.status, exc.code, str(exc), exc.detail)
                return
            except ValueError as exc:  # 参数/字段缺失或非法
                self._fail(HTTPStatus.BAD_REQUEST, "E_SCHEMA", str(exc))
                return
            except PermissionError as exc:
                self._fail(HTTPStatus.FORBIDDEN, "E_FORBIDDEN", str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - 网关边界，统一兜底
                self._fail(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "E_INTERNAL",
                    f"{type(exc).__name__}: {exc}",
                    traceback.format_exc(limit=5).splitlines(),
                )
                return
            self._ok(data)

        def do_GET(self) -> None:
            self._serve("GET")

        def do_POST(self) -> None:
            self._serve("POST")

        def do_OPTIONS(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    return GatewayHandler


def serve_gateway(
    root: Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    root = root.resolve()
    handler = make_handler(root)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving LLM-WorkMem JSON gateway at http://{host}:{port}/  (root={root})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
