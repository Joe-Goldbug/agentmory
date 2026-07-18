"""Immutable evidence records used by the project-scoped recall layer."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable


_WHITESPACE = re.compile(r"\s+")


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_statement(value: str) -> str:
    """Normalize only whitespace/case for deterministic identity checks."""

    return _WHITESPACE.sub(" ", value.strip().lower())


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(_text(item) for item in value if _text(item))
    return (_text(value),) if _text(value) else ()


@dataclass(frozen=True)
class EvidenceItem:
    fact_id: str
    project_id: str
    fact_type: str
    statement: str
    observed_at: str = ""
    valid_from: str | None = None
    valid_to: str | None = None
    state: str = "unverified"
    source_event_ids: tuple[str, ...] = ()
    source_paths: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    confidence: float = 0.5
    supersedes: str | None = None
    retrieval_reasons: tuple[str, ...] = ()
    subject_key: str = ""

    @property
    def normalized_statement(self) -> str:
        return normalize_statement(self.statement)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_event_ids"] = list(self.source_event_ids)
        data["source_paths"] = list(self.source_paths)
        data["verification"] = list(self.verification)
        data["retrieval_reasons"] = list(self.retrieval_reasons)
        return data


@dataclass(frozen=True)
class EvidenceCoverage:
    status: str
    missing: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "missing": list(self.missing),
            "warnings": list(self.warnings),
        }


def _initial_state(payload: dict[str, Any], statement: str) -> str:
    explicit = _text(payload.get("state"))
    if explicit in {"current", "historical", "conflicted", "unverified"}:
        return explicit
    if payload.get("valid_to"):
        return "historical"
    if statement:
        return "current"
    return "unverified"


def build_evidence_item(
    payload: dict[str, Any],
    *,
    fact_id: str | None = None,
    project_id: str | None = None,
    source_event_id: str | None = None,
    source_path: str | None = None,
    fact_type: str | None = None,
    statement: str | None = None,
) -> EvidenceItem:
    """Build one normalized evidence item from an event or fact dictionary."""

    resolved_statement = _text(statement if statement is not None else payload.get("statement"))
    if not resolved_statement:
        resolved_statement = _text(payload.get("task"))
    decisions = _tuple_strings(payload.get("decisions"))
    changes = _tuple_strings(payload.get("changes"))
    verification = _tuple_strings(payload.get("verification"))
    details = tuple(item for item in (*decisions, *changes) if item)
    if details:
        resolved_statement = "; ".join(dict.fromkeys((resolved_statement, *details)))

    event_id = _text(source_event_id or payload.get("event_id"))
    event_ids = _tuple_strings(payload.get("source_event_ids"))
    if event_id and event_id not in event_ids:
        event_ids = (*event_ids, event_id)
    path = _text(source_path)
    paths = _tuple_strings(payload.get("source_paths"))
    if path and path not in paths:
        paths = (*paths, path)

    resolved_fact_id = _text(fact_id or payload.get("fact_id") or event_id)
    if not resolved_fact_id:
        resolved_fact_id = f"fact-{abs(hash((project_id, resolved_statement)))}"
    resolved_project_id = _text(project_id or payload.get("project_id"))
    resolved_type = _text(fact_type or payload.get("fact_type") or payload.get("event_type"))
    resolved_type = resolved_type or "observation"
    subject_key = _text(
        payload.get("subject_key")
        or payload.get("fact_key")
        or payload.get("subject")
        or payload.get("event_type")
        or resolved_type
    )
    try:
        confidence = float(payload.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = min(max(confidence, 0.0), 1.0)

    return EvidenceItem(
        fact_id=resolved_fact_id,
        project_id=resolved_project_id,
        fact_type=resolved_type,
        statement=resolved_statement,
        observed_at=_text(payload.get("observed_at") or payload.get("timestamp")),
        valid_from=payload.get("valid_from"),
        valid_to=payload.get("valid_to"),
        state=_initial_state(payload, resolved_statement),
        source_event_ids=event_ids,
        source_paths=paths,
        verification=verification,
        confidence=confidence,
        supersedes=_text(payload.get("supersedes")) or None,
        retrieval_reasons=_tuple_strings(payload.get("retrieval_reasons")),
        subject_key=subject_key,
    )


def _prefer(left: EvidenceItem, right: EvidenceItem) -> EvidenceItem:
    left_rank = (bool(left.verification), left.confidence, left.observed_at, left.fact_id)
    right_rank = (bool(right.verification), right.confidence, right.observed_at, right.fact_id)
    return left if left_rank >= right_rank else right


def deduplicate_evidence(items: Iterable[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    """Keep one deterministic representative for duplicate evidence."""

    by_key: dict[tuple[str, str, str, str], EvidenceItem] = {}
    for item in items:
        key = (
            item.project_id,
            item.fact_id or item.normalized_statement,
            item.subject_key,
            item.observed_at,
        )
        existing = by_key.get(key)
        by_key[key] = item if existing is None else _prefer(existing, item)
    return tuple(sorted(by_key.values(), key=lambda item: (item.observed_at, item.fact_id)))


def arbitrate_state(items: Iterable[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    """Apply supersession and conflict rules without deleting historical facts."""

    unique = list(deduplicate_evidence(items))
    superseded_ids = {item.supersedes for item in unique if item.supersedes}
    current_groups: dict[tuple[str, str], list[EvidenceItem]] = {}
    for item in unique:
        if item.fact_id in superseded_ids or item.valid_to:
            continue
        current_groups.setdefault((item.project_id, item.subject_key), []).append(item)

    result: list[EvidenceItem] = []
    for item in unique:
        state = "historical" if item.fact_id in superseded_ids or item.valid_to else item.state
        group = current_groups.get((item.project_id, item.subject_key), [])
        statements = {candidate.normalized_statement for candidate in group}
        if len(statements) > 1 and item in group:
            state = "conflicted"
        elif state not in {"conflicted", "unverified", "historical"}:
            state = "current"
        result.append(replace(item, state=state))
    return tuple(sorted(result, key=lambda item: (item.state != "current", -item.confidence, item.fact_id)))


def render_evidence_json(items: Iterable[EvidenceItem]) -> list[dict[str, Any]]:
    return [item.as_dict() for item in items]


def render_coverage_json(coverage: EvidenceCoverage) -> dict[str, Any]:
    return json.loads(json.dumps(coverage.as_dict(), ensure_ascii=False))


__all__ = [
    "EvidenceCoverage",
    "EvidenceItem",
    "arbitrate_state",
    "build_evidence_item",
    "deduplicate_evidence",
    "normalize_statement",
    "render_coverage_json",
    "render_evidence_json",
]
