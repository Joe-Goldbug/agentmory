"""Tests for lwm/lease.py: task lease concurrency and optimistic conflict management."""

from __future__ import annotations

import time
from pathlib import Path

from lwm import lease


def test_acquire_and_release_lease(tmp_path: Path) -> None:
    proj_id = "test-project-1"
    agent_1 = "Claude-Code"

    # 1. 申请租约
    res = lease.acquire_lease(tmp_path, proj_id, agent_1, objective="重构认证模块", ttl_seconds=60)
    assert res["ok"] is True
    assert res["conflict"] is False
    assert res["agent_name"] == agent_1

    # 2. 查询活跃租约
    active = lease.get_active_lease(tmp_path, proj_id)
    assert active is not None
    assert active["agent_name"] == agent_1
    assert active["objective"] == "重构认证模块"

    # 3. 释放租约
    rel = lease.release_lease(tmp_path, proj_id, res["lease_id"])
    assert rel["ok"] is True
    assert rel["released"] is True

    # 4. 确认已无活跃租约
    assert lease.get_active_lease(tmp_path, proj_id) is None


def test_lease_concurrency_conflict_and_force_takeover(tmp_path: Path) -> None:
    proj_id = "test-project-2"
    agent_1 = "Claude-Code"
    agent_2 = "Cursor"

    # Agent 1 持有租约
    res1 = lease.acquire_lease(tmp_path, proj_id, agent_1, objective="排查支付 Bug", ttl_seconds=60)
    assert res1["ok"] is True

    # Agent 2 尝试申请，发生冲突告警
    res2 = lease.acquire_lease(tmp_path, proj_id, agent_2, objective="修改UI样式", ttl_seconds=60, force=False)
    assert res2["ok"] is False
    assert res2["conflict"] is True
    assert "任务冲突" in res2["message"]
    assert res2["active_lease"]["agent_name"] == agent_1

    # Agent 2 强制接管 (force=True)
    res3 = lease.acquire_lease(tmp_path, proj_id, agent_2, objective="修改UI样式", ttl_seconds=60, force=True)
    assert res3["ok"] is True
    assert res3["agent_name"] == agent_2

    # 活跃租约更新为 Agent 2
    active = lease.get_active_lease(tmp_path, proj_id)
    assert active is not None
    assert active["agent_name"] == agent_2


def test_expired_lease_auto_invalidates(tmp_path: Path) -> None:
    proj_id = "test-project-3"
    # 设置 1 秒超短 TTL
    res = lease.acquire_lease(tmp_path, proj_id, "Antigravity", objective="短时任务", ttl_seconds=1)
    assert res["ok"] is True

    time.sleep(1.1)
    # 过期后查询应为 None
    assert lease.get_active_lease(tmp_path, proj_id) is None
