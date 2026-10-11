"""多 Agent 任务租约与并发冲突防护模块（标准库优先）。

遵循 GLOBAL.md 原则：仅使用 json, pathlib, time, uuid。
存储路径：``state/task_leases.json``

设计理念：
- 乐观软锁机制（Optimistic Soft Lease）：
  当多个 Agent（例如 Claude Code、Cursor、Antigravity）并行处理同一项目时，
  记录当前活跃持约者。若存在他人有效租约，在上下文和 API 中产生显式冲突告警；
  支持开发者明确指令下的强制接管（Force Takeover），兼顾协同安全与开发心流。
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEASES_FILE = "state/task_leases.json"
DEFAULT_TTL_SECONDS = 600  # 默认 10 分钟自动超时释放


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _store_path(root: Path) -> Path:
    return root / LEASES_FILE


def _load_leases(root: Path) -> dict[str, dict[str, Any]]:
    path = _store_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (ValueError, OSError):
        pass
    return {}


def _save_leases(root: Path, data: dict[str, dict[str, Any]]) -> None:
    path = _store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active_lease(root: Path, project_id: str) -> dict[str, Any] | None:
    """获取指定项目的当前活跃租约；若已过期则自动视为无租约。"""
    project_id = project_id.strip()
    leases = _load_leases(root)
    lease = leases.get(project_id)
    if not lease:
        return None
    now = time.time()
    if lease.get("expires_at", 0) <= now:
        # 已过期
        return None
    remaining_seconds = int(lease["expires_at"] - now)
    lease_copy = dict(lease)
    lease_copy["remaining_seconds"] = remaining_seconds
    return lease_copy


def acquire_lease(
    root: Path,
    project_id: str,
    agent_name: str,
    objective: str = "",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    force: bool = False,
) -> dict[str, Any]:
    """申请或续期项目任务租约。若存在他人活跃租约且 force=False，返回冲突告警。"""
    project_id = project_id.strip()
    agent_name = agent_name.strip()
    leases = _load_leases(root)
    current = get_active_lease(root, project_id)
    now = time.time()

    # 存在未过期的他人租约且未指定强制覆盖
    if current and current.get("agent_name") != agent_name and not force:
        return {
            "ok": False,
            "conflict": True,
            "message": (
                f"任务冲突：检测到 Agent [{current.get('agent_name')}] 正在处理该项目"
                f"（租约剩余 {current.get('remaining_seconds')}s，目标: {current.get('objective', '无')}）。"
                f"如需接管请指定 force=True。"
            ),
            "active_lease": current,
        }

    lease_id = uuid.uuid4().hex[:12]
    new_lease = {
        "lease_id": lease_id,
        "project_id": project_id,
        "agent_name": agent_name,
        "objective": objective,
        "acquired_at": now,
        "acquired_at_iso": _now_iso(),
        "expires_at": now + ttl_seconds,
        "ttl_seconds": ttl_seconds,
    }
    leases[project_id] = new_lease
    _save_leases(root, leases)

    result = dict(new_lease)
    result["ok"] = True
    result["conflict"] = False
    result["remaining_seconds"] = ttl_seconds
    return result


def release_lease(root: Path, project_id: str, lease_id: str | None = None) -> dict[str, Any]:
    """主动释放项目任务租约。"""
    project_id = project_id.strip()
    leases = _load_leases(root)
    if project_id not in leases:
        return {"ok": True, "released": False, "message": "该项目当前无活跃租约"}

    current = leases[project_id]
    if lease_id and current.get("lease_id") != lease_id:
        return {"ok": False, "released": False, "message": "租约 ID 不匹配，无法释放"}

    del leases[project_id]
    _save_leases(root, leases)
    return {"ok": True, "released": True, "project_id": project_id}


def list_active_leases(root: Path) -> list[dict[str, Any]]:
    """列出系统中所有当前有效的租约。"""
    leases = _load_leases(root)
    now = time.time()
    active = []
    for pid, l in leases.items():
        if l.get("expires_at", 0) > now:
            item = dict(l)
            item["remaining_seconds"] = int(l["expires_at"] - now)
            active.append(item)
    return active
