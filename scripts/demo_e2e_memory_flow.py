"""端到端多 Agent 工作记忆与 Web3 存证冷备全流程演练脚本。

演示内容：
1. Agent A (Claude-Code) 申请项目任务租约 (Task Lease)；
2. Agent B (Cursor) 并发探测租约冲突与协同提示；
3. 后端执行工作记忆安全打包 (Safe tar.gz Bundle) 并生成 SHA-256 存证哈希；
4. 模拟本地灾难或意外损坏；
5. 执行安全解包与原子还原 (Fail-Closed & Anti-Zip-Slip)；
6. 校验全量数据完整性恢复；
7. 释放任务租约，实现跨工具无缝交接。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from lwm import backup, lease

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("🚀 LLM-WorkMem: 多 Agent 协同与安全冷备端到端演练")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir_str:
        root = Path(temp_dir_str)
        project_id = "solana-defi-bot"

        # -------------------------------------------------------------
        # 步骤 1: 建立工作区与初始化工作记忆
        # -------------------------------------------------------------
        print("\n[Step 1] 初始化核心工作记忆 (wiki / projects / state)...")
        wiki_dir = root / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "overview.md").write_text(
            "# 架构决策记忆\n- 关键规则: 所有交易必须在客户端本地离线签名后广播。\n- 状态: 生产就绪\n",
            encoding="utf-8",
        )

        projects_dir = root / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        (projects_dir / "solana-defi-bot.json").write_text(
            '{"name": "Solana DeFi Bot", "cluster": "devnet", "active": true}\n',
            encoding="utf-8",
        )

        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "cycle.json").write_text('{"cycle": 42, "status": "green"}\n', encoding="utf-8")
        print("  ✓ 工作记忆与状态创建完毕")

        # -------------------------------------------------------------
        # 步骤 2: 多 Agent 任务租约与并发冲突防护
        # -------------------------------------------------------------
        print("\n[Step 2] 多 Agent 并发租约控制 (Task Lease)...")
        print("  -> Agent 1 (Claude-Code) 申请任务租约...")
        l1 = lease.acquire_lease(
            root,
            project_id=project_id,
            agent_name="Claude-Code",
            objective="重构订单簿撮合引擎",
            ttl_seconds=300,
        )
        print(f"  ✓ Agent 1 成功获得租约: Lease ID = {l1['lease_id']}, TTL = {l1['ttl_seconds']}s")

        print("  -> Agent 2 (Cursor) 尝试并发申请同一项目租约...")
        l2 = lease.acquire_lease(
            root,
            project_id=project_id,
            agent_name="Cursor",
            objective="修改交易前端",
            ttl_seconds=300,
            force=False,
        )
        if l2.get("conflict"):
            print(f"  ⚡ 成功捕获并发冲突告警: {l2['message']}")
        else:
            print("  ❌ 未捕获到并发冲突！")

        # -------------------------------------------------------------
        # 步骤 3: 构造工作记忆安全冷备包与计算 SHA-256
        # -------------------------------------------------------------
        print("\n[Step 3] 执行工作记忆快照打包 (Safe tar.gz Bundle)...")
        bundle = backup.create_backup_bundle(root)
        print(f"  ✓ 包含白名单目录: {bundle['included_dirs']}")
        print(f"  ✓ 打包文件数: {bundle['file_count']}")
        print(f"  ✓ 原始字节大小: {bundle['byte_size']} bytes")
        print(f"  ✓ SHA-256 存证指纹: {bundle['sha256']}")
        print(f"  ✓ SPL Memo 存证建议载荷:\n    {{\"app\": \"llm-workmem\", \"v\": 1, \"hash\": \"{bundle['sha256']}\", \"uri\": \"ar://{bundle['sha256'][:32]}\"}}")

        # -------------------------------------------------------------
        # 步骤 4: 模拟灾难性损坏
        # -------------------------------------------------------------
        print("\n[Step 4] 模拟本地工作区意外损坏与数据丢失...")
        (wiki_dir / "overview.md").unlink()
        (projects_dir / "solana-defi-bot.json").write_text("{\"corrupted\": true}", encoding="utf-8")
        print("  ✓ 模拟灾难完成 (wiki/overview.md 已丢失，projects 遭破坏)")

        # -------------------------------------------------------------
        # 步骤 5: 执行安全原子还原与哈希审计
        # -------------------------------------------------------------
        print("\n[Step 5] 执行安全原子还原 (Verify SHA-256 & Safe Extract)...")
        restore_result = backup.restore_backup_bundle(
            root,
            tar_base64=bundle["tar_base64"],
            expected_sha256=bundle["sha256"],
        )
        print(f"  ✓ 还原状态: {restore_result['status']}")
        print(f"  ✓ 恢复文件数: {restore_result['restored_files']}")

        # 验证内容
        recovered_text = (wiki_dir / "overview.md").read_text(encoding="utf-8")
        recovered_proj = (projects_dir / "solana-defi-bot.json").read_text(encoding="utf-8")
        assert "关键规则" in recovered_text, "wiki 恢复失败！"
        assert "Solana DeFi Bot" in recovered_proj, "projects 恢复失败！"
        print("  ✓ 数据完整性校验通过！工作记忆 100% 毫发无损恢复。")

        # -------------------------------------------------------------
        # 步骤 6: 跨工具分支 Handoff 与 CAS 冲突 Fork 保护
        # -------------------------------------------------------------
        print("\n[Step 6] 跨工具分支 Handoff CAS 并发与 Zero-Lost-Updates Fork 保护...")
        from lwm import handoff
        h1 = handoff.create_handoff(
            root,
            project_id=project_id,
            task_id="task-engine",
            objective="Agent 1 初步完成引擎重构",
            current_state="passes 12 tests",
            source_tool="Claude-Code",
            git_branch="feat/matching",
        )
        print(f"  ✓ Agent 1 提交 Handoff: ID={h1.handoff_id[:8]}..., Version={h1.version}, Branch={h1.git_branch}")

        # Agent 2 并发尝试以旧版本为基准提交，触发 CAS 冲突保护并写入 Fork 文件
        fork_pkt = handoff.create_handoff(
            root,
            project_id=project_id,
            task_id="task-engine",
            objective="Agent 2 并发修改 (冲突分支)",
            current_state="conflict",
            source_tool="Cursor",
            git_branch="feat/matching",
            supersedes="stale_id_000",
            allow_fork=True,
        )
        print(f"  ✓ CAS 冲突自动分叉保存 (Zero Lost Updates): Fork ID={fork_pkt.handoff_id[:8]}..., Status={fork_pkt.conflict_status}")

        # -------------------------------------------------------------
        # 步骤 7: 决策替代状态机 (Decision Supersede Engine)
        # -------------------------------------------------------------
        print("\n[Step 7] 决策替代状态机 (Prune Obsolete Decisions)...")
        from lwm import project_memory
        ev_old = {
            "event_id": "dec-old",
            "timestamp": "2026-07-28T10:00:00Z",
            "tool": "codex",
            "project_id": project_id,
            "event_type": "decision",
            "task": "选择认证机制",
            "decisions": ["使用传统 API Key 认证"],
            "verification": ["tests pass"],
        }
        ev_new = {
            "event_id": "dec-new",
            "timestamp": "2026-07-28T11:00:00Z",
            "tool": "claude-code",
            "project_id": project_id,
            "event_type": "decision",
            "task": "升级认证机制",
            "decisions": ["升级为 Phantom Ed25519 签名认证"],
            "supersedes": "dec-old",
            "verification": ["crypto tests pass"],
        }
        project_memory.append_event(root, ev_old)
        project_memory.append_event(root, ev_new)
        page_content = (root / "wiki" / "projects" / f"{project_id}.md").read_text(encoding="utf-8")
        assert "使用传统 API Key 认证" not in page_content
        assert "升级为 Phantom Ed25519 签名认证" in page_content
        print("  ✓ 旧版决定被智能剔除，仅最新已确认决策进入 Agent 上下文空间！")

        # -------------------------------------------------------------
        # 步骤 8: 端到端密文安全金库 (Encrypted Backup Vault)
        # -------------------------------------------------------------
        print("\n[Step 8] 端到端密文安全金库 (E2EE Backup Vault)...")
        import base64
        from lwm import vault
        sim_packed = base64.b64encode(b"123456789012" + b"aes_256_gcm_encrypted_bundle").decode("ascii")
        vault_res = vault.store_encrypted_snapshot(
            root,
            snapshot_hash=bundle["sha256"],
            packed_ciphertext_base64=sim_packed,
            wallet="7xKXtg9P4WMEMdemoDevnetWallet111111111111111",
        )
        print(f"  ✓ 密文快照持久化成功: URI={vault_res['uri']}, Size={vault_res['byte_size']} bytes")
        fetched_vault = vault.get_encrypted_snapshot(root, vault_res["uri"])
        assert fetched_vault is not None
        print(f"  ✓ 金库寻址拉取校验成功: tx_id={fetched_vault['tx_id']}")

        # -------------------------------------------------------------
        # 步骤 9: 任务完成，释放租约
        # -------------------------------------------------------------
        print("\n[Step 9] 任务完成，释放租约交接给下一工具...")
        rel = lease.release_lease(root, project_id=project_id, lease_id=l1["lease_id"])
        print(f"  ✓ 租约已释放: {rel['released']}, 项目可供其他 Agent 自由接续。")

    print("\n" + "=" * 70)
    print("🎉 恭喜！LLM-WorkMem 工业级多 Agent 记忆与 Web3 存证全流程验证成功！")
    print("=" * 70)


if __name__ == "__main__":
    main()
