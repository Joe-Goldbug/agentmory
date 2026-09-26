"""Manifest-bound data-owner migration for the local runtime.

The migration is intentionally separate from schedule preparation. A caller
must present the exact read-only manifest and approval id that was reviewed;
the module then verifies the snapshot again before changing ownership.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DATA_ENTITY_NAMES = (
    "wiki",
    "raw",
    "automation",
    "state",
    "llms.txt",
    "llms-full.txt",
    "llms.json",
    "knowledge-digest.html",
    "knowledge-digest.pages",
    "lwm-sources.json",
)


class MigrationApprovalError(RuntimeError):
    """The migration snapshot or approval boundary is invalid."""


@dataclass(frozen=True)
class MigrationVerification:
    manifest_path: str
    manifest_sha256: str
    approval_id: str
    root: str
    runtime_base: str
    checked_entries: int
    backup_archive: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tree_hash(path: Path) -> str:
    """Hash files, directories, and symlinks without following top-level links."""

    if path.is_symlink():
        return _sha256_bytes(f"symlink->{os.readlink(path)}".encode())
    if path.is_file():
        return _sha256_bytes(path.read_bytes())
    if not path.is_dir():
        return ""
    rows: list[str] = []
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path).as_posix()
        if child.is_symlink():
            rows.append(f"L {relative} -> {os.readlink(child)}")
        elif child.is_file():
            rows.append(f"F {relative} {_sha256_bytes(child.read_bytes())}")
        elif child.is_dir():
            rows.append(f"D {relative}")
    return _sha256_bytes(("\n".join(rows) + "\n").encode())


def _absolute(path: Path) -> Path:
    return path.expanduser().absolute()


def _under(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _git_value(root: Path, *args: str) -> str:
    if not (root / ".git").exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _source_dirty_hash(root: Path) -> str:
    output = _git_value(root, "status", "--porcelain")
    relevant: list[str] = []
    for line in output.splitlines():
        path = line[3:].strip() if len(line) >= 4 else ""
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1]
        if path.startswith(("lwm/", "mcp/", "integrations/", "scripts/", "adapters/")) or path in {
            "AGENTS.md",
            "GLOBAL.md",
            "pyproject.toml",
        }:
            relevant.append(line)
    return _sha256_bytes("\n".join(relevant).encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MigrationApprovalError(message)


def _check_preview_artifact(payload: dict[str, Any], key: str) -> Path:
    previews = payload.get("preview_artifacts")
    _require(isinstance(previews, dict), "manifest preview artifacts are missing")
    artifact = previews.get(key)
    _require(isinstance(artifact, dict), f"manifest preview artifact missing: {key}")
    path_value = artifact.get("path")
    expected_hash = artifact.get("sha256")
    _require(isinstance(path_value, str) and Path(path_value).is_absolute(), f"invalid artifact path: {key}")
    _require(isinstance(expected_hash, str) and expected_hash, f"invalid artifact hash: {key}")
    path = Path(path_value)
    _require(path.exists() or path.is_symlink(), f"manifest artifact is missing: {path}")
    _require(tree_hash(path) == expected_hash, f"manifest artifact changed: {path}")
    return path


def _check_entry_topology(
    *,
    entry_type: str,
    path: Path,
    root: Path,
    runtime_base: Path,
    data_root: Path,
    launch_agents: Path,
) -> None:
    allowed = (root, runtime_base, launch_agents)
    _require(
        any(_under(path, base) for base in allowed),
        f"manifest entry escapes approved roots: {path}",
    )
    if entry_type == "data_entity" and _under(path, data_root):
        name = path.relative_to(data_root).as_posix()
        if path.is_symlink():
            expected = root / name
            _require(
                name == "state" and path.resolve() == expected.resolve(),
                f"unexpected runtime data symlink: {path}",
            )
    if entry_type == "repository_access_path" and _under(path, root):
        name = path.relative_to(root).as_posix()
        if name in DATA_ENTITY_NAMES and path.is_symlink():
            expected = data_root / name
            _require(
                path.resolve() == expected.resolve(),
                f"repository access path points outside DATA_ROOT: {path}",
            )


def verify_manifest(
    manifest_path: Path,
    approval_id: str,
    *,
    root: Path,
    runtime_base: Path,
) -> MigrationVerification:
    """Verify the reviewed manifest and all mutable hashes before migration."""

    manifest_path = manifest_path.expanduser().resolve()
    _require(manifest_path.is_file(), f"migration manifest is missing: {manifest_path}")
    raw_manifest = manifest_path.read_bytes()
    manifest_hash = _sha256_bytes(raw_manifest)
    expected_id = f"lwm9b-{manifest_hash[:16]}"
    _require(approval_id == expected_id, f"approval id mismatch; expected {expected_id}")
    try:
        payload = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise MigrationApprovalError(f"invalid migration manifest JSON: {exc}") from exc
    _require(isinstance(payload, dict), "migration manifest must be a JSON object")
    _require(payload.get("schema_version") == 1, "unsupported migration manifest schema")
    _require(payload.get("read_only") is True, "migration manifest must be read-only preview")

    root = root.expanduser().resolve()
    runtime_base = runtime_base.expanduser().resolve()
    data_root = runtime_base / "llm-workmem"
    _require(payload.get("root") == str(root), "migration root differs from manifest")
    _require(payload.get("runtime_base") == str(runtime_base), "runtime base differs from manifest")
    _require(payload.get("data_root") == str(data_root), "data root differs from manifest")
    manifest_launch_agents = payload.get("launch_agents")
    if manifest_launch_agents is None:
        launch_agents = runtime_base.parent.parent / "LaunchAgents"
    else:
        _require(
            isinstance(manifest_launch_agents, str) and Path(manifest_launch_agents).is_absolute(),
            "manifest launch-agents path is invalid",
        )
        launch_agents = Path(manifest_launch_agents)
    _check_preview_artifact(payload, "backup_archive")

    source_revision = str(payload.get("source_revision") or "")
    current_revision = _git_value(root, "rev-parse", "HEAD")
    if source_revision and source_revision != "unknown" and current_revision:
        _require(source_revision == current_revision, "source revision changed since manifest preview")
    source_dirty_hash = str(payload.get("source_dirty_hash") or "")
    current_dirty_hash = _source_dirty_hash(root)
    if source_dirty_hash and current_dirty_hash:
        _require(source_dirty_hash == current_dirty_hash, "source dirty state changed since manifest preview")

    entries = payload.get("entries")
    _require(isinstance(entries, list), "migration manifest entries are missing")
    _require(payload.get("entry_count") == len(entries), "migration manifest entry count is invalid")
    for raw_entry in entries:
        _require(isinstance(raw_entry, dict), "migration manifest contains an invalid entry")
        entry_type = str(raw_entry.get("type") or "")
        path_value = raw_entry.get("path")
        expected_hash = raw_entry.get("current_sha256")
        _require(isinstance(path_value, str) and Path(path_value).is_absolute(), "manifest entry path is invalid")
        _require(isinstance(expected_hash, str), f"manifest entry hash is invalid: {path_value}")
        path = Path(path_value)
        _check_entry_topology(
            entry_type=entry_type,
            path=path,
            root=root,
            runtime_base=runtime_base,
            data_root=data_root,
            launch_agents=launch_agents,
        )
        _require(
            tree_hash(path) == expected_hash,
            f"manifest entry changed since preview: {path}",
        )

    return MigrationVerification(
        manifest_path=str(manifest_path),
        manifest_sha256=manifest_hash,
        approval_id=approval_id,
        root=str(root),
        runtime_base=str(runtime_base),
        checked_entries=len(entries),
        backup_archive=str(payload["preview_artifacts"]["backup_archive"]["path"]),
    )


def _assert_post_migration_layout(root: Path, runtime_root: Path) -> None:
    for name in DATA_ENTITY_NAMES:
        runtime_path = runtime_root / name
        source_path = root / name
        _require(
            runtime_path.exists() and not runtime_path.is_symlink(),
            f"runtime data owner is not physical after migration: {runtime_path}",
        )
        _require(
            source_path.is_symlink() and source_path.resolve() == runtime_path.resolve(),
            f"repository access path is not linked to DATA_ROOT: {source_path}",
        )
    source_adapters = root / "adapters"
    runtime_adapters = runtime_root / "adapters"
    if source_adapters.exists() or source_adapters.is_symlink():
        _require(not source_adapters.is_symlink(), "checkout adapters must remain source-owned")
    if runtime_adapters.exists() or runtime_adapters.is_symlink():
        _require(not runtime_adapters.is_symlink(), "runtime adapters must remain a physical generated copy")


def apply_data_owner_migration(
    manifest_path: Path,
    approval_id: str,
    *,
    root: Path,
    runtime_base: Path,
    home: Path | None = None,
) -> dict[str, object]:
    """Apply only the manifest-approved local data ownership migration."""

    verification = verify_manifest(
        manifest_path,
        approval_id,
        root=root,
        runtime_base=runtime_base,
    )
    from lwm import harvest

    expected_runtime = harvest.runtime_paths(root, home=home).runtime_base
    _require(
        expected_runtime.resolve() == Path(verification.runtime_base).resolve(),
        "runtime base does not match the selected HOME/runtime layout",
    )
    runtime_root = harvest.materialize_data_layout(root, home=home, approved=True)
    _assert_post_migration_layout(Path(verification.root), runtime_root)
    return {
        **verification.as_dict(),
        "applied": True,
        "runtime_root": str(runtime_root),
        "scope": "data-owner-only; no app install, launchd reload, or project rebuild",
    }


__all__ = [
    "MigrationApprovalError",
    "MigrationVerification",
    "apply_data_owner_migration",
    "tree_hash",
    "verify_manifest",
]
