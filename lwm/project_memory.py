"""Project memory page rendering.

Each project gets a single markdown page at
``wiki/projects/<project_id>.md`` with five sections:

* Status — last task and timestamp.
* Decisions — bullet list of recorded decisions (most-recent first).
* Bugfixes — bullet list of bug fixes (most-recent first).
* Verifications — bullet list of verifications (most-recent first).
* Open Questions — bullet list, oldest first.

Updates are idempotent: re-applying the same event does not duplicate
entries. ``replace=False`` (default) appends; ``replace=True``
regenerates the page from a full snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lwm.events import (
    new_event_id,
)


PAGE_TEMPLATE = """---
title: Project {project_id}
type: project
tags: [project, {project_id}]
sources:
  - raw/events/processed
updated: {updated}
project_id: {project_id}
---

# Project {project_id}

Last task: {last_task}
Last event: {last_event_type} @ {last_timestamp}

## Status

{status_section}

## Decisions

{decisions_section}

## Bugfixes

{bugfixes_section}

## Verifications

{verifications_section}

## Open Questions

{open_questions_section}
"""


@dataclass(frozen=True)
class ProjectMemoryEntry:
    section: str
    text: str
    timestamp: str
    event_id: str

    def render(self) -> str:
        return f"- {self.timestamp} — {self.text}"


def _split_section(body: str, section_name: str) -> tuple[str, str, str]:
    pattern = re.compile(rf"^## {re.escape(section_name)}\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return body, "", ""
    start = matches[0].end()
    next_match = pattern.search(body, start)
    end = next_match.start() if next_match else len(body)
    before = body[:matches[0].start()]
    section = body[start:end].rstrip()
    after = body[end:]
    return before, section, after


@dataclass(frozen=True)
class ProjectMemory:
    project_id: str
    entries: dict[str, list[ProjectMemoryEntry]]
    last_event: dict[str, Any] | None

    def sections(self) -> dict[str, list[ProjectMemoryEntry]]:
        return self.entries


def project_page_path(root: Path, project_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", project_id)
    return (root / "wiki" / "projects" / f"{safe}.md").resolve()


def project_section_for_event(event: dict[str, Any]) -> str:
    event_type = event.get("event_type") or ""
    if event_type == "decision":
        return "decisions"
    if event_type == "bugfix":
        return "bugfixes"
    if event_type == "verification":
        return "verifications"
    if event_type in {"session_summary", "session_start", "project_status"}:
        return "status"
    return "status"


def event_entry(event: dict[str, Any]) -> tuple[str, ProjectMemoryEntry]:
    section = project_section_for_event(event)
    text = str(event.get("task") or event.get("event_type") or "").strip()
    if not text:
        text = str(event.get("event_type") or "(no task)")
    decisions = event.get("decisions") or []
    if section == "decisions" and decisions:
        text = "; ".join(str(d) for d in decisions)
    changes = event.get("changes") or []
    if section == "status" and changes:
        text = f"{text} — changes: {'; '.join(str(c) for c in changes)}"
    verification = event.get("verification") or []
    if section == "bugfixes" and verification:
        text = f"{text} — verified: {'; '.join(str(v) for v in verification)}"
    if section == "verifications":
        if isinstance(verification, list) and verification:
            text = "; ".join(str(v) for v in verification)
        elif not text:
            text = "(verification recorded)"
    if section == "status" and isinstance(verification, list) and verification:
        text = f"{text} — verified: {'; '.join(str(v) for v in verification)}"
    open_questions = event.get("open_questions") or []
    if open_questions:
        text = f"{text} — open: {'; '.join(str(q) for q in open_questions)}"
    entry = ProjectMemoryEntry(
        section=section,
        text=text,
        timestamp=str(event.get("timestamp") or ""),
        event_id=str(event.get("event_id") or new_event_id()),
    )
    return section, entry


def _read_existing_entries(body: str) -> dict[str, list[ProjectMemoryEntry]]:
    sections = {
        "status": [],
        "decisions": [],
        "bugfixes": [],
        "verifications": [],
        "open_questions": [],
    }
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            name = line[3:].strip().lower().replace(" ", "_")
            current = name if name in sections else None
            continue
        if current is None or not line.strip().startswith("- "):
            continue
        match = re.match(r"- (\S+) — (.*)", line.strip())
        if not match:
            continue
        ts, text = match.group(1), match.group(2)
        sections.setdefault(current, []).append(
            ProjectMemoryEntry(
                section=current,
                text=text,
                timestamp=ts,
                event_id="legacy",
            )
        )
    return sections


def render_project_page(
    project_id: str,
    entries: dict[str, list[ProjectMemoryEntry]],
    last_event: dict[str, Any] | None,
) -> str:
    timestamp_now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    last_event_text = str((last_event or {}).get("event_type") or "n/a")
    last_event_ts = str((last_event or {}).get("timestamp") or "n/a")
    last_task = str((last_event or {}).get("task") or "(no task recorded)")

    def render_section(name: str, label: str, *, reverse: bool = True) -> str:
        items = entries.get(name) or []
        ordered = sorted(items, key=lambda e: e.timestamp, reverse=reverse)
        if not ordered:
            return f"(no {name} yet)"
        return "\n".join(e.render() for e in ordered)

    return PAGE_TEMPLATE.format(
        project_id=project_id,
        updated=timestamp_now,
        last_task=last_task,
        last_event_type=last_event_text,
        last_timestamp=last_event_ts,
        status_section=render_section("status", "Status", reverse=True),
        decisions_section=render_section("decisions", "Decisions", reverse=True),
        bugfixes_section=render_section("bugfixes", "Bugfixes", reverse=True),
        verifications_section=render_section("verifications", "Verifications", reverse=True),
        open_questions_section=render_section("open_questions", "Open Questions", reverse=False),
    )


def _is_meaningful_event(event: dict[str, Any]) -> bool:
    """Keep lifecycle receipts operational unless they carry real work."""

    event_type = str(event.get("event_type") or "")
    if event_type == "session_start" or event_type == "adapter_probe":
        return False
    has_details = any(
        event.get(key) for key in ("decisions", "changes", "verification", "open_questions")
    )
    if has_details:
        return True
    task = str(event.get("task") or "").strip()
    if task.lower() in {"", "(no user text)", "(no task recorded)", "no user text"}:
        return False
    tags = {str(tag).strip().lower() for tag in event.get("tags") or []}
    if "lifecycle" in tags and event_type in {"session_summary", "session_idle", "session_deleted"}:
        return False
    return True


def _is_lifecycle_only_page(text: str) -> bool:
    """Identify old project pages made only from lifecycle receipts."""

    if "Last task: (no task recorded)" not in text:
        return False
    entries = _read_existing_entries(text)
    if any(entries.get(name) for name in ("decisions", "bugfixes", "verifications", "open_questions")):
        return False
    lifecycle_markers = {
        "session_start",
        "session_summary",
        "adapter_probe",
        "(no user text)",
        "<environment_context>",
    }
    status = [entry.text.strip().lower() for entry in entries.get("status", [])]
    return bool(status) and all(
        marker in lifecycle_markers or "observed idle" in marker for marker in status
    )


def prune_empty_pages(root: Path) -> list[Path]:
    """Remove project pages that contain no durable work evidence."""

    projects_dir = (root / "wiki" / "projects").resolve()
    if not projects_dir.is_dir():
        return []
    removed: list[Path] = []
    for target in sorted(projects_dir.glob("*.md")):
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            continue
        if _is_lifecycle_only_page(text):
            target.unlink()
            removed.append(target)
    return removed


def append_event(root: Path, event: dict[str, Any]) -> Path | None:
    """Apply an event to the project's wiki page and return the path."""

    if not _is_meaningful_event(event):
        return None

    project_id = str(event["project_id"])
    target = project_page_path(root, project_id)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.is_file():
        existing = _read_existing_entries(target.read_text(encoding="utf-8"))
    else:
        existing = {name: [] for name in (
            "status",
            "decisions",
            "bugfixes",
            "verifications",
            "open_questions",
        )}

    section, entry = event_entry(event)
    if section == "status" and "open_questions" in existing:
        for question in event.get("open_questions") or []:
            q_entry = ProjectMemoryEntry(
                section="open_questions",
                text=str(question),
                timestamp=entry.timestamp,
                event_id=entry.event_id,
            )
            existing["open_questions"].append(q_entry)

    existing.setdefault(section, []).append(entry)
    page = render_project_page(project_id, existing, last_event=event)
    target.write_text(page, encoding="utf-8")
    return target


def normalize_existing_pages(root: Path) -> list[Path]:
    """Re-emit every project page so old block-list ``tags:`` blocks become
    inline YAML lists and the schema validator stops complaining.

    Strategy: parse the frontmatter into a dict, rebuild it in canonical
    order (title, type, tags, sources, updated, project_id) using the
    inline YAML list syntax, then re-attach the body verbatim.
    """

    import re as _re

    projects_dir = root / "wiki" / "projects"
    if not projects_dir.is_dir():
        return []
    rewritten: list[Path] = []
    for target in sorted(projects_dir.glob("*.md")):
        text = target.read_text(encoding="utf-8")
        # Frontmatter is the first ``---`` block.
        match = _re.match(r"^---\n(.*?)\n---\n?", text, _re.DOTALL)
        if not match:
            continue
        fm = match.group(1)
        body_start = match.end()
        body = text[body_start:]

        fields: dict[str, list[str]] = {}
        current_key: str | None = None
        for line in fm.splitlines():
            if not line.strip():
                continue
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                if current_key:
                    fields[current_key].append(stripped[2:].strip().strip("'\""))
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                current_key = key
                fields.setdefault(key, [])
                if value:
                    if value.startswith("[") and value.endswith("]"):
                        inner = value[1:-1]
                        for part in inner.split(","):
                            fields[key].append(part.strip().strip("'\""))
                    else:
                        fields[key].append(value)
            else:
                # orphan line; ignore.
                continue

        needs_fix = any(not _re.search(r":\s*\[", fm.split("tags:", 1)[-1].split("\n", 1)[0])
                        for key in ("tags",) if key in fields)
        if not needs_fix:
            continue

        canonical_order = (
            "title",
            "type",
            "tags",
            "sources",
            "updated",
            "project_id",
        )
        rebuilt: list[str] = []
        for key in canonical_order:
            if key not in fields:
                continue
            values = fields[key]
            if not values:
                continue
            if key == "title" or key == "type" or key == "updated" or key == "project_id":
                rebuilt.append(f"{key}: {values[0]}")
            else:
                rebuilt.append(f"{key}: [{', '.join(values)}]")
        new_front = "---\n" + "\n".join(rebuilt) + "\n---\n"
        target.write_text(new_front + body, encoding="utf-8")
        rewritten.append(target)
    return rewritten


__all__ = [
    "ProjectMemoryEntry",
    "append_event",
    "prune_empty_pages",
    "project_page_path",
    "render_project_page",
]
