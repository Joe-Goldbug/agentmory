"""Reviewable workflow and cross-project relationship candidates.

These records are suggestions, not memory truth.  They remain under
``state/candidates`` until a human accepts or corrects them.  Context recall
only exposes accepted records.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from lwm.project_memory import classify_event, load_processed_events

CANDIDATES_DIR = Path("state/candidates")
CandidateState = Literal["pending_review", "accepted", "rejected", "corrected"]

TRANSPORT_TAGS = frozenset({
    "codex", "vscode", "kiro", "antigravity", "gemini-cli", "structured-summary",
    "opencode", "claude-code", "trae", "trae-solo", "shell", "minimax",
})


def generic_observation(task: str) -> bool:
    return bool(re.fullmatch(r"observed [\w-]+ turn results", task.strip(), re.I))


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _candidate_id(kind: str, topic: str, scope: str) -> str:
    material = json.dumps([kind, " ".join(topic.casefold().split()), scope], ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class WorkflowCandidate:
    candidate_id: str
    trigger: str
    context: str
    steps: tuple[str, ...]
    verification: tuple[str, ...]
    outcome: str
    exceptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    counterevidence_ids: tuple[str, ...] = ()
    state: CandidateState = "pending_review"
    correction: str = ""
    created_at: str = ""
    kind: Literal["workflow"] = "workflow"
    semantic_topic: str = ""
    identity_scope: str = ""
    evidence_revision: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipCandidate:
    candidate_id: str
    relationship: str
    context: str
    steps: tuple[str, ...]
    verification: tuple[str, ...]
    outcome: str
    exceptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    counterevidence_ids: tuple[str, ...] = ()
    state: CandidateState = "pending_review"
    correction: str = ""
    created_at: str = ""
    kind: Literal["relationship"] = "relationship"
    semantic_topic: str = ""
    identity_scope: str = "cross-project"
    evidence_revision: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strings(events: Iterable[dict[str, Any]], key: str) -> tuple[str, ...]:
    values: list[str] = []
    for event in events:
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            values.extend(str(item).strip() for item in value if str(item).strip())
    return tuple(dict.fromkeys(values))


def _durable_events(events: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Keep candidate synthesis on the same admission boundary as memory."""

    return tuple(
        event
        for event in events
        if isinstance(event, dict) and classify_event(event).durability == "durable"
    )


def build_workflow_candidates(
    events: Iterable[dict[str, Any]], *, min_count: int = 3
) -> list[WorkflowCandidate]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    admitted = _durable_events(events)
    for event in admitted:
        task = str(event.get("task") or "observation").strip().lower()
        if generic_observation(task):
            continue
        key = ("task", str(event.get("tool") or "unknown"), task)
        groups.setdefault(key, []).append(event)
    # Exact wording is only one seed. Repeated action + verification themes
    # let the semantic compiler discover workflows across distinct tasks.
    themes: dict[tuple[str, str], list[dict[str, Any]]] = {}
    exact_ids = {
        str(event.get("event_id"))
        for group in groups.values()
        if len(group) >= min_count
        for event in group
        if event.get("event_id")
    }
    for event in admitted:
        if not event.get("verification") or not (event.get("decisions") or event.get("changes")):
            continue
        for tag in set(
            str(tag).strip().casefold() for tag in event.get("tags") or () if str(tag).strip()
        ):
            if tag in TRANSPORT_TAGS:
                continue
            themes.setdefault((str(event.get("tool") or "unknown"), tag), []).append(event)
    for (tool, tag), group in themes.items():
        ids = {str(event.get("event_id")) for event in group if event.get("event_id")}
        if len(ids) >= min_count and not ids.issubset(exact_ids):
            groups[("theme", tool, tag)] = group
    candidates: list[WorkflowCandidate] = []
    for (seed_kind, tool, task), group in groups.items():
        if len(group) < min_count:
            continue
        evidence_ids = tuple(
            sorted({str(event.get("event_id")) for event in group if event.get("event_id")})
        )
        projects = sorted(
            {str(event.get("project_id")) for event in group if event.get("project_id")}
        )
        steps = tuple(
            dict.fromkeys(_strings(group, "decisions") + _strings(group, "changes") + (task,))
        )
        verification = _strings(group, "verification")
        exceptions = _strings(group, "risks") + _strings(group, "open_questions")
        candidates.append(
            WorkflowCandidate(
                candidate_id=_candidate_id(
                    "workflow", f"{seed_kind}:{task}", f"tool:{tool}:cross-project"
                ),
                trigger=f"{tool} records this workflow observation"
                if seed_kind == "task"
                else f"{tool} records a `{task}` workflow theme for semantic review",
                context=f"Observed across {len(projects)} project(s): {', '.join(projects) or 'unknown scope'}.",
                steps=steps,
                verification=verification,
                outcome=str(group[-1].get("task") or task),
                exceptions=exceptions,
                evidence_ids=evidence_ids,
                created_at=_now(),
                semantic_topic=f"{seed_kind}:{task}",
                identity_scope=f"tool:{tool}:cross-project",
            )
        )
    return candidates


def build_relationship_candidates(
    events: Iterable[dict[str, Any]], *, min_projects: int = 2
) -> list[RelationshipCandidate]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for event in _durable_events(events):
        for tag in set(
            str(tag).strip().casefold() for tag in event.get("tags") or () if str(tag).strip()
        ):
            if tag in TRANSPORT_TAGS:
                continue
            buckets.setdefault(tag, []).append(event)
    candidates: list[RelationshipCandidate] = []
    for tag, group in buckets.items():
        projects = sorted(
            {str(event.get("project_id")) for event in group if event.get("project_id")}
        )
        if len(projects) < min_projects:
            continue
        evidence_ids = tuple(
            sorted({str(event.get("event_id")) for event in group if event.get("event_id")})
        )
        candidates.append(
            RelationshipCandidate(
                candidate_id=_candidate_id("relationship", tag, "cross-project"),
                relationship=f"The `{tag}` pattern may connect these projects",
                context=f"Projects: {', '.join(projects)}.",
                steps=_strings(group, "decisions") + _strings(group, "changes"),
                verification=_strings(group, "verification"),
                outcome=f"The tag `{tag}` recurs across {len(projects)} projects.",
                exceptions=_strings(group, "risks") + _strings(group, "open_questions"),
                evidence_ids=evidence_ids,
                created_at=_now(),
                semantic_topic=tag,
            )
        )
    return candidates


def _existing_candidate_path(
    root: Path, candidate: WorkflowCandidate | RelationshipCandidate
) -> Path:
    target = root / CANDIDATES_DIR / f"{candidate.candidate_id}.json"
    if target.is_file():
        return target
    # Legacy evidence-keyed records stay in place. Match semantic identity,
    # not shared evidence; a rejection wins over duplicate pending records.
    matches: list[tuple[int, Path]] = []
    priority = {"rejected": 0, "corrected": 1, "accepted": 2, "pending_review": 3}
    for path in sorted((root / CANDIDATES_DIR).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict) or payload.get("kind") != candidate.kind:
            continue
        if payload.get("semantic_topic"):
            same = (
                payload["semantic_topic"] == candidate.semantic_topic
                and payload.get("identity_scope") == candidate.identity_scope
            )
        elif candidate.kind == "relationship":
            same = payload.get("relationship") == candidate.relationship
        else:
            same = (
                payload.get("trigger") == candidate.trigger
                and str(payload.get("outcome") or "").strip().casefold()
                == candidate.outcome.strip().casefold()
            )
        if same:
            matches.append((priority.get(payload.get("state"), 4), path))
    return sorted(matches)[0][1] if matches else target


def save_candidate(root: Path, candidate: WorkflowCandidate | RelationshipCandidate) -> Path:
    target = _existing_candidate_path(root, candidate)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Candidate review is a user-owned decision.  A later harvest may observe
    # the same evidence again, but it must not reset accept/reject/corrected
    # state or replace the user's correction with a fresh timestamp.
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = None
        if isinstance(existing, dict) and existing.get("state") in {
            "pending_review",
            "accepted",
            "rejected",
            "corrected",
        }:
            # Regeneration cannot revoke a previously recorded counterexample.
            counters = set(existing.get("counterevidence_ids") or ()) | set(candidate.counterevidence_ids)
            updated = {
                "evidence_ids": sorted((set(existing.get("evidence_ids") or ()) | set(candidate.evidence_ids)) - counters),
                "counterevidence_ids": sorted(counters),
            }
            if all(set(existing.get(key) or ()) == set(value) for key, value in updated.items()):
                return target
            existing.update(updated)
            existing["semantic_topic"] = candidate.semantic_topic
            existing["identity_scope"] = candidate.identity_scope
            existing["evidence_revision"] = int(existing.get("evidence_revision") or 1) + 1
            existing["evidence_updated_at"] = _now()
            target.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            return target

    target.write_text(
        json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def generate_candidates(root: Path, events: Iterable[dict[str, Any]]) -> list[Path]:
    # Both builders need the same evidence.  Materialize one-shot iterators
    # once so a generator cannot silently starve relationship synthesis.
    evidence = tuple(events)
    paths: list[Path] = []
    for candidate in [
        *build_workflow_candidates(evidence),
        *build_relationship_candidates(evidence),
    ]:
        paths.append(save_candidate(root, candidate))
    return paths


def seed_analysis_candidates(root: Path, events: Iterable[dict[str, Any]]) -> list[Path]:
    """Bridge reviewable candidates into the optional Memory Compiler queue."""

    from lwm.memory_compiler import Candidate as AnalysisCandidate
    from lwm.memory_compiler import load_candidate, seed_candidate
    from lwm.queue_compaction import compact_analysis_queue

    compact_analysis_queue(root)

    evidence = tuple(events)
    event_index = {
        str(event.get("event_id")): event
        for event in evidence
        if isinstance(event, dict) and event.get("event_id")
    }
    paths: list[Path] = []
    reviewable = [
        *build_workflow_candidates(evidence),
        *build_relationship_candidates(evidence),
    ]
    for candidate in reviewable:
        review_path = _existing_candidate_path(root, candidate)
        try:
            review_payload = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            review_payload = {}
        review_state = (
            str(review_payload.get("state") or candidate.state)
            if isinstance(review_payload, dict)
            else candidate.state
        )
        if review_state == "rejected":
            continue
        existing_analysis = load_candidate(root, review_path.stem)
        counters = set(candidate.counterevidence_ids)
        if isinstance(review_payload, dict):
            counters.update(review_payload.get("counterevidence_ids") or ())
        if existing_analysis is not None:
            counters.update(existing_analysis.counterevidence_ids)
        # Missing counterevidence must remain visible to validation, not vanish.
        evidence_ids = tuple(
            event_id for event_id in candidate.evidence_ids
            if event_id in event_index and event_id not in counters
        )
        if not evidence_ids:
            continue
        scope = tuple(
            sorted(
                {
                    str(event_index[event_id].get("project_id"))
                    for event_id in evidence_ids
                    if event_index[event_id].get("project_id")
                }
            )
        )
        claim = (
            f"{candidate.trigger}: {candidate.outcome}"
            if candidate.kind == "workflow"
            else candidate.relationship
        )
        context = candidate.context
        if isinstance(review_payload, dict) and review_payload.get("correction"):
            context = f"{context} User correction: {str(review_payload['correction'])[:1000]}"
        analysis = AnalysisCandidate(
            candidate_id=review_path.stem,
            kind=candidate.kind,
            claim=claim,
            scope=scope,
            evidence_ids=evidence_ids,
            counterevidence_ids=tuple(sorted(counters)),
            context=context,
            uncertainty="Generated from admitted durable evidence; compiler review required.",
            validity="unknown",
            state="pending_analysis",
            created_at=candidate.created_at,
        )
        paths.append(seed_candidate(root, analysis))
    return paths


def review_candidate(
    root: Path,
    candidate_id: str,
    *,
    decision: Literal["accept", "reject", "correct"],
    correction: str = "",
) -> dict[str, Any]:
    path = root / CANDIDATES_DIR / f"{candidate_id}.json"
    if not path.is_file():
        raise FileNotFoundError(candidate_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if decision == "accept":
        source_ids = {
            str(event.get("event_id"))
            for _, event in load_processed_events(root)
            if event.get("event_id")
        }
        evidence_ids = payload.get("evidence_ids")
        counterevidence_ids = payload.get("counterevidence_ids") or []
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or not isinstance(counterevidence_ids, list)
            or any(
                not isinstance(event_id, str) or event_id not in source_ids
                for event_id in [*evidence_ids, *counterevidence_ids]
            )
        ):
            raise ValueError("candidate source events must all exist before acceptance")
    state: CandidateState = {"accept": "accepted", "reject": "rejected", "correct": "corrected"}[
        decision
    ]  # type: ignore[assignment]
    payload["state"] = state
    payload["correction"] = correction
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def load_accepted(root: Path) -> list[dict[str, Any]]:
    base = root / CANDIDATES_DIR
    if not base.is_dir():
        return []
    accepted: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and payload.get("state") == "accepted":
            accepted.append(payload)
    return accepted


__all__ = [
    "CANDIDATES_DIR",
    "RelationshipCandidate",
    "WorkflowCandidate",
    "build_relationship_candidates",
    "build_workflow_candidates",
    "generate_candidates",
    "load_accepted",
    "review_candidate",
    "save_candidate",
    "seed_analysis_candidates",
]
