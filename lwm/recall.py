"""Project-scoped deterministic recall and evidence packet construction."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from lwm import cbmem
from lwm.evidence import (
    EvidenceCoverage,
    EvidenceItem,
    arbitrate_state,
    build_evidence_item,
    deduplicate_evidence,
    render_evidence_json,
)
from lwm.project_id import record_project
from lwm.query import _tokenize


_DIMENSIONS = (
    "current_state",
    "timeline",
    "decision",
    "verification",
    "conflict",
    "cross_project",
    "code",
)


@dataclass(frozen=True)
class RecallPlan:
    dimensions: tuple[str, ...]
    checks: tuple[str, ...]
    time_window: tuple[str, str] | None = None
    now: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimensions": list(self.dimensions),
            "checks": list(self.checks),
            "time_window": list(self.time_window) if self.time_window else None,
            "now": self.now,
        }


@dataclass(frozen=True)
class RecallPacket:
    question: str
    project_id: str | None
    project_path: str | None
    scope: str
    plan: RecallPlan
    summary: str
    evidence: tuple[EvidenceItem, ...]
    conflicts: tuple[EvidenceItem, ...]
    missing: tuple[str, ...]
    coverage: str
    warnings: tuple[str, ...]
    trace_id: str
    token_estimate: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "project_id": self.project_id,
            "project_path": self.project_path,
            "scope": self.scope,
            "plan": self.plan.as_dict(),
            "summary": self.summary,
            "evidence": render_evidence_json(self.evidence),
            "conflicts": render_evidence_json(self.conflicts),
            "missing": list(self.missing),
            "coverage": self.coverage,
            "warnings": list(self.warnings),
            "trace_id": self.trace_id,
            "token_estimate": self.token_estimate,
        }


def _as_datetime(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now().astimezone()


def _date_window(question: str, now: datetime) -> tuple[str, str] | None:
    q = question.lower()
    today = now.date()
    if "昨天" in q or "yesterday" in q:
        day = today - timedelta(days=1)
        return day.isoformat(), day.isoformat()
    if "上周" in q or "last week" in q:
        end = today - timedelta(days=1)
        return (end - timedelta(days=6)).isoformat(), end.isoformat()
    if "最近" in q or "recent" in q or "last" in q:
        return (today - timedelta(days=7)).isoformat(), today.isoformat()
    if any(word in q for word in ("何时", "什么时候", "日期", "when", "date")):
        return None
    return None


def plan_question(
    question: str,
    *,
    now: datetime | str | None = None,
    timezone_name: str | None = None,
    has_project: bool = True,
) -> RecallPlan:
    """Build a deterministic retrieval plan; no model call is required."""

    del timezone_name  # The caller supplies an aware datetime in the local timezone.
    current = _as_datetime(now)
    q = question.strip().lower()
    dimensions: list[str] = []
    checks: list[str] = ["source-backed evidence", "deduplicate repeated matches"]

    if any(word in q for word in ("现在", "当前", "最新", "现行", "current", "latest")):
        dimensions.append("current_state")
        checks.append("prefer the latest verified state over historical notes")
    if any(word in q for word in ("何时", "什么时候", "日期", "昨天", "上周", "when", "date")):
        dimensions.append("timeline")
        checks.append("anchor relative dates to an exact local date range")
    if any(word in q for word in ("为什么", "决定", "选择", "方案", "decision", "why", "should")):
        dimensions.append("decision")
        checks.append("preserve the decision and its source event")
    if any(word in q for word in ("完成", "验证", "证明", "是否", "verify", "verified")):
        dimensions.append("verification")
        checks.append("require explicit verification evidence")
    if any(word in q for word in ("冲突", "矛盾", "不同说法", "conflict", "contradiction")):
        dimensions.append("conflict")
        checks.append("surface competing current facts")
    if any(word in q for word in ("跨项目", "多个项目", "共同", "across", "projects")):
        dimensions.append("cross_project")
        checks.append("separate project-local facts from global patterns")
    if any(word in q for word in ("代码", "文件", "函数", "调用链", "code", "file", "symbol")):
        dimensions.append("code")
        checks.append("use CBMEM only for code evidence")
    if has_project:
        dimensions.append("project")
        checks.append("filter all project evidence by stable project id")

    unique_dimensions = tuple(dict.fromkeys(dimensions))
    return RecallPlan(
        dimensions=unique_dimensions,
        checks=tuple(checks),
        time_window=_date_window(q, current),
        now=current.isoformat(timespec="seconds"),
    )


def _load_events(root: Path, project_id: str | None, *, include_cross_project: bool) -> list[dict[str, Any]]:
    processed = root / "raw" / "events" / "processed"
    if not processed.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for path in sorted(processed.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        event_project = str(payload.get("project_id") or "")
        importance = str(payload.get("importance") or "project")
        if project_id and event_project != project_id:
            if not (include_cross_project and importance in {"cross_project", "global"}):
                continue
        elif not project_id and importance not in {"cross_project", "global"}:
            continue
        payload["source_paths"] = [str(path.relative_to(root))]
        events.append(payload)
    return events


def _event_items(events: Iterable[dict[str, Any]]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for event in events:
        payload = dict(event)
        payload["fact_type"] = payload.get("fact_type") or payload.get("event_type") or "observation"
        payload["subject_key"] = payload.get("subject_key") or payload.get("fact_key") or payload.get("event_id")
        item = build_evidence_item(payload)
        reasons = list(item.retrieval_reasons) + ["event_source"]
        items.append(replace(item, retrieval_reasons=tuple(reasons)))
    return items


def _matches_time(item: EvidenceItem, window: tuple[str, str] | None) -> bool:
    if not window:
        return True
    try:
        day = datetime.fromisoformat(item.observed_at.replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return False
    return window[0] <= day <= window[1]


def _matches_question(item: EvidenceItem, question: str) -> bool:
    tokens = _tokenize(question)
    if not tokens:
        return True
    blob = item.normalized_statement
    return any(token in blob for token in tokens)


def _cbmem_items(project_path: str, question: str, project_id: str) -> tuple[list[EvidenceItem], str | None]:
    try:
        result = cbmem.search(Path(project_path), question, limit=6)
    except Exception as exc:  # noqa: BLE001 - code memory is an optional source
        return [], f"CBMEM unavailable: {exc}"
    if not result.ok:
        return [], f"CBMEM search failed: {result.stderr[-300:]}"
    try:
        content = json.dumps(result.json(), ensure_ascii=False)
    except (ValueError, TypeError):
        content = result.stdout.strip()
    if not content:
        return [], "CBMEM returned no code evidence"
    return [
        build_evidence_item(
            {
                "fact_id": f"cbmem-{uuid.uuid4()}",
                "project_id": project_id,
                "fact_type": "code",
                "statement": content[:4000],
                "source_paths": ["CBMEM"],
                "verification": ["CBMEM query returned successfully"],
                "subject_key": "code-query",
            }
        )
    ], None


def _coverage(
    plan: RecallPlan,
    items: tuple[EvidenceItem, ...],
    *,
    project_id: str | None,
    warnings: list[str],
) -> EvidenceCoverage:
    missing: list[str] = []
    if project_id is None:
        missing.append("project identity")
    if not items:
        missing.append("source-backed evidence")
    if "timeline" in plan.dimensions and plan.time_window and not any(
        _matches_time(item, plan.time_window) for item in items
    ):
        missing.append("timeline evidence in requested range")
    if "current_state" in plan.dimensions and not any(item.state == "current" for item in items):
        missing.append("current state")
    if "verification" in plan.dimensions and not any(item.verification for item in items):
        missing.append("explicit verification")
    if "conflict" in plan.dimensions and not any(item.state == "conflicted" for item in items):
        warnings.append("No conflict found in the selected evidence; absence is not proof of consistency.")
    if missing and not items:
        status = "insufficient"
    elif missing:
        status = "partial"
    else:
        status = "complete"
    return EvidenceCoverage(status=status, missing=tuple(dict.fromkeys(missing)), warnings=tuple(warnings))


def build_recall_packet(
    root: Path,
    question: str,
    *,
    project_path: str | None = None,
    limit: int = 6,
    mode: str = "compact",
    now: datetime | str | None = None,
) -> RecallPacket:
    """Build a compact, source-backed packet for the active agent."""

    root = root.resolve()
    resolution = record_project(root, project_path) if project_path else None
    project_id = resolution.project_id if resolution else None
    scope = "project" if project_id else "global-only"
    plan = plan_question(question, now=now, has_project=bool(project_id))
    warnings: list[str] = []
    if not project_id:
        warnings.append("Project could not be resolved; returning global-only evidence.")
    events = _load_events(
        root,
        project_id,
        include_cross_project="cross_project" in plan.dimensions,
    )
    items = _event_items(events)
    if plan.time_window:
        items = [item for item in items if _matches_time(item, plan.time_window)]
    matched = [item for item in items if _matches_question(item, question)]
    if matched:
        items = matched
    if "code" in plan.dimensions and project_path and project_id:
        code_items, warning = _cbmem_items(project_path, question, project_id)
        items.extend(code_items)
        if warning:
            warnings.append(warning)

    ledger = arbitrate_state(deduplicate_evidence(items))
    if mode == "compact":
        ledger = ledger[:limit]
    else:
        ledger = ledger[: max(limit, 12)]
    conflicts = tuple(item for item in ledger if item.state == "conflicted")
    coverage = _coverage(plan, ledger, project_id=project_id, warnings=warnings)
    warnings.extend(coverage.warnings)
    summary_items = [item.statement for item in ledger[:3] if item.statement]
    summary = "；".join(summary_items)
    if not summary:
        summary = "No source-backed evidence found."
    trace_id = str(uuid.uuid4())
    packet_data = {
        "question": question,
        "project_id": project_id,
        "scope": scope,
        "plan": plan.as_dict(),
        "evidence": render_evidence_json(ledger),
    }
    token_estimate = max(1, len(json.dumps(packet_data, ensure_ascii=False)) // 4)
    return RecallPacket(
        question=question,
        project_id=project_id,
        project_path=project_path,
        scope=scope,
        plan=plan,
        summary=summary,
        evidence=tuple(ledger),
        conflicts=conflicts,
        missing=coverage.missing,
        coverage=coverage.status,
        warnings=tuple(dict.fromkeys(warnings)),
        trace_id=trace_id,
        token_estimate=token_estimate,
    )


def render_recall_packet(packet: RecallPacket) -> str:
    lines = [
        "# Recall Packet",
        "",
        f"- Scope: {packet.scope}",
        f"- Project: {packet.project_id or 'global-only'}",
        f"- Coverage: {packet.coverage}",
        f"- Token estimate: {packet.token_estimate}",
        "",
        "## Summary",
        packet.summary,
        "",
        "## Evidence",
    ]
    if packet.evidence:
        for item in packet.evidence:
            lines.append(
                f"- [{item.state}] {item.statement} | source={','.join(item.source_paths) or 'unknown'}"
            )
    else:
        lines.append("- No source-backed evidence found.")
    if packet.missing:
        lines.extend(["", "## Missing", *[f"- {item}" for item in packet.missing]])
    if packet.warnings:
        lines.extend(["", "## Warnings", *[f"- {item}" for item in packet.warnings]])
    return "\n".join(lines) + "\n"


__all__ = [
    "RecallPacket",
    "RecallPlan",
    "build_recall_packet",
    "plan_question",
    "render_recall_packet",
]
