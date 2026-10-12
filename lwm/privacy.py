"""Privacy filter for incoming work events.

Default-on rules:

* Path redaction: any ``project_path`` or ``files_touched`` entry that
  matches sensitive directory patterns is replaced with the path's
  basename + ``<REDACTED:path>``.
* Secret redaction: regex-based replacement for known secret patterns
  (``api_key=...``, ``sk-...``, AWS access key IDs, JWTs).
* Truncation: any standalone string field (``task``, ``decisions`` etc.)
  larger than :data:`lwm.events.MAX_TEXT_BYTES` is truncated and
  flagged ``truncated=true``.

Design notes:

* The filter is purely deterministic. No external calls. No LLM.
* Rules live in :mod:`lwm.privacy_rules` so users can edit them without
  touching this module. This module loads and applies them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lwm.events import truncate_event_text


DEFAULT_PRIVACY_RULES_PATH = Path("privacy_rules.toml")


@dataclass(frozen=True)
class PrivacyIssue:
    field: str
    reason: str
    redacted: bool

    def render(self) -> str:
        return f"{self.field}: {self.reason} (redacted={self.redacted})"


@dataclass(frozen=True)
class PrivacyReport:
    event: dict[str, Any]
    issues: tuple[PrivacyIssue, ...]
    blocked: bool

    @property
    def ok(self) -> bool:
        return not self.issues


# --- Path redaction ---------------------------------------------------------

DEFAULT_PATH_BLOCK_PATTERNS: tuple[str, ...] = (
    r"(^|/)(\.env|\.env\.[^/]+)$",
    r"(^|/)credentials(/|$)",
    r"(^|/)secrets?(/|$)",
    r"(^|/)tokens?(/|$)",
    r"(^|/)\.ssh(/|$)",
    r"(^|/)(\.aws|\.gcp|\.kube)(/|$)",
)

DEFAULT_PATH_BLOCK_NAMES: tuple[str, ...] = (
    "credentials",
    "credentials.json",
    ".env",
    ".envrc",
    "secret",
    "secrets",
    "id_rsa",
    "id_ed25519",
)

# --- Secret redaction -------------------------------------------------------

# Match "name=value" or "name: value" patterns with a recognizable identifier.
_SECRET_KV_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_])((?:[A-Za-z0-9_-]*?(?:"
    r"api[_-]?key|apikey|api[_-]?token|access[_-]?token|auth[_-]?token|token|bearer|"
    r"client[_-]?secret|secret|password|passwd|pwd|"
    r"private[_-]?key|cookie|session[_-]?id|refresh[_-]?token"
    r")[A-Za-z0-9_-]*"
    r"))['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.\+/=]{6,})['\"]?"
)

_OPENAI_SK_RE = re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9._-]{19,}\b")
_AWS_AKID_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB_PAT_RE = re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")
_SLACK_TOKEN_RE = re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")
_PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_block", _PRIVATE_KEY_BLOCK_RE),
    ("openai_sk", _OPENAI_SK_RE),
    ("aws_access_key", _AWS_AKID_RE),
    ("github_pat", _GITHUB_PAT_RE),
    ("slack_token", _SLACK_TOKEN_RE),
    ("jwt", _JWT_RE),
    ("secret_kv", _SECRET_KV_RE),
)

REDACTED_TEXT = "<REDACTED>"


def _is_blocked_path(p: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pat.search(p) for pat in patterns)


def _compiled_path_patterns(rules: dict[str, Any]) -> tuple[re.Pattern[str], ...]:
    raw = list(DEFAULT_PATH_BLOCK_PATTERNS)
    extra = rules.get("path_block_patterns") or []
    if isinstance(extra, list):
        raw.extend(str(x) for x in extra)
    return tuple(re.compile(p) for p in raw)


def _path_block_names(rules: dict[str, Any]) -> frozenset[str]:
    extra = rules.get("path_block_names") or []
    names = set(DEFAULT_PATH_BLOCK_NAMES)
    if isinstance(extra, list):
        names.update(str(x) for x in extra)
    return frozenset(names)


def load_privacy_rules(rules_path: Path | None = None) -> dict[str, Any]:
    """Load extra rules from a TOML-ish file. Missing file ⇒ empty rules."""

    path = rules_path or DEFAULT_PRIVACY_RULES_PATH
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return _parse_simple_toml(text)


def _parse_simple_toml(text: str) -> dict[str, Any]:
    """Parse the minimal TOML subset we use: ``key = ["a", "b"]`` lists."""

    rules: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            current_list_key = None
            continue
        if current_list_key is not None:
            stripped = line.strip()
            if stripped.startswith("]"):
                current_list_key = None
                continue
            if stripped.startswith('"') and stripped.endswith('"'):
                rules.setdefault(current_list_key, []).append(stripped[1:-1])
            elif stripped.startswith("'") and stripped.endswith("'"):
                rules.setdefault(current_list_key, []).append(stripped[1:-1])
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and not value.endswith("]"):
                current_list_key = key
                rules.setdefault(key, [])
                continue
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                items: list[str] = []
                if inner:
                    for part in _split_toml_array(inner):
                        part = part.strip()
                        if (part.startswith('"') and part.endswith('"')) or (
                            part.startswith("'") and part.endswith("'")
                        ):
                            items.append(part[1:-1])
                        else:
                            items.append(part)
                rules[key] = items
            current_list_key = None
    return rules


def _split_toml_array(inner: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_q: str | None = None
    for ch in inner:
        if in_q:
            buf.append(ch)
            if ch == in_q:
                in_q = None
            continue
        if ch in {'"', "'"}:
            in_q = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def redact_text(text: str) -> tuple[str, tuple[str, ...]]:
    """Apply deterministic secret patterns to text.

    This is used for both event fields and bounded source snapshots. Keep the
    replacement stable so downstream hashes and audit records remain useful.
    """

    applied: list[str] = []
    redacted = text
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            new = pattern.sub(REDACTED_TEXT, redacted)
            if new != redacted:
                applied.append(name)
            redacted = new
    return redacted, tuple(applied)


def _source_scan_text(source: dict[str, Any], session_id: Any) -> str:
    """Keep host conversation identity distinct from authentication secrets."""
    proof = source.get("host_proof")
    if not isinstance(proof, dict):
        return " ".join(str(value) for value in source.values())
    scan_proof = dict(proof)
    identity = proof.get("session_id")
    if (
        isinstance(identity, str)
        and identity == session_id
        and proof.get("integration")
        and proof.get("event")
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", identity)
    ):
        # Scan the value for actual credential formats, but not the misleading
        # authentication-style key name. The original event remains untouched.
        scan_proof.pop("session_id")
        scan_proof["conversation_identity"] = identity
    scan_source = {**source, "host_proof": scan_proof}
    return " ".join(str(value) for value in scan_source.values())


def sanitize_event(
    payload: dict[str, Any],
    *,
    rules: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], tuple[PrivacyIssue, ...], bool]:
    """Return a sanitized copy of the event plus a list of issues.

    The original payload is not mutated. A blocked event still returns a
    dict (with redactions applied) so the caller can persist it under
    ``raw/events/rejected/`` with full context.
    """

    rules = rules if rules is not None else load_privacy_rules()
    compiled_paths = _compiled_path_patterns(rules)
    block_names = _path_block_names(rules)

    issues: list[PrivacyIssue] = []
    out = dict(payload)
    blocked = False

    project_path = str(out.get("project_path") or "")
    if project_path and (
        Path(project_path).name in block_names
        or _is_blocked_path(project_path, compiled_paths)
    ):
        out["project_path"] = "<REDACTED:path>"
        issues.append(
            PrivacyIssue("$.project_path", "blocked by path rule", redacted=True)
        )
        blocked = True

    files = out.get("files_touched")
    if isinstance(files, list):
        new_files: list[str] = []
        any_redacted = False
        for entry in files:
            if (
                isinstance(entry, str)
                and (
                    Path(entry).name in block_names
                    or _is_blocked_path(entry, compiled_paths)
                )
            ):
                new_files.append("<REDACTED:path>")
                any_redacted = True
            else:
                new_files.append(entry)
        if any_redacted:
            out["files_touched"] = new_files
            issues.append(
                PrivacyIssue(
                    "$.files_touched", "blocked path(s) redacted", redacted=True
                )
            )
            blocked = True

    scan_targets = [
        ("$.task", out.get("task")),
        ("$.tool_version", out.get("tool_version")),
    ]
    for key in (
        "decisions",
        "changes",
        "verification",
        "open_questions",
        "tags",
    ):
        scan_targets.append((f"$.{key}", out.get(key)))
    for json_key in ("$.source",):
        value = out.get("source")
        if isinstance(value, dict):
            source_text = _source_scan_text(value, out.get("session_id"))
            scan_targets.append((json_key, source_text))

    for json_field, value in scan_targets:
        if isinstance(value, str):
            new_value, applied = redact_text(value)
            if applied:
                if json_field == "$.task":
                    out["task"] = new_value
                elif json_field == "$.tool_version":
                    out["tool_version"] = new_value
                issues.append(
                    PrivacyIssue(
                        json_field,
                        f"redacted: {','.join(applied)}",
                        redacted=True,
                    )
                )
                blocked = True
        elif isinstance(value, list):
            new_list: list[str] = []
            any_redacted = False
            applied_here: list[str] = []
            for entry in value:
                if not isinstance(entry, str):
                    new_list.append(entry)
                    continue
                new_entry, kinds = redact_text(entry)
                if kinds:
                    applied_here.extend(kinds)
                    new_list.append(new_entry)
                    any_redacted = True
                else:
                    new_list.append(entry)
            if any_redacted:
                json_list_key = json_field.lstrip("$.")
                if json_list_key in out:
                    out[json_list_key] = new_list
                issues.append(
                    PrivacyIssue(
                        json_field,
                        f"redacted: {','.join(set(applied_here))}",
                        redacted=True,
                    )
                )
                blocked = True

    for key in (
        "task",
        "decisions",
        "changes",
        "verification",
        "open_questions",
        "tags",
        "files_touched",
    ):
        if key not in out:
            continue
        value = out[key]
        if isinstance(value, str):
            new_value, truncated = truncate_event_text(value)
            if truncated:
                out[key] = new_value
                issues.append(
                    PrivacyIssue(
                        f"$.{key}",
                        "truncated (text exceeded limit)",
                        redacted=True,
                    )
                )
        elif isinstance(value, list):
            new_list = []
            any_truncated = False
            for entry in value:
                if isinstance(entry, str):
                    new_entry, truncated = truncate_event_text(entry)
                    if truncated:
                        any_truncated = True
                    new_list.append(new_entry)
                else:
                    new_list.append(entry)
            if any_truncated:
                out[key] = new_list
                issues.append(
                    PrivacyIssue(f"$.{key}", "truncated one or more strings", redacted=True)
                )

    if blocked:
        out["privacy"] = "redacted"
    elif out.get("privacy") == "raw":
        out["privacy"] = "sanitized"

    return out, tuple(issues), blocked


__all__ = [
    "DEFAULT_PATH_BLOCK_NAMES",
    "DEFAULT_PATH_BLOCK_PATTERNS",
    "DEFAULT_PRIVACY_RULES_PATH",
    "PrivacyIssue",
    "PrivacyReport",
    "REDACTED_TEXT",
    "SECRET_PATTERNS",
    "load_privacy_rules",
    "redact_text",
    "sanitize_event",
]
