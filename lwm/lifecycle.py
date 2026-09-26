"""Canonical lifecycle boundary shared by native IDE hooks.

Hosts may report a nested current directory.  This module resolves its Git
worktree before emitting context, events, or receipts, so every lifecycle
record for one repository has one path and one project id.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from lwm import capabilities, context, inbox
from lwm.capability_proof import validate_host_proof
from lwm.events import make_event
from lwm.project_id import record_project, resolve_project_root
from lwm.tool_registry import ToolRegistry


DEFAULT_LIFECYCLE_SOURCE = "watcher-observed"


@dataclass(frozen=True)
class LifecycleResult:
    project_path: str
    project_id: str
    event_path: Path
    context_markdown: str = ""
    handoff_id: str | None = None
    handoff_created: bool = False
    warning: str = ""


def _event(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    event_type: str,
    session_id: str | None = None,
    task: str | None = None,
    task_id: str | None = None,
    source: str = DEFAULT_LIFECYCLE_SOURCE,
    host_proof: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    definition = ToolRegistry.load(root).resolve(tool)
    canonical_tool = definition.tool_id if definition is not None else tool
    canonical = resolve_project_root(project_path)
    resolution = record_project(root, canonical)
    payload = make_event(
        tool=canonical_tool,
        project_path=str(canonical),
        project_id=resolution.project_id,
        event_type=event_type,
        importance="scratch" if event_type == "session_start" else "project",
        privacy="sanitized",
        session_id=session_id,
        task=(task or None),
        task_id=task_id,
        source={
            "kind": source,
            "path": f"{canonical_tool}/{event_type}",
            **({"host_proof": dict(host_proof)} if host_proof else {}),
        },
        tags=[canonical_tool, "lifecycle"],
    )
    return payload, inbox.submit_event(root, payload)


def _structured_event_from_summary(
    *,
    payload: dict[str, Any],
    tool: str,
    source: str,
    summary: Mapping[str, Any],
    handoff_id: str,
    task_id: str,
) -> dict[str, Any] | None:
    """Convert only bounded structured summary fields into durable evidence."""

    decisions = list(summary.get("decisions") or ())
    changes = list(summary.get("changes") or ())
    verifications = list(
        summary.get("verifications") or summary.get("verification") or ()
    )
    risks = list(summary.get("risks") or ())
    open_questions = list(summary.get("open_questions") or ())
    if not any((decisions, changes, verifications, risks, open_questions)):
        return None
    if changes and verifications:
        event_type = "bugfix"
    elif decisions:
        event_type = "decision"
    elif verifications:
        event_type = "verification"
    else:
        event_type = "project_status"
    task = str(
        summary.get("objective")
        or summary.get("current_state")
        or "structured task summary"
    )
    return make_event(
        tool=tool,
        project_path=payload["project_path"],
        project_id=payload["project_id"],
        event_type=event_type,
        importance="project",
        privacy="sanitized",
        task=task,
        task_id=task_id,
        handoff_id=handoff_id,
        source_receipt_id=payload["event_id"],
        decisions=decisions,
        changes=changes,
        verification=verifications,
        risks=risks,
        open_questions=open_questions,
        source={"kind": source, "path": f"{tool}/structured-summary"},
        tags=[tool, "structured-summary"],
    )


def start(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    session_id: str | None = None,
    task_id: str | None = None,
    source: str = DEFAULT_LIFECYCLE_SOURCE,
    host_proof: Mapping[str, Any] | None = None,
) -> LifecycleResult:
    root = root.resolve()
    normalized_proof = validate_host_proof(
        root,
        tool=tool,
        phase="start",
        source=source,
        session_id=session_id,
        host_proof=host_proof,
    )
    payload, event_path = _event(
        root, tool=tool, project_path=project_path, event_type="session_start",
        session_id=session_id, task_id=task_id, source=source,
        host_proof=normalized_proof,
    )
    canonical_tool = str(payload["tool"])
    report = context.build(root, tool=canonical_tool, project_path=payload["project_path"])
    capabilities.record(
        root,
        tool=canonical_tool,
        direction="read",
        project_id=payload["project_id"],
        source=source,
        evidence_path=str(event_path.relative_to(root)) if event_path.is_relative_to(root) else str(event_path),
        operation_id=f"read:{payload['event_id']}",
    )
    return LifecycleResult(payload["project_path"], payload["project_id"], event_path, report.markdown)


def stop(
    root: Path,
    *,
    tool: str,
    project_path: str | Path,
    session_id: str | None = None,
    task: str | None = None,
    task_id: str | None = None,
    handoff_summary: Mapping[str, Any] | None = None,
    source: str = DEFAULT_LIFECYCLE_SOURCE,
    host_proof: Mapping[str, Any] | None = None,
) -> LifecycleResult:
    root = root.resolve()
    normalized_proof = validate_host_proof(
        root,
        tool=tool,
        phase="stop",
        source=source,
        session_id=session_id,
        host_proof=host_proof,
    )
    payload, event_path = _event(
        root, tool=tool, project_path=project_path, event_type="session_summary",
        session_id=session_id, task=task, task_id=task_id, source=source,
        host_proof=normalized_proof,
    )
    canonical_tool = str(payload["tool"])
    capabilities.record(
        root,
        tool=canonical_tool,
        direction="write",
        project_id=payload["project_id"],
        source=source,
        evidence_path=str(event_path.relative_to(root)) if event_path.is_relative_to(root) else str(event_path),
        operation_id=f"write:{payload['event_id']}",
    )
    handoff_id: str | None = None
    handoff_created = False
    warning = ""
    if handoff_summary is not None:
        try:
            from lwm.handoff import create_handoff_from_summary

            packet = create_handoff_from_summary(
                root,
                project_id=payload["project_id"],
                source_tool=canonical_tool,
                summary=handoff_summary,
                evidence_id=payload["event_id"],
                task_id=task_id,
            )
            handoff_id = packet.handoff_id
            handoff_created = True
            structured_event = _structured_event_from_summary(
                payload=payload,
                tool=canonical_tool,
                source=source,
                summary=handoff_summary,
                handoff_id=packet.handoff_id,
                task_id=packet.task_id,
            )
            if structured_event is not None:
                inbox.submit_event(root, structured_event)
                from lwm.handoff import append_handoff_evidence

                append_handoff_evidence(
                    root,
                    handoff_id=packet.handoff_id,
                    evidence_ids=(structured_event["event_id"],),
                )
        except (OSError, TypeError, ValueError) as exc:
            # A malformed summary must not break the host tool's stop hook.
            warning = f"handoff not created: {exc}"
    return LifecycleResult(
        payload["project_path"],
        payload["project_id"],
        event_path,
        handoff_id=handoff_id,
        handoff_created=handoff_created,
        warning=warning,
    )


__all__ = ["LifecycleResult", "start", "stop"]
