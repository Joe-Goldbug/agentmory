"""Stable-claim-key global promotion.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 6. Workflow and relationship consolidation

The legacy promote module keys global pages by *tag + project count*, which
produces the 39/40/41 project-counting noise. This module re-keys global
promotion by a stable claim hash so that adding or losing a project
re-evaluates the same candidate page instead of creating a new one.

A claim may be promoted only when:

* the candidate is an admitted durable event (Truthful Core) — never a
  lifecycle/session/adapter/shell tag;
* at least two distinct project ids back the claim;
* at least one verification entry exists across the supporting events;
* the claim passes the no-cosmic / no-secret validator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from lwm.project_memory import classify_event


BLOCKED_PROMOTION_TAGS = frozenset(
    {
        "lifecycle",
        "session",
        "adapter",
        "workflow_observation",
        "shell",
    }
)

MIN_PROMOTION_PROJECTS = 2
MIN_VERIFIED_PROJECTS = 2

# Patterns reused from the Memory Compiler. We deliberately duplicate the small
# list here to keep this module free of an LLM dependency at import time.
FORBIDDEN_PATTERNS = (
    r"\bcauses?\b",
    r"\bbecause of\b",
    r"\balways\b",
    r"\bnever\b",
)

_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})"
)


@dataclass(frozen=True)
class PromotionCandidate:
    claim: str
    project_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    verification_count: int
    promoted: bool
    claim_key: str
    target_path: Path | None
    reasons: tuple[str, ...] = ()


def normalize_claim(text: str) -> str:
    """Normalize a claim to a canonical form used for hashing.

    * lower-case
    * collapse runs of whitespace
    * drop trailing punctuation
    """

    lowered = (text or "").lower()
    spaced = re.sub(r"\s+", " ", lowered).strip()
    return spaced.rstrip(".!?:;,。")


def stable_claim_key(claim: str, *, prefix: str = "claim") -> str:
    """Stable, hash-based key independent of project count."""

    normalized = normalize_claim(claim)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    slug_source = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:32] or "untitled"
    return f"{prefix}-{slug_source}-{digest}"


def _eligible_events(
    events: Iterable[dict],
    *,
    claim: str,
    evidence_ids: set[str] | None = None,
) -> list[dict]:
    """Return durable events whose task or decisions match ``claim``."""

    target = normalize_claim(claim)
    eligible: list[dict] = []
    for event in events:
        if evidence_ids is not None and str(event.get("event_id") or "") not in evidence_ids:
            continue
        if classify_event(event).durability != "durable":
            continue
        tags = {str(tag).lower() for tag in event.get("tags") or []}
        if tags & BLOCKED_PROMOTION_TAGS:
            continue
        if evidence_ids is None:
            haystacks = [
                str(event.get("task") or ""),
                *(str(d) for d in event.get("decisions") or []),
                *(str(d) for d in event.get("changes") or []),
            ]
            joined = " ".join(haystacks).lower()
            if target and target not in normalize_claim(joined):
                continue
        eligible.append(event)
    return eligible


def _safe_path_part(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "-", text).strip("-")[:64] or "page"


def render_global_page(
    *,
    claim: str,
    claim_key: str,
    project_ids: tuple[str, ...],
    event_ids: tuple[str, ...],
    evidence_paths: tuple[str, ...],
    actor: str,
    reasons: tuple[str, ...] = (),
    page_type: str = "principle",
) -> str:
    if page_type not in {"pattern", "relationship", "principle"}:
        raise ValueError(f"unsupported global page type: {page_type}")
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    frontmatter_lines = [
        "---",
        f"title: {claim}",
        f"type: {page_type}",
        "status: approved",
        f"claim_key: {claim_key}",
        f"actor: {actor}",
        f"projects: [{', '.join(project_ids)}]",
        f"event_ids: [{', '.join(event_ids)}]",
        "evidence_paths:",
        *(
            f"  - {path}"
            for path in evidence_paths
        ),
        f"created_at: {now}",
        f"updated: {now}",
        f"tags: [{page_type}, approved, stable-claim]",
        "sources:",
        "  - raw/events/processed",
        "---",
        "",
        f"# {claim}",
        "",
        "## Supporting projects",
        "",
        *(f"- `{pid}`" for pid in project_ids),
        "",
        "## Evidence",
        "",
        *(f"- event `{eid}`" for eid in event_ids),
        "",
    ]
    if reasons:
        frontmatter_lines += [
            "## Promotion reasons",
            "",
            *(f"- {r}" for r in reasons),
            "",
        ]
    return "\n".join(frontmatter_lines)


def evaluate_promotion(
    root: Path,
    *,
    claim: str,
    events: Iterable[dict],
    evidence_ids: Iterable[str] | None = None,
    actor: str = "human",
) -> PromotionCandidate:
    """Evaluate one claim against an event stream.

    Returns a :class:`PromotionCandidate` describing whether the claim is
    promotable, the target page path, and the supporting evidence. The target
    path is the same regardless of how many projects currently back the
    claim — project-count changes do not produce new pages.
    """

    key = stable_claim_key(claim)
    target = root / "wiki" / "global" / f"{_safe_path_part(key)}.md"

    if not claim.strip():
        return PromotionCandidate(
            claim=claim,
            project_ids=(),
            event_ids=(),
            evidence_paths=(),
            verification_count=0,
            promoted=False,
            claim_key=key,
            target_path=target,
            reasons=("empty_claim",),
        )

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, claim, re.IGNORECASE):
            return PromotionCandidate(
                claim=claim,
                project_ids=(),
                event_ids=(),
                evidence_paths=(),
                verification_count=0,
                promoted=False,
                claim_key=key,
                target_path=target,
                reasons=(f"forbidden_pattern:{pattern}",),
            )
    if _SECRET_RE.search(claim):
        return PromotionCandidate(
            claim=claim,
            project_ids=(),
            event_ids=(),
            evidence_paths=(),
            verification_count=0,
            promoted=False,
            claim_key=key,
            target_path=target,
            reasons=("secret_in_claim",),
        )

    selected_ids = set(evidence_ids) if evidence_ids is not None else None
    eligible = _eligible_events(events, claim=claim, evidence_ids=selected_ids)
    if not eligible:
        return PromotionCandidate(
            claim=claim,
            project_ids=(),
            event_ids=(),
            evidence_paths=(),
            verification_count=0,
            promoted=False,
            claim_key=key,
            target_path=target,
            reasons=("no_eligible_durable_events",),
        )

    project_ids = sorted({str(e.get("project_id")) for e in eligible if e.get("project_id")})
    event_ids = tuple(
        str(e.get("event_id") or "") for e in eligible if e.get("event_id")
    )
    evidence_paths = tuple(
        str(e.get("source", {}).get("path") or "")
        for e in eligible
        if isinstance(e.get("source"), dict)
    )
    verification_count = sum(
        1 for e in eligible if e.get("verification")
    )
    verified_projects = sorted(
        {
            str(e.get("project_id"))
            for e in eligible
            if e.get("verification") and e.get("project_id")
        }
    )

    reasons: list[str] = []
    if len(project_ids) < MIN_PROMOTION_PROJECTS:
        reasons.append(f"insufficient_projects:{len(project_ids)}")
    if len(verified_projects) < MIN_VERIFIED_PROJECTS:
        reasons.append(f"insufficient_verified_projects:{len(verified_projects)}")
    if verification_count < 1:
        reasons.append("no_verification")

    return PromotionCandidate(
        claim=claim,
        project_ids=tuple(project_ids),
        event_ids=event_ids,
        evidence_paths=evidence_paths,
        verification_count=verification_count,
        promoted=not reasons,
        claim_key=key,
        target_path=target,
        reasons=tuple(reasons) if reasons else ("ok",),
    )


def persist_promotion(
    candidate: PromotionCandidate,
    *,
    actor: str = "human",
    page_type: str = "principle",
) -> Path | None:
    """Write the candidate's target page and an audit log entry.

    Returns the page path on success, ``None`` if the candidate is not
    promotable.
    """

    if not candidate.promoted or candidate.target_path is None:
        return None
    if page_type not in {"pattern", "relationship", "principle"}:
        raise ValueError(f"unsupported global page type: {page_type}")
    candidate.target_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path: Path | None = None
    if candidate.target_path.is_file():
        backup_dir = candidate.target_path.parent / ".promotion-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rollback_path = backup_dir / f"{candidate.claim_key}-{timestamp}.md"
        rollback_path.write_bytes(candidate.target_path.read_bytes())
    rendered = render_global_page(
        claim=candidate.claim,
        claim_key=candidate.claim_key,
        project_ids=candidate.project_ids,
        event_ids=candidate.event_ids,
        evidence_paths=tuple(path for path in candidate.evidence_paths if path),
        actor=actor,
        reasons=candidate.reasons,
        page_type=page_type,
    )
    temporary = candidate.target_path.with_name(candidate.target_path.name + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(candidate.target_path)
    _append_audit(
        candidate,
        actor=actor,
        action="promoted",
        rollback_path=rollback_path,
        page_type=page_type,
    )
    return candidate.target_path


def _append_audit(
    candidate: PromotionCandidate,
    *,
    actor: str,
    action: str,
    rollback_path: Path | None = None,
    page_type: str = "principle",
) -> None:
    """Append a single-line audit record; the only durable side effect that is
    not the page itself.
    """

    if candidate.target_path is None:
        return
    audit = candidate.target_path.parent.parent / "promotion-audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "actor": actor,
        "action": action,
        "claim": candidate.claim,
        "claim_key": candidate.claim_key,
        "target": str(candidate.target_path),
        "projects": list(candidate.project_ids),
        "event_ids": list(candidate.event_ids),
        "evidence_paths": list(candidate.evidence_paths),
        "reasons": list(candidate.reasons),
        "page_type": page_type,
        "rollback": {
            "backup_path": str(rollback_path) if rollback_path else None,
            "restore_target": str(candidate.target_path),
        },
    }
    with audit.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


__all__ = [
    "BLOCKED_PROMOTION_TAGS",
    "MIN_PROMOTION_PROJECTS",
    "MIN_VERIFIED_PROJECTS",
    "PromotionCandidate",
    "evaluate_promotion",
    "normalize_claim",
    "persist_promotion",
    "render_global_page",
    "stable_claim_key",
]
