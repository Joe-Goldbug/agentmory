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
* positive, claim-relevant verifications exist in at least two projects;
* the claim passes the no-cosmic / no-secret validator.

Only derived approved pages are revalidated and retracted, with backups and
audit history. Manual rules are never touched; reapproval remains explicit.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from lwm import lockfile
from lwm.analysis import _parse_frontmatter, _split_csv_list
from lwm.project_memory import classify_event, load_processed_events


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

_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})")


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
    counterevidence_ids: tuple[str, ...] = ()


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
        if not _active_event(event):
            continue
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


def _active_event(event: dict) -> bool:
    terminal = {
        "retired",
        "retracted",
        "withdrawn",
        "source_withdrawn",
        "superseded",
        "rejected",
        "deleted",
    }
    return not (
        str(event.get("status") or "").lower() in terminal
        or event.get("superseded_by")
        or event.get("withdrawn_at")
        or event.get("retired_at")
        or (
            isinstance(event.get("source"), dict)
            and str(event["source"].get("status") or "").lower() in terminal
        )
    )


def _verified_for_claim(event: dict, claim: str) -> bool:
    target = normalize_claim(claim)
    values = event.get("verification_results", event.get("verification", []))
    if isinstance(values, (str, dict)):
        values = [values]
    if not isinstance(values, list):
        return False
    positive_support = False
    for value in values:
        if isinstance(value, dict):
            positive = str(value.get("status") or "").lower() in {
                "passed",
                "pass",
                "success",
                "succeeded",
                "ok",
            }
            relevant = normalize_claim(str(value.get("claim") or "")) == target or value.get(
                "claim_key"
            ) == stable_claim_key(claim)
            if positive and relevant:
                positive_support = True
            elif relevant and str(value.get("status") or "").lower() in {"failed", "fail", "error"}:
                return False
        elif isinstance(value, str):
            text = normalize_claim(value)
            negative = re.search(
                r"\b(fail(?:ed|ure|s)?|error|unknown|unrelated|not|unverified)\b", text
            )
            positive = re.search(r"\b(pass(?:ed)?|success(?:ful)?|succeeded|ok)\b", text)
            if positive and not negative and target and target in text:
                positive_support = True
            elif negative and target and target in text:
                return False
    return positive_support


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
    counterevidence_ids: tuple[str, ...] = (),
) -> str:
    if page_type not in {"pattern", "relationship", "principle"}:
        raise ValueError(f"unsupported global page type: {page_type}")
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    frontmatter_lines = [
        "---",
        f"title: {json.dumps(claim, ensure_ascii=False)}",
        f"type: {page_type}",
        "status: approved",
        f"claim_key: {claim_key}",
        f"actor: {actor}",
        f"projects: [{', '.join(project_ids)}]",
        f"event_ids: [{', '.join(event_ids)}]",
        f"counterevidence_ids: [{', '.join(counterevidence_ids)}]",
        "promotion_metadata: "
        + json.dumps(
            {
                "claim": claim,
                "event_ids": event_ids,
                "counterevidence_ids": counterevidence_ids,
                "claim_key": claim_key,
                "page_type": page_type,
            },
            ensure_ascii=False,
        ),
        "evidence_paths:",
        *(f"  - {path}" for path in evidence_paths),
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
    counterevidence_ids: Iterable[str] = (),
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
    counter_ids = set(counterevidence_ids)
    events = tuple(event for event in events if isinstance(event, dict))
    # One source cannot impersonate two project verifications.
    event_index = {str(event.get("event_id")): event for event in events if event.get("event_id")}
    eligible = _eligible_events(event_index.values(), claim=claim, evidence_ids=selected_ids)
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
    event_ids = tuple(str(e.get("event_id") or "") for e in eligible if e.get("event_id"))
    evidence_paths = tuple(
        str(e.get("source", {}).get("path") or "")
        for e in eligible
        if isinstance(e.get("source"), dict)
    )
    verification_count = sum(1 for e in eligible if _verified_for_claim(e, claim))
    verified_projects = sorted(
        {
            str(e.get("project_id"))
            for e in eligible
            if _verified_for_claim(e, claim) and e.get("project_id")
        }
    )

    reasons: list[str] = []
    if selected_ids is not None and selected_ids - set(event_ids):
        reasons.append("missing_or_retired_evidence")
    if counter_ids:
        reasons.append("counterevidence_requires_review")
    if any(
        _active_event(e)
        and (
            set(e.get("retracts_event_ids") or ()) & set(event_ids)
            or e.get("retracts_claim_key") == key
            or e.get("supersedes_claim_key") == key
        )
        for e in events
    ):
        reasons.append("source_retraction")
    if any(e.get("counterevidence_ids") for e in eligible):
        reasons.append("source_counterevidence")
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
        counterevidence_ids=tuple(sorted(counter_ids)),
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

    if candidate.target_path is None:
        return None
    if not candidate.promoted:
        return _retract_promotion(candidate, actor=actor)
    if page_type not in {"pattern", "relationship", "principle"}:
        raise ValueError(f"unsupported global page type: {page_type}")
    candidate.target_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path: Path | None = None
    if candidate.target_path.is_file():
        if not _derived_metadata(
            candidate.target_path.read_text(encoding="utf-8"), candidate.claim_key
        ):
            return None
        backup_dir = candidate.target_path.parent / ".promotion-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
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
        counterevidence_ids=candidate.counterevidence_ids,
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


def _derived_metadata(text: str, claim_key: str | None = None) -> dict | None:
    fields, _ = _parse_frontmatter(text)
    if "stable-claim" not in _split_csv_list(fields.get("tags", "")):
        return None
    if fields.get("type") not in {"pattern", "relationship", "principle"}:
        return None
    try:
        metadata = (
            json.loads(fields["promotion_metadata"])
            if fields.get("promotion_metadata")
            else {
                "claim": fields.get("title", ""),
                "claim_key": fields.get("claim_key", ""),
                "event_ids": list(_split_csv_list(fields.get("event_ids", ""))),
                "counterevidence_ids": list(_split_csv_list(fields.get("counterevidence_ids", ""))),
                "page_type": fields.get("type"),
            }
        )
    except ValueError:
        return None
    if not isinstance(metadata, dict) or not isinstance(metadata.get("claim"), str):
        return None
    if (
        metadata.get("claim_key") != stable_claim_key(metadata["claim"])
        or (claim_key is not None and metadata["claim_key"] != claim_key)
        or not isinstance(metadata.get("event_ids"), list)
        or not metadata["event_ids"]
        or not all(isinstance(eid, str) for eid in metadata["event_ids"])
    ):
        return None
    return {**metadata, "status": fields.get("status")}


def _retract_promotion(candidate: PromotionCandidate, *, actor: str) -> Path | None:
    path = candidate.target_path
    if path is None or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    metadata = _derived_metadata(text, candidate.claim_key)
    if not metadata or metadata["status"] not in {"approved", "source_withdrawn"}:
        return None
    backup_dir = path.parent / ".promotion-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = backup_dir / f"{candidate.claim_key}-{stamp}.md"
    backup.write_bytes(path.read_bytes())
    front, body = text[4:].split("\n---\n", 1)
    front = re.sub(r"^status:.*$", "status: retracted", front, count=1, flags=re.MULTILINE)
    front = re.sub(
        r"^tags:.*$",
        f"tags: [{metadata['page_type']}, retracted, stable-claim]",
        front,
        count=1,
        flags=re.MULTILINE,
    )
    front += "\nretraction_reasons: " + json.dumps(candidate.reasons)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")
    temporary.replace(path)
    _append_audit(
        candidate,
        actor=actor,
        action="retracted",
        rollback_path=backup,
        page_type=metadata["page_type"],
    )
    return path


def revalidate_promotions(root: Path, *, actor: str = "memory-compiler") -> dict:
    """Recompute derived approvals only. Never generate or reapprove a page."""
    root = root.resolve()
    report = {"retracted": [], "unchanged": [], "errors": []}
    with lockfile.cycle_lock(root):
        pages = []
        for path in sorted((root / "wiki/global").glob("*.md")):
            metadata = _derived_metadata(path.read_text(encoding="utf-8"))
            if metadata and metadata["status"] in {"approved", "source_withdrawn"}:
                pages.append((path, metadata))
        if not pages:
            return report
        events = [event for _, event in load_processed_events(root)]
        review_states: dict[str, list[dict]] = {}
        for path in sorted((root / "state/analysis/candidates").glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("claim"), str):
                review_states.setdefault(stable_claim_key(payload["claim"]), []).append(payload)
        for path, metadata in pages:
            evaluated = evaluate_promotion(
                root,
                claim=metadata["claim"],
                events=events,
                evidence_ids=metadata["event_ids"],
                counterevidence_ids=metadata.get("counterevidence_ids", ()),
            )
            approvals = review_states.get(metadata["claim_key"], [])
            if any(item.get("state") == "rejected" for item in approvals):
                evaluated = replace(
                    evaluated, promoted=False, reasons=("human_approval_withdrawn",)
                )
            elif any(item.get("counterevidence_ids") for item in approvals):
                evaluated = replace(
                    evaluated, promoted=False, reasons=("counterevidence_requires_review",)
                )
            if evaluated.target_path != path:
                continue
            if not evaluated.promoted and persist_promotion(evaluated, actor=actor):
                report["retracted"].append(path.name)
            else:
                report["unchanged"].append(path.name)
    return report


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
        "counterevidence_ids": list(candidate.counterevidence_ids),
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
    "revalidate_promotions",
    "stable_claim_key",
]
