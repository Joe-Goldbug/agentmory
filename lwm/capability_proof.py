"""Capability proof receipts.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Architecture And Interfaces / 3. Event And Handoff Contracts
      -> Implementation Changes / 3. Tool Registry

A proof receipt carries real evidence — tool, project, operation, timestamp
and an evidence path — that the named tool actually performed the named
operation. Watcher observations and CLI inspection are *observation* receipts
and can never be promoted to ``verified_*`` status.
"""

from __future__ import annotations

try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - POSIX has no msvcrt
    msvcrt = None

import json
import re
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


from lwm.tool_registry import ToolCoverage as ToolCoverageLike  # noqa: E402  (late-bound to break circular import)


PROOF_RECEIPT_SOURCES = frozenset(
    {
        "native-hook",
        "lifecycle-hook",
        "ide-extension",
        "mcp-bridge",
    }
)
OBSERVATION_RECEIPT_SOURCES = frozenset(
    {"watcher-observed", "cli-context", "file-probe", "explicit-smoke"}
)
ALL_RECEIPT_SOURCES = PROOF_RECEIPT_SOURCES | OBSERVATION_RECEIPT_SOURCES

DEFAULT_PROOF_WINDOW = timedelta(days=14)
MAX_HISTORY = 250

# Capability freshness describes host/source activity, not a hand-written
# decision or verification record. Keep this allowlist aligned with lifecycle
# and bounded observation events so audit write-backs cannot fake capture.
CAPTURE_EVENT_TYPES = frozenset(
    {
        "session_start",
        "session_summary",
        "session_end",
        "checkpoint",
        "workflow_observation",
        "adapter_probe",
    }
)

RECEIPTS_PATH = Path("state/capability-receipts.json")
TOOL_RECEIPTS_PATH = Path("state/receipts/tools")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _latest_capture(
    root: Path,
    *,
    tool: str,
    expected_project_id: str | None,
) -> str | None:
    """Find the newest source event without treating a receipt as capture proof."""

    candidates: list[tuple[datetime, str]] = []
    for bucket in (root / "raw" / "events" / "inbox", root / "raw" / "events" / "processed"):
        if not bucket.is_dir():
            continue
        for path in bucket.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or str(payload.get("tool") or "") != tool:
                continue
            if str(payload.get("event_type") or "") not in CAPTURE_EVENT_TYPES:
                continue
            if expected_project_id and payload.get("project_id") != expected_project_id:
                continue
            timestamp = str(payload.get("timestamp") or payload.get("observed_at") or "")
            parsed = _parse_timestamp(timestamp)
            if parsed is not None:
                candidates.append((parsed, timestamp))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _capture_freshness(timestamp: str | None) -> str:
    if not timestamp:
        return "missing"
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return "unknown"
    return "fresh" if datetime.now(timezone.utc) - parsed <= DEFAULT_PROOF_WINDOW else "stale"


@dataclass(frozen=True)
class ProofReceipt:
    tool: str
    direction: str  # "read" or "write"
    project_id: str | None
    source: str
    evidence_path: str
    operation_id: str
    timestamp: str
    status: str = "verified"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProofReceipt":
        return cls(
            tool=str(payload.get("tool") or ""),
            direction=str(payload.get("direction") or ""),
            project_id=(
                str(payload["project_id"])
                if payload.get("project_id") is not None
                else None
            ),
            source=str(payload.get("source") or "unknown"),
            evidence_path=str(payload.get("evidence_path") or ""),
            operation_id=str(payload.get("operation_id") or ""),
            timestamp=str(payload.get("timestamp") or payload.get("recorded_at") or _now()),
            status=str(payload.get("status") or "verified"),
            detail=str(payload.get("detail") or ""),
        )


def _coerce(payload: dict[str, Any]) -> ProofReceipt:
    return ProofReceipt.from_dict(payload)


def _payload_path(root: Path) -> Path:
    return root / RECEIPTS_PATH


def _evidence_file(root: Path, evidence_path: str) -> Path | None:
    """Resolve evidence without accepting a path string as proof."""

    raw = str(evidence_path or "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    root_resolved = root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (root_resolved / candidate).resolve()
    try:
        relative = resolved.relative_to(root_resolved)
    except ValueError:
        return None
    if resolved.is_file():
        return resolved

    # Lifecycle evidence starts in raw/events/inbox and is later moved to
    # processed or rejected. Keep the proof bound to the same unique event
    # file without treating arbitrary relocated paths as evidence.
    if relative.parts[:2] != ("raw", "events") or not relative.name.endswith(".json"):
        return None
    event_root = root_resolved / "raw" / "events"
    matches = tuple(path for path in event_root.rglob(relative.name) if path.is_file())
    return matches[0] if len(matches) == 1 else None


def _receipt_has_evidence(root: Path, receipt: dict[str, Any]) -> bool:
    return _evidence_file(root, str(receipt.get("evidence_path") or "")) is not None


def validate_host_proof(
    root: Path,
    *,
    tool: str,
    phase: str,
    source: str,
    session_id: str | None,
    host_proof: Mapping[str, Any] | None,
) -> dict[str, str] | None:
    """Validate the host binding required before a lifecycle proof claim.

    A caller may still forge arbitrary JSON, so this is not cryptographic
    attestation. It does prevent generic bridge traffic from casually
    relabeling itself as a native integration and leaves the integration/event
    binding in the lifecycle event for audit.
    """

    if source not in PROOF_RECEIPT_SOURCES:
        return None
    if phase not in {"start", "stop"}:
        raise ValueError("proof sources are only valid for start or stop")
    if not isinstance(host_proof, Mapping):
        raise ValueError("host_proof is required for a proof source")
    integration = host_proof.get("integration")
    event = host_proof.get("event")
    if not isinstance(integration, str) or not integration.strip():
        raise ValueError("host_proof.integration is required")
    if not isinstance(event, str) or not event.strip():
        raise ValueError("host_proof.event is required")

    from lwm.tool_registry import ToolRegistry

    definition = ToolRegistry.load(root.resolve()).resolve(tool)
    allowed = definition.proof_integrations if definition is not None else ()
    if integration.strip() not in allowed:
        raise ValueError(
            f"host proof integration is not registered for {tool}: {integration.strip()}"
        )

    proof_session_id = host_proof.get("session_id")
    if proof_session_id is not None and (
        not isinstance(proof_session_id, str) or not proof_session_id.strip()
    ):
        raise ValueError("host_proof.session_id must be a non-empty string")
    if session_id and proof_session_id != session_id:
        raise ValueError("host_proof.session_id must match session_id")
    if proof_session_id and not session_id:
        raise ValueError("session_id is required when host_proof.session_id is set")
    normalized = {
        "schema_version": "1",
        "integration": integration.strip(),
        "event": event.strip(),
    }
    if proof_session_id:
        normalized["session_id"] = proof_session_id.strip()
    return normalized


def _safe_path_component(value: str, *, fallback: str) -> str:
    """Keep receipt filenames inside the per-tool receipt directory."""

    raw = value.strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-")
    if not safe or safe in {".", ".."}:
        return fallback
    return safe[:160]


def load(root: Path) -> dict[str, Any]:
    path = _payload_path(root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save(root: Path, payload: dict[str, Any]) -> None:
    path = _payload_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@contextmanager
def _receipt_lock(root: Path):
    """Serialize aggregate receipt updates across concurrent host hooks."""

    path = _payload_path(root).with_name("capability-receipts.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        elif msvcrt is not None:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - 无可用锁实现时退化为不加锁
            yield


def record(
    root: Path,
    *,
    tool: str,
    direction: str,
    project_id: str | None,
    source: str,
    evidence_path: str,
    operation_id: str,
    detail: str = "",
) -> ProofReceipt:
    """Append a proof receipt to the durable receipt store.

    The single ``status`` field on the receipt reflects whether the
    ``source`` qualifies as a proof source. ``watcher-observed`` and other
    observation sources stay ``observed_*`` and never reach ``verified_*``.
    """

    if direction not in {"read", "write"}:
        raise ValueError("direction must be read or write")
    if source not in ALL_RECEIPT_SOURCES:
        raise ValueError(f"unknown source: {source}")

    normalized_operation_id = operation_id.strip() or f"observation:{uuid.uuid4().hex}"
    has_evidence = _evidence_file(root, evidence_path) is not None and bool(
        normalized_operation_id.strip()
    )
    qualifies_as_proof = source in PROOF_RECEIPT_SOURCES and has_evidence
    receipt = ProofReceipt(
        tool=tool,
        direction=direction,
        project_id=project_id,
        source=source,
        evidence_path=evidence_path,
        operation_id=normalized_operation_id,
        timestamp=_now(),
        status="verified" if qualifies_as_proof else "observed",
        detail=(
            detail
            if has_evidence or source not in PROOF_RECEIPT_SOURCES
            else f"{detail}; evidence file missing or outside root".strip("; ")
        ),
    )

    safe_tool = _safe_path_component(tool, fallback="unknown-tool")
    safe_operation = _safe_path_component(
        normalized_operation_id, fallback=f"operation-{uuid.uuid4().hex[:8]}"
    )
    with _receipt_lock(root):
        payload = load(root)
        history = payload.get("_history")
        if not isinstance(history, dict):
            history = {}
        bucket = history.setdefault(tool, [])
        if not isinstance(bucket, list):
            bucket = []
        bucket = [
            item
            for item in bucket
            if not (
                isinstance(item, dict)
                and item.get("direction") == direction
                and item.get("project_id") == project_id
                and item.get("source") == source
                and item.get("operation_id") == normalized_operation_id
            )
        ]
        bucket.append(receipt.to_dict())
        history[tool] = bucket[-MAX_HISTORY:]
        payload["_history"] = history
        payload[tool] = receipt.to_dict()
        save(root, payload)

        per_tool = root / TOOL_RECEIPTS_PATH / safe_tool
        per_tool.mkdir(parents=True, exist_ok=True)
        (per_tool / f"{safe_operation}.json").write_text(
            json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return receipt


def is_proof_source(source: str) -> bool:
    return source in PROOF_RECEIPT_SOURCES


def is_within_window(
    receipt: ProofReceipt | dict[str, Any],
    *,
    window: timedelta = DEFAULT_PROOF_WINDOW,
    now: datetime | None = None,
) -> bool:
    data = receipt if isinstance(receipt, dict) else receipt.to_dict()
    try:
        recorded = datetime.fromisoformat(
            str(data.get("timestamp") or data.get("recorded_at") or "").replace(
                "Z", "+00:00"
            )
        )
    except (KeyError, TypeError, ValueError):
        return False
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    return recorded >= reference - window


def latest_proof_receipts(
    root: Path,
    *,
    tool: str,
    expected_project_id: str | None = None,
) -> tuple[ProofReceipt | None, ProofReceipt | None]:
    """Return the most recent proof receipts for read/write, project-scoped."""

    payload = load(root)
    history = payload.get("_history")
    entries_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    aggregate_entries: list[dict[str, Any]] = []
    if isinstance(history, dict) and isinstance(history.get(tool), list):
        aggregate_entries.extend(item for item in history[tool] if isinstance(item, dict))
    current = payload.get(tool)
    if isinstance(current, dict):
        aggregate_entries.append(current)

    per_tool = root / TOOL_RECEIPTS_PATH / _safe_path_component(tool, fallback="unknown-tool")
    if per_tool.is_dir():
        for path in per_tool.glob("*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(item, dict):
                aggregate_entries.append(item)

    for item in aggregate_entries:
        key = (
            str(item.get("direction") or ""),
            str(item.get("project_id") or ""),
            str(item.get("source") or ""),
            str(item.get("operation_id") or ""),
        )
        previous = entries_by_key.get(key)
        if previous is None or str(item.get("timestamp") or "") >= str(
            previous.get("timestamp") or ""
        ):
            entries_by_key[key] = item
    entries = list(entries_by_key.values())

    scoped = [
        item
        for item in entries
        if item.get("source") in PROOF_RECEIPT_SOURCES
        and item.get("status") == "verified"
        and bool(str(item.get("evidence_path") or "").strip())
        and bool(str(item.get("operation_id") or "").strip())
        and _receipt_has_evidence(root, item)
        and (
            expected_project_id is None
            or item.get("project_id") == expected_project_id
        )
    ]
    reads = max(
        (
            item
            for item in scoped
            if item.get("direction") == "read"
        ),
        key=lambda item: str(item.get("timestamp") or item.get("recorded_at") or ""),
        default=None,
    )
    writes = max(
        (
            item
            for item in scoped
            if item.get("direction") == "write"
        ),
        key=lambda item: str(item.get("timestamp") or item.get("recorded_at") or ""),
        default=None,
    )
    return (
        _coerce(reads) if reads else None,
        _coerce(writes) if writes else None,
    )


def capability_status(
    *,
    read_receipt: ProofReceipt | dict[str, Any] | None,
    write_receipt: ProofReceipt | dict[str, Any] | None,
    expected_project_id: str | None,
) -> str:
    """Compute the truthful capability status for one tool.

    A receipt is only *proof* when it carries a qualifying source and lives
    inside the freshness window. ``watcher-observed`` and friends stay
    ``observed_*`` and never appear as ``verified_*``.

    A receipt that exists but belongs to a different project is ignored: the
    caller is asking about one specific project, so an unrelated observation
    must not bleed into that project's status.
    """

    def data_of(receipt: object) -> dict[str, Any] | None:
        if receipt is None:
            return None
        if isinstance(receipt, dict):
            return receipt
        return receipt.to_dict()

    def project_match(data: dict[str, Any]) -> bool:
        return (
            expected_project_id is None
            or data.get("project_id") == expected_project_id
        )

    read = data_of(read_receipt)
    write = data_of(write_receipt)
    read_match = read is not None and project_match(read)
    write_match = write is not None and project_match(write)

    def qualifies(data: dict[str, Any]) -> bool:
        return (
            data.get("source") in PROOF_RECEIPT_SOURCES and is_within_window(data)
            and data.get("status") == "verified"
            and bool(str(data.get("evidence_path") or "").strip())
            and bool(str(data.get("operation_id") or "").strip())
        )

    if read_match and qualifies(read) and write_match and qualifies(write):
        return "verified_bidirectional"
    if read_match and qualifies(read):
        return "verified_read"
    if write_match and qualifies(write):
        return "verified_write"
    if read_match and write_match and not (qualifies(read) or qualifies(write)):
        return "observed_read_only"
    if read_match and not qualifies(read):
        return "observed_read"
    if write_match and not qualifies(write):
        return "observed_write"
    return "configured_unverified"


def coverage_for_tool(
    root: Path,
    *,
    tool: str,
    expected_project_id: str | None,
    configured: bool,
    host_probe: Mapping[str, Any] | None = None,
) -> ToolCoverageLike:
    """Build a :class:`ToolCoverage` view from the receipt store.

    Imported lazily to avoid a circular dependency on ``tool_registry``.
    """

    from lwm.tool_registry import ToolCoverage

    capture_at = _latest_capture(
        root,
        tool=tool,
        expected_project_id=expected_project_id,
    )
    read, write = latest_proof_receipts(
        root, tool=tool, expected_project_id=expected_project_id
    )
    status = capability_status(
        read_receipt=read,
        write_receipt=write,
        expected_project_id=expected_project_id,
    )
    gaps: list[str] = []
    if not configured:
        gaps.append("not_configured")
    if capture_at is None:
        gaps.append("no_capture_event")
    elif _capture_freshness(capture_at) == "stale":
        gaps.append("stale_capture")
    if status == "configured_unverified":
        gaps.append("no_proof_receipts")
    if status.startswith("observed_"):
        gaps.append("observation_only")
    status_reason = _coverage_reason(
        status=status,
        configured=configured,
        gaps=tuple(gaps),
        host_probe=host_probe,
    )
    return ToolCoverage(
        tool_id=tool,
        status=_coverage_status(status, configured),
        capture_status=("ok" if capture_at else "awaiting_first_event") if configured else "missing",
        delivery_status=status,
        read_status=read.status if read else "missing",
        write_status=write.status if write else "missing",
        last_capture_at=capture_at,
        capture_freshness=_capture_freshness(capture_at),
        last_read_at=read.timestamp if read else None,
        last_write_at=write.timestamp if write else None,
        gaps=tuple(gaps),
        status_reason=status_reason,
    )


def _coverage_reason(
    *,
    status: str,
    configured: bool,
    gaps: tuple[str, ...],
    host_probe: Mapping[str, Any] | None,
) -> str:
    """Explain coverage in plain language without promoting weak evidence."""

    if status == "verified_bidirectional":
        return "Real host read and write proof are present within the freshness window."
    if status.startswith("verified_"):
        return "Only one direction has qualifying host proof; the other direction is still missing."
    if not configured:
        return "LLM-WorkMem is not configured for this tool on the current host."
    if "observation_only" in gaps:
        return "Only watcher or observer evidence exists; it cannot become host proof."

    probe_status = str((host_probe or {}).get("status") or "")
    if probe_status == "not_found":
        return "Configuration exists, but the tool host was not found on this machine."
    if "no_capture_event" in gaps:
        if probe_status == "app_present":
            return "The app is present; waiting for its first real lifecycle event."
        return "Configuration exists; waiting for the tool to emit its first real lifecycle event."
    if "stale_capture" in gaps:
        return "A host capture exists, but it is stale; a fresh lifecycle event is required."
    if "no_proof_receipts" in gaps:
        if probe_status == "app_present":
            return "The app is present, but no qualifying read/write host proof exists yet."
        if probe_status == "available":
            return "The host is available, but no qualifying read/write proof exists yet."
        return "The tool is configured, but no qualifying read/write host proof exists yet."
    if status.startswith("observed_"):
        return "The tool is observed locally, but the current evidence is not host proof."
    return "Coverage is configured but not yet proven end to end."


# Late-bound to break a circular import: tool_registry.ToolCoverage is the
# canonical dataclass.


def _coverage_status(
    proof_status: str, configured: bool
) -> ToolCoverageLike.status:  # type: ignore[valid-type]
    if proof_status == "verified_bidirectional":
        return "supported"
    if proof_status.startswith("verified_") or configured:
        return "partially_supported"
    if not configured:
        return "unsupported"
    return "pending_integration"


def iter_history(root: Path) -> Iterable[dict[str, Any]]:
    payload = load(root)
    history = payload.get("_history")
    if not isinstance(history, dict):
        return ()
    for tool_entries in history.values():
        if isinstance(tool_entries, list):
            for item in tool_entries:
                if isinstance(item, dict):
                    yield item


__all__ = [
    "ALL_RECEIPT_SOURCES",
    "CAPTURE_EVENT_TYPES",
    "DEFAULT_PROOF_WINDOW",
    "MAX_HISTORY",
    "OBSERVATION_RECEIPT_SOURCES",
    "PROOF_RECEIPT_SOURCES",
    "ProofReceipt",
    "RECEIPTS_PATH",
    "TOOL_RECEIPTS_PATH",
    "capability_status",
    "coverage_for_tool",
    "is_proof_source",
    "is_within_window",
    "iter_history",
    "latest_proof_receipts",
    "load",
    "record",
    "save",
]
