"""Handoff service: cross-tool task identity and state.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Architecture And Interfaces / 3. Event And Handoff Contracts
      -> Implementation Changes / 4. Handoff and unified task identity

Each project carries at most one *active* handoff. A new handoff must declare
the id of the handoff it supersedes; legacy (pre-supersedes) writes are
rejected. Closed handoffs stay in storage for audit; the active pointer is
updated atomically.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


import subprocess

HANDOFFS_DIR = Path("state/handoffs")
ACTIVE_POINTER = "active.json"
MAX_HANDOFF_TEXT_CHARS = 480
MAX_HANDOFF_ITEMS = 8
MAX_HANDOFF_ITEM_CHARS = 240


class HandoffConflictError(ValueError):
    """Raised on concurrent handoff collision when supersedes does not match active."""

    def __init__(
        self,
        message: str,
        *,
        active_id: str | None = None,
        fork_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.active_id = active_id
        self.fork_path = fork_path


def resolve_project_branch(project_path: Path | str | None) -> tuple[str, str]:
    """Resolve git branch and head commit for a project path without crashing."""
    if not project_path:
        return "", ""
    p = Path(project_path)
    if not p.is_dir():
        return "", ""
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            env={"GIT_TERMINAL_PROMPT": "0"},
        )
        branch = res.stdout.strip() if res.returncode == 0 else ""
        if branch == "HEAD":
            branch = ""
        head_res = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            env={"GIT_TERMINAL_PROMPT": "0"},
        )
        head = head_res.stdout.strip() if head_res.returncode == 0 else ""
        return branch, head
    except (OSError, subprocess.SubprocessError):
        return "", ""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class HandoffPacket:
    handoff_id: str
    project_id: str
    task_id: str
    objective: str
    current_state: str
    decisions: tuple[str, ...] = ()
    changes: tuple[str, ...] = ()
    verifications: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    next_action: str = ""
    source_tool: str = ""
    evidence_ids: tuple[str, ...] = ()
    created_at: str = ""
    supersedes: str | None = None
    closed_at: str | None = None
    git_branch: str = ""
    head_commit: str = ""
    version: int = 1
    conflict_status: str | None = None
    schema_version: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HandoffPacket":
        existing_id = str(payload.get("handoff_id") or "").strip()
        return cls(
            handoff_id=existing_id or uuid.uuid4().hex,
            project_id=str(payload.get("project_id") or ""),
            task_id=str(payload.get("task_id") or ""),
            objective=str(payload.get("objective") or ""),
            current_state=str(payload.get("current_state") or ""),
            decisions=tuple(payload.get("decisions") or ()),
            changes=tuple(payload.get("changes") or ()),
            verifications=tuple(payload.get("verifications") or ()),
            risks=tuple(payload.get("risks") or ()),
            open_questions=tuple(payload.get("open_questions") or ()),
            next_action=str(payload.get("next_action") or ""),
            source_tool=str(payload.get("source_tool") or ""),
            evidence_ids=tuple(payload.get("evidence_ids") or ()),
            created_at=str(payload.get("created_at") or _now()),
            supersedes=payload.get("supersedes"),
            closed_at=payload.get("closed_at"),
            git_branch=str(payload.get("git_branch") or ""),
            head_commit=str(payload.get("head_commit") or ""),
            version=int(payload.get("version") or 1),
            conflict_status=payload.get("conflict_status"),
            schema_version=int(payload.get("schema_version") or 2),
        )


def _handoffs_dir(root: Path) -> Path:
    return root / HANDOFFS_DIR


def _active_path(root: Path, *, project_id: str, branch: str | None = None) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in project_id)
    if branch and branch.strip() and branch.strip() != "HEAD":
        safe_branch = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in branch.strip())
        return _handoffs_dir(root) / f"active-{safe}--{safe_branch}.json"
    return _handoffs_dir(root) / f"active-{safe}.json"


def _bounded_text(value: Any, *, field: str, required: bool = False) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError(f"{field} must be a string")
    if required and not text:
        raise ValueError(f"{field} is required")
    if len(text) > MAX_HANDOFF_TEXT_CHARS:
        raise ValueError(f"{field} exceeds {MAX_HANDOFF_TEXT_CHARS} characters")
    return text


def _bounded_items(values: Iterable[str], *, field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a list of strings")
    items = tuple(values)
    if len(items) > MAX_HANDOFF_ITEMS:
        raise ValueError(f"{field} exceeds {MAX_HANDOFF_ITEMS} items")
    result: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"{field} items must be strings")
        text = item.strip()
        if len(text) > MAX_HANDOFF_ITEM_CHARS:
            raise ValueError(
                f"{field} item exceeds {MAX_HANDOFF_ITEM_CHARS} characters"
            )
        if text:
            result.append(text)
    return tuple(result)


def _summary_items(
    summary: Mapping[str, Any], key: str, *aliases: str
) -> tuple[str, ...]:
    present_key = key
    value = summary.get(key)
    if value is None:
        for alias in aliases:
            if summary.get(alias) is not None:
                present_key = alias
                value = summary[alias]
                break
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{present_key} must be a list of strings")
    return _bounded_items(value, field=present_key)


def load_active(
    root: Path,
    *,
    project_id: str,
    branch: str | None = None,
    fallback_to_project: bool = True,
) -> HandoffPacket | None:
    if branch and branch.strip() and branch.strip() != "HEAD":
        branch_path = _active_path(root, project_id=project_id, branch=branch)
        if branch_path.is_file():
            try:
                payload = json.loads(branch_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("project_id") == project_id:
                    return HandoffPacket.from_dict(payload)
            except (OSError, ValueError):
                pass
        if not fallback_to_project:
            return None
    path = _active_path(root, project_id=project_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("project_id") != project_id:
        return None
    return HandoffPacket.from_dict(payload)


def list_handoffs(root: Path, *, project_id: str | None = None) -> tuple[HandoffPacket, ...]:
    base = _handoffs_dir(root)
    if not base.is_dir():
        return ()
    out: list[HandoffPacket] = []
    for path in sorted(base.glob("*.json")):
        if path.name == ACTIVE_POINTER or path.name.startswith("active-"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        packet = HandoffPacket.from_dict(payload)
        if project_id is not None and packet.project_id != project_id:
            continue
        out.append(packet)
    return tuple(out)


def create_handoff(
    root: Path,
    *,
    project_id: str,
    task_id: str,
    objective: str,
    current_state: str,
    source_tool: str,
    supersedes: str | None = None,
    decisions: Iterable[str] = (),
    changes: Iterable[str] = (),
    verifications: Iterable[str] = (),
    risks: Iterable[str] = (),
    open_questions: Iterable[str] = (),
    next_action: str = "",
    evidence_ids: Iterable[str] = (),
    project_path: Path | str | None = None,
    git_branch: str = "",
    head_commit: str = "",
    allow_fork: bool = False,
) -> HandoffPacket:
    """Create and persist a new handoff for ``project_id``.

    The active pointer is updated atomically. ``supersedes`` is enforced: if it
    is set, the existing active handoff (if any) must carry that id; otherwise
    the call is rejected with HandoffConflictError (saving an audit fork file to
    ensure zero lost updates).
    """

    project_id = _bounded_text(project_id, field="project_id", required=True)
    task_id = _bounded_text(task_id, field="task_id", required=True)
    objective = _bounded_text(objective, field="objective")
    current_state = _bounded_text(current_state, field="current_state")
    source_tool = _bounded_text(source_tool, field="source_tool", required=True)
    next_action = _bounded_text(next_action, field="next_action")
    decisions = _bounded_items(decisions, field="decisions")
    changes = _bounded_items(changes, field="changes")
    verifications = _bounded_items(verifications, field="verifications")
    risks = _bounded_items(risks, field="risks")
    open_questions = _bounded_items(open_questions, field="open_questions")
    evidence_ids = _bounded_items(evidence_ids, field="evidence_ids")
    supersedes = _bounded_text(supersedes, field="supersedes") or None

    if (not git_branch or not head_commit) and project_path:
        b, c = resolve_project_branch(project_path)
        git_branch = git_branch or b
        head_commit = head_commit or c

    current = load_active(root, project_id=project_id, branch=git_branch or None, fallback_to_project=False)
    version = (current.version + 1) if current is not None else 1

    base = _handoffs_dir(root)
    base.mkdir(parents=True, exist_ok=True)

    if current is not None and supersedes != current.handoff_id:
        fork_id = uuid.uuid4().hex
        fork_packet = HandoffPacket(
            handoff_id=fork_id,
            project_id=project_id,
            task_id=task_id,
            objective=objective,
            current_state=current_state,
            decisions=tuple(decisions),
            changes=tuple(changes),
            verifications=tuple(verifications),
            risks=tuple(risks),
            open_questions=tuple(open_questions),
            next_action=next_action,
            source_tool=source_tool,
            evidence_ids=tuple(evidence_ids),
            created_at=_now(),
            supersedes=supersedes,
            git_branch=git_branch,
            head_commit=head_commit,
            version=version,
            conflict_status="fork_supersedes_mismatch",
        )
        _atomic_write(base / f"{fork_id}.json", fork_packet.to_dict())
        _atomic_write(base / f"fork-{fork_id}.json", fork_packet.to_dict())
        if allow_fork:
            return fork_packet
        raise HandoffConflictError(
            f"supersedes must match active handoff {current.handoff_id}; "
            f"got {supersedes or 'missing'}",
            active_id=current.handoff_id,
            fork_path=base / f"fork-{fork_id}.json",
        )

    if current is None and supersedes is not None:
        raise ValueError(f"cannot supersede missing active handoff: {supersedes}")

    packet = HandoffPacket(
        handoff_id=uuid.uuid4().hex,
        project_id=project_id,
        task_id=task_id,
        objective=objective,
        current_state=current_state,
        decisions=tuple(decisions),
        changes=tuple(changes),
        verifications=tuple(verifications),
        risks=tuple(risks),
        open_questions=tuple(open_questions),
        next_action=next_action,
        source_tool=source_tool,
        evidence_ids=tuple(evidence_ids),
        created_at=_now(),
        supersedes=supersedes,
        git_branch=git_branch,
        head_commit=head_commit,
        version=version,
    )

    _atomic_write(base / f"{packet.handoff_id}.json", packet.to_dict())
    _write_active(root, packet)
    return packet


def create_handoff_from_summary(
    root: Path,
    *,
    project_id: str,
    source_tool: str,
    summary: Mapping[str, Any],
    evidence_id: str,
    task_id: str | None = None,
    project_path: Path | str | None = None,
    git_branch: str = "",
    head_commit: str = "",
    allow_fork: bool = False,
) -> HandoffPacket:
    """Create a handoff from bounded structured stop data only.

    Raw prompts or transcripts are deliberately not accepted. When an active
    handoff exists for the same task, this performs a compare-and-swap by
    superseding that exact packet. A different active task is never overwritten
    by a stale session stop.
    """

    if not isinstance(summary, Mapping):
        raise ValueError("handoff summary must be an object")
    resolved_task_id = task_id or summary.get("task_id")
    resolved_task_id = _bounded_text(resolved_task_id, field="task_id", required=True)

    if (not git_branch or not head_commit) and project_path:
        b, c = resolve_project_branch(project_path)
        git_branch = git_branch or b
        head_commit = head_commit or c

    current = load_active(root, project_id=project_id, branch=git_branch or None, fallback_to_project=False)
    if current is not None and current.task_id != resolved_task_id:
        raise ValueError("active handoff belongs to a different task")
    supersedes = summary.get("supersedes")
    if current is not None:
        supersedes = supersedes or current.handoff_id
    evidence = [str(evidence_id)] if str(evidence_id).strip() else []
    evidence.extend(_summary_items(summary, "evidence_ids"))
    return create_handoff(
        root,
        project_id=project_id,
        task_id=resolved_task_id,
        objective=summary.get("objective", ""),
        current_state=summary.get("current_state", ""),
        decisions=_summary_items(summary, "decisions"),
        changes=_summary_items(summary, "changes"),
        verifications=_summary_items(summary, "verifications", "verification"),
        risks=_summary_items(summary, "risks"),
        open_questions=_summary_items(summary, "open_questions"),
        next_action=summary.get("next_action", ""),
        source_tool=source_tool,
        evidence_ids=evidence,
        supersedes=supersedes,
        project_path=project_path,
        git_branch=git_branch,
        head_commit=head_commit,
        allow_fork=allow_fork,
    )


def append_handoff_evidence(
    root: Path, *, handoff_id: str, evidence_ids: Iterable[str]
) -> HandoffPacket:
    """Append bounded evidence links to an active handoff atomically."""

    path = _handoffs_dir(root) / f"{handoff_id}.json"
    if not path.is_file():
        raise FileNotFoundError(handoff_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    packet = HandoffPacket.from_dict(payload)
    if packet.closed_at:
        raise ValueError("cannot append evidence to a closed handoff")
    additions = _bounded_items(evidence_ids, field="evidence_ids")
    merged = _bounded_items(
        tuple(dict.fromkeys((*packet.evidence_ids, *additions))),
        field="evidence_ids",
    )
    updated = HandoffPacket.from_dict({**payload, "evidence_ids": merged})
    _atomic_write(path, updated.to_dict())
    active = load_active(root, project_id=updated.project_id)
    if active and active.handoff_id == handoff_id:
        _write_active(root, updated)
    return updated


def _write_active(root: Path, packet: HandoffPacket) -> None:
    target = _active_path(root, project_id=packet.project_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, packet.to_dict())
    if packet.git_branch:
        branch_target = _active_path(root, project_id=packet.project_id, branch=packet.git_branch)
        _atomic_write(branch_target, packet.to_dict())


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def ack_handoff(root: Path, *, handoff_id: str, target_tool: str) -> HandoffPacket:
    """Record that ``target_tool`` read this handoff.

    The ack is appended to the packet's ``verifications`` and the file is
    rewritten. The active pointer is unchanged.
    """

    path = _handoffs_dir(root) / f"{handoff_id}.json"
    if not path.is_file():
        raise FileNotFoundError(handoff_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    packet = HandoffPacket.from_dict(payload)
    already_acknowledged = any(
        item.startswith(f"ack:{target_tool}@") for item in packet.verifications
    )
    if not already_acknowledged:
        stamp = f"ack:{target_tool}@{_now()}"
        packet = HandoffPacket.from_dict(
            {**payload, "verifications": [*packet.verifications, stamp]}
        )
    _atomic_write(path, packet.to_dict())
    if (active := load_active(root, project_id=packet.project_id)) and active.handoff_id == handoff_id:
        _write_active(root, packet)
    return packet


def close_handoff(root: Path, *, handoff_id: str) -> HandoffPacket:
    """Close a handoff: the active pointer is cleared and the packet is sealed.

    Closed handoffs remain in storage for audit. The active pointer is removed
    when a new handoff supersedes this one; explicit close only stamps the
    close time.
    """

    path = _handoffs_dir(root) / f"{handoff_id}.json"
    if not path.is_file():
        raise FileNotFoundError(handoff_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    packet = HandoffPacket.from_dict({**payload, "closed_at": _now()})
    _atomic_write(path, packet.to_dict())
    active_path = _active_path(root, project_id=packet.project_id)
    if active_path.is_file():
        try:
            current = json.loads(active_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = None
        if isinstance(current, dict) and current.get("handoff_id") == handoff_id:
            active_path.unlink()
    if packet.git_branch:
        branch_path = _active_path(root, project_id=packet.project_id, branch=packet.git_branch)
        if branch_path.is_file():
            try:
                curr_b = json.loads(branch_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                curr_b = None
            if isinstance(curr_b, dict) and curr_b.get("handoff_id") == handoff_id:
                branch_path.unlink()
    return packet


def render_handoff_markdown(packet: HandoffPacket) -> str:
    lines = [
        f"# Handoff {packet.handoff_id}",
        "",
        f"- Project: `{packet.project_id}`",
        f"- Task: `{packet.task_id}`",
        f"- Source tool: `{packet.source_tool}`",
        f"- Created: {packet.created_at}",
    ]
    if packet.supersedes:
        lines.append(f"- Supersedes: `{packet.supersedes}`")
    if packet.closed_at:
        lines.append(f"- Closed: {packet.closed_at}")
    if packet.objective:
        lines += ["", "## Objective", "", packet.objective]
    if packet.current_state:
        lines += ["", "## Current state", "", packet.current_state]
    for header, items in (
        ("Decisions", packet.decisions),
        ("Changes", packet.changes),
        ("Verifications", packet.verifications),
        ("Risks", packet.risks),
        ("Open questions", packet.open_questions),
    ):
        if not items:
            continue
        lines += ["", f"## {header}", ""]
        lines.extend(f"- {item}" for item in items)
    if packet.next_action:
        lines += ["", "## Next action", "", packet.next_action]
    if packet.evidence_ids:
        lines += ["", "## Evidence IDs", ""]
        lines.extend(f"- `{eid}`" for eid in packet.evidence_ids)
    return "\n".join(lines) + "\n"


__all__ = [
    "ACTIVE_POINTER",
    "HANDOFFS_DIR",
    "HandoffConflictError",
    "HandoffPacket",
    "ack_handoff",
    "append_handoff_evidence",
    "close_handoff",
    "create_handoff",
    "create_handoff_from_summary",
    "list_handoffs",
    "load_active",
    "render_handoff_markdown",
    "resolve_project_branch",
]
