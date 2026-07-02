"""Ingest Claude Code session JSONL transcripts into markdown notes.

Claude Code writes every conversation to ``~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl``.
This module reads one such file and produces a compact markdown note under
``<wiki_root>/raw/notes/<YYYY-MM-DD>/<source>-<session-id>.md`` so that the
existing ``lwm watch`` / ``lwm harvest`` / ``lwm audit`` pipeline can
pick it up and surface it through the wiki.

Design notes:
- We do **not** call an LLM here. The output is a deterministic, structured
  markdown that captures session metadata, the first user prompt, the final
  assistant message, and tool-call counts. Summarisation is left to a
  subsequent ``lwm digest`` step (out of scope for v0.1).
- Failures are captured into ``IngestOutcome``; the caller (``lwm watch``)
  must never see an exception.
- The ingest is idempotent: re-running on the same JSONL produces a file
  with the same name. The output is overwritten to reflect the latest state.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestOutcome:
    """Result of ingesting one session JSONL. ``ok=False`` carries the reason
    in ``error``; ``output_path`` is set iff a note was written."""

    source: str
    session_id: str
    ok: bool
    output_path: Path | None = None
    error: str | None = None
    message_count: int = 0


# Maximum number of tool calls to enumerate in the note. Beyond this we just
# report a count — keeps notes scannable for very long sessions.
_MAX_TOOL_NAMES = 12


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines and tolerating parse errors.

    The Claude Code JSONL sometimes contains partial entries during a session
    that is being written to. We never raise — malformed lines are dropped.
    """
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("ingest: cannot read %s: %s", path, exc)
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _entry_text(entry: dict[str, Any]) -> str:
    """Extract plain text from a Claude Code transcript entry.

    The shape is documented in openedclaude/claude-reviews-claude architecture
    notes. ``message.content`` is either a string or a list of blocks.
    """
    msg = entry.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "output_text"}:
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool:{block.get('name', '?')}]")
        return "\n".join(p for p in parts if p)
    return ""


def _iso_day(entry: dict[str, Any]) -> str:
    """Best-effort: derive the day bucket (YYYY-MM-DD) from an entry."""
    ts = entry.get("timestamp")
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()
        except (ValueError, OSError):
            pass
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass
    return date.today().isoformat()


def _session_id_from_path(path: Path) -> str:
    return path.stem


def _truncate(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def render_session_note(
    entries: list[dict[str, Any]],
    *,
    source: str,
    session_id: str,
    source_path: Path | None = None,
) -> str:
    """Build the markdown body for a session note from parsed JSONL entries."""
    user_msgs: list[str] = []
    assistant_msgs: list[str] = []
    tool_counts: dict[str, int] = {}
    types_seen: set[str] = set()
    earliest: str | None = None
    latest: str | None = None

    for entry in entries:
        etype = entry.get("type")
        if isinstance(etype, str):
            types_seen.add(etype)
        ts = entry.get("timestamp")
        if isinstance(ts, str):
            if earliest is None or ts < earliest:
                earliest = ts
            if latest is None or ts > latest:
                latest = ts

        if etype == "user":
            text = _entry_text(entry)
            if text:
                user_msgs.append(text)
        elif etype == "assistant":
            text = _entry_text(entry)
            if text:
                assistant_msgs.append(text)
            msg = entry.get("message") or {}
            for block in msg.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = str(block.get("name", "unknown"))
                    tool_counts[name] = tool_counts.get(name, 0) + 1

    first_prompt = user_msgs[0] if user_msgs else "(no user prompt captured)"
    last_reply = (
        assistant_msgs[-1] if assistant_msgs else "(no assistant reply captured)"
    )

    tool_lines: list[str] = []
    for name, count in sorted(
        tool_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )[:_MAX_TOOL_NAMES]:
        tool_lines.append(f"  - `{name}` ×{count}")
    extra = max(0, len(tool_counts) - _MAX_TOOL_NAMES)
    if extra:
        tool_lines.append(f"  - …and {extra} more")

    if not tool_lines:
        tool_lines.append("  - (none)")

    lines: list[str] = [
        f"# Session Note — {source} / {session_id}",
        "",
        f"- Source: `{source}`",
        f"- Session ID: `{session_id}`",
    ]
    if source_path is not None:
        lines.append(f"- Transcript: `{source_path}`")
    lines.extend(
        [
            f"- First event: `{earliest or 'unknown'}`",
            f"- Last event: `{latest or 'unknown'}`",
            f"- User turns: {len(user_msgs)}",
            f"- Assistant turns: {len(assistant_msgs)}",
            f"- Entry types: {', '.join(sorted(types_seen)) or '(none)'}",
            "",
            "## First user prompt",
            "",
            "```",
            _truncate(first_prompt),
            "```",
            "",
            "## Last assistant reply",
            "",
            "```",
            _truncate(last_reply),
            "```",
            "",
            "## Tool call counts",
            "",
            *tool_lines,
            "",
        ]
    )
    return "\n".join(lines)


def ingest_session(
    root: Path,
    jsonl_path: Path,
    *,
    source: str = "claude-code",
) -> IngestOutcome:
    """Ingest a single session JSONL into ``raw/notes/<date>/<source>-<sid>.md``.

    Never raises. All failures are captured into :class:`IngestOutcome`.
    """
    if not jsonl_path.is_file():
        return IngestOutcome(
            source=source,
            session_id=jsonl_path.stem,
            ok=False,
            error=f"file not found: {jsonl_path}",
        )

    entries = _read_jsonl(jsonl_path)
    if not entries:
        return IngestOutcome(
            source=source,
            session_id=jsonl_path.stem,
            ok=False,
            error="empty or unreadable JSONL",
        )

    session_id = _session_id_from_path(jsonl_path)
    day = _iso_day(entries[0]) if entries else date.today().isoformat()

    notes_dir = root / "raw" / "notes" / day
    try:
        notes_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return IngestOutcome(
            source=source,
            session_id=session_id,
            ok=False,
            error=f"mkdir failed: {exc}",
        )

    body = render_session_note(
        entries, source=source, session_id=session_id, source_path=jsonl_path
    )
    out_path = notes_dir / f"{source}-{session_id}.md"
    try:
        out_path.write_text(body, encoding="utf-8")
    except OSError as exc:
        return IngestOutcome(
            source=source,
            session_id=session_id,
            ok=False,
            error=f"write failed: {exc}",
        )

    return IngestOutcome(
        source=source,
        session_id=session_id,
        ok=True,
        output_path=out_path,
        message_count=len(entries),
    )


def ingest_sessions(
    root: Path,
    jsonl_paths: Iterable[Path],
    *,
    source: str = "claude-code",
) -> list[IngestOutcome]:
    """Ingest a batch of session JSONL files."""
    return [ingest_session(root, p, source=source) for p in jsonl_paths]


__all__ = [
    "IngestOutcome",
    "ingest_session",
    "ingest_sessions",
    "render_session_note",
]
