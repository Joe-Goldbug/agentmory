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

from lwm import project_id

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


def _claim_id(subject: str, statement: str, identity: str = "") -> str:
    material = f"{identity}\n{normalize_statement(subject)}\n{normalize_statement(statement)}"
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


_METADATA = re.compile(
    r"^(scope|applies_to|project_id|project_ids|project_path|project|date|updated|updated_at|"
    r"asserted|asserted_at|verified|verified_at|supersedes|topic|title|description|"
    r"status|type|tags|source|sources):\s*(.*)$", re.I,
)
_GLOBAL_SECTIONS = {"user preferences", "user profile", "general tips", "用户偏好", "偏好", "用户画像"}
_GLOBAL_SOURCES = {"agents", "global", "user-profile", "patterns"}
_SKIP_SECTIONS = {"rollout_summary_files", "rollout summary files", "keywords", "see also"}


def _date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    compact = re.match(r"^(\d{4})(\d{2})(\d{2})(?:-|$)", value)
    if compact:
        value = "-".join(compact.groups())
    match = re.search(r"\d{4}-\d{2}-\d{2}(?:T\d{2}(?::|-)\d{2}(?::|-)\d{2}(?:Z|[+-]\d{2}:\d{2})?)?", value)
    if not match:
        return None
    try:
        date_text = match.group().replace("Z", "+00:00")
        if "T" in date_text:
            day, clock = date_text.split("T", 1)
            date_text = day + "T" + re.sub(r"^(\d{2})-(\d{2})-(\d{2})", r"\1:\2:\3", clock)
        parsed = datetime.fromisoformat(date_text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed > datetime.now(timezone.utc):
            return None
        return parsed.isoformat(timespec="seconds")
    except ValueError:
        return None


def _name(value: str) -> str:
    return re.sub(r"[^\w]+", " ", normalize_statement(value)).strip()


def _mentions(value: str, name: str) -> bool:
    return bool(name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", _name(value)))


def _markdown_blocks(text: str) -> list[dict[str, Any]]:
    """Keep section metadata attached until all sibling evidence has been read."""
    document: dict[str, Any] = {"heading": "", "metadata": {}, "events": [], "tasks": {}}
    stack = [document]
    blocks: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    fence: str | None = None
    frontmatter = False
    table_header: list[str] | None = None

    def flush() -> None:
        nonlocal pending
        if pending is not None:
            blocks.append(pending)
            pending = None

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line_no == 1 and line == "---":
            frontmatter = True
            continue
        if frontmatter:
            if line == "---":
                frontmatter = False
            elif match := _METADATA.match(line):
                document["metadata"][match[1].lower()] = match[2].strip("\"'")
            continue
        if re.match(r"^(?:`{3,}|~{3,})", line):
            flush()
            marker = line[0]
            if fence == marker:
                fence = None
            elif fence is None:
                fence = marker
            continue
        if fence:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        if heading:
            flush()
            level = len(heading[1])
            while len(stack) > 1 and stack[-1]["level"] >= level:
                stack.pop()
            section: dict[str, Any] = {"heading": heading[2], "level": level, "metadata": {}, "events": [], "tasks": {}}
            if task := re.match(r"Task\s+(\d+):", heading[2], re.I):
                stack[-1]["tasks"][task[1]] = section
            stack.append(section)
            table_header = None
            continue
        if any(section["heading"].lower() in _SKIP_SECTIONS for section in stack):
            flush()
            if stack[-1]["heading"].lower() in {"rollout_summary_files", "rollout summary files"}:
                event = re.search(r"(?:rollout_summaries|extensions/ad_hoc/notes)/([^\s)]+)", line)
                if event:
                    owner = stack[-2]
                    updated = re.search(r"updated_at=([^\s,)]+)", line)
                    owner["events"].append({
                        "source": event[0], "asserted_at": _date(event[1]),
                        "updated_at": _date(updated[1]) if updated else None,
                    })
            continue
        if match := _METADATA.match(line):
            flush()
            stack[-1]["metadata"][match[1].lower()] = match[2].strip("\"'")
            continue
        if not line or re.fullmatch(r"[-*_]{3,}", line) or line.startswith(("<!--", "↳")):
            flush()
            table_header = None
            continue
        if line.startswith("|") and line.endswith("|"):
            flush()
            cells = [cell.replace(r"\|", "|").strip() for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if table_header is None:
                table_header = cells
                continue
            table = dict(zip(table_header, cells))
            blocks.append({"text": "; ".join(f"{key}: {value}" for key, value in table.items()),
                           "line": line_no, "end_line": line_no, "format": "table", "table": table,
                           "sections": list(stack)})
            continue
        table_header = None
        marker = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)(.*)$", line)
        if marker:
            flush()
            kind = "list" if not line.startswith(">") else "quote"
            pending = {"text": marker[1], "line": line_no, "end_line": line_no,
                       "format": kind, "sections": list(stack)}
        elif pending is not None and (pending["format"] == "paragraph" or raw[:1].isspace()):
            pending["text"] += " " + line
            pending["end_line"] = line_no
        else:
            flush()
            pending = {"text": line, "line": line_no, "end_line": line_no,
                       "format": "paragraph", "sections": list(stack)}
    flush()
    return blocks


def _scope_for(
    metadata: dict[str, str], headings: list[str], statement: str,
    path: Path, projects: dict[str, str],
) -> dict[str, Any]:
    project_path = metadata.get("project_path")
    applies = metadata.get("applies_to", "")
    cwd = re.search(r"\bcwd=(.+?)(?:;|$)", applies)
    if cwd:
        project_path = cwd[1].strip().strip("`\"'")
    path_heading = next((heading.strip("` ") for heading in reversed(headings)
                         if heading.strip("` ").startswith(("/", "~/"))), None)
    project_path = project_path or path_heading
    # Native memory/config paths identify the source, not the remembered project.
    native_path = project_path and any(part in {".codex", ".config", ".agents"}
                                       for part in Path(project_path).parts)
    if project_path and not native_path:
        project_path = str(Path(project_path).expanduser().resolve())
    else:
        project_path = None
    explicit_id = metadata.get("project_id")
    if explicit_ids := metadata.get("project_ids"):
        ids = [value.strip(" []\"'") for value in explicit_ids.split(",") if value.strip(" []\"'")]
        if ids:
            return {"scope": ids, "project_ids": ids, "project_path": project_path}
    explicit_scope = metadata.get("scope", "").strip(" []\"'")
    if explicit_scope not in {"", "global", "unknown", "project", "cross-project"}:
        ids = [value.strip(" \"'") for value in explicit_scope.split(",")]
        # A prose scope description is not a project id.
        if all(value in projects.values() or re.fullmatch(r"(?:git|local|adhoc)-[\da-f]{16}", value) for value in ids):
            return {"scope": ids, "project_ids": ids, "project_path": project_path}
    if explicit_id:
        return {"scope": [explicit_id], "project_ids": [explicit_id], "project_path": project_path}
    if project_path:
        pid = projects.get(project_path)
        if pid:
            return {"scope": [pid], "project_ids": [pid], "project_path": project_path,
                    "project_name": Path(project_path).name}
        return {"scope": "unknown", "project_ids": [], "project_path": project_path,
                "project_name": Path(project_path).name}
    identity_heading = next((heading for heading in reversed(headings)
                             if re.match(r"(?:Task Group|Project|项目):", heading, re.I)), None)
    identity = metadata.get("project") or (identity_heading.split(":", 1)[1].strip() if identity_heading else "")
    if not identity:
        # Plain project titles in source notes carry ownership for every row,
        # including safeguards which do not repeat the project name.
        title = headings[0] if headings else metadata.get("title", "")
        if any(_mentions(title, _name(Path(project).name)) for project in projects):
            identity = title
    named = {pid for project, pid in projects.items()
             if _mentions(identity, _name(Path(project).name))}
    if len(named) == 1:
        pid = next(iter(named))
        matched_path = next(project for project, value in projects.items() if value == pid)
        return {"scope": [pid], "project_ids": [pid], "project_path": matched_path,
                "project_name": Path(matched_path).name}
    if identity or path_heading:
        return {"scope": "unknown", "project_ids": [], "project_name": identity or path_heading}
    mentioned = sorted({pid for project, pid in projects.items()
                        if _mentions(statement, _name(Path(project).name))})
    if mentioned:
        return {"scope": mentioned, "project_ids": mentioned}
    if explicit_scope in {"unknown", "project", "cross-project"}:
        return {"scope": "unknown", "project_ids": []}
    global_source = path.stem.lower() in _GLOBAL_SOURCES
    global_section = any(heading.lower() in _GLOBAL_SECTIONS for heading in headings)
    return {"scope": "global" if explicit_scope == "global" or global_source or global_section else "unknown",
            "project_ids": []}


def _identity(claim: dict[str, Any]) -> str:
    scope = claim.get("scope")
    if isinstance(scope, list):
        return "projects:" + ",".join(sorted(scope))
    if scope == "unknown":
        return "unknown:" + str(claim.get("project_path") or claim.get("project_name") or "")
    return str(scope or "unknown")


def _extract_claims(root: Path, tool: str) -> list[dict[str, Any]]:
    current = root / "raw" / "tool-snapshots" / tool / "current"
    if not current.is_dir():
        return []
    projects = project_id.load_project_map(root)
    claims: list[dict[str, Any]] = []
    for path in sorted(current.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
            if "<!-- LWM-COMPANION:OWNED -->" in text:
                continue
            # Keep native human rules and line numbers, excluding our mirror.
            text = re.sub(
                r"(?s)<!-- LLM-(?:WIKI|WORKMEM):START -->.*?<!-- LLM-(?:WIKI|WORKMEM):END -->",
                lambda match: "\n" * match.group(0).count("\n"), text,
            )
            captured_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
        except OSError:
            continue
        for block in _markdown_blocks(text):
            statement = re.sub(r"\s+", " ", block["text"]).strip()
            if re.search(r"\b(?:rollout_path|cwd|updated_at)=", statement):
                continue
            sections = block["sections"]
            headings = [section["heading"] for section in sections if section["heading"]]
            metadata = {key: value for section in sections for key, value in section["metadata"].items()}
            events = [event for section in sections for event in section["events"]]
            task_ids = re.findall(r"\[Task\s+(\d+)\]", statement, re.I)
            if task_ids:
                events = [event for section in sections for task_id in task_ids
                          for event in section["tasks"].get(task_id, {}).get("events", [])]
            dates = {key: _date(metadata.get(key) or metadata.get(key + "_at")) for key in ("asserted", "verified")}
            for annotation in re.finditer(r"\[(asserted|verified):\s*([^\]]+)\]", statement, re.I):
                dates[annotation[1].lower()] = _date(annotation[2])
            statement = re.sub(r"\s*\[(?:asserted|verified):[^\]]+\]", "", statement, flags=re.I).strip()
            supersedes = metadata.get("supersedes")
            if relations := re.findall(r"\[supersedes:\s*([^\]]+)\]", statement, re.I):
                supersedes = ",".join(([supersedes] if supersedes else []) + relations)
                statement = re.sub(r"\s*\[supersedes:[^\]]+\]", "", statement, flags=re.I).strip()
            asserted_at = dates["asserted"] or max((event["asserted_at"] for event in events if event["asserted_at"]), default=None)
            document_at = _date(metadata.get("date") or metadata.get("updated") or metadata.get("updated_at"))
            document_at = document_at or _date(path.stem)
            verified_at = dates["verified"]
            observed_at = verified_at or asserted_at or document_at
            scope = _scope_for(metadata, headings, statement, path, projects)
            subject = _subject(statement)
            if len(normalize_statement(statement)) < 16:
                continue
            directive = bool(re.search(r"\b(?:use|always|never|must|do not|prefer|user|workflow|policy)\b|用户|偏好|规则|必须|不得", " ".join(headings) + " " + statement, re.I))
            claim = {
                "statement": statement, "normalized": normalize_statement(statement), "subject": subject,
                "tool": tool, "priority": SOURCE_PRIORITY[tool], "source_path": str(path),
                "source_label": _snapshot_label(path), "line": block["line"], "end_line": block["end_line"],
                "section": headings, "format": block["format"], "table": block.get("table"),
                "source_metadata": metadata, "source_events": events, **scope,
                "captured_at": captured_at, "document_at": document_at, "asserted_at": asserted_at,
                "observed_at": observed_at, "verified_at": verified_at,
                "date_basis": "verified" if verified_at else "asserted" if asserted_at else "document" if document_at else "unknown",
                "kind": "directive" if directive else "reference",
                "dated_observation": "report" in path.stem.lower() or metadata.get("type") in {"report", "observation"},
                "status": "observed", "supersedes": supersedes, "evidence": [str(path)],
                "authority": "native-reference", "auxiliary": True,
            }
            claim["claim_id"] = _claim_id(subject, statement, _identity(claim))
            claims.append(claim)
    return claims


def _proposition(statement: str) -> str:
    value = normalize_statement(statement)
    value = re.sub(r"\b(?:does|do|did)\s+(?:not|no longer)\s+|\b(?:not|never|no longer)\s+", "", value)
    value = re.sub(r"不再|不得|禁止|不要|不", "", value)
    return " ".join(word[:-1] if word.endswith("s") and len(word) > 3 else word
                    for word in value.split())


def _claim_topic(claim: dict[str, Any]) -> str | None:
    explicit = claim.get("source_metadata", {}).get("topic")
    if explicit:
        return normalize_statement(explicit)
    if claim.get("table"):
        return "table:" + normalize_statement(next(iter(claim["table"].values())))
    topic = _topic(claim["statement"])
    if topic:
        return topic
    if claim.get("scope") != "unknown" and ":" in claim["normalized"]:
        return claim["normalized"].split(":", 1)[0]
    proposition = re.match(r"(.+?)\s+(?:uses?|requires?|supports?|stores?|is|are)\s+(.+)$", claim["normalized"])
    if proposition and claim.get("scope") != "unknown":
        qualifier = re.search(r"\bfor\s+(.+)$", proposition[2])
        return "proposition:" + proposition[1] + (":" + qualifier[1] if qualifier else "")
    return None


def _group_claims(claims: Iterable[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for claim in claims:
        matched = None
        for group in groups:
            if any(
                _identity(claim) == _identity(existing) and (
                    claim["normalized"] == existing["normalized"]
                    or (_claim_topic(claim) is not None and _claim_topic(claim) == _claim_topic(existing))
                    or _proposition(claim["statement"]) == _proposition(existing["statement"])
                )
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
        winner = max(group, key=lambda item: (item.get("verified_at") or "", item["priority"], item.get("observed_at") or "", item["source_path"]))
        return winner, [item for item in group if item is not winner]
    ranked = sorted(group, key=lambda item: (item.get("verified_at") or "", item.get("observed_at") or ""), reverse=True)
    if ranked[0].get("verified_at") and ranked[0]["verified_at"] > (ranked[1].get("verified_at") or ""):
        return ranked[0], ranked[1:]
    return None, ranked


def _supersession_targets(value: str) -> list[str]:
    """Only explicit retirement language supplies a deterministic target."""
    targets: list[str] = []
    for sentence in re.split(r"(?<=[!?。；])\s*|(?<=\.)\s+|;", value):
        for pattern in (
            r"(.+?)\s+(?:is|are|was|were|已)\s+(?:now\s+)?(?:historical(?:/superseded)?|superseded|obsolete|retired|withdrawn|replaced)\b",
            r"\bsupersedes\s+(.+?)(?:\s+for\s+|$)",
            r"(.+?)(?:已被|已经被|已|已经)(?:取代|替代|废弃|淘汰|停用)",
            r"不再(?:采用|使用|执行)(.+?)(?:，|,|。|$)",
        ):
            match = re.search(pattern, sentence, re.I)
            if match:
                target = match[1].strip()
                targets.extend(re.split(r",|\band\b|、", target, flags=re.I))
    return [target.strip(" `\"'.!?。") for target in targets if target.strip()]


_TARGET_STOP_WORDS = set("the a an old prior earlier historical current active new model plan note proposal language website public release direction for of is are by now this that daily".split())


def _target_matches(target: str, statement: str) -> bool:
    if normalize_statement(target) == normalize_statement(statement):
        return True
    if re.search(r"[\u4e00-\u9fff]", target) and normalize_statement(target) in normalize_statement(statement):
        return True
    def stem(word: str) -> str:
        return word[:-3] if word.endswith("ing") and len(word) > 6 else word.rstrip("s")
    tokens = {stem(word) for word in _name(target).split() if word not in _TARGET_STOP_WORDS}
    words = {stem(word) for word in _name(statement).split()}
    return bool(tokens) and tokens <= words


def _explicit_retirements(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    retired: dict[str, dict[str, Any]] = {}
    by_identity: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_identity.setdefault(_identity(claim), []).append(claim)
    for newer in claims:
        metadata = newer.get("source_metadata", {})
        targets = _supersession_targets(newer["statement"] + "; " + metadata.get("scope", "") + "; " + metadata.get("applies_to", ""))
        source_targets = [value.strip(" []`\"'") for value in str(newer.get("supersedes") or "").split(",") if value.strip()]
        if not targets and not source_targets:
            continue
        for older in by_identity[_identity(newer)]:
            if older is newer:
                continue
            if _identity(newer).startswith("unknown:"):
                # Unknown ownership cannot retire a different source's facts.
                if older["source_path"] != newer["source_path"]:
                    continue
            old_date = older.get("verified_at") or older.get("asserted_at") or older.get("document_at")
            new_date = newer.get("verified_at") or newer.get("asserted_at") or newer.get("document_at")
            if old_date and new_date and old_date > new_date:
                continue
            source_match = any(target in {older["claim_id"], older["source_path"], Path(older["source_path"]).name}
                               for target in source_targets + targets)
            # Preserve the correction itself and safety/negation statements, even
            # when they mention a retired mechanism as a historical reference.
            old_text = older["statement"]
            corrective = bool(_supersession_targets(old_text)) or bool(re.search(
                r"\b(?:do not|never|must not|not current|safeguard|safety|bind|defenses?|historical|supersedes?|override|overrides|removed|conflicts?)\b|不得|不要|不再|历史|安全", old_text, re.I,
            ))
            if source_match or (not corrective and any(_target_matches(target, old_text) for target in targets)):
                existing = retired.get(older["claim_id"])
                if existing is None or (newer.get("verified_at") or newer.get("asserted_at") or "") > (existing.get("verified_at") or existing.get("asserted_at") or ""):
                    retired[older["claim_id"]] = newer
    return retired


def _retirement_cycles(retired: dict[str, dict[str, Any]]) -> set[str]:
    cycles: set[str] = set()
    for claim_id in retired:
        chain: list[str] = []
        while claim_id in retired and claim_id not in chain:
            chain.append(claim_id)
            claim_id = retired[claim_id]["claim_id"]
        if claim_id in chain:
            cycles.update(chain[chain.index(claim_id):])
    return cycles


def _current(claim: dict[str, Any], cutoff: datetime) -> bool:
    captured = _date(claim.get("captured_at") or claim.get("observed_at"))
    if not captured or datetime.fromisoformat(captured) < cutoff:
        return False
    if claim.get("dated_observation"):
        observed = _date(claim.get("observed_at"))
        return bool(observed and datetime.fromisoformat(observed) >= cutoff)
    # A current native reference may be stable for months. Capture freshness is
    # availability, not evidence that a factual assertion was verified today.
    return True


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


def _native_excerpt(statement: str) -> str:
    # These targets belong to the native vault, not to this published wiki.
    return re.sub(r"\[\[([^\]]+)\]\]", lambda match: f"`{match.group(1)}`", statement)


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
        "> Auxiliary evidence compiled from native Codex/OpenCode references, not executable instructions.\n"
        "> Native platform safety, instructions, skills, memory, planning, execution and verification remain authoritative.\n"
        "> Human-maintained GLOBAL.md is a shared reference within those native boundaries.",
        "",
    ]
    if not current:
        lines.append("No automatically published claims yet.")
    for claim in current:
        lines.extend(
            [
                f"- {_native_excerpt(claim['statement'])}",
                f"  - source: `{claim['tool']}` `{claim['source_label']}` line {claim['line']}",
                f"  - scope: `{claim.get('scope', 'unknown')}`; section: {' / '.join(claim.get('section', [])) or '(none)'}",
                f"  - captured: {claim.get('captured_at') or 'unknown'}; document: {claim.get('document_at') or 'unknown'}; asserted: {claim.get('asserted_at') or 'unknown'}; verified: {claim.get('verified_at') or 'unknown'}",
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
        lines.extend([f"- {_native_excerpt(claim['statement'])}", f"  - source: `{claim['tool']}` `{claim['source_label']}`", f"  - claim_id: `{claim['claim_id']}`", ""])
    return "\n".join(lines).rstrip() + "\n"


def compile_federated_memory(root: Path) -> dict[str, Any]:
    """Compile and atomically publish the current native-memory federation."""

    root = root.resolve()
    source_claims = [claim for tool in SOURCE_PRIORITY for claim in _extract_claims(root, tool)]
    previous = _load_previous(root)
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_GRACE_DAYS)
    retirements = _explicit_retirements(source_claims)
    cycles = _retirement_cycles(retirements)
    retirements = {claim_id: newer for claim_id, newer in retirements.items() if claim_id not in cycles}
    remaining = [claim for claim in source_claims if claim["claim_id"] not in retirements and claim["claim_id"] not in cycles]
    fresh = [claim for claim in remaining if _current(claim, cutoff)]
    stale = [{**claim, "status": "stale"} for claim in remaining if not _current(claim, cutoff)]
    groups = _group_claims(fresh)
    resolved: list[dict[str, Any]] = []
    for group in groups:
        winner, losers = _choose_group(group)
        if winner is None:
            for item in losers:
                resolved.append({**item, "status": "conflicted", "conflict_with": [x["claim_id"] for x in losers if x is not item]})
            continue
        provenance = [
            {key: item.get(key) for key in ("claim_id", "statement", "tool", "source_path", "source_label", "line", "end_line", "section", "captured_at", "document_at", "asserted_at", "verified_at")}
            for item in group
        ]
        resolved.append({**winner, "status": "active", "provenance": provenance,
                         "evidence": sorted({source for item in group for source in item["evidence"]})})
        for loser in losers:
            resolved.append({**loser, "status": "superseded", "superseded_by": winner["claim_id"]})

    resolved.extend({**claim, "status": "superseded", "superseded_by": retirements[claim["claim_id"]]["claim_id"],
                     "supersession_reason": "explicit_source_retirement"}
                    for claim in source_claims if claim["claim_id"] in retirements)
    resolved.extend({**claim, "status": "conflicted", "conflict_reason": "cyclic_source_supersession",
                     "conflict_with": sorted(cycles - {claim["claim_id"]})}
                    for claim in source_claims if claim["claim_id"] in cycles)
    resolved.extend(stale)
    current_ids = {claim["claim_id"] for claim in resolved}
    available_tools = {tool for tool in SOURCE_PRIORITY if (root / "raw" / "tool-snapshots" / tool / "current").is_dir()}
    for old in previous:
        if old.get("claim_id") in current_ids or old.get("tool") not in available_tools:
            continue
        archived = {**old, "status": "archived", "archived_at": _now(), "archive_reason": "absent_from_current_authoritative_snapshot"}
        resolved.append(archived)

    release_id = "release-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:12]
    payload = {"schema_version": 2, "authority": "auxiliary-native-evidence", "release_id": release_id, "generated_at": _now(), "claims": resolved}
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

    return {
        "release_id": payload.get("release_id"),
        "claims": [claim for claim in claims if claim.get("status") == "active" and _current(claim, cutoff)][:limit],
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
