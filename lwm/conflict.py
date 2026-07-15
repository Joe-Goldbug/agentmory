"""Conflict detection for project/global memory.

When two events across projects contain the same ``tags`` but
contradicting ``decisions``, we write a conflict page in
``wiki/review/conflict-<date>.md`` listing both sides for human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Conflict:
    tag: str
    project_ids: tuple[str, ...]
    decisions: tuple[tuple[str, str], ...]  # (project_id, decision_text)
    timestamp: str

    def render(self) -> str:
        body = [f"## Tag `{self.tag}` — {self.timestamp}"]
        body.append("")
        for project_id, decision in self.decisions:
            body.append(f"- **{project_id}**: {decision}")
        return "\n".join(body)


def detect_conflicts(
    events: Iterable[dict],
    *,
    min_projects: int = 2,
) -> list[Conflict]:
    """Return conflicts from a flat list of events (already loaded)."""

    by_tag: dict[str, dict[str, list[str]]] = {}
    for event in events:
        tags = event.get("tags") or []
        decisions = event.get("decisions") or []
        project_id = str(event.get("project_id") or "")
        str(event.get("timestamp") or "")
        if not tags or not decisions:
            continue
        for tag in tags:
            bucket = by_tag.setdefault(str(tag), {})
            for decision in decisions:
                bucket.setdefault(project_id, []).append(str(decision))
    conflicts: list[Conflict] = []
    for tag, projects in by_tag.items():
        if len(projects) < min_projects:
            continue
        flat = []
        for pid, decs in projects.items():
            for dec in decs:
                flat.append((pid, dec))
        if len({dec for _, dec in flat}) > 1:
            conflicts.append(
                Conflict(
                    tag=tag,
                    project_ids=tuple(sorted(projects.keys())),
                    decisions=tuple(flat),
                    timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                )
            )
    return conflicts


def write_conflict_page(root: Path, conflicts: list[Conflict]) -> Path | None:
    if not conflicts:
        return None
    review_dir = root / "wiki" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().date().isoformat()
    target = review_dir / f"conflict-{today}.md"
    header = (
        "---\n"
        f"title: Conflict Report {today}\n"
        "type: review\n"
        "tags:\n  - conflict\n  - review\n"
        "sources:\n  - raw/events/processed\n"
        f"updated: {today}\n"
        "---\n\n"
        f"# Conflict Report — {today}\n\n"
    )
    body = "\n\n".join(c.render() for c in conflicts) + "\n"
    target.write_text(header + body, encoding="utf-8")
    return target


__all__ = ["Conflict", "detect_conflicts", "write_conflict_page"]
