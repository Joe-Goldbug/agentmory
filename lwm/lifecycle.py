"""Canonical lifecycle boundary shared by native IDE hooks.

Hosts may report a nested current directory.  This module resolves its Git
worktree before emitting context, events, or receipts, so every lifecycle
record for one repository has one path and one project id.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lwm import capabilities, context, inbox
from lwm.events import make_event
from lwm.project_id import record_project, resolve_project_root


@dataclass(frozen=True)
class LifecycleResult:
    project_path: str
    project_id: str
    event_path: Path
    context_markdown: str = ""


def _event(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    event_type: str,
    session_id: str | None = None,
    task: str | None = None,
    source: str = "native-hook",
) -> tuple[dict[str, Any], Path]:
    canonical = resolve_project_root(project_path)
    resolution = record_project(root, canonical)
    payload = make_event(
        tool=tool,
        project_path=str(canonical),
        project_id=resolution.project_id,
        event_type=event_type,
        importance="scratch" if event_type == "session_start" else "project",
        privacy="sanitized",
        session_id=session_id,
        task=(task or None),
        source={"kind": source, "path": f"{tool}/{event_type}"},
        tags=[tool, "lifecycle"],
    )
    return payload, inbox.submit_event(root, payload)


def start(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    session_id: str | None = None,
    source: str = "native-hook",
) -> LifecycleResult:
    root = root.resolve()
    payload, event_path = _event(
        root, tool=tool, project_path=project_path, event_type="session_start",
        session_id=session_id, source=source,
    )
    report = context.build(root, tool=tool, project_path=payload["project_path"])
    capabilities.record(root, tool=tool, direction="read", project_id=payload["project_id"], source=source)
    return LifecycleResult(payload["project_path"], payload["project_id"], event_path, report.markdown)


def stop(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    session_id: str | None = None,
    task: str | None = None,
    source: str = "native-hook",
) -> LifecycleResult:
    root = root.resolve()
    payload, event_path = _event(
        root, tool=tool, project_path=project_path, event_type="session_summary",
        session_id=session_id, task=task, source=source,
    )
    capabilities.record(root, tool=tool, direction="write", project_id=payload["project_id"], source=source)
    return LifecycleResult(payload["project_path"], payload["project_id"], event_path)


__all__ = ["LifecycleResult", "start", "stop"]
