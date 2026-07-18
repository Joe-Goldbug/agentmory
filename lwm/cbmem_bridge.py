"""Direct CBMEM bridge for registered projects.

LLM-WorkMem owns the project association and health receipt. CBMEM owns the
code graph and its watcher/index format. No Markdown snapshot is created here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lwm import cbmem, registry


def _migrate_legacy_projects(root: Path) -> None:
    source = root / "lwm-sources.json"
    if not source.is_file():
        return
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    projects = payload.get("cbmem", {}).get("projects", [])
    if isinstance(projects, list):
        for project in projects:
            if isinstance(project, str) and project.strip():
                registry.register(root, project)


def sync_registered_projects(root: Path) -> dict[str, Any]:
    root = root.resolve()
    _migrate_legacy_projects(root)
    projects = registry.load(root)
    report: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "projects": {},
    }
    try:
        binary = cbmem.resolve_binary()
    except cbmem.CbmemNotFoundError as exc:
        report["status"] = "unavailable"
        report["error"] = str(exc)
        for project_id, row in projects.items():
            report["projects"][project_id] = {"status": "unavailable", "path": row.get("canonical_path")}
    else:
        report["binary"] = binary
        for project_id, row in projects.items():
            project = Path(str(row.get("canonical_path", ""))).expanduser()
            if not project.is_dir() or not row.get("cbmem_enabled", True):
                report["projects"][project_id] = {"status": "skipped", "path": str(project)}
                continue
            try:
                result = cbmem.index_project(project, timeout=900)
                report["projects"][project_id] = {
                    "status": "ok" if result.ok else "failed",
                    "path": str(project),
                    "returncode": result.returncode,
                    "stderr": result.stderr[-500:],
                }
            except Exception as exc:  # noqa: BLE001
                report["projects"][project_id] = {"status": "failed", "path": str(project), "error": str(exc)}
    statuses = [row.get("status") for row in report["projects"].values()]
    report["status"] = report.get("status") or ("healthy" if all(s == "ok" for s in statuses) else "degraded")
    target = root / "state" / "cbmem-health.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


__all__ = ["sync_registered_projects"]
