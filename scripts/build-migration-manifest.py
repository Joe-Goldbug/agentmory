#!/usr/bin/env python3
"""Build a read-only LLM-WorkMem migration manifest.

This command only reads the checkout and runtime paths and writes the manifest
to the explicitly requested output path. It never copies, removes, relinks,
installs, or reloads launchd. The manifest is the review input for a later
migration, not the migration itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    type: str
    exists: bool
    current_sha256: str
    action: str
    target_owner: str
    backup: str
    rollback: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _artifact(path: Path, *, kind: str) -> dict[str, object]:
    return {
        "kind": kind,
        "path": str(path),
        "exists": _exists(path),
        "sha256": _tree_hash(path),
    }


def _tree_hash(path: Path) -> str:
    """Hash a tree without following directory symlinks."""

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


def _exists(path: Path) -> bool:
    return path.is_symlink() or path.exists()


def _git_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_dirty_hash(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    relevant: list[str] = []
    for line in result.stdout.splitlines():
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


def _entry(
    path: Path,
    *,
    kind: str,
    action: str,
    owner: str,
    backup: Path,
    rollback: str,
) -> ManifestEntry:
    return ManifestEntry(
        path=str(path),
        type=kind,
        exists=_exists(path),
        current_sha256=_tree_hash(path),
        action=action,
        target_owner=owner,
        backup=str(backup),
        rollback=rollback,
    )


def _raw_entries(data_root: Path, backup_root: Path) -> Iterable[ManifestEntry]:
    base = data_root / "raw" / "events" / "processed"
    if not base.is_dir():
        return ()
    return tuple(
        _entry(
            path,
            kind="raw_event",
            action="append_only_no_touch",
            owner=str(data_root),
            backup=backup_root / "raw-events-before.sha256",
            rollback="(no rollback: processed raw evidence is immutable)",
        )
        for path in sorted(base.rglob("*.json"))
    )


def build_manifest(
    *,
    root: Path,
    runtime_base: Path,
    launch_agents: Path,
    backup_root: Path,
    backup_archive: Path | None = None,
    candidate_plist: Path | None = None,
    candidate_plist_diff: Path | None = None,
    staging_root: Path | None = None,
) -> dict[str, object]:
    data_root = runtime_base / "llm-workmem"
    entries: list[ManifestEntry] = []

    for label in ("com.ethan.lwm.harvest", "com.ethan.lwm.dream"):
        plist = launch_agents / f"{label}.plist"
        entries.append(
            _entry(
                plist,
                kind="launchd_plist",
                action="review_then_replace_after_approval",
                owner=str(launch_agents),
                backup=backup_root / "launchd" / plist.name,
                rollback=f"cp {backup_root / 'launchd' / plist.name} {plist}",
            )
        )

    app = runtime_base / "app"
    entries.append(
        _entry(
            app,
            kind="runtime_app",
            action="install_as_atomic_app_generation_after_approval",
            owner=str(runtime_base),
            backup=backup_root / "runtime-app",
            rollback=f"restore complete app generation from {backup_root / 'runtime-app'}",
        )
    )
    entries.append(
        _entry(
            runtime_base / "lwm-workmem" / "lwm",
            kind="legacy_runtime_code",
            action="remove_only_after_independent_import_and_approval",
            owner=str(data_root),
            backup=backup_root / "legacy-runtime-code",
            rollback=f"restore legacy code mirror from {backup_root / 'legacy-runtime-code'}",
        )
    )

    data_names = (
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
        "item",
    )
    for name in data_names:
        target = data_root / name
        entries.append(
            _entry(
                target,
                kind="data_entity",
                action="keep_or_move_to_runtime_owner_after_approval",
                owner=str(data_root),
                backup=backup_root / "data" / name,
                rollback=f"restore {backup_root / 'data' / name} to {target}",
            )
        )

    for name in data_names + ("GLOBAL.md",):
        link = root / name
        entries.append(
            _entry(
                link,
                kind="repository_access_path",
                action="preserve_or_replace_link_only_after_approval",
                owner=str(data_root),
                backup=backup_root / "repo-links" / name,
                rollback=f"restore access path metadata for {link}",
            )
        )

    entries.extend(_raw_entries(data_root, backup_root))
    grouped: dict[str, int] = {}
    for item in entries:
        grouped[item.type] = grouped.get(item.type, 0) + 1

    return {
        "schema_version": 1,
        "spec": "docs/superpowers/specs/2026-07-31-llm-workmem-unified-behavior-memory-interface.md",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_revision": _git_revision(root),
        "source_dirty_hash": _git_dirty_hash(root),
        "root": str(root),
        "runtime_base": str(runtime_base),
        "data_root": str(data_root),
        "launch_agents": str(launch_agents),
        "read_only": True,
        "entry_count": len(entries),
        "by_type": dict(sorted(grouped.items())),
        "allowed_generated_paths": [
            "adapters/**",
            "state/receipts/cycles/<cycle-id>.json",
            "state/receipts/latest-cycle.json",
            "state/receipts/last-attempt.json",
            "state/health.json",
            "state/receipts/contexts/<cycle-id>.json",
        ],
        "allowed_append_only_paths": ["raw/events/inbox/**", "raw/events/processed/**"],
        "entries": [asdict(item) for item in entries],
        "preview_artifacts": {
            "backup_archive": _artifact(backup_archive, kind="rollback_archive")
            if backup_archive
            else None,
            "candidate_plist": _artifact(candidate_plist, kind="candidate_launchd_plist")
            if candidate_plist
            else None,
            "candidate_plist_diff": _artifact(candidate_plist_diff, kind="launchd_diff")
            if candidate_plist_diff
            else None,
            "staging_root": _artifact(staging_root, kind="staged_runtime_app")
            if staging_root
            else None,
        },
        "rollback": {
            "rule": "restore the complete app/data/link generation from the backup before reloading launchd",
            "launchd_reload": "do not reload launchd during preview",
            "raw": "never rewrite or delete processed raw evidence",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--runtime-base",
        type=Path,
        default=Path.home() / "Library" / "Application Support" / "llm-workmem-runtime",
    )
    parser.add_argument(
        "--launch-agents",
        type=Path,
        default=Path.home() / "Library" / "LaunchAgents",
    )
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--backup-archive", type=Path)
    parser.add_argument("--candidate-plist", type=Path)
    parser.add_argument("--candidate-plist-diff", type=Path)
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(
        root=args.root.resolve(),
        runtime_base=args.runtime_base.expanduser().resolve(),
        launch_agents=args.launch_agents.expanduser().resolve(),
        backup_root=args.backup_root.expanduser().resolve(),
        backup_archive=args.backup_archive.expanduser().resolve() if args.backup_archive else None,
        candidate_plist=args.candidate_plist.expanduser().resolve() if args.candidate_plist else None,
        candidate_plist_diff=args.candidate_plist_diff.expanduser().resolve()
        if args.candidate_plist_diff
        else None,
        staging_root=args.staging_root.expanduser().resolve() if args.staging_root else None,
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = _sha256_bytes(output.read_bytes())
    print(f"manifest entries: {manifest['entry_count']}")
    for kind, count in manifest["by_type"].items():
        print(f"  {kind}: {count}")
    print(f"manifest SHA-256: {digest}")
    print(f"approval_id: lwm9b-{digest[:16]}")
    print(f"path: {output}")
    print("mode: read-only preview; no live path was changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
