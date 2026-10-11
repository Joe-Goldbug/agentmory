"""Tests for lwm/backup.py: backup bundle creation and safe atomic restore."""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from lwm import backup


def test_backup_bundle_create_and_restore(tmp_path: Path) -> None:
    # 准备工作区目录与文件
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# Overview\nOriginal memory.", encoding="utf-8")

    proj_dir = tmp_path / "projects"
    proj_dir.mkdir(parents=True)
    (proj_dir / "demo.json").write_text('{"name": "demo"}', encoding="utf-8")

    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "loop_state.json").write_text('{"cycle": 1}', encoding="utf-8")

    # 1. 创建备份包
    bundle = backup.create_backup_bundle(tmp_path)
    assert bundle["version"] == 1
    assert bundle["byte_size"] > 0
    assert bundle["file_count"] == 3
    assert set(bundle["included_dirs"]) == {"wiki", "projects", "state"}
    assert len(bundle["sha256"]) == 64

    # 2. 模拟工作区数据损坏/被清空
    (wiki_dir / "overview.md").write_text("# Corrupted!", encoding="utf-8")
    (proj_dir / "demo.json").unlink()

    # 3. 执行还原
    res = backup.restore_backup_bundle(tmp_path, bundle["tar_base64"], bundle["sha256"])
    assert res["status"] == "success"
    assert res["sha256"] == bundle["sha256"]

    # 4. 验证完全恢复
    assert (wiki_dir / "overview.md").read_text(encoding="utf-8") == "# Overview\nOriginal memory."
    assert (proj_dir / "demo.json").read_text(encoding="utf-8") == '{"name": "demo"}'


def test_restore_rejects_hash_tampering(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "test.md").write_text("content", encoding="utf-8")

    bundle = backup.create_backup_bundle(tmp_path)
    fake_hash = "0" * 64

    # 篡改哈希时必须抛出 ValueError 并拒绝解包
    with pytest.raises(ValueError, match="哈希校验失败"):
        backup.restore_backup_bundle(tmp_path, bundle["tar_base64"], fake_hash)


def test_restore_rejects_zip_slip_parent_traversal(tmp_path: Path) -> None:
    # 构造恶意包含 .. 的 tarball
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tar:
        ti = tarfile.TarInfo(name="wiki/../malicious.txt")
        data = b"evil content"
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))

    tar_bytes = bio.getvalue()
    sha256 = hashlib.sha256(tar_bytes).hexdigest()
    b64 = base64.b64encode(tar_bytes).decode("ascii")

    with pytest.raises(PermissionError, match="Zip-Slip"):
        backup.restore_backup_bundle(tmp_path, b64, sha256)


def test_restore_rejects_non_safe_dir_membership(tmp_path: Path) -> None:
    # 构造包含非白名单目录 (如 raw/ 或 etc/passwd) 的 tarball
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tar:
        ti = tarfile.TarInfo(name="etc/shadow")
        data = b"root:x:0:0"
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))

    tar_bytes = bio.getvalue()
    sha256 = hashlib.sha256(tar_bytes).hexdigest()
    b64 = base64.b64encode(tar_bytes).decode("ascii")

    with pytest.raises(PermissionError, match="非白名单目录"):
        backup.restore_backup_bundle(tmp_path, b64, sha256)
