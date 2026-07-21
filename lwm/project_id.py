"""Stable project-id derivation.

The hub treats the same git repository under different local paths as a
single project so its memory entries can be merged. Resolution order:

1. ``git -C <path> remote get-url origin`` → ``git-<sha1-hex-16>``.
2. Otherwise the git toplevel absolute path → ``local-<sha1-hex-16>``.
3. Otherwise the absolute path itself → ``adhoc-<sha1-hex-16>``.

Results are cached in ``<root>/state/project-map.json`` so the same
project always maps to the same id within a wiki.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GIT_REMOTE_SSH = re.compile(r"git@[^:]+:(.+?)(?:\.git)?/?$")
GIT_REMOTE_HTTPS = re.compile(r"https?://[^/]+/(.+?)(?:\.git)?/?$")
_GIT_ENV = {"GIT_TERMINAL_PROMPT": "0"}


@dataclass(frozen=True)
class ProjectIdResolution:
    project_id: str
    kind: str  # "git" | "local" | "adhoc"
    remote: str | None = None
    toplevel: str | None = None

    def render(self) -> str:
        bits = [f"id={self.project_id}", f"kind={self.kind}"]
        if self.remote:
            bits.append(f"remote={self.remote}")
        if self.toplevel:
            bits.append(f"toplevel={self.toplevel}")
        return ", ".join(bits)


def _hash_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _normalize_remote(remote: str) -> str:
    remote = remote.strip()
    for pattern in (GIT_REMOTE_SSH, GIT_REMOTE_HTTPS):
        match = pattern.match(remote)
        if match:
            return match.group(1)
    return remote


def _run_git(cwd: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=10,
            env={**_GIT_ENV, **dict(__import__("os").environ)},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def resolve_project_id(path: str | Path) -> ProjectIdResolution:
    """Resolve a project id without consulting the cache."""

    target = resolve_project_root(path)
    if not target.exists():
        # Even non-existent paths still get a stable id (offline-safe).
        digest = _hash_hex(str(target))
        return ProjectIdResolution(
            project_id=f"adhoc-{digest}", kind="adhoc", toplevel=str(target)
        )

    remote = _run_git(target, ["remote", "get-url", "origin"])
    if remote:
        normalized = _normalize_remote(remote)
        digest = _hash_hex(normalized)
        return ProjectIdResolution(
            project_id=f"git-{digest}", kind="git", remote=normalized, toplevel=str(target)
        )

    toplevel = _run_git(target, ["rev-parse", "--show-toplevel"])
    if toplevel:
        digest = _hash_hex(str(Path(toplevel).resolve()))
        return ProjectIdResolution(
            project_id=f"local-{digest}", kind="local", toplevel=str(Path(toplevel).resolve())
        )

    digest = _hash_hex(str(target))
    return ProjectIdResolution(
        project_id=f"adhoc-{digest}", kind="adhoc", toplevel=str(target)
    )


def resolve_project_root(path: str | Path) -> Path:
    """Return the Git worktree root for *path*, or its resolved directory.

    Lifecycle adapters receive whatever directory their host reports.  This
    normalizes nested folders and worktree children before either a context
    lookup or an event is written, preventing one repository from splitting
    into several path identities.
    """

    target = Path(path).expanduser().resolve()
    if not target.exists():
        return target
    candidate = target if target.is_dir() else target.parent
    toplevel = _run_git(candidate, ["rev-parse", "--show-toplevel"])
    return Path(toplevel).resolve() if toplevel else candidate


def _cache_path(root: Path) -> Path:
    return (root / "state" / "project-map.json").resolve()


def load_project_map(root: Path) -> dict[str, str]:
    path = _cache_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def save_project_map(root: Path, mapping: dict[str, str]) -> Path:
    path = _cache_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def record_project(root: Path, path: str | Path) -> ProjectIdResolution:
    """Resolve + persist a project id for ``path``."""

    project_root = resolve_project_root(path)
    resolution = resolve_project_id(project_root)
    cache = load_project_map(root)
    key = str(project_root)
    if cache.get(key) != resolution.project_id:
        cache[key] = resolution.project_id
        save_project_map(root, cache)
    return resolution


def ensure_project_id(
    root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Mutate ``payload`` in place to fill ``project_id`` if missing.

    When the caller already supplied a stable ``project_id`` we still
    persist the ``path → id`` mapping in ``state/project-map.json`` so
    that downstream consumers (context rendering, project-aware MCP
    tools) can locate the right project page without re-deriving the id
    from git.  Without this bridge the same path can resolve to two
    different ids (cached caller's id vs. fresh git sha).
    """

    project_path = payload.get("project_path") or ""
    if not project_path:
        return payload
    provided_id = payload.get("project_id")

    if provided_id:
        cache = load_project_map(root)
        key = str(Path(project_path).expanduser().resolve())
        if cache.get(key) != str(provided_id):
            cache[key] = str(provided_id)
            save_project_map(root, cache)
        return payload

    resolution = record_project(root, project_path)
    payload["project_id"] = resolution.project_id
    return payload


__all__ = [
    "ProjectIdResolution",
    "ensure_project_id",
    "load_project_map",
    "record_project",
    "resolve_project_id",
    "resolve_project_root",
    "save_project_map",
]
