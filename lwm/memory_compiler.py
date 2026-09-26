"""Memory Compiler: optional LLM-backed candidate analysis.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 5. Memory Compiler

The compiler is opt-in. When disabled, the rest of LWM-WorkMem continues to
work — candidate admission falls through to ``analysis_pending`` and other
stages run as usual. The LLM is never a hard dependency.

* The provider is loaded lazily; missing ``httpx`` is a soft no-op.
* The 7 ``LWM_ANALYSIS_*`` environment variables control behaviour.
* Localhost endpoints are allowed without an API key; remote endpoints must
  have one.
* ``temperature=0`` and only admitted, sanitized evidence is sent.
* Cache key = provider + model + prompt version + evidence hash.
* Retries at 60s / 300s / 1800s (max 3).
* API key, full input, and full output never reach wiki, events, receipts, or
  logs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from urllib.parse import urlparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from lwm import lockfile

ANALYSIS_DIR = Path("state/analysis/candidates")
TRANSITIONS_DIR = Path("state/analysis/transitions")
CACHE_DIR = Path("state/analysis/cache")
DEAD_LETTER_DIR = Path("state/analysis/dead-letter")
USAGE_PATH = Path("state/analysis/usage.json")
RETRY_DIR = Path("state/analysis/retry")

PROMPT_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_DAILY_TOKEN_BUDGET = 50_000
DEFAULT_MAX_ATTEMPTS = 3
RETRY_BACKOFF = (60, 300, 1800)
MAX_PROVIDER_RESPONSE_BYTES = 256 * 1024
PROVIDER_RESULT_FIELDS = frozenset(
    {
        "kind",
        "claim",
        "scope",
        "evidence_ids",
        "counterevidence_ids",
        "context",
        "uncertainty",
        "validity",
    }
)

CandidateState = Literal[
    "pending_analysis",
    "retry_wait",
    "analyzing",
    "analyzed",
    "accepted",
    "rejected",
    "promotion_pending",
    "promoted",
    "dead_letter",
]

VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_analysis": frozenset({"analyzing", "dead_letter"}),
    "retry_wait": frozenset({"analyzing", "dead_letter"}),
    "analyzing": frozenset({"analyzed", "retry_wait", "dead_letter"}),
    "analyzed": frozenset({"accepted", "rejected", "promotion_pending"}),
    "accepted": frozenset({"promotion_pending"}),
    "promotion_pending": frozenset({"promoted", "rejected"}),
    "rejected": frozenset(),
    "promoted": frozenset(),
    "dead_letter": frozenset(),
}


@dataclass(frozen=True)
class AnalysisConfig:
    enabled: bool
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int
    daily_token_budget: int
    max_attempts: int

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AnalysisConfig":
        env = dict(os.environ) if env is None else dict(env)
        return cls(
            enabled=str(env.get("LWM_ANALYSIS_ENABLED", "0")).strip() == "1",
            base_url=str(env.get("LWM_ANALYSIS_BASE_URL", "")).strip(),
            api_key=str(env.get("LWM_ANALYSIS_API_KEY", "")).strip(),
            model=str(env.get("LWM_ANALYSIS_MODEL", "")).strip(),
            timeout_seconds=int(
                str(env.get("LWM_ANALYSIS_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
            ),
            daily_token_budget=int(
                str(env.get("LWM_ANALYSIS_DAILY_TOKEN_BUDGET", DEFAULT_DAILY_TOKEN_BUDGET))
            ),
            max_attempts=int(
                str(env.get("LWM_ANALYSIS_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS))
            ),
        )

    def is_usable(self) -> tuple[bool, str]:
        if not self.enabled:
            return False, "analysis_disabled"
        if not self.base_url:
            return False, "missing_base_url"
        if not self.model:
            return False, "missing_model"
        hostname = urlparse(self.base_url).hostname
        is_local = hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
        if not is_local and not self.api_key:
            return False, "remote_endpoint_requires_api_key"
        return True, ""


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    kind: Literal["workflow", "relationship", "conflict", "summary"]
    claim: str
    scope: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    counterevidence_ids: tuple[str, ...] = ()
    context: str = ""
    uncertainty: str = ""
    validity: Literal["current", "time_bounded", "unknown"] = "unknown"
    state: CandidateState = "pending_analysis"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Candidate":
        return cls(
            candidate_id=str(
                payload.get("candidate_id")
                or hashlib.sha256(
                    json.dumps(payload, sort_keys=True, ensure_ascii=False).encode(
                        "utf-8"
                    )
                ).hexdigest()[:16]
            ),
            kind=payload.get("kind", "summary"),
            claim=str(payload.get("claim") or ""),
            scope=tuple(payload.get("scope") or ()),
            evidence_ids=tuple(payload.get("evidence_ids") or ()),
            counterevidence_ids=tuple(payload.get("counterevidence_ids") or ()),
            context=str(payload.get("context") or ""),
            uncertainty=str(payload.get("uncertainty") or ""),
            validity=payload.get("validity", "unknown"),
            state=payload.get("state", "pending_analysis"),
            created_at=str(payload.get("created_at") or _now()),
        )


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return root / ANALYSIS_DIR / f"{candidate_id}.json"


def _transition_path(root: Path, candidate_id: str) -> Path:
    return root / TRANSITIONS_DIR / f"{candidate_id}.jsonl"


def _cache_path(root: Path, *, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return root / CACHE_DIR / f"{digest}.json"


def save_candidate(root: Path, candidate: Candidate) -> Path:
    target = _candidate_path(root, candidate.candidate_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def load_candidate(root: Path, candidate_id: str) -> Candidate | None:
    path = _candidate_path(root, candidate_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return Candidate.from_dict(payload)


def seed_candidate(root: Path, candidate: Candidate) -> Path:
    """Create an analysis candidate without resetting an existing state."""

    target = _candidate_path(root, candidate.candidate_id)
    if load_candidate(root, candidate.candidate_id) is not None:
        return target
    return save_candidate(root, candidate)


def review_analysis_candidate(
    root: Path,
    candidate_id: str,
    *,
    decision: Literal["accept", "reject", "promote"],
    actor: str = "human",
) -> Candidate:
    """Apply a human review decision to a validated compiler candidate."""

    candidate = load_candidate(root, candidate_id)
    if candidate is None:
        raise FileNotFoundError(candidate_id)
    target_state = {
        "accept": "accepted",
        "reject": "rejected",
        "promote": "promotion_pending",
    }[decision]
    if candidate.state == target_state:
        return candidate
    if target_state not in VALID_TRANSITIONS.get(candidate.state, frozenset()):
        raise ValueError(f"invalid analysis review: {candidate.state}->{target_state}")
    reviewed = Candidate.from_dict({**candidate.to_dict(), "state": target_state})
    evidence_hash = _hash_evidence(
        [{"event_id": event_id} for event_id in candidate.evidence_ids]
    )
    save_candidate(root, reviewed)
    record_transition(
        root,
        candidate_id,
        from_state=candidate.state,
        to_state=target_state,
        note=f"human review: {decision}",
        evidence_hash=evidence_hash,
        actor=actor,
    )
    return reviewed


def load_accepted_analysis_candidates(root: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return only human-accepted compiler candidates for bounded Context."""

    base = root / ANALYSIS_DIR
    if not base.is_dir():
        return []
    accepted: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        candidate = load_candidate(root, path.stem)
        if candidate is None or candidate.state != "accepted":
            continue
        accepted.append(
            {
                "candidate_id": candidate.candidate_id,
                "kind": candidate.kind,
                "claim": candidate.claim[:1200],
                "scope": list(candidate.scope),
                "evidence_ids": list(candidate.evidence_ids),
                "context": candidate.context[:1600],
                "uncertainty": candidate.uncertainty[:800],
                "validity": candidate.validity,
                "state": candidate.state,
            }
        )
        if len(accepted) >= limit:
            break
    return accepted


def record_transition(
    root: Path,
    candidate_id: str,
    *,
    from_state: str,
    to_state: str,
    note: str = "",
    evidence_hash: str = "",
    actor: str = "memory-compiler",
) -> None:
    """Append a transition record. The full input/output is never logged."""

    if to_state not in VALID_TRANSITIONS.get(from_state, frozenset()):
        raise ValueError(f"invalid candidate transition: {from_state}->{to_state}")

    target = _transition_path(root, candidate_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "at": _now(),
                    "candidate_id": candidate_id,
                    "from": from_state,
                    "to": to_state,
                    "note": note,
                    "evidence_hash": evidence_hash,
                    "actor": actor,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


# Validation

FORBIDDEN_PATTERNS = (
    r"\bcauses?\b",
    r"\bbecause of\b",
    r"\balways\b",
    r"\bnever\b",
    r"only by",
    r"<REDACTED>",
)
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def validate_candidate(
    candidate: Candidate,
    *,
    known_event_ids: Iterable[str],
) -> tuple[bool, str]:
    known = set(known_event_ids)
    if not candidate.claim.strip():
        return False, "empty_claim"
    if candidate.kind not in {"workflow", "relationship", "conflict", "summary"}:
        return False, f"unknown_kind:{candidate.kind}"
    if candidate.validity not in {"current", "time_bounded", "unknown"}:
        return False, f"unknown_validity:{candidate.validity}"
    if not candidate.evidence_ids:
        return False, "no_evidence_ids"
    missing = [eid for eid in candidate.evidence_ids if eid not in known]
    if missing:
        return False, f"fabricated_evidence:{','.join(missing[:3])}"
    overlap = set(candidate.evidence_ids) & set(candidate.counterevidence_ids)
    if overlap:
        return False, f"id_both_claim_and_counter:{','.join(overlap)}"

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, candidate.claim, re.IGNORECASE):
            return False, f"forbidden_pattern:{pattern}"
    for pattern in _SECRET_PATTERNS:
        if pattern.search(candidate.claim):
            return False, "secret_in_claim"
    return True, ""


def validate_provider_payload(
    payload: dict[str, Any], *, candidate: Candidate
) -> tuple[bool, str]:
    """Validate provider output before it can update a candidate."""

    unknown = sorted(set(payload) - PROVIDER_RESULT_FIELDS)
    if unknown:
        return False, f"unsupported_provider_fields:{','.join(unknown[:3])}"
    if "kind" in payload and payload["kind"] not in {
        "workflow",
        "relationship",
        "conflict",
        "summary",
    }:
        return False, "invalid_provider_kind"
    if "claim" in payload and (
        not isinstance(payload["claim"], str) or not payload["claim"].strip()
    ):
        return False, "invalid_provider_claim"
    for field in ("context", "uncertainty"):
        if field in payload and not isinstance(payload[field], str):
            return False, f"invalid_provider_{field}"
    if "validity" in payload and payload["validity"] not in {
        "current",
        "time_bounded",
        "unknown",
    }:
        return False, "invalid_provider_validity"

    for field, expected in (
        ("scope", set(candidate.scope)),
        ("evidence_ids", set(candidate.evidence_ids)),
    ):
        if field not in payload:
            continue
        value = payload[field]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return False, f"invalid_provider_{field}"
        if set(value) != expected:
            return False, f"provider_{field}_drift"

    if "counterevidence_ids" in payload:
        value = payload["counterevidence_ids"]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return False, "invalid_provider_counterevidence_ids"
        if not set(value).issubset(set(candidate.counterevidence_ids)):
            return False, "provider_counterevidence_drift"
    return True, ""


# Provider (lazy)

def cache_key_for(
    config: AnalysisConfig, *, evidence_hash: str, prompt_version: int = PROMPT_VERSION
) -> str:
    return json.dumps(
        {
            "base": config.base_url,
            "model": config.model,
            "version": prompt_version,
            "evidence": evidence_hash,
        },
        sort_keys=True,
    )


def _read_cached(root: Path, *, key: str) -> dict[str, Any] | None:
    path = _cache_path(root, key=key)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cached(root: Path, *, key: str, payload: dict[str, Any]) -> None:
    path = _cache_path(root, key=key)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in payload.items() if k != "api_key"}
    path.write_text(
        json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _hash_evidence(items: Iterable[Any]) -> str:
    material = json.dumps(list(items), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


_PROVIDER_EVIDENCE_FIELDS = frozenset(
    {
        "event_id",
        "event_type",
        "tool",
        "project_id",
        "timestamp",
        "task",
        "decisions",
        "changes",
        "verification",
        "risks",
        "open_questions",
    }
)
_SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})"
)


def _redact_text(value: str, *, max_chars: int = 800) -> str:
    return _SECRET_RE.sub("<REDACTED>", value[:max_chars])


def sanitize_evidence(evidence: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the smallest provider-safe projection of admitted evidence."""

    output: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        clean: dict[str, Any] = {}
        for key in _PROVIDER_EVIDENCE_FIELDS:
            if key not in item:
                continue
            value = item[key]
            if isinstance(value, str):
                clean[key] = _redact_text(value)
            elif isinstance(value, list):
                clean[key] = [_redact_text(str(entry)) for entry in value[:12]]
            elif isinstance(value, (int, float, bool)) or value is None:
                clean[key] = value
        output.append(clean)
    return output


def estimate_tokens(*items: Any) -> int:
    """Conservative local estimate used only for the daily safety budget."""

    material = json.dumps(items, ensure_ascii=False, sort_keys=True)
    return max(1, (len(material) + 3) // 4)


def reserve_daily_budget(root: Path, *, token_count: int, budget: int) -> bool:
    """Atomically reserve a daily token allowance for optional analysis."""

    path = root / USAGE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        payload = {}
    if not isinstance(payload, dict) or payload.get("date") != today:
        payload = {"date": today, "used_tokens": 0}
    used = int(payload.get("used_tokens") or 0)
    if token_count < 0 or used + token_count > max(0, budget):
        return False
    payload["used_tokens"] = used + token_count
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def reconcile_daily_budget(
    root: Path, *, reserved_tokens: int, actual_tokens: int
) -> None:
    """Replace a conservative reservation with provider-reported usage."""

    if reserved_tokens < 0 or actual_tokens < 0:
        return
    path = root / USAGE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return
    today = datetime.now(timezone.utc).date().isoformat()
    if not isinstance(payload, dict) or payload.get("date") != today:
        return
    used = int(payload.get("used_tokens") or 0)
    payload["used_tokens"] = max(0, used - reserved_tokens + actual_tokens)
    payload["last_actual_tokens"] = actual_tokens
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _actual_usage_tokens(payload: dict[str, Any]) -> int | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    total = usage.get("total_tokens")
    return total if isinstance(total, int) and total >= 0 else None


def classify_with_provider(
    config: AnalysisConfig,
    *,
    prompt: str,
    evidence: list[dict[str, Any]],
    cache_root: Path,
    reserved_tokens: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Call the configured LLM provider or return ``(None, reason)``."""

    usable, reason = config.is_usable()
    if not usable:
        return None, reason

    safe_evidence = sanitize_evidence(evidence)
    safe_prompt = _redact_text(prompt, max_chars=4000)
    key = cache_key_for(config, evidence_hash=_hash_evidence(safe_evidence))
    cached = _read_cached(cache_root, key=key)
    if cached is not None:
        return cached, "cache_hit"

    try:
        import httpx  # type: ignore
    except ImportError:
        return None, "provider_unavailable"

    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    body = {
        "model": config.model,
        "temperature": 0,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You classify project events."},
            {"role": "user", "content": safe_prompt},
        ],
    }
    last_error = ""
    for attempt in range(1, config.max_attempts + 1):
        try:
            response = httpx.post(
                f"{config.base_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
                timeout=config.timeout_seconds,
            )
        except (httpx.HTTPError, OSError) as exc:
            last_error = f"http:{type(exc).__name__}"
            if attempt < config.max_attempts:
                time.sleep(RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)])
            continue
        if response.status_code >= 500:
            last_error = f"status:{response.status_code}"
            if attempt < config.max_attempts:
                time.sleep(RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)])
            continue
        if response.status_code >= 400:
            return None, f"status:{response.status_code}"
        try:
            raw_content = getattr(response, "content", b"")
            if isinstance(raw_content, (bytes, bytearray)) and len(raw_content) > MAX_PROVIDER_RESPONSE_BYTES:
                return None, "response_too_large"
            data = response.json()
        except ValueError:
            return None, "invalid_json"
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None, "invalid_payload"
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_PROVIDER_RESPONSE_BYTES:
            return None, "response_too_large"
        try:
            parsed = json.loads(content)
        except (ValueError, TypeError):
            return None, "invalid_payload"
        if not isinstance(parsed, dict):
            return None, "invalid_payload_shape"
        actual_tokens = _actual_usage_tokens(data)
        if reserved_tokens is not None and actual_tokens is not None:
            reconcile_daily_budget(
                cache_root,
                reserved_tokens=reserved_tokens,
                actual_tokens=actual_tokens,
            )
        _write_cached(cache_root, key=key, payload=parsed)
        return parsed, ""

    return None, last_error or "exhausted"


def _load_processed_event_index(root: Path) -> dict[str, dict[str, Any]]:
    base = root / "raw" / "events" / "processed"
    index: dict[str, dict[str, Any]] = {}
    if not base.is_dir():
        return index
    for path in base.rglob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and payload.get("event_id"):
            index[str(payload["event_id"])] = payload
    return index


def _retry_path(root: Path, candidate_id: str) -> Path:
    return root / RETRY_DIR / f"{candidate_id}.json"


def _retry_state(root: Path, candidate_id: str) -> dict[str, Any]:
    path = _retry_path(root, candidate_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"attempts": 0}
    return payload if isinstance(payload, dict) else {"attempts": 0}


def _save_retry_state(root: Path, candidate_id: str, payload: dict[str, Any]) -> None:
    path = _retry_path(root, candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dead_letter(root: Path, candidate: Candidate, *, reason: str) -> None:
    dead = root / DEAD_LETTER_DIR / f"{candidate.candidate_id}.json"
    dead.parent.mkdir(parents=True, exist_ok=True)
    dead.write_text(
        json.dumps(
            {"candidate": candidate.to_dict(), "reason": reason, "at": _now()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _analyze_pending_unlocked(
    root: Path,
    *,
    config: AnalysisConfig | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Analyze pending candidates without making analysis a core dependency."""

    root = root.resolve()
    config = config or AnalysisConfig.from_env()
    reference = now or datetime.now(timezone.utc)
    events = _load_processed_event_index(root)
    report: dict[str, Any] = {
        "status": "disabled" if not config.enabled else "ok",
        "analyzed": [],
        "deferred": [],
        "dead_letter": [],
        "errors": [],
    }
    if not config.enabled:
        return report
    for path in sorted((root / ANALYSIS_DIR).glob("*.json")):
        candidate = load_candidate(root, path.stem)
        if candidate is None or candidate.state not in {"pending_analysis", "retry_wait"}:
            continue
        evidence = [events[eid] for eid in candidate.evidence_ids if eid in events]
        evidence_hash = _hash_evidence(sanitize_evidence(evidence))
        retry = _retry_state(root, candidate.candidate_id)
        retry_at = str(retry.get("retry_at") or "")
        if retry_at:
            try:
                if datetime.fromisoformat(retry_at.replace("Z", "+00:00")) > reference:
                    if candidate.state != "retry_wait":
                        waiting = Candidate.from_dict(
                            {**candidate.to_dict(), "state": "retry_wait"}
                        )
                        save_candidate(root, waiting)
                        record_transition(
                            root,
                            candidate.candidate_id,
                            from_state=candidate.state,
                            to_state="retry_wait",
                            note="waiting for bounded retry window",
                            evidence_hash=evidence_hash,
                        )
                    report["deferred"].append(candidate.candidate_id)
                    continue
            except ValueError:
                pass
        if not evidence:
            updated = Candidate.from_dict({**candidate.to_dict(), "state": "dead_letter"})
            save_candidate(root, updated)
            record_transition(
                root,
                candidate.candidate_id,
                from_state=candidate.state,
                to_state="dead_letter",
                note="no admitted evidence",
                evidence_hash=evidence_hash,
            )
            _dead_letter(root, updated, reason="no_admitted_evidence")
            report["dead_letter"].append(candidate.candidate_id)
            continue

        prompt = (
            "Return one JSON candidate using only the supplied evidence. "
            "Do not invent evidence ids, causes, permanent identities, or secrets.\n"
            + json.dumps(sanitize_evidence(evidence), ensure_ascii=False)
        )
        reserved_tokens = estimate_tokens(prompt) + 1200
        if not reserve_daily_budget(
            root, token_count=reserved_tokens, budget=config.daily_token_budget
        ):
            report["deferred"].append(candidate.candidate_id)
            report["errors"].append(f"budget_exceeded:{candidate.candidate_id}")
            break

        record_transition(
            root,
            candidate.candidate_id,
            from_state=candidate.state,
            to_state="analyzing",
            note="dispatched",
            evidence_hash=evidence_hash,
        )
        result, reason = classify_with_provider(
            config,
            prompt=prompt,
            evidence=evidence,
            cache_root=root,
            reserved_tokens=reserved_tokens,
        )
        if result is None:
            attempts = int(retry.get("attempts") or 0) + 1
            if attempts >= config.max_attempts:
                updated = Candidate.from_dict({**candidate.to_dict(), "state": "dead_letter"})
                save_candidate(root, updated)
                record_transition(
                    root,
                    candidate.candidate_id,
                    from_state="analyzing",
                    to_state="dead_letter",
                    note=reason,
                    evidence_hash=evidence_hash,
                )
                _dead_letter(root, updated, reason=reason)
                report["dead_letter"].append(candidate.candidate_id)
            else:
                next_retry = reference.timestamp() + RETRY_BACKOFF[min(attempts - 1, len(RETRY_BACKOFF) - 1)]
                _save_retry_state(
                    root,
                    candidate.candidate_id,
                    {"attempts": attempts, "retry_at": datetime.fromtimestamp(next_retry, timezone.utc).isoformat(), "reason": reason},
                )
                save_candidate(root, Candidate.from_dict({**candidate.to_dict(), "state": "retry_wait"}))
                record_transition(
                    root,
                    candidate.candidate_id,
                    from_state="analyzing",
                    to_state="retry_wait",
                    note=reason,
                    evidence_hash=evidence_hash,
                )
                report["deferred"].append(candidate.candidate_id)
            continue

        provider_valid, provider_reason = validate_provider_payload(
            result, candidate=candidate
        )
        if not provider_valid:
            updated = Candidate.from_dict({**candidate.to_dict(), "state": "dead_letter"})
            save_candidate(root, updated)
            record_transition(
                root,
                candidate.candidate_id,
                from_state="analyzing",
                to_state="dead_letter",
                note=provider_reason,
                evidence_hash=evidence_hash,
            )
            _dead_letter(root, updated, reason=provider_reason)
            report["dead_letter"].append(candidate.candidate_id)
            continue

        proposed = Candidate.from_dict(
            {
                **candidate.to_dict(),
                **{key: value for key, value in result.items() if key in {"kind", "claim", "context", "uncertainty", "validity"}},
                "evidence_ids": list(candidate.evidence_ids),
                "counterevidence_ids": list(candidate.counterevidence_ids),
                "state": "analyzed",
            }
        )
        valid, validation_reason = validate_candidate(proposed, known_event_ids=events.keys())
        if not valid:
            updated = Candidate.from_dict({**candidate.to_dict(), "state": "dead_letter"})
            save_candidate(root, updated)
            record_transition(
                root,
                candidate.candidate_id,
                from_state="analyzing",
                to_state="dead_letter",
                note=validation_reason,
                evidence_hash=evidence_hash,
            )
            _dead_letter(root, updated, reason=validation_reason)
            report["dead_letter"].append(candidate.candidate_id)
            continue
        save_candidate(root, proposed)
        record_transition(
            root,
            candidate.candidate_id,
            from_state="analyzing",
            to_state="analyzed",
            note="validated provider result",
            evidence_hash=evidence_hash,
        )
        report["analyzed"].append(candidate.candidate_id)
    return report


def analyze_pending(
    root: Path,
    *,
    config: AnalysisConfig | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Analyze candidates behind the shared cycle writer boundary."""

    root = root.resolve()
    try:
        with lockfile.cycle_lock(root):
            return _analyze_pending_unlocked(root, config=config, now=now)
    except lockfile.CycleLockBusyError as exc:
        return {
            "status": "analysis_pending",
            "analyzed": [],
            "deferred": [],
            "dead_letter": [],
            "errors": ["cycle_lock_unavailable" if exc.error else "cycle_lock_busy"],
        }


__all__ = [
    "ANALYSIS_DIR",
    "CACHE_DIR",
    "DEAD_LETTER_DIR",
    "AnalysisConfig",
    "Candidate",
    "CandidateState",
    "PROMPT_VERSION",
    "VALID_TRANSITIONS",
    "TRANSITIONS_DIR",
    "cache_key_for",
    "classify_with_provider",
    "analyze_pending",
    "estimate_tokens",
    "load_candidate",
    "load_accepted_analysis_candidates",
    "record_transition",
    "reconcile_daily_budget",
    "reserve_daily_budget",
    "sanitize_evidence",
    "save_candidate",
    "seed_candidate",
    "review_analysis_candidate",
    "validate_provider_payload",
    "validate_candidate",
]
