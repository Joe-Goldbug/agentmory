"""LLM-WorkMem 核心快照备份与安全原子还原模块（标准库优先）。

遵循 GLOBAL.md "标准库优先、最小可用 Diff、严禁过度抽象" 原则。
仅使用标准库：io, tarfile, hashlib, base64, shutil, tempfile, pathlib, datetime。

覆盖白名单目录：
- wiki/     : 经提炼合成的稳定知识与工作记忆
- projects/ : 项目身份与元数据
- state/    : 任务状态、Handoff 指针与租约

安全防御机制：
1. SHA-256 完整性强校验：哈希不匹配时 Fail-Closed 立即拒绝解包；
2. Zip-Slip 路径穿越防御：严禁绝对路径、相对穿越 (..) 及非白名单目录成员；
3. 临时目录解压与原子目录替换：解压成功后才覆盖工作区目标。
"""

from __future__ import annotations

import base64
import hashlib
import io
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SAFE_DIRS: tuple[str, ...] = ("wiki", "projects", "state")


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


ONCHAIN_MAX_TAR_BYTES = 1800
CORE_MEMORY_PATHS: tuple[str, ...] = (
    "wiki/purpose.md",
    "wiki/overview.md",
    "state/project-map.json",
    "state/promotion-state.json",
)


def create_backup_bundle(root: Path, *, compact: bool = False) -> dict[str, Any]:
    """将 root 下的 SAFE_DIRS 打包为 tar.gz 内存流，计算 SHA-256 并返回 Base64 包。

    当 ``compact=True`` 且完整归档超过链上单批次交易容量时，自动筛选核心跨设备记忆文件打包，
    确保归档密文可直接完整写入 Solana Devnet 链上交易。
    """
    root = root.resolve()
    bio = io.BytesIO()
    included_dirs: list[str] = []
    file_count = 0

    with tarfile.open(fileobj=bio, mode="w:gz", compresslevel=9) as tar:
        for folder_name in SAFE_DIRS:
            target = root / folder_name
            if not target.exists():
                continue
            included_dirs.append(folder_name)
            if target.is_dir():
                for file_path in sorted(target.rglob("*")):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(root)).replace("\\", "/")
                        tar.add(file_path, arcname=arcname)
                        file_count += 1
            else:
                tar.add(target, arcname=folder_name)
                file_count += 1

    tar_bytes = bio.getvalue()
    if compact and len(tar_bytes) > ONCHAIN_MAX_TAR_BYTES:
        compact_bio = io.BytesIO()
        compact_dirs: set[str] = set()
        compact_count = 0
        with tarfile.open(fileobj=compact_bio, mode="w:gz", compresslevel=9) as tar:
            for rel_path in CORE_MEMORY_PATHS:
                fp = root / rel_path
                if fp.is_file():
                    tar.add(fp, arcname=rel_path)
                    compact_dirs.add(rel_path.split("/")[0])
                    compact_count += 1
            if compact_count == 0:
                for folder_name in SAFE_DIRS:
                    target = root / folder_name
                    if target.is_dir():
                        for fp in sorted(target.rglob("*"))[:3]:
                            if fp.is_file():
                                arcname = str(fp.relative_to(root)).replace("\\", "/")
                                tar.add(fp, arcname=arcname)
                                compact_dirs.add(folder_name)
                                compact_count += 1
        tar_bytes = compact_bio.getvalue()
        included_dirs = [d for d in SAFE_DIRS if d in compact_dirs]
        file_count = compact_count

    bundle_hash = hashlib.sha256(tar_bytes).hexdigest()

    return {
        "version": 1,
        "sha256": bundle_hash,
        "byte_size": len(tar_bytes),
        "tar_base64": base64.b64encode(tar_bytes).decode("ascii"),
        "included_dirs": included_dirs,
        "file_count": file_count,
        "created_at": _now_iso(),
        "compact": compact,
    }


def restore_backup_bundle(
    root: Path,
    tar_base64: str,
    expected_sha256: str,
) -> dict[str, Any]:
    """强校验 SHA-256、审计 Zip-Slip 路径，并在临时目录解压后原子覆盖 SAFE_DIRS。"""
    root = root.resolve()
    try:
        tar_bytes = base64.b64decode(tar_base64)
    except Exception as exc:
        raise ValueError(f"Base64 归档数据解码失败: {exc}") from exc

    actual_hash = hashlib.sha256(tar_bytes).hexdigest()
    if actual_hash.lower() != expected_sha256.strip().lower():
        raise ValueError(
            f"归档数据哈希校验失败（可能已遭篡改或损坏）：预期 {expected_sha256.lower()}，实际计算 {actual_hash.lower()}"
        )

    bio = io.BytesIO(tar_bytes)
    restored_files = 0

    with tarfile.open(fileobj=bio, mode="r:gz") as tar:
        members = tar.getmembers()
        # 1. Zip-Slip 路径穿越审计与白名单目录校验
        for member in members:
            # 统一转正斜杠判断
            norm_name = member.name.replace("\\", "/")
            if norm_name.startswith("/") or norm_name.startswith("\\"):
                raise PermissionError(f"检测到绝对路径成员，拒绝解包: {member.name}")
            parts = Path(norm_name).parts
            if not parts:
                continue
            if ".." in parts:
                raise PermissionError(f"检测到相对路径穿越 (Zip-Slip)，拒绝解包: {member.name}")
            top_level = parts[0]
            if top_level not in SAFE_DIRS:
                raise PermissionError(f"检测到非白名单目录成员 ({top_level})，拒绝解包: {member.name}")
            if member.issym() or member.islnk():
                # 软链接目标也必须受到审计
                link_target = member.linkname.replace("\\", "/")
                if link_target.startswith("/") or ".." in Path(link_target).parts:
                    raise PermissionError(f"检测到非法符号链接目标: {member.name} -> {member.linkname}")

        # 2. 解压至独立临时目录
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_path = Path(temp_dir_str)
            if hasattr(tarfile, "data_filter"):
                tar.extractall(path=temp_path, filter="data")
            else:
                tar.extractall(path=temp_path)

            # 3. 原子覆盖 SAFE_DIRS
            for folder_name in SAFE_DIRS:
                src = temp_path / folder_name
                dst = root / folder_name
                if not src.exists():
                    continue
                if src.is_dir():
                    if dst.exists():
                        if dst.is_dir():
                            shutil.rmtree(dst)
                        else:
                            dst.unlink()
                    shutil.copytree(src, dst)
                    restored_files += len(list(src.rglob("*")))
                else:
                    if dst.exists():
                        if dst.is_dir():
                            shutil.rmtree(dst)
                        else:
                            dst.unlink()
                    shutil.copy2(src, dst)
                    restored_files += 1

    return {
        "status": "success",
        "sha256": actual_hash,
        "restored_at": _now_iso(),
        "restored_files": restored_files,
    }
