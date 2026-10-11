"""Canonical lifecycle boundary shared by native IDE hooks.

Hosts may report a nested current directory.  This module resolves its Git
worktree before emitting context, events, or receipts, so every lifecycle
record for one repository has one path and one project id.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import wraps
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
    event_path: Path | None
    context_markdown: str = ""
    handoff_id: str | None = None
    handoff_created: bool = False
    warning: str = ""


def _idempotent(phase: str):
    """Persist session/turn identity across hook processes and inbox moves."""
    def decorate(function):
        @wraps(function)
        def run(root: Path, **kwargs) -> LifecycleResult:
            if os.environ.get("LWM_ANALYSIS_JOB") == "1":
                return LifecycleResult(str(kwargs["project_path"]), "", None)
            session = kwargs.get("session_id")
            if not session:
                return function(root, **kwargs)
            tool = ToolRegistry.load(root).resolve(kwargs["tool"])
            identity = [phase, tool.tool_id if tool else kwargs["tool"],
                        str(resolve_project_root(kwargs["project_path"])), session]
            # An earlier watcher observation cannot stand in for a later
            # native callback or lend it a proof binding it never had.
            identity.append(kwargs.get("source", DEFAULT_LIFECYCLE_SOURCE))
            if phase == "stop":
                identity.append(kwargs.get("task_id") or
                                (kwargs.get("handoff_summary") or {}).get("task_id") or
                                json.dumps(kwargs.get("handoff_summary"), sort_keys=True))
            key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
            directory = root / "state/host-lifecycle"
            directory.mkdir(parents=True, exist_ok=True)
            marker = directory / f"{key}.json"
            with (directory / f"{key}.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if marker.is_file():
                    saved = json.loads(marker.read_text())
                    event_path = Path(saved["event_path"])
                    if not event_path.is_file():
                        matches = [p for bucket in inbox.VALID_BUCKETS
                                   for p in (root / "raw/events" / bucket).glob(f"*/{event_path.name}")]
                        event_path = matches[0] if len(matches) == 1 else event_path
                    if event_path.is_file():
                        saved["event_path"] = event_path
                        if phase == "start":
                            saved["context_markdown"] = context.build(
                                root, tool=identity[1], project_path=saved["project_path"]).markdown
                        return LifecycleResult(**saved)
                result = function(root, **kwargs)
                saved = asdict(result)
                saved["event_path"] = str(result.event_path)
                temporary = marker.with_suffix(f".{os.getpid()}.tmp")
                temporary.write_text(json.dumps(saved))
                os.replace(temporary, marker)
                return result
        return run
    return decorate


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
    source_timestamp: str | None = None,
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
        importance="scratch",
        privacy="sanitized",
        timestamp=source_timestamp,
        session_id=session_id,
        task=(task or None),
        task_id=task_id,
        source={
            "kind": source,
            "path": f"{canonical_tool}/{event_type}",
            **({"timestamp_basis": "native_cache", "collected_at": datetime.now(timezone.utc).isoformat()} if source_timestamp else {}),
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
        timestamp=payload["timestamp"],
        task=task,
        task_id=task_id,
        session_id=payload.get("session_id"),
        handoff_id=handoff_id,
        source_receipt_id=payload["event_id"],
        decisions=decisions,
        changes=changes,
        verification=verifications,
        risks=risks,
        open_questions=open_questions,
        source={"kind": source, "path": f"{tool}/structured-summary",
                **{key: payload["source"][key] for key in ("timestamp_basis", "collected_at") if key in payload["source"]}},
        tags=[tool, "structured-summary"],
    )


def _submit_work(root: Path, event: dict[str, Any], source: str) -> None:
    path = inbox.submit_event(root, event)
    capabilities.record(
        root, tool=event["tool"], direction="write", project_id=event["project_id"],
        source=source, evidence_path=str(path.relative_to(root)),
        operation_id=f"work:{event['event_id']}",
    )


@_idempotent("start")
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
    delivery = {
        "format": "markdown", "context_sha256": hashlib.sha256(report.markdown.encode()).hexdigest(),
        "project_id": payload["project_id"], "stage": "prepared-for-host",
        "host_mechanism": {
            "codex": "hookSpecificOutput.additionalContext",
            "claude-code": "SessionStart stdout",
            "antigravity": "injectSteps.ephemeralMessage",
            "opencode": "experimental.chat.system.transform",
        }.get(canonical_tool, "bridge-return-only"),
    }
    payload["source"]["delivery"] = delivery
    inbox.submit_event(root, payload)
    capabilities.record(
        root,
        tool=canonical_tool,
        direction="read",
        project_id=payload["project_id"],
        source=source,
        evidence_path=str(event_path.relative_to(root)) if event_path.is_relative_to(root) else str(event_path),
        operation_id=f"read:{payload['event_id']}",
        detail=json.dumps({"delivery": delivery}, sort_keys=True),
    )
    return LifecycleResult(payload["project_path"], payload["project_id"], event_path, report.markdown)


@_idempotent("stop")
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
    source_timestamp: str | None = None,
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
        source_timestamp=source_timestamp,
    )
    canonical_tool = str(payload["tool"])
    structured_event = None
    if handoff_summary is not None:
        try:
            bounded = dict(handoff_summary)
            for field in ("decisions", "changes", "risks", "open_questions", "verifications"):
                value = handoff_summary.get(field) or (
                    handoff_summary.get("verification") if field == "verifications" else None
                ) or []
                if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"{field} must contain strings")
                bounded[field] = [item.strip()[:1000] for item in value[:8] if item.strip()]
            structured_event = _structured_event_from_summary(
                payload=payload, tool=canonical_tool, source=source,
                summary=bounded, handoff_id="", task_id=task_id or "",
            )
            if structured_event is not None:
                # Work survives host teardown even if receipts/handoff cannot finish.
                inbox.submit_event(root, structured_event)
        except (OSError, TypeError, ValueError):
            structured_event = None
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
            if structured_event is None:
                structured_event = _structured_event_from_summary(
                    payload=payload, tool=canonical_tool, source=source,
                    summary=handoff_summary, handoff_id=packet.handoff_id, task_id=packet.task_id,
                )
            else:
                structured_event = {**structured_event, "handoff_id": packet.handoff_id, "task_id": packet.task_id}
            if structured_event is not None:
                _submit_work(root, structured_event, source)
                from lwm.handoff import append_handoff_evidence

                append_handoff_evidence(
                    root,
                    handoff_id=packet.handoff_id,
                    evidence_ids=(structured_event["event_id"],),
                )
        except (OSError, TypeError, ValueError) as exc:
            # A malformed summary must not break the host tool's stop hook.
            warning = f"handoff not created: {exc}"
            # Evidence and a compact handoff have different size contracts.
            # A rejected handoff never discards a valid observed work event.
            if structured_event is not None:
                _submit_work(root, structured_event, source)
    return LifecycleResult(
        payload["project_path"],
        payload["project_id"],
        event_path,
        handoff_id=handoff_id,
        handoff_created=handoff_created,
        warning=warning,
    )


__all__ = ["LifecycleResult", "start", "stop"]
