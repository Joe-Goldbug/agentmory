"""Capability registry and receipts for real tool connectivity.

Backwards-compatible facade over the new modules
:mod:`lwm.tool_registry` and :mod:`lwm.capability_proof`. All public symbols
that existing callers import keep working; new code should import directly
from the two modules.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from lwm.capability_proof import (
    ALL_RECEIPT_SOURCES,
    PROOF_RECEIPT_SOURCES,
    capability_status,
    is_proof_source,
    load,
    latest_proof_receipts,
    is_within_window,
    build_event_location_index,
    _evidence_file,
    record as _new_record,
)
from lwm.harvest import canonical_data_root
from lwm.tool_registry import ToolRegistry, default_registry


# ---- Compatibility shims --------------------------------------------------


def _compat_known_tools() -> tuple[str, ...]:
    """Legacy tuple kept for any caller that iterates ``KNOWN_TOOLS``."""

    return tuple(d.tool_id for d in default_registry().all())


KNOWN_TOOLS: tuple[str, ...] = _compat_known_tools()

# Kept so old imports of ``NATIVE_RECEIPT_SOURCES`` continue to resolve; it now
# only enumerates the proof sources (watcher is no longer proof).
NATIVE_RECEIPT_SOURCES = set(PROOF_RECEIPT_SOURCES)


#: Legacy per-tool relative paths derived from the registry.
TOOL_TARGETS: dict[str, tuple[str, ...]] = {
    d.tool_id: d.discovery_paths
    for d in default_registry().all()
}


def _path(root: Path) -> Path:
    return root / "state" / "capability-receipts.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _tool_targets(
    tool: str, home: Path, *, registry: ToolRegistry | None = None
) -> tuple[Path, ...]:
    """Resolve adapter files from the current real installation paths.

    The implementation is intentionally simple: it consults the registry's
    ``discovery_paths`` first, and falls back to a tiny set of per-tool
    overrides for tools that publish to non-fixed locations (opencode plugin
    path, vscode prompts directory).
    """

    definition = (registry or default_registry()).resolve(tool)
    if definition is None:
        return ()

    if tool == "opencode":
        config_root = home / ".config" / "opencode"
        agents = config_root / "AGENTS.md"
        plugin_candidates: list[Path] = [config_root / "plugins" / "llm-workmem.ts"]
        config_path = config_root / "opencode.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            plugins = config.get("plugin", []) if isinstance(config, dict) else []
            if isinstance(plugins, list):
                for plugin in plugins:
                    if not isinstance(plugin, str) or "lwm-workmem" not in plugin.lower():
                        continue
                    candidate = Path(plugin).expanduser()
                    if not candidate.is_absolute():
                        candidate = config_root / candidate
                    plugin_candidates.insert(0, candidate)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        plugin = next(
            (candidate for candidate in plugin_candidates if candidate.is_file()),
            plugin_candidates[0],
        )
        return (agents, plugin)

    if tool == "vscode":
        prompts = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
        candidates = (
            prompts / "llm-workmem.instructions.md",
            prompts / "copilot-workflow-memory.instructions.md",
        )
        installed = tuple(path for path in candidates if path.is_file())
        return installed or (candidates[0],)

    return tuple(home / relative for relative in definition.discovery_paths)


def record(
    root: Path,
    *,
    tool: str,
    direction: str,
    project_id: str | None = None,
    source: str = "unknown",
    detail: str = "",
    evidence_path: str = "",
    operation_id: str = "",
) -> dict[str, Any]:
    """Compatibility wrapper that bridges to :func:`lwm.capability_proof.record`.

    Accepts the legacy ``source="watcher-observed"`` style: the receipt is
    stored, but its ``status`` is forced to ``observed`` and it never produces a
    ``verified_*`` capability status.
    """

    root = canonical_data_root(root)
    definition = ToolRegistry.load(root).resolve(tool)
    canonical_tool = definition.tool_id if definition is not None else tool
    try:
        receipt = _new_record(
            root,
            tool=canonical_tool,
            direction=direction,
            project_id=project_id,
            source=source if source in ALL_RECEIPT_SOURCES else "watcher-observed",
            evidence_path=evidence_path,
            operation_id=operation_id,
            detail=detail,
        )
    except (OSError, TypeError, ValueError) as exc:
        return {
            "tool": canonical_tool,
            "direction": direction,
            "project_id": project_id,
            "source": source,
            "status": "unavailable",
            "error": str(exc),
        }
    return receipt.to_dict()


def _latest_receipt(
    payload: dict[str, Any],
    key: str,
    expected_project_id: str | None,
    *,
    allowed_sources: set[str] | None = None,
) -> dict[str, Any] | None:
    """Legacy shim: returns the newest receipt matching ``"{tool}:{direction}"``.

    New storage groups receipts by tool under ``payload[tool]`` with the
    direction in the receipt body. The shim scans all entries to keep the
    legacy key contract working.
    """

    if ":" in key:
        tool_id, _direction = key.split(":", 1)
    else:
        tool_id, _direction = key, None

    candidates: list[dict[str, Any]] = []
    current = payload.get(tool_id)
    if isinstance(current, dict):
        candidates.append(current)
    history = payload.get("_history")
    if isinstance(history, dict):
        bucket = history.get(tool_id)
        if isinstance(bucket, list):
            candidates.extend(item for item in bucket if isinstance(item, dict))
    # Fallback to the literal ``{tool}:{direction}`` key for legacy payloads.
    legacy = payload.get(key)
    if isinstance(legacy, dict):
        candidates.append(legacy)

    if _direction is not None:
        candidates = [
            item for item in candidates if item.get("direction") == _direction
        ]
    if expected_project_id:
        candidates = [
            item for item in candidates if item.get("project_id") == expected_project_id
        ]
    if allowed_sources:
        candidates = [
            item for item in candidates if item.get("source") in allowed_sources
        ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: str(item.get("timestamp") or item.get("recorded_at") or ""),
    )


def summary(
    root: Path, *, project_path: str | Path | None = None
) -> dict[str, dict[str, Any]]:
    installed = probe(root, project_path=project_path)
    out: dict[str, dict[str, Any]] = {}
    for tool in installed:
        read = installed[tool]["read_receipt"] or {"status": "unverified"}
        write = installed[tool]["write_receipt"] or {"status": "unverified"}
        out[tool] = {
            "configuration": installed[tool]["status"],
            "installed": installed[tool]["installed"],
            "targets": installed[tool]["targets"],
            "read": read if isinstance(read, dict) else {"status": "unverified"},
            "write": write if isinstance(write, dict) else {"status": "unverified"},
            "bidirectional": installed[tool]["status"] == "verified_bidirectional",
            "proof_scope": installed[tool]["proof_scope"],
            "useful_memory_status": installed[tool]["useful_memory_status"],
        }
    return out


def _is_fresh_native(receipt: Any, expected_project_id: str | None) -> bool:
    if not isinstance(receipt, dict) or receipt.get("status") != "verified":
        return False
    if not is_proof_source(receipt.get("source", "")):
        return False
    if expected_project_id and receipt.get("project_id") != expected_project_id:
        return False
    try:
        recorded = datetime.fromisoformat(str(receipt["recorded_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    return recorded >= datetime.now(timezone.utc) - timedelta(days=14)


def probe(
    root: Path,
    *,
    home: Path | None = None,
    project_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Check configuration separately from real read/write receipts.

    A present instruction file proves only that an adapter is installed. A
    verified receipt is required before claiming that a tool actually read or
    wrote the hub.
    """
    root = canonical_data_root(root)
    home = (home or Path.home()).expanduser().resolve()
    expected_project_id = None
    if project_path is not None:
        from lwm.project_id import resolve_project_id

        expected_project_id = resolve_project_id(project_path).project_id
    out: dict[str, dict[str, Any]] = {}
    registry = ToolRegistry.load(root)
    event_locations = build_event_location_index(root)
    receipt_history = load(root).get("_history", {})
    for definition in registry.enabled():
        tool = definition.tool_id
        targets = list(_tool_targets(tool, home, registry=registry))
        installed = bool(targets) and any(
            path.is_file() or path.is_dir() for path in targets
        )
        readable = installed and any(
            path.is_file() and path.stat().st_size > 0 for path in targets
        )
        read_proof, write_proof = latest_proof_receipts(
            root, tool=tool, expected_project_id=expected_project_id,
            event_index=event_locations,
        )
        read_receipt = read_proof.to_dict() if read_proof else None
        write_receipt = write_proof.to_dict() if write_proof else None
        status = capability_status(
            read_receipt=read_receipt,
            write_receipt=write_receipt,
            expected_project_id=expected_project_id,
        )
        if status == "configured_unverified" and (not installed or not readable):
            status = "not_configured"
        out[tool] = {
            "status": status,
            "installed": installed,
            "targets": [str(path) for path in targets],
            "read_receipt": read_receipt if isinstance(read_receipt, dict) else None,
            "write_receipt": write_receipt if isinstance(write_receipt, dict) else None,
            "expected_project_id": expected_project_id,
            "proof_scope": "host_lifecycle_transport",
        }
        # Empty session-end callbacks must not hide earlier durable work.
        work_receipts = [write_receipt] if write_receipt else []
        history = receipt_history.get(tool, []) if isinstance(receipt_history, dict) else []
        if isinstance(history, list):
            work_receipts += [item for item in history if isinstance(item, dict)
                              and item.get("direction") == "write"
                              and item.get("status") == "verified"
                              and is_proof_source(item.get("source", ""))
                              and is_within_window(item)
                              and (not expected_project_id or item.get("project_id") == expected_project_id)]
        work_status = "missing"
        rank = {"missing": 0, "unverified": 1, "operational_only": 2, "pending_ingest": 3, "accepted": 4, "published": 5}
        for receipt in work_receipts:
            write_path = _evidence_file(root, str(receipt.get("evidence_path") or ""), event_index=event_locations)
            if write_path is None:
                continue
            candidate_status = "pending_ingest" if "inbox" in write_path.parts else "operational_only"
            try:
                from lwm.project_memory import classify_event, project_page_path

                work = json.loads(write_path.read_text(encoding="utf-8"))
                if "processed" in write_path.parts and classify_event(work).durability == "durable":
                    page = project_page_path(root, str(work.get("project_id") or ""))
                    candidate_status = "accepted"
                    if page.is_file() and str(work.get("event_id") or "") in page.read_text(encoding="utf-8"):
                        candidate_status = "published"
            except (OSError, ValueError, TypeError):
                candidate_status = "unverified"
            if rank[candidate_status] > rank[work_status]:
                work_status = candidate_status
            if work_status == "published":
                break
        out[tool]["useful_memory_status"] = work_status
    return out


__all__ = [
    "KNOWN_TOOLS",
    "NATIVE_RECEIPT_SOURCES",
    "TOOL_TARGETS",
    "load",
    "probe",
    "record",
    "summary",
]
