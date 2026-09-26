"""Versioned JSON bridge for host-tool session boundaries.

Every IDE or CLI integration needs the same small contract:

``context``
    Read bounded context for the current project.
``start``
    Record a session boundary and return the same bounded context.
``stop``
    Record the session boundary and, when supplied, persist a bounded
    structured handoff.

The bridge is intentionally a transport adapter, not a second memory engine.
It delegates to :mod:`lwm.hub_service` and :mod:`lwm.lifecycle`, so aliases,
validation, receipts and handoff rules stay in one place.  Simulated contract
checks use ``watcher-observed`` and therefore cannot produce verified proof.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from lwm import capabilities, hub_service, lifecycle
from lwm.capability_proof import (
    ALL_RECEIPT_SOURCES,
    PROOF_RECEIPT_SOURCES,
    validate_host_proof,
)
from lwm.tool_registry import ToolRegistry


BRIDGE_SCHEMA_VERSION = 1
BRIDGE_PHASES = frozenset({"context", "start", "stop"})
SIMULATION_SOURCE = "watcher-observed"


def _required_text(request: Mapping[str, Any], key: str) -> str:
    value = request.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required and must be a non-empty string")
    return value.strip()


def _optional_text(request: Mapping[str, Any], key: str) -> str | None:
    value = request.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    value = value.strip()
    return value or None


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _event_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"bridge event cannot be read: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"bridge event is not an object: {path}")
    return payload


def _receipt_for_operation(
    root: Path,
    *,
    tool: str,
    project_id: str,
    direction: str,
    operation_id: str,
) -> dict[str, Any] | None:
    """Return the exact receipt for this bridge operation, if it exists."""

    payload = capabilities.load(root)
    history = payload.get("_history")
    entries: list[dict[str, Any]] = []
    if isinstance(history, dict) and isinstance(history.get(tool), list):
        entries = [item for item in history[tool] if isinstance(item, dict)]
    current = payload.get(tool)
    if isinstance(current, dict):
        entries.append(current)
    for entry in reversed(entries):
        if (
            entry.get("direction") == direction
            and entry.get("project_id") == project_id
            and entry.get("operation_id") == operation_id
        ):
            return dict(entry)
    return None


def _common_response(
    *,
    phase: str,
    tool: str,
    project_path: str,
    project_id: str | None,
    session_id: str | None,
    task_id: str | None,
    source: str,
    simulation: bool,
    host_proof: Mapping[str, str] | None,
) -> dict[str, Any]:
    if simulation:
        verification_mode = "simulated"
    elif source in PROOF_RECEIPT_SOURCES:
        verification_mode = "host-reported"
    else:
        verification_mode = "observed"
    response = {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "bridge": "lwm.session_bridge",
        "phase": phase,
        "tool": tool,
        "project_path": project_path,
        "project_id": project_id,
        "session_id": session_id,
        "task_id": task_id,
        "source": source,
        "simulation": simulation,
        "verification_mode": verification_mode,
    }
    if host_proof is not None:
        response["host_proof"] = dict(host_proof)
    return response


def dispatch(
    root: Path,
    request: Mapping[str, Any],
    *,
    trusted_host: bool = False,
) -> dict[str, Any]:
    """Dispatch one versioned bridge request and return JSON-safe output.

    Proof-bearing requests are reserved for native adapters. The public CLI
    uses the default ``False`` value, so a user-supplied JSON request cannot
    turn a registered integration name into host proof.
    """

    if not isinstance(request, Mapping):
        raise ValueError("bridge request must be a JSON object")
    phase = _required_text(request, "phase").lower()
    if phase not in BRIDGE_PHASES:
        raise ValueError(f"phase must be one of: {', '.join(sorted(BRIDGE_PHASES))}")

    registry = ToolRegistry.load(root.resolve())
    requested_tool = _required_text(request, "tool")
    definition = registry.resolve(requested_tool)
    if definition is None:
        raise ValueError(f"unknown tool: {requested_tool}")
    tool = definition.tool_id

    project_value = request.get("project_path", request.get("project"))
    if not isinstance(project_value, str) or not project_value.strip():
        raise ValueError("project_path is required and must be a non-empty string")
    project_path = project_value.strip()
    session_id = _optional_text(request, "session_id")
    task_id = _optional_text(request, "task_id")
    task = _optional_text(request, "task")
    source = _optional_text(request, "source") or SIMULATION_SOURCE
    if source not in ALL_RECEIPT_SOURCES:
        raise ValueError(f"unknown receipt source: {source}")
    simulation = request.get("simulation", False)
    if not isinstance(simulation, bool):
        raise ValueError("simulation must be a boolean")
    if simulation and source not in {
        "watcher-observed",
        "cli-context",
        "file-probe",
        "explicit-smoke",
    }:
        raise ValueError("simulation cannot use a proof source")
    if source in PROOF_RECEIPT_SOURCES and not trusted_host:
        raise ValueError(
            "proof sources require a trusted native host adapter; "
            "use an observation source for direct bridge calls"
        )
    raw_host_proof = request.get("host_proof")
    if raw_host_proof is not None and not isinstance(raw_host_proof, Mapping):
        raise ValueError("host_proof must be a JSON object")
    normalized_proof = validate_host_proof(
        root.resolve(),
        tool=tool,
        phase=phase,
        source=source,
        session_id=session_id,
        host_proof=raw_host_proof,
    )

    limit = request.get("limit", 6)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("limit must be an integer between 1 and 20")

    response = _common_response(
        phase=phase,
        tool=tool,
        project_path=project_path,
        project_id=None,
        session_id=session_id,
        task_id=task_id,
        source=source,
        simulation=simulation,
        host_proof=normalized_proof,
    )

    if phase == "context":
        report, receipt = hub_service.context_for_tool(
            root.resolve(), tool=tool, project_path=project_path, limit=limit
        )
        response.update(
            {
                "project_path": report.project_path,
                "project_id": report.project_id,
                "context_markdown": report.markdown,
                "context": report.data,
                "read_receipt": receipt,
                "status": "ok",
            }
        )
        return response

    if phase == "start":
        result = lifecycle.start(
            root.resolve(),
            tool=tool,
            project_path=project_path,
            session_id=session_id,
            task_id=task_id,
            source=source,
            host_proof=normalized_proof,
        )
        event = _event_payload(result.event_path)
        operation_id = f"read:{event['event_id']}"
        response.update(
            {
                "project_path": result.project_path,
                "project_id": result.project_id,
                "context_markdown": result.context_markdown,
                "event": {
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "path": _relative_path(root, result.event_path),
                    "operation_id": operation_id,
                },
                "read_receipt": _receipt_for_operation(
                    root,
                    tool=tool,
                    project_id=result.project_id,
                    direction="read",
                    operation_id=operation_id,
                ),
                "status": "ok",
            }
        )
        return response

    handoff_summary = request.get("handoff", request.get("handoff_summary"))
    if handoff_summary is not None and not isinstance(handoff_summary, Mapping):
        raise ValueError("handoff must be a JSON object")
    result = lifecycle.stop(
        root.resolve(),
        tool=tool,
        project_path=project_path,
        session_id=session_id,
        task=task,
        task_id=task_id,
        handoff_summary=handoff_summary,
        source=source,
        host_proof=normalized_proof,
    )
    event = _event_payload(result.event_path)
    operation_id = f"write:{event['event_id']}"
    response.update(
        {
            "project_path": result.project_path,
            "project_id": result.project_id,
            "event": {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "path": _relative_path(root, result.event_path),
                "operation_id": operation_id,
            },
            "write_receipt": _receipt_for_operation(
                root,
                tool=tool,
                project_id=result.project_id,
                direction="write",
                operation_id=operation_id,
            ),
            "handoff": {
                "created": result.handoff_created,
                "handoff_id": result.handoff_id,
            },
            "warning": result.warning,
            "status": "ok",
        }
    )
    return response


def simulate_registry_contract(root: Path, project_path: Path) -> dict[str, Any]:
    """Exercise the bridge for every registered tool in an isolated root.

    This is deliberately a contract test, not a host integration test.  It
    uses watcher observations and reports ``simulated`` so callers cannot
    mistake a successful package check for real native-tool evidence.
    """

    source_registry = ToolRegistry.load(root.resolve())
    task_id = "bridge-contract-simulation"
    rows: list[dict[str, Any]] = []
    # Simulation must never use the caller's data root. Copy only the registry
    # definition into a disposable root, then let the normal bridge write there.
    with tempfile.TemporaryDirectory(prefix="lwm-bridge-contract-") as directory:
        simulation_root = Path(directory)
        source_registry.save(simulation_root)
        for definition in source_registry.enabled():
            context = dispatch(
                simulation_root,
                {
                    "phase": "context",
                    "tool": definition.tool_id,
                    "project_path": str(project_path),
                    "task_id": task_id,
                    "source": SIMULATION_SOURCE,
                    "simulation": True,
                },
            )
            start = dispatch(
                simulation_root,
                {
                    "phase": "start",
                    "tool": definition.tool_id,
                    "project_path": str(project_path),
                    "session_id": f"{definition.tool_id}-simulation",
                    "task_id": task_id,
                    "source": SIMULATION_SOURCE,
                    "simulation": True,
                },
            )
            stop = dispatch(
                simulation_root,
                {
                    "phase": "stop",
                    "tool": definition.tool_id,
                    "project_path": str(project_path),
                    "session_id": f"{definition.tool_id}-simulation",
                    "task_id": task_id,
                    "source": SIMULATION_SOURCE,
                    "simulation": True,
                    "handoff": {
                        "task_id": task_id,
                        "objective": "verify the shared session bridge contract",
                        "current_state": f"{definition.tool_id} bridge exercised",
                        "verifications": ["bridge start and stop returned status ok"],
                        "next_action": "replace simulation with host evidence",
                    },
                },
            )
            rows.append(
                {
                    "tool": definition.tool_id,
                    "context_status": context["status"],
                    "start_status": start["status"],
                    "stop_status": stop["status"],
                    "canonical_tool": start["tool"],
                    "verification_mode": "simulated",
                    "proof_claim": "not_proven",
                }
            )
    return {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "verification_mode": "simulated",
        "project_path": str(project_path.resolve()),
        "tools": rows,
        "all_contracts_pass": all(
            row["context_status"] == "ok"
            and row["start_status"] == "ok"
            and row["stop_status"] == "ok"
            for row in rows
        ),
    }


__all__ = [
    "BRIDGE_PHASES",
    "BRIDGE_SCHEMA_VERSION",
    "SIMULATION_SOURCE",
    "dispatch",
    "simulate_registry_contract",
]
