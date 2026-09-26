"""Compatibility helpers for the retired insight promotion surface.

Promotion is gated by hard rules (no LLM needed):

* The candidate must originate from ≥ 2 distinct ``project_id`` values.
* It must have at least one verification field across the contributing
  events.
* It must not contain the literal tokens ``tmp``, ``scratch``,
  ``once``, or any user-defined temporary marker.
* It must not conflict with an existing global page (same title+tag).

The current authoritative path is the stateful compiler candidate flow:
``hub review-analysis`` followed by ``hub promote-analysis``. This module
still reads and records legacy insight decisions, but it must never write a
global page or create a second promotion authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lwm.insights import CrossProjectInsight
from lwm.project_memory import classify_event

TEMP_TOKEN_RE = re.compile(r"\b(tmp|scratch|once|temporary)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PromotionDecision:
    insight_title: str
    approved: bool
    reasons: tuple[str, ...]
    target_path: Path | None


def gather_supporting_events(
    events: Iterable[dict],
    *,
    tag: str,
    project_ids: Iterable[str],
) -> list[dict]:
    ps = set(project_ids)
    out = []
    for event in events:
        if tag not in (event.get("tags") or []):
            continue
        if event.get("project_id") not in ps:
            continue
        if classify_event(event).durability != "durable":
            continue
        out.append(event)
    return out


def _has_verification(events: list[dict]) -> bool:
    for event in events:
        if event.get("verification"):
            return True
    return False


def _has_temp_token(text: str) -> bool:
    return bool(TEMP_TOKEN_RE.search(text or ""))


def existing_global_titles(root: Path) -> set[str]:
    global_dir = root / "wiki" / "global"
    if not global_dir.is_dir():
        return set()
    titles = set()
    for path in global_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("title:"):
                titles.add(stripped.split(":", 1)[1].strip())
                break
    return titles


PROMOTION_STATE_FILENAME = "promotion-state.json"


def _promotion_state_path(root: Path) -> Path:
    return (root / "state" / PROMOTION_STATE_FILENAME).resolve()


def load_promotion_state(root: Path) -> dict:
    path = _promotion_state_path(root)
    if not path.is_file():
        return {"approved": [], "rejected": []}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"approved": [], "rejected": []}
    if not isinstance(data, dict):
        return {"approved": [], "rejected": []}
    return {
        "approved": list(data.get("approved", [])),
        "rejected": list(data.get("rejected", [])),
    }


def save_promotion_state(root: Path, state: dict) -> Path:
    path = _promotion_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def record_promotion(root: Path, decision: "PromotionDecision") -> None:
    """Persist the outcome of one promotion in ``state/promotion-state.json``.

    Both approved and rejected decisions are tracked so audit can prove
    why a candidate never reached ``wiki/global/``.
    """

    state = load_promotion_state(root)
    entry = {
        "title": decision.insight_title,
        "approved": bool(decision.approved),
        "reasons": list(decision.reasons),
        "target": str(decision.target_path) if decision.target_path else None,
        "at": _now_iso(),
    }
    if decision.approved:
        state["approved"].append(entry)
    else:
        state["rejected"].append(entry)
    save_promotion_state(root, state)


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def promote(
    root: Path,
    insight: CrossProjectInsight,
    *,
    supporting_events: list[dict] | None = None,
    llm_summary: str | None = None,
) -> PromotionDecision:
    """Evaluate the retired insight shape without writing global memory.

    The old insight object has no candidate state, explicit evidence IDs, or
    human approval transition. Keeping its former write behavior would leave
    a second authority beside ``hub promote-analysis``. The arguments remain
    accepted for compatibility, but promotion is deliberately fail-closed.
    """

    return PromotionDecision(
        insight_title=insight.title,
        approved=False,
        reasons=(
            "legacy_auto_promotion_disabled: use hub review-analysis and "
            "hub promote-analysis",
        ),
        target_path=None,
    )


def auto_promote_all(
    root: Path,
    insights: list[CrossProjectInsight],
    events: list[dict],
) -> tuple[list[PromotionDecision], list[CrossProjectInsight]]:
    """Record legacy decisions without writing any global page.

    This compatibility function is intentionally observation-only. It lets
    old callers inspect why a candidate was withheld while forcing all new
    global writes through the stateful, evidence-bound review path.
    """

    decisions: list[PromotionDecision] = []
    leftovers: list[CrossProjectInsight] = []
    for insight in insights:
        supporting = gather_supporting_events(
            events,
            tag=insight.tag,
            project_ids=insight.project_ids,
        )
        decision = promote(root, insight, supporting_events=supporting)
        decisions.append(decision)
        try:
            record_promotion(root, decision)
        except Exception:
            pass
        if not decision.approved:
            leftovers.append(insight)
    return decisions, leftovers


__all__ = [
    "PromotionDecision",
    "auto_promote_all",
    "existing_global_titles",
    "gather_supporting_events",
    "promote",
]
