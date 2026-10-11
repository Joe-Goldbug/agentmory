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

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from lwm.events import (
    new_event_id,
)
from lwm.privacy import SECRET_PATTERNS


# ---------------------------------------------------------------------------
# Durable event admission contract
#
# Spec: docs/superpowers/specs/
#       2026-07-31-llm-workmem-unified-behavior-memory-interface.md
#       -> Implementation Changes / 2. Truthful Core
#
# Only structured decisions, changes, verifications, risks, project status and
# open questions may enter long-term memory. Commands, complete prompts,
# environment blocks, session lifecycle receipts and watcher observations stay
# ``operational`` or become ``rejected``. Raw evidence is never mutated.
# ---------------------------------------------------------------------------

Durability = Literal["durable", "operational", "rejected"]

DURABLE_EVENT_TYPES = frozenset(
    {"decision", "bugfix", "verification", "project_status"}
)

OPERATIONAL_EVENT_TYPES = frozenset(
    {
        "session_start",
        "session_idle",
        "session_summary",
        "session_deleted",
        "adapter_probe",
        "workflow_observation",
    }
)

#: Structured fields that may carry durable work evidence.
DURABLE_FIELDS = ("decisions", "changes", "verification", "risks", "open_questions")

MAX_TASK_CHARS = 240
MAX_ENTRY_CHARS = 480
MAX_ITEMS_PER_FIELD = 8
MAX_ITEM_CHARS = 240

#: High-signal markers for complete prompts / instruction blocks / environment
#: dumps. Matched case-insensitively against task plus every durable field.
NOISE_MARKERS = (
    "<environment_context>",
    "</environment_context>",
    "<permissions instructions>",
    "<user_instructions>",
    "<system-reminder>",
    "# agents.md instructions",
    "you are codex",
    "you are claude code",
    "command timed out",
)

#: Placeholder tasks emitted by lifecycle hooks that carry no work evidence.
EMPTY_TASK_MARKERS = frozenset(
    {
        "",
        "(no task)",
        "(no task recorded)",
        "(no user text)",
        "(no user prompt)",
        "no user text",
        "no user prompt",
    }
)

#: A bare shell command transcript is operational, never durable.
_COMMAND_ONLY_RE = re.compile(
    r"^(sudo\s+)?(git|npm|npx|uv|pip|python3?|ls|cd|cat|rg|grep|find|make|"
    r"pytest|ruff|brew|launchctl|shasum|curl|echo|mkdir|cp|mv|chmod|open)\b"
)


@dataclass(frozen=True)
class EventAdmission:
    """Result of classifying one source event for durable memory."""

    durability: Durability
    reason: str
    section: str | None


def _bounded_items(value: Any) -> tuple[str, ...]:
    """Normalize a structured field into bounded, non-empty text items."""

    if value is None:
        return ()
    if isinstance(value, str):
        raw: list[Any] = [value]
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        return ()
    items: list[str] = []
    for entry in raw[:MAX_ITEMS_PER_FIELD]:
        if not isinstance(entry, (str, int, float)):
            # Malformed nested structures never reach durable memory.
            continue
        text = " ".join(str(entry).split()).strip()
        if not text:
            continue
        items.append(text[:MAX_ITEM_CHARS])
    return tuple(items)


def _bounded_task(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()[:MAX_TASK_CHARS]


def _contains_noise_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in NOISE_MARKERS)


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in SECRET_PATTERNS)


def _is_command_only(task: str) -> bool:
    if not task or "\n" in task.strip():
        return False
    return bool(_COMMAND_ONLY_RE.match(task.strip()))


def classify_event(event: object) -> EventAdmission:
    """Classify one event as ``durable``, ``operational`` or ``rejected``.

    ``durable`` events materialize into project memory. ``operational`` events
    stay in raw evidence and may inform recent-activity views only.
    ``rejected`` events must never be rendered anywhere.

    ``event`` is intentionally typed as ``object``: raw JSON on disk may be any
    shape, and malformed payloads must be rejected rather than crash a rebuild.
    """

    if not isinstance(event, dict):
        return EventAdmission("rejected", "malformed_event", None)

    event_type = str(event.get("event_type") or "").strip()
    task = _bounded_task(event.get("task"))
    fields = {key: _bounded_items(event.get(key)) for key in DURABLE_FIELDS}
    combined = "\n".join(
        [task, *(item for values in fields.values() for item in values)]
    )

    if _contains_noise_marker(combined):
        return EventAdmission("rejected", "instruction_or_environment_dump", None)
    if _contains_secret(combined):
        return EventAdmission("rejected", "secret_material", None)

    if event_type not in DURABLE_EVENT_TYPES:
        reason = (
            "non_durable_event_type"
            if event_type in OPERATIONAL_EVENT_TYPES
            else "unknown_event_type"
        )
        return EventAdmission("operational", reason, None)

    if task.lower() in EMPTY_TASK_MARKERS and not any(fields.values()):
        return EventAdmission("operational", "placeholder_task", None)
    if _is_command_only(task) and not any(fields.values()):
        return EventAdmission("operational", "command_transcript_only", None)

    if event_type == "decision" and fields["decisions"]:
        return EventAdmission("durable", "structured_decision", "decisions")
    if event_type == "bugfix" and fields["changes"] and fields["verification"]:
        return EventAdmission("durable", "verified_bugfix", "bugfixes")
    if event_type == "verification" and fields["verification"]:
        return EventAdmission("durable", "structured_verification", "verifications")
    if event_type == "project_status" and task and any(fields.values()):
        return EventAdmission("durable", "structured_project_status", "status")
    return EventAdmission("operational", "insufficient_durable_fields", None)


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
    tool: str = ""
    evidence_path: str = ""
    supersedes: str | None = None

    def render(self) -> str:
        """Render one bullet plus its provenance line.

        Spec requires every durable memory line to keep ``event_id``, the
        originating tool and the evidence path. The provenance line starts with
        ``↳`` so it is never re-parsed as a memory bullet.
        """

        head = f"- {self.timestamp} — {self.text}"
        if not self.tool and not self.evidence_path:
            return head
        provenance = " · ".join(
            part
            for part in (self.tool, self.event_id, self.evidence_path)
            if part and part != "legacy"
        )
        if not provenance:
            return head
        return f"{head}\n  ↳ {provenance}"


_SUPERSEDES_TAG_RE = re.compile(
    r"\[(?:supersedes|replaces):\s*([^\]]+)\]|\((?:supersedes|replaces):\s*([^)]+)\)",
    re.IGNORECASE,
)


def _extract_superseded_targets(entry: ProjectMemoryEntry) -> set[str]:
    targets: set[str] = set()
    if entry.supersedes:
        targets.add(entry.supersedes.strip())
    for m in _SUPERSEDES_TAG_RE.finditer(entry.text):
        target = m.group(1) or m.group(2)
        if target and target.strip():
            targets.add(target.strip())
    return targets


def _filter_active_decisions(
    entries: Iterable[ProjectMemoryEntry],
) -> list[ProjectMemoryEntry]:
    """Filter out decisions that have been superseded by newer decisions.

    Ensures outdated decisions never contaminate active agent prompt contexts.
    """
    items = list(entries)
    if not items:
        return []
    chronological = sorted(items, key=lambda e: (e.timestamp, e.event_id))
    superseded_indices: set[int] = set()

    for idx, entry in enumerate(chronological):
        targets = _extract_superseded_targets(entry)
        if not targets:
            continue
        for prior_idx in range(idx):
            if prior_idx in superseded_indices:
                continue
            prior = chronological[prior_idx]
            for target in targets:
                target_clean = target.strip().lower()
                if not target_clean:
                    continue
                # 1. Match event_id directly if not legacy
                if prior.event_id != "legacy" and prior.event_id.lower() == target_clean:
                    superseded_indices.add(prior_idx)
                    break
                # 2. Match exact text (ignoring case)
                prior_clean = prior.text.strip().lower()
                if prior_clean == target_clean:
                    superseded_indices.add(prior_idx)
                    break
                # 3. Match substring if target is sufficiently specific (>= 4 chars)
                if len(target_clean) >= 4 and target_clean in prior_clean:
                    superseded_indices.add(prior_idx)
                    break

    superseded_set = {chronological[i] for i in superseded_indices}
    return [e for e in items if e not in superseded_set]


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


def _durable_text(event: dict[str, Any], section: str) -> str:
    """Build the bounded, human-readable text for one durable entry."""

    task = _bounded_task(event.get("task"))
    fields = {key: _bounded_items(event.get(key)) for key in DURABLE_FIELDS}

    if section == "decisions" and fields["decisions"]:
        text = "; ".join(fields["decisions"])
    elif section == "verifications" and fields["verification"]:
        text = "; ".join(fields["verification"])
    elif section == "bugfixes":
        text = task or "(bugfix)"
        if fields["changes"]:
            text = f"{text} — changes: {'; '.join(fields['changes'])}"
        if fields["verification"]:
            text = f"{text} — verified: {'; '.join(fields['verification'])}"
    else:
        text = task or str(event.get("event_type") or "(no task)")
        if fields["changes"]:
            text = f"{text} — changes: {'; '.join(fields['changes'])}"
        if fields["verification"]:
            text = f"{text} — verified: {'; '.join(fields['verification'])}"
        if fields["risks"]:
            text = f"{text} — risks: {'; '.join(fields['risks'])}"

    return text[:MAX_ENTRY_CHARS]


def event_entry(
    event: dict[str, Any],
    *,
    evidence_path: str = "",
    admission: EventAdmission | None = None,
) -> tuple[str, ProjectMemoryEntry]:
    """Build the project-memory entry for one admitted event."""

    admission = admission or classify_event(event)
    section = admission.section or project_section_for_event(event)
    supersedes = str(
        event.get("supersedes_decision")
        or event.get("supersedes")
        or event.get("replaces")
        or ""
    ).strip() or None
    entry = ProjectMemoryEntry(
        section=section,
        text=_durable_text(event, section),
        timestamp=str(event.get("timestamp") or ""),
        event_id=str(event.get("event_id") or new_event_id()),
        tool=str(event.get("tool") or ""),
        evidence_path=evidence_path,
        supersedes=supersedes,
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
        if current is not None and line.strip().startswith("↳ ") and sections.get(current):
            parts = [p.strip() for p in line.strip()[2:].split(" · ") if p.strip()]
            if parts:
                last_entry = sections[current][-1]
                tool = parts[0] if len(parts) >= 2 else last_entry.tool
                eid = parts[1] if len(parts) >= 2 else parts[0]
                evidence = parts[2] if len(parts) >= 3 else last_entry.evidence_path
                sections[current][-1] = ProjectMemoryEntry(
                    section=last_entry.section,
                    text=last_entry.text,
                    timestamp=last_entry.timestamp,
                    event_id=eid or "legacy",
                    tool=tool,
                    evidence_path=evidence,
                    supersedes=last_entry.supersedes,
                )
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


#: Bounded per-section history kept on a project page. Raw evidence under
#: ``raw/events/processed/`` remains the full, unbounded history.
SECTION_LIMITS = {
    "status": 12,
    "decisions": 20,
    "bugfixes": 20,
    "verifications": 20,
    "open_questions": 20,
}


def render_project_page(
    project_id: str,
    entries: dict[str, list[ProjectMemoryEntry]],
    last_event: dict[str, Any] | None,
    *,
    updated: str | None = None,
) -> str:
    """Render one project page.

    ``updated`` is supplied by deterministic rebuilds (newest admitted event
    timestamp) so that re-running an unchanged rebuild produces a byte-identical
    file. When omitted the current UTC time is used for incremental appends.
    """

    if updated:
        timestamp_now = updated
    else:
        timestamp_now = (
            datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
            + "Z"
        )
    last_event_text = str((last_event or {}).get("event_type") or "n/a")
    last_event_ts = str((last_event or {}).get("timestamp") or "n/a")
    last_task = _bounded_task((last_event or {}).get("task")) or "(no task recorded)"

    def render_section(name: str, label: str, *, reverse: bool = True) -> str:
        items = entries.get(name) or []
        if name == "decisions":
            items = _filter_active_decisions(items)
        # Deterministic ordering: timestamp first, event_id as tiebreaker.
        ordered = sorted(
            items, key=lambda e: (e.timestamp, e.event_id), reverse=reverse
        )
        limit = SECTION_LIMITS.get(name)
        if limit is not None:
            ordered = ordered[:limit]
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
    """Backwards-compatible wrapper over :func:`classify_event`.

    Retained so existing callers keep working; durable admission is now decided
    exclusively by :func:`classify_event`.
    """

    return classify_event(event).durability == "durable"


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


@dataclass(frozen=True)
class RebuildReport:
    """Outcome of a deterministic project-memory rebuild."""

    scanned_events: int = 0
    admitted_events: int = 0
    operational_events: int = 0
    rejected_events: int = 0
    pages_written: int = 0
    pages_removed: int = 0
    written_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    unchanged_paths: tuple[str, ...] = ()
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanned_events": self.scanned_events,
            "admitted_events": self.admitted_events,
            "operational_events": self.operational_events,
            "rejected_events": self.rejected_events,
            "pages_written": self.pages_written,
            "pages_removed": self.pages_removed,
            "written_paths": list(self.written_paths),
            "removed_paths": list(self.removed_paths),
            "unchanged_paths": list(self.unchanged_paths),
            "dry_run": self.dry_run,
        }


def processed_events_dir(root: Path) -> Path:
    return root / "raw" / "events" / "processed"


def _stable_event_id(event: dict[str, Any]) -> str:
    """Stable identity for legacy events that predate ``event_id``."""

    existing = str(event.get("event_id") or "").strip()
    if existing:
        return existing
    material = "".join(
        [
            str(event.get("project_id") or ""),
            str(event.get("timestamp") or ""),
            str(event.get("event_type") or ""),
            _bounded_task(event.get("task")),
            *(
                item
                for key in DURABLE_FIELDS
                for item in _bounded_items(event.get(key))
            ),
        ]
    )
    return "legacy-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def load_processed_events(
    root: Path,
) -> tuple[tuple[Path, dict[str, Any]], ...]:
    """Load every valid processed event, sorted deterministically.

    Invalid JSON is skipped, never deleted or rewritten: ``raw/`` is the
    append-only source of truth.
    """

    base = processed_events_dir(root)
    if not base.is_dir():
        return ()
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(base.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        loaded.append((path, payload))
    loaded.sort(
        key=lambda item: (
            str(item[1].get("timestamp") or ""),
            _stable_event_id(item[1]),
        )
    )
    return tuple(loaded)


def _relative_evidence_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def aggregate_project_pages(
    root: Path,
    admitted: Iterable[tuple[Path, dict[str, Any], EventAdmission]],
) -> dict[str, tuple[dict[str, list[ProjectMemoryEntry]], dict[str, Any], str]]:
    """Aggregate admitted events into in-memory project pages.

    Returns ``project_id -> (sections, newest_event, newest_timestamp)``.
    """

    pages: dict[
        str, tuple[dict[str, list[ProjectMemoryEntry]], dict[str, Any], str]
    ] = {}
    seen_ids: dict[str, set[str]] = {}

    for path, event, admission in admitted:
        project_id = str(event.get("project_id") or "").strip()
        if not project_id:
            continue
        event_id = _stable_event_id(event)
        if event_id in seen_ids.setdefault(project_id, set()):
            continue
        seen_ids[project_id].add(event_id)

        sections, _newest, _ts = pages.setdefault(
            project_id,
            (
                {
                    "status": [],
                    "decisions": [],
                    "bugfixes": [],
                    "verifications": [],
                    "open_questions": [],
                },
                {},
                "",
            ),
        )
        evidence = _relative_evidence_path(root, path)
        normalized = dict(event)
        normalized["event_id"] = event_id
        section, entry = event_entry(
            normalized, evidence_path=evidence, admission=admission
        )
        sections.setdefault(section, []).append(entry)

        for question in _bounded_items(event.get("open_questions")):
            sections["open_questions"].append(
                ProjectMemoryEntry(
                    section="open_questions",
                    text=question,
                    timestamp=entry.timestamp,
                    event_id=event_id,
                    tool=entry.tool,
                    evidence_path=evidence,
                )
            )

        timestamp = str(event.get("timestamp") or "")
        if timestamp >= pages[project_id][2]:
            pages[project_id] = (sections, normalized, timestamp)

    return pages


def _is_generated_project_page(text: str) -> bool:
    """Only pages this module generated may be reconciled away."""

    head = text[:400]
    return "type: project" in head and "project_id:" in head


def reconcile_forgotten_event(root: Path, project_id: str, event_id: str) -> bool:
    """Remove source-backed page text without replacing human-authored content."""

    target = project_page_path(root, project_id)
    if not target.is_file():
        return False
    original = target.read_text(encoding="utf-8")
    if not _is_generated_project_page(original):
        return False

    surviving = [
        event
        for _, event in load_processed_events(root)
        if event.get("project_id") == project_id
        and event.get("event_id") != event_id
        and classify_event(event).durability == "durable"
    ]
    newest = max(
        surviving,
        key=lambda event: (str(event.get("timestamp") or ""), str(event.get("event_id") or "")),
        default=None,
    )
    last_task = _bounded_task((newest or {}).get("task")) or "(no task recorded)"
    last_type = str((newest or {}).get("event_type") or "n/a")
    last_timestamp = str((newest or {}).get("timestamp") or "n/a")

    lines: list[str] = []
    in_section = False
    for line in original.splitlines(keepends=True):
        if line.startswith("## "):
            in_section = True
        if in_section and line.lstrip().startswith("↳ "):
            provenance = {part.strip() for part in line.strip()[2:].split(" · ")}
            if event_id in provenance:
                if lines and lines[-1].startswith("- "):
                    lines.pop()
                continue
        if not in_section and line.startswith("Last task: "):
            line = f"Last task: {last_task}\n"
        elif not in_section and line.startswith("Last event: "):
            line = f"Last event: {last_type} @ {last_timestamp}\n"
        lines.append(line)
    updated = "".join(lines)
    if updated == original:
        return False
    target.write_text(updated, encoding="utf-8")
    return True


def rebuild_project_pages(
    root: Path,
    project_id: str | None = None,
    dry_run: bool = False,
) -> RebuildReport:
    """Deterministically rebuild project pages from admitted raw events.

    Raw evidence is only read. Pages are built fully in memory and written once.
    A previously generated page is removed only when no durable event remains
    for that project.
    """

    events = load_processed_events(root)
    scanned = admitted_count = operational = rejected = 0
    admitted: list[tuple[Path, dict[str, Any], EventAdmission]] = []

    for path, event in events:
        if project_id and str(event.get("project_id") or "") != project_id:
            continue
        scanned += 1
        admission = classify_event(event)
        if admission.durability == "durable":
            admitted_count += 1
            admitted.append((path, event, admission))
        elif admission.durability == "operational":
            operational += 1
        else:
            rejected += 1

    pages = aggregate_project_pages(root, admitted)

    written: list[str] = []
    unchanged: list[str] = []
    removed: list[str] = []

    for pid, (sections, newest_event, newest_ts) in sorted(pages.items()):
        target = project_page_path(root, pid)
        body = render_project_page(
            pid, sections, newest_event, updated=newest_ts or None
        )
        rel = _relative_evidence_path(root, target)
        if target.is_file() and target.read_text(encoding="utf-8") == body:
            unchanged.append(rel)
            continue
        written.append(rel)
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

    projects_dir = root / "wiki" / "projects"
    if projects_dir.is_dir():
        for target in sorted(projects_dir.glob("*.md")):
            pid = target.stem
            if project_id and pid != project_id:
                continue
            if pid in pages:
                continue
            try:
                text = target.read_text(encoding="utf-8")
            except OSError:
                continue
            if not _is_generated_project_page(text):
                continue
            removed.append(_relative_evidence_path(root, target))
            if not dry_run:
                target.unlink()

    return RebuildReport(
        scanned_events=scanned,
        admitted_events=admitted_count,
        operational_events=operational,
        rejected_events=rejected,
        pages_written=len(written),
        pages_removed=len(removed),
        written_paths=tuple(written),
        removed_paths=tuple(removed),
        unchanged_paths=tuple(unchanged),
        dry_run=dry_run,
    )


__all__ = [
    "DURABLE_EVENT_TYPES",
    "DURABLE_FIELDS",
    "EventAdmission",
    "MAX_ENTRY_CHARS",
    "MAX_ITEMS_PER_FIELD",
    "MAX_ITEM_CHARS",
    "MAX_TASK_CHARS",
    "NOISE_MARKERS",
    "OPERATIONAL_EVENT_TYPES",
    "ProjectMemoryEntry",
    "RebuildReport",
    "SECTION_LIMITS",
    "aggregate_project_pages",
    "append_event",
    "classify_event",
    "event_entry",
    "load_processed_events",
    "project_page_path",
    "reconcile_forgotten_event",
    "prune_empty_pages",
    "rebuild_project_pages",
    "render_project_page",
    "_filter_active_decisions",
]
