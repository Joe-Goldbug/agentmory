"""Cross-project insight candidate generation.

Insight candidates are suggestions from the ingest pipeline that some
behavior/decision is recurring across projects. They live under
``wiki/review/candidate-<date>-<idx>.md`` and require human review
before promotion to ``wiki/global/``.

Two flavours:

* *cross-project* — same tag, ≥2 projects, ≥1 verification anywhere.
* *workflow_observation* — same tool records ≥3 events on the same
  event_type within 7 days.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CrossProjectInsight:
    title: str
    tag: str
    project_ids: tuple[str, ...]
    summary: str
    evidence: tuple[str, ...]
    timestamp: str

    def render(self) -> str:
        body = [
            f"## {self.title}",
            "",
            f"- Tag: `{self.tag}`",
            f"- Projects: {', '.join(self.project_ids)}",
            f"- Captured: {self.timestamp}",
            "",
            "### Summary",
            "",
            self.summary,
            "",
            "### Evidence",
            "",
            "\n".join(f"- {line}" for line in self.evidence),
            "",
        ]
        return "\n".join(body)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _cross_project_candidates(
    events: list[dict],
    *,
    min_projects: int = 2,
) -> list[CrossProjectInsight]:
    bucket: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        tags = event.get("tags") or []
        project_id = event.get("project_id")
        if not tags or not project_id:
            continue
        for tag in tags:
            bucket[str(tag)].append(event)

    insights: list[CrossProjectInsight] = []
    for tag, group in bucket.items():
        projects = {str(e["project_id"]) for e in group if e.get("project_id")}
        if len(projects) < min_projects:
            continue
        evidence = []
        for event in group:
            text = str(event.get("task") or event.get("event_type") or "(no task)")
            evidence.append(f"[{event.get('project_id')}] {text}")
        insights.append(
            CrossProjectInsight(
                title=f"Recurring tag `{tag}` across {len(projects)} projects",
                tag=tag,
                project_ids=tuple(sorted(projects)),
                summary=(
                    f"The tag `{tag}` was raised in {len(projects)} projects. "
                    "Verify the recurring pattern and decide if it deserves a "
                    "global rule."
                ),
                evidence=tuple(evidence[:10]),
                timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )
        )
    return insights


def _workflow_candidates(
    events: list[dict],
    *,
    min_count: int = 3,
    within_days: int = 7,
) -> list[CrossProjectInsight]:
    counter: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    for event in events:
        if event.get("event_type") != "workflow_observation":
            continue
        tool = str(event.get("tool") or "unknown")
        kind = str(event.get("task") or event.get("event_type") or "observation")
        counter[(tool, kind)] += 1
        if len(examples[(tool, kind)]) < 5:
            examples[(tool, kind)].append(
                f"[{event.get('timestamp')}] {event.get('project_id')}: "
                f"{event.get('task') or '(no task)'}"
            )
    insights: list[CrossProjectInsight] = []
    for (tool, kind), count in counter.items():
        if count < min_count:
            continue
        insights.append(
            CrossProjectInsight(
                title=f"Workflow `{tool}` repeatedly records `{kind}` ({count}×)",
                tag=f"workflow:{tool}:{kind}",
                project_ids=tuple(),
                summary=(
                    f"Tool `{tool}` produced {count} observations of the same "
                    "kind in the recent window. Promote only after manual review."
                ),
                evidence=tuple(examples[(tool, kind)]),
                timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )
        )
    return insights


def collect_candidates(events: list[dict]) -> list[CrossProjectInsight]:
    return _cross_project_candidates(events) + _workflow_candidates(events)


def write_candidates(
    root: Path,
    insights: list[CrossProjectInsight],
    *,
    day: str | None = None,
) -> list[Path]:
    if not insights:
        return []
    review_dir = root / "wiki" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    date_part = day or datetime.utcnow().date().isoformat()
    target = review_dir / f"candidates-{date_part}.md"
    header = (
        "---\n"
        f"title: Insight Candidates {date_part}\n"
        "type: review\n"
        "tags: [insight-candidate, review]\n"
        "sources:\n  - raw/events/processed\n"
        f"updated: {date_part}\n"
        "---\n\n"
        f"# Insight Candidates — {date_part}\n\n"
    )
    body_parts = [insight.render() for insight in insights]
    target.write_text(header + "\n".join(body_parts), encoding="utf-8")
    return [target]


def load_processed_events(root: Path) -> list[dict]:
    """Load every event currently under ``raw/events/processed/``."""

    base = root / "raw" / "events" / "processed"
    if not base.is_dir():
        return []
    out: list[dict] = []
    import json

    for day_dir in sorted(base.iterdir()):
        if not day_dir.is_dir():
            continue
        for path in sorted(day_dir.glob("*.json")):
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return out


__all__ = [
    "CrossProjectInsight",
    "collect_candidates",
    "load_processed_events",
    "write_candidates",
]
