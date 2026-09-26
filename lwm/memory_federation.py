"""Compile native Codex/OpenCode memory into one auditable release.

Native files remain source evidence.  This module creates a derived,
versioned view instead of copying one tool's files over another tool's files.
The deterministic resolver is always available; an optional LLM may enrich
candidate analysis elsewhere, but it is never allowed to invent evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


FEDERATION_DIR = Path("state/federation")
CLAIMS_PATH = FEDERATION_DIR / "claims.json"
RELEASE_PATH = FEDERATION_DIR / "release.json"
RELEASES_DIR = FEDERATION_DIR / "releases"
ARCHIVE_DIR = FEDERATION_DIR / "archive"
UNIFIED_PAGE = Path("wiki/unified/workflow-memory.md")
CONFLICT_PAGE = Path("wiki/unified/conflicts.md")

# The user identified current OpenCode and Codex memory as the best working
# sources. GLOBAL.md remains the human authority for behavior rules and is not
# auto-overwritten by this compiler.
SOURCE_PRIORITY = {"opencode": 120, "codex": 110}
CLAIM_MAX_CHARS = 600
STALE_GRACE_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_statement(value: str) -> str:
    value = re.sub(r"[`*_>#]", "", value or "")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value.rstrip(".!?。！？")


def _claim_id(subject: str, statement: str) -> str:
    material = f"{normalize_statement(subject)}\n{normalize_statement(statement)}"
    return "claim-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _safe_json_write(path: Path, payload: Any) -> None:
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


def _safe_text_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _snapshot_label(path: Path) -> str:
    return path.stem.lower()


def _subject(statement: str) -> str:
    clean = normalize_statement(statement)
    if ":" in clean:
        return clean.split(":", 1)[0][:120]
    words = clean.split()
    return " ".join(words[:8])


def _topic(statement: str) -> str | None:
    normalized = normalize_statement(statement)
    if ":" not in normalized:
        return None
    subject, value = normalized.split(":", 1)
    qualifier = re.search(r"\bfor\s+(.+)$", value)
    return f"{subject}:{qualifier.group(1)}" if qualifier else None


def _extract_claims(root: Path, tool: str) -> list[dict[str, Any]]:
    current = root / "raw" / "tool-snapshots" / tool / "current"
    if not current.is_dir():
        return []
    claims: list[dict[str, Any]] = []
    for path in sorted(current.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
            observed_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
        except OSError:
            continue
        in_frontmatter = False
        metadata_section = False
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if line == "---":
                in_frontmatter = not in_frontmatter
                continue
            if line.startswith("#"):
                heading = line.lstrip("# ").strip().lower().replace(" ", "_")
                metadata_section = heading in {"rollout_summary_files", "keywords"}
                continue
            if in_frontmatter or metadata_section or line.startswith("↳"):
                continue
            if not line.startswith(("- ", "* ", "> ")):
                continue
            statement = re.sub(r"^(?:[-*>]\s*)+", "", line).strip()
            if re.search(r"\b(?:rollout_path|cwd|updated_at)=", statement):
                continue
            verified = re.search(r"\s+\[verified:\s*(\d{4}-\d{2}-\d{2})\]$", statement, re.I)
            verified_at = verified.group(1) if verified else None
            if verified_at:
                try:
                    if datetime.fromisoformat(verified_at).date() > datetime.now(timezone.utc).date():
                        verified_at = None
                except ValueError:
                    verified_at = None
            if verified:
                statement = statement[:verified.start()].rstrip()
            statement = re.sub(r"\s+", " ", statement)[:CLAIM_MAX_CHARS]
            if len(normalize_statement(statement)) < 16:
                continue
            subject = _subject(statement)
            claims.append(
                {
                    "claim_id": _claim_id(subject, statement),
                    "statement": statement,
                    "normalized": normalize_statement(statement),
                    "subject": subject,
                    "tool": tool,
                    "priority": SOURCE_PRIORITY[tool],
                    "source_path": str(path),
                    "source_label": _snapshot_label(path),
                    "line": line_no,
                    "observed_at": observed_at,
                    "verified_at": verified_at,
                    "status": "observed",
                    "supersedes": None,
                    "evidence": [str(path)],
                }
            )
    return claims


def _group_claims(claims: Iterable[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for claim in claims:
        matched = None
        for group in groups:
            if any(
                claim["normalized"] == existing["normalized"]
                or (_topic(claim["statement"]) is not None and _topic(claim["statement"]) == _topic(existing["statement"]))
                for existing in group
            ):
                matched = group
                break
        if matched is None:
            groups.append([claim])
        else:
            matched.append(claim)
    return groups


def _choose_group(group: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    unique = {item["normalized"] for item in group}
    if len(unique) == 1:
        winner = max(group, key=lambda item: (item["priority"], item["observed_at"], item["source_path"]))
        return winner, [item for item in group if item is not winner]
    ranked = sorted(group, key=lambda item: (item.get("verified_at") or "", item["observed_at"]), reverse=True)
    if ranked[0].get("verified_at") and ranked[0]["verified_at"] > (ranked[1].get("verified_at") or ""):
        return ranked[0], ranked[1:]
    return None, ranked


def _load_previous(root: Path) -> list[dict[str, Any]]:
    return _load_release(root).get("claims", [])


def _load_release(root: Path) -> dict[str, Any]:
    try:
        pointer = json.loads((root / RELEASE_PATH).read_text(encoding="utf-8"))
        release_id = pointer["release_id"]
        if not re.fullmatch(r"release-[A-Za-z0-9T-]+", release_id):
            return {}
        expected = RELEASES_DIR / f"{release_id}.json"
        if pointer.get("path") != str(expected):
            return {}
        payload = json.loads((root / expected).read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("release_id") != release_id
            or not isinstance(payload.get("claims"), list)
            or not (root / RELEASES_DIR / f"{release_id}-workflow.md").is_file()
            or not (root / RELEASES_DIR / f"{release_id}-conflicts.md").is_file()
        ):
            return {}
        return payload
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _render_page(claims: list[dict[str, Any]], release_id: str) -> str:
    current = [claim for claim in claims if claim.get("status") == "active"]
    lines = [
        "---",
        "title: Unified Workflow Memory",
        "type: unified-memory",
        "status: current",
        "tags: [workflow, memory, unified-memory]",
        f"release_id: {release_id}",
        "sources: [state/federation/claims.json]",
        f"updated: {_now()}",
        "---",
        "",
        "# Unified Workflow Memory",
        "",
        "> Automatically compiled from current Codex/OpenCode memory snapshots.\n> GLOBAL.md remains the behavior-rule authority.",
        "",
    ]
    if not current:
        lines.append("No automatically published claims yet.")
    for claim in current:
        lines.extend(
            [
                f"- {claim['statement']}",
                f"  - source: `{claim['tool']}` `{claim['source_label']}` line {claim['line']}",
                f"  - claim_id: `{claim['claim_id']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_conflicts(claims: list[dict[str, Any]], release_id: str) -> str:
    conflicts = [claim for claim in claims if claim.get("status") == "conflicted"]
    lines = [
        "---",
        "title: Unified Memory Conflicts",
        "type: review",
        "status: current",
        "tags: [review, conflict, unified-memory]",
        "sources: [state/federation/claims.json]",
        f"updated: {_now()}",
        f"release_id: {release_id}",
        "---",
        "",
        "# Unified Memory Conflicts",
        "",
    ]
    if not conflicts:
        lines.append("No unresolved conflicts.")
    for claim in conflicts:
        lines.extend([f"- {claim['statement']}", f"  - source: `{claim['tool']}` `{claim['source_label']}`", f"  - claim_id: `{claim['claim_id']}`", ""])
    return "\n".join(lines).rstrip() + "\n"


def compile_federated_memory(root: Path) -> dict[str, Any]:
    """Compile and atomically publish the current native-memory federation."""

    root = root.resolve()
    source_claims = [claim for tool in SOURCE_PRIORITY for claim in _extract_claims(root, tool)]
    previous = _load_previous(root)
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_GRACE_DAYS)
    fresh = [claim for claim in source_claims if datetime.fromisoformat(claim["observed_at"]) >= cutoff]
    stale = [{**claim, "status": "stale"} for claim in source_claims if claim not in fresh]
    groups = _group_claims(fresh)
    resolved: list[dict[str, Any]] = []
    for group in groups:
        winner, losers = _choose_group(group)
        if winner is None:
            for item in losers:
                resolved.append({**item, "status": "conflicted", "conflict_with": [x["claim_id"] for x in losers if x is not item]})
            continue
        resolved.append({**winner, "status": "active"})
        for loser in losers:
            resolved.append({**loser, "status": "superseded", "superseded_by": winner["claim_id"]})

    resolved.extend(stale)
    current_ids = {claim["claim_id"] for claim in resolved}
    available_tools = {tool for tool in SOURCE_PRIORITY if (root / "raw" / "tool-snapshots" / tool / "current").is_dir()}
    for old in previous:
        if old.get("claim_id") in current_ids or old.get("tool") not in available_tools:
            continue
        archived = {**old, "status": "archived", "archived_at": _now(), "archive_reason": "absent_from_current_authoritative_snapshot"}
        resolved.append(archived)

    release_id = "release-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:12]
    payload = {"schema_version": 1, "release_id": release_id, "generated_at": _now(), "claims": resolved}
    root.joinpath(RELEASES_DIR).mkdir(parents=True, exist_ok=True)
    _safe_json_write(root / RELEASES_DIR / f"{release_id}.json", payload)
    _safe_text_write(root / RELEASES_DIR / f"{release_id}-workflow.md", _render_page(resolved, release_id))
    _safe_text_write(root / RELEASES_DIR / f"{release_id}-conflicts.md", _render_conflicts(resolved, release_id))
    _safe_json_write(root / CLAIMS_PATH, payload)
    unified = root / UNIFIED_PAGE
    conflicts = root / CONFLICT_PAGE
    _safe_text_write(unified, _render_page(resolved, release_id))
    _safe_text_write(conflicts, _render_conflicts(resolved, release_id))
    for claim in resolved:
        if claim["status"] == "archived":
            _safe_json_write(root / ARCHIVE_DIR / f"{claim['claim_id']}.json", claim)
    _safe_json_write(root / RELEASE_PATH, {"schema_version": 1, "release_id": release_id, "path": str(RELEASES_DIR / f"{release_id}.json"), "generated_at": _now()})
    return {
        "status": "ok",
        "release_id": release_id,
        "source_claims": len(source_claims),
        "active": sum(item.get("status") == "active" for item in resolved),
        "superseded": sum(item.get("status") == "superseded" for item in resolved),
        "conflicted": sum(item.get("status") == "conflicted" for item in resolved),
        "archived": sum(item.get("status") == "archived" for item in resolved),
        "stale": len(stale),
        "page": str(UNIFIED_PAGE),
    }


def load_published_memory(root: Path, *, limit: int = 24) -> dict[str, Any]:
    payload = _load_release(root)
    claims = payload.get("claims", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_GRACE_DAYS)

    def current(claim: dict[str, Any]) -> bool:
        try:
            return datetime.fromisoformat(claim["observed_at"]) >= cutoff
        except (KeyError, TypeError, ValueError):
            return False

    return {
        "release_id": payload.get("release_id"),
        "claims": [claim for claim in claims if claim.get("status") == "active" and current(claim)][:limit],
        "conflicts": [claim for claim in claims if claim.get("status") == "conflicted"][:limit],
    }


def restore_federated_release(root: Path, release_id: str) -> dict[str, Any]:
    """Restore a previously generated release without touching raw evidence."""

    root = root.resolve()
    if not re.fullmatch(r"release-[A-Za-z0-9T-]+", release_id):
        raise ValueError(f"invalid federation release: {release_id}")
    path = root / RELEASES_DIR / f"{release_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(release_id) from exc
    if not isinstance(payload, dict) or payload.get("release_id") != release_id:
        raise ValueError(f"invalid federation release: {release_id}")
    claims = list(payload.get("claims") or [])
    _safe_text_write(root / RELEASES_DIR / f"{release_id}-workflow.md", _render_page(claims, release_id))
    _safe_text_write(root / RELEASES_DIR / f"{release_id}-conflicts.md", _render_conflicts(claims, release_id))
    _safe_json_write(root / CLAIMS_PATH, payload)
    _safe_text_write(root / UNIFIED_PAGE, _render_page(claims, release_id))
    _safe_text_write(root / CONFLICT_PAGE, _render_conflicts(claims, release_id))
    _safe_json_write(root / RELEASE_PATH, {"schema_version": 1, "release_id": release_id, "path": str(RELEASES_DIR / f"{release_id}.json"), "restored_at": _now()})
    return {"status": "restored", "release_id": release_id, "active": sum(item.get("status") == "active" for item in claims)}


__all__ = [
    "compile_federated_memory",
    "load_published_memory",
    "normalize_statement",
    "restore_federated_release",
]
