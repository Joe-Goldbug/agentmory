"""`lwm context` builder.

Composes the markdown view that tools consume:

1. Global memory (per principle).
2. Project memory for the resolved project.
3. Open questions for the project.
4. Cross-project insight candidates (recent N).
5. Recent 7-day tool collaboration summary.
6. Risk / verification rules from global principles.

JSON mode returns structured fields so plugins (MCP, IDE) can index.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from lwm import dedup, project_id, project_memory


@dataclass(frozen=True)
class ContextReport:
    tool: str
    project_path: str | None
    project_id: str | None
    markdown: str
    data: dict[str, Any]

    @property
    def ok(self) -> bool:
        return bool(self.markdown.strip())


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower().replace(" ", "_")
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        if line.strip():
            sections[current].append(line.strip())
    return sections


def _recent_tool_activity(root: Path, *, limit: int = 7) -> list[dict[str, Any]]:
    index = dedup.load_event_index(root)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=limit)
    rows: list[dict[str, Any]] = []
    for entry in index.values():
        ts = _parse_iso(str(entry.get("timestamp")))
        if ts is None or ts < cutoff:
            continue
        rows.append(entry)
    rows.sort(key=lambda e: str(e.get("timestamp") or ""), reverse=True)
    return rows[:30]


def _open_questions_for(project_text: str) -> list[str]:
    sections = _read_sections(project_text)
    return [line for line in sections.get("open_questions", []) if line.startswith("- ")]


def _resolve_id_for_context(root: Path, project_path: str) -> str:
    """Resolve the project id for context rendering.

    We prefer the cached id in ``state/project-map.json`` (set by
    ``record_event`` / ``record_project`` during ingest) so that the same
    path always maps to the same id *after* the first event lands. For an
    unseen path we fall back to the git/local/adhoc resolver.
    """

    cache = project_id.load_project_map(root)
    key = str(Path(project_path).expanduser().resolve())
    cached = cache.get(key)
    if cached:
        return cached
    return project_id.resolve_project_id(project_path).project_id


def _discover_project_path(root: Path) -> str | None:
    """Use cwd only when the hub already knows that path as a project."""

    current = str(Path.cwd().resolve())
    cache = project_id.load_project_map(root)
    if current in cache:
        return current
    return None


def build(
    root: Path,
    *,
    tool: str,
    project_path: str | None,
    format: str = "markdown",
    limit: int = 6,
) -> ContextReport:
    root = root.resolve()
    project_path = project_path or _discover_project_path(root)
    project_text: str | None = None
    resolved_id: str | None = None
    if project_path:
        resolved_id = _resolve_id_for_context(root, project_path)
        # Project pages might still live under the resolved git-style
        # sha1-16 id (legacy layout) — try both.
        page = project_memory.project_page_path(root, resolved_id)
        if not page.is_file():
            for variant in (
                project_id.resolve_project_id(project_path).project_id,
            ):
                alt = project_memory.project_page_path(root, variant)
                if alt.is_file():
                    page = alt
                    resolved_id = variant
                    break
        if page.is_file():
            project_text = page.read_text(encoding="utf-8")

    data: dict[str, Any] = {
        "tool": tool,
        "project_path": project_path,
        "project_id": resolved_id,
        "scope": "project" if resolved_id else "global-only",
        "warnings": [],
        "global_rules": [],
        "project": None,
        "open_questions": [],
        "insight_candidates": [],
        "recent_activity": [],
    }

    global_dir = root / "wiki" / "global"
    if global_dir.is_dir():
        for path in sorted(global_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title_match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else path.stem
            data["global_rules"].append(
                {"title": title, "path": str(path), "preview": text[:400]}
            )

    if project_text is not None:
        sections = _read_sections(project_text)
        title_match = re.search(r"^title:\s*(.+)$", project_text, re.MULTILINE)
        data["project"] = {
            "project_id": resolved_id,
            "title": title_match.group(1).strip() if title_match else resolved_id,
            "status": sections.get("status", []),
            "decisions": sections.get("decisions", []),
            "bugfixes": sections.get("bugfixes", []),
            "verifications": sections.get("verifications", []),
            "open_questions": sections.get("open_questions", []),
        }
        data["open_questions"] = sections.get("open_questions", [])
    elif resolved_id:
        data["warnings"].append("Project is registered but its STATE page is not materialized yet.")
    else:
        data["warnings"].append("Project could not be resolved; context is global-only.")

    review_dir = root / "wiki" / "review"
    if review_dir.is_dir():
        candidates = sorted(review_dir.glob("candidates-*.md"))[-limit:]
        for path in candidates:
            text = path.read_text(encoding="utf-8")
            data["insight_candidates"].append(
                {"path": str(path), "preview": text[:600]}
            )

    activity = _recent_tool_activity(root)
    data["recent_activity"] = activity

    if format == "json":
        return ContextReport(
            tool=tool,
            project_path=project_path,
            project_id=resolved_id,
            markdown=json.dumps(data, ensure_ascii=False, indent=2),
            data=data,
        )

    lines: list[str] = [
        f"# LLM-WorkMem Context — tool={tool}",
        "",
    ]
    if project_path:
        lines.append(f"Project: `{project_path}` (id={resolved_id})")
        lines.append("")
    lines.append(f"Scope: {data['scope']}")
    if data["warnings"]:
        for warning in data["warnings"]:
            lines.append(f"Warning: {warning}")
    lines.append("")

    lines.append("## Global Memory")
    if data["global_rules"]:
        for rule in data["global_rules"]:
            lines.append(f"- {rule['title']} (`{rule['path']}`)")
    else:
        lines.append("- (none yet — promote candidates from review/)")
    lines.append("")

    lines.append("## Project Memory")
    if data["project"]:
        for line in data["project"].get("status", [])[:6]:
            lines.append(f"- {line}")
        lines.append("")
        if data["project"]["decisions"]:
            lines.append("### Recent Decisions")
            for line in data["project"]["decisions"][-6:]:
                lines.append(f"- {line}")
            lines.append("")
        if data["project"]["bugfixes"]:
            lines.append("### Recent Bugfixes")
            for line in data["project"]["bugfixes"][-6:]:
                lines.append(f"- {line}")
            lines.append("")
        if data["project"]["verifications"]:
            lines.append("### Verifications")
            for line in data["project"]["verifications"][-6:]:
                lines.append(f"- {line}")
            lines.append("")
    else:
        lines.append("- (project memory is not available in this context)")
        lines.append("")

    if data["open_questions"]:
        lines.append("## Open Questions")
        for line in data["open_questions"]:
            lines.append(f"- {line}")
        lines.append("")

    if data["insight_candidates"]:
        lines.append("## Cross-Project Insight Candidates")
        for candidate in data["insight_candidates"]:
            lines.append(f"- {candidate['path']}")
        lines.append("")

    if data["recent_activity"]:
        lines.append("## Recent Tool Activity (7d)")
        for entry in data["recent_activity"][:10]:
            lines.append(
                f"- {entry.get('timestamp')} · {entry.get('tool')} "
                f"· {entry.get('event_type')} · {entry.get('project_id')}"
            )
        lines.append("")

    if data["global_rules"]:
        lines.append("## Risk & Verification Rules")
        for rule in data["global_rules"][:4]:
            lines.append(f"- {rule['title']} — preview: {rule['preview'].splitlines()[-1][:120] if rule['preview'] else ''}")
        lines.append("")

    return ContextReport(
        tool=tool,
        project_path=project_path,
        project_id=resolved_id,
        markdown="\n".join(lines).rstrip() + "\n",
        data=data,
    )


__all__ = ["ContextReport", "build"]
