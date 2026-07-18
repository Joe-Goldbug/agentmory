"""Unified work-event schema for the LLM-WorkMem central hub.

The central hub keeps every IDE / Shell emitting the same JSON shape. The
schema is intentionally small and additive: extras are fine, missing
required keys are not. Validation never raises — it returns an
:class:`EventIssue` collection so callers can log or drop the event.

The schema mirrors the document in
``docs/superpowers/specs/2026-07-11-llm-workmem-central-hub-design.md``
§4. Any change here must be reflected in that document.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ALLOWED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "session_start",
        "session_summary",
        "session_end",
        "checkpoint",
        "decision",
        "bugfix",
        "verification",
        "project_status",
        "workflow_observation",
        "insight_candidate",
        "reflection",
        "fact_superseded",
        "adapter_probe",
    }
)

ALLOWED_IMPORTANCES: frozenset[str] = frozenset(
    {"scratch", "project", "cross_project", "global"}
)

ALLOWED_PRIVACY_TAGS: frozenset[str] = frozenset(
    {"raw", "sanitized", "redacted", "blocked"}
)

REQUIRED_KEYS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "tool",
    "project_path",
    "project_id",
    "event_type",
    "importance",
    "privacy",
)

OPTIONAL_LIST_KEYS: tuple[str, ...] = (
    "decisions",
    "changes",
    "verification",
    "open_questions",
    "files_touched",
    "tags",
)

_OPTIONAL_SCALAR_KEYS: tuple[str, ...] = (
    "tool_version",
    "session_id",
    "task",
    "confidence",
    "source",
)

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)$"
)

MAX_TEXT_BYTES = 16 * 1024


@dataclass(frozen=True)
class EventIssue:
    """One validation problem with an event payload."""

    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True)
class EventReport:
    issues: tuple[EventIssue, ...]
    event: dict[str, Any] | None

    @property
    def ok(self) -> bool:
        return not self.issues


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _now_iso() -> str:
    """Return the current local time as ISO8601 with offset."""

    return datetime.now(tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def new_event_id() -> str:
    """Generate a v4 UUID string."""

    return str(uuid.uuid4())


def make_event(
    *,
    tool: str,
    project_path: str,
    project_id: str,
    event_type: str,
    importance: str = "project",
    privacy: str = "sanitized",
    task: str | None = None,
    decisions: Iterable[str] | None = None,
    changes: Iterable[str] | None = None,
    verification: Iterable[str] | None = None,
    open_questions: Iterable[str] | None = None,
    files_touched: Iterable[str] | None = None,
    tags: Iterable[str] | None = None,
    session_id: str | None = None,
    tool_version: str | None = None,
    confidence: float | None = None,
    source: dict[str, Any] | None = None,
    timestamp: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Construct a well-formed event payload (no IO)."""

    payload: dict[str, Any] = {
        "event_id": event_id or new_event_id(),
        "timestamp": timestamp or _now_iso(),
        "tool": tool,
        "project_path": str(project_path),
        "project_id": str(project_id),
        "event_type": event_type,
        "importance": importance,
        "privacy": privacy,
    }
    if tool_version is not None:
        payload["tool_version"] = tool_version
    if session_id is not None:
        payload["session_id"] = session_id
    if task is not None:
        payload["task"] = task
    if decisions is not None:
        payload["decisions"] = list(decisions)
    if changes is not None:
        payload["changes"] = list(changes)
    if verification is not None:
        payload["verification"] = list(verification)
    if open_questions is not None:
        payload["open_questions"] = list(open_questions)
    if files_touched is not None:
        payload["files_touched"] = list(files_touched)
    if tags is not None:
        payload["tags"] = list(tags)
    if confidence is not None:
        payload["confidence"] = float(confidence)
    if source is not None:
        payload["source"] = dict(source)
    return payload


def validate_event(payload: Any) -> EventReport:
    """Validate a parsed JSON payload against the event schema.

    Returns a report with the original payload on success. The payload is
    not mutated. The function never raises on schema mismatch.
    """

    issues: list[EventIssue] = []
    if not isinstance(payload, dict):
        return EventReport(
            issues=(EventIssue("$", "event must be a JSON object"),),
            event=None,
        )

    for key in REQUIRED_KEYS:
        if key not in payload:
            issues.append(EventIssue(f"$.{key}", "missing required key"))
    for key in OPTIONAL_LIST_KEYS:
        if key in payload and not _is_str_list(payload[key]):
            label = f"$.{key}"
            issues.append(EventIssue(label, "must be a list of strings"))
    for key in _OPTIONAL_SCALAR_KEYS:
        if key not in payload:
            continue
        value = payload[key]
        if key == "confidence":
            if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                issues.append(EventIssue("$.confidence", "must be float in [0,1]"))
        elif key == "source":
            if not isinstance(value, dict):
                issues.append(EventIssue("$.source", "must be an object"))

    if "timestamp" in payload and not TIMESTAMP_RE.match(str(payload["timestamp"])):
        issues.append(EventIssue("$.timestamp", "must be ISO 8601 with offset"))
    if "tool" in payload and not isinstance(payload["tool"], str):
        issues.append(EventIssue("$.tool", "must be a string"))
    if "project_path" in payload and not isinstance(payload["project_path"], str):
        issues.append(EventIssue("$.project_path", "must be a string"))
    if "project_id" in payload and not isinstance(payload["project_id"], str):
        issues.append(EventIssue("$.project_id", "must be a string"))
    if "event_type" in payload and payload["event_type"] not in ALLOWED_EVENT_TYPES:
        issues.append(
            EventIssue(
                "$.event_type",
                f"unknown event_type (allowed: {sorted(ALLOWED_EVENT_TYPES)})",
            )
        )
    if "importance" in payload and payload["importance"] not in ALLOWED_IMPORTANCES:
        issues.append(
            EventIssue(
                "$.importance",
                f"unknown importance (allowed: {sorted(ALLOWED_IMPORTANCES)})",
            )
        )
    if "privacy" in payload and payload["privacy"] not in ALLOWED_PRIVACY_TAGS:
        issues.append(
            EventIssue(
                "$.privacy",
                f"unknown privacy tag (allowed: {sorted(ALLOWED_PRIVACY_TAGS)})",
            )
        )

    if issues:
        return EventReport(issues=tuple(issues), event=None)
    return EventReport(issues=(), event=payload)


def read_event_file(path: Path) -> EventReport:
    """Load + validate an event JSON file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return EventReport(
            issues=(EventIssue(str(path), f"read failed: {exc}"),),
            event=None,
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return EventReport(
            issues=(EventIssue(str(path), f"json parse: {exc.msg}"),),
            event=None,
        )
    report = validate_event(payload)
    if not report.ok:
        return EventReport(
            issues=tuple(EventIssue(f"{path}#{i.path}", i.message) for i in report.issues),
            event=None,
        )
    return report


def truncate_event_text(value: str, *, limit_bytes: int = MAX_TEXT_BYTES) -> tuple[str, bool]:
    """Return ``(value, truncated)`` truncating to ``limit_bytes`` UTF-8 bytes."""

    raw = value.encode("utf-8")
    if len(raw) <= limit_bytes:
        return value, False
    return raw[:limit_bytes].decode("utf-8", errors="ignore") + "…", True


__all__ = [
    "ALLOWED_EVENT_TYPES",
    "ALLOWED_IMPORTANCES",
    "ALLOWED_PRIVACY_TAGS",
    "EventIssue",
    "EventReport",
    "MAX_TEXT_BYTES",
    "make_event",
    "new_event_id",
    "read_event_file",
    "truncate_event_text",
    "validate_event",
]
