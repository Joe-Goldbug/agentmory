"""Canonical project registry used by adapters and CBMEM."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lwm.project_id import resolve_project_id


def path(root: Path) -> Path:
    return root / "state" / "projects.json"


def load(root: Path) -> dict[str, dict[str, Any]]:
    target = path(root)
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def register(root: Path, project_path: str | Path, *, cbmem: bool = True) -> dict[str, Any]:
    target = Path(project_path).expanduser().resolve()
    resolution = resolve_project_id(target)
    projects = load(root)
    existing = projects.get(resolution.project_id, {})
    row = {
        **existing,
        "project_id": resolution.project_id,
        "canonical_path": str(target),
        "kind": resolution.kind,
        "remote": resolution.remote,
        "cbmem_enabled": cbmem,
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "active",
    }
    projects[resolution.project_id] = row
    target_path = path(root)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(projects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return row


__all__ = ["load", "path", "register"]
