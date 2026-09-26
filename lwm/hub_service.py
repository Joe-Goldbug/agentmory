"""Shared service functions used by CLI and MCP surfaces."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from lwm import behavior_contract, capabilities, context, dedup, inbox
from lwm.capability_proof import coverage_for_tool
from lwm.cycle_receipt import load_last_attempt, load_latest
from lwm.events import make_event, validate_event
from lwm.memory_compiler import (
    Candidate,
    analyze_pending,
    load_candidate,
    record_transition,
    review_analysis_candidate,
    save_candidate,
)
from lwm.harvest import canonical_data_root
from lwm.project_id import record_project, resolve_project_root
from lwm.tool_registry import ToolRegistry


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_root_path(root: Path, value: str) -> Path | None:
    """Resolve an evidence path without allowing receipt traversal."""

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _collector_importable(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def record_event(
    root: Path,
    event: Mapping[str, Any],
    *,
    receipt_source: str = "cli-record",
    deduplicate: bool = False,
) -> dict[str, Any]:
    """Canonical event submission used by CLI, MCP and adapters.

    Producers may provide a complete event or a sparse structured payload. The
    same defaults, project-root resolution, schema validation, inbox write and
    observation receipt are applied regardless of the transport.
    """

    root = canonical_data_root(root)
    incoming = dict(event)
    definition = ToolRegistry.load(root).resolve(str(incoming.get("tool") or "shell"))
    incoming["tool"] = definition.tool_id if definition is not None else str(
        incoming.get("tool") or "shell"
    )
    for key in (
        "decisions",
        "changes",
        "verification",
        "open_questions",
        "risks",
        "files_touched",
        "tags",
    ):
        if incoming.get(key) is None:
            incoming.pop(key, None)
    for key in (
        "tool_version",
        "session_id",
        "task_id",
        "handoff_id",
        "operation_id",
        "source_receipt_id",
        "confidence",
        "source",
    ):
        if incoming.get(key) is None:
            incoming.pop(key, None)
    # A transport must not leak its own process cwd into project identity.
    # When a producer omits the path, the supplied data root is the only
    # deterministic local fallback shared by CLI, MCP and adapters.
    project_path = str(incoming.get("project_path") or root)
    canonical_path = resolve_project_root(project_path)
    incoming["project_path"] = str(canonical_path)
    project_id = str(incoming.get("project_id") or "")
    if not project_id:
        project_id = record_project(root, canonical_path).project_id
        incoming["project_id"] = project_id

    defaults = make_event(
        tool=str(incoming.get("tool") or "shell"),
        project_path=str(canonical_path),
        project_id=project_id,
        event_type=str(incoming.get("event_type") or "workflow_observation"),
        importance=str(incoming.get("importance") or "project"),
        privacy=str(incoming.get("privacy") or "sanitized"),
        task=(str(incoming["task"]) if incoming.get("task") is not None else None),
        timestamp=str(incoming.get("timestamp") or _now_iso()),
        event_id=str(incoming.get("event_id") or uuid.uuid4()),
    )
    for key, value in defaults.items():
        incoming.setdefault(key, value)

    validation = validate_event(incoming)
    if not validation.ok:
        raise ValueError("; ".join(issue.render() for issue in validation.issues))
    if deduplicate:
        duplicate = dedup.find_duplicate(root, incoming)
        if duplicate.duplicate:
            return {
                "event": incoming,
                "event_id": incoming["event_id"],
                "path": "",
                "absolute_path": "",
                "receipt": None,
                "duplicate": True,
                "existing_event_id": duplicate.existing_event_id,
            }
    target = inbox.submit_event(root, incoming)
    receipt = capabilities.record(
        root,
        tool=str(incoming["tool"]),
        direction="write",
        project_id=str(incoming.get("project_id") or "") or None,
        source=receipt_source,
    )
    try:
        display_path = str(target.relative_to(root))
    except ValueError:
        display_path = str(target)
    return {
        "event": incoming,
        "event_id": incoming["event_id"],
        "path": display_path,
        "absolute_path": str(target),
        "receipt": receipt,
        "duplicate": False,
    }


def retain_event(
    root: Path,
    event: Mapping[str, Any],
    *,
    receipt_source: str = "retain",
) -> dict[str, Any]:
    """Retain one structured event with deterministic duplicate suppression."""

    return record_event(
        root,
        event,
        receipt_source=receipt_source,
        deduplicate=True,
    )


def context_for_tool(
    root: Path,
    *,
    tool: str,
    project_path: str | Path | None,
    limit: int = 6,
) -> tuple[context.ContextReport, dict[str, Any]]:
    """Canonical startup Context rendering and read-receipt recording."""

    root = canonical_data_root(root)
    canonical_project = resolve_project_root(project_path) if project_path else None
    report = context.build(
        root,
        tool=tool,
        project_path=str(canonical_project) if canonical_project else None,
        limit=limit,
    )
    receipt = capabilities.record(
        root,
        tool=tool,
        direction="read",
        project_id=report.project_id,
        source="cli-context",
    )
    if receipt.get("status") != "verified":
        warnings = list(report.data.get("warnings") or [])
        warnings.append(
            f"Read receipt unavailable: {receipt.get('error', 'observation only')}"
        )
        data = {**report.data, "warnings": warnings}
        markdown = report.markdown.rstrip() + f"\n\nWarning: {warnings[-1]}\n"
        report = replace(report, markdown=markdown, data=data)
    return report, receipt


def review_analysis(
    root: Path,
    candidate_id: str,
    *,
    decision: str,
    actor: str = "human",
) -> dict[str, Any]:
    """Apply an explicit human decision to an analyzed compiler candidate."""

    if decision not in {"accept", "reject", "promote"}:
        raise ValueError("decision must be accept, reject, or promote")
    candidate = review_analysis_candidate(
        canonical_data_root(root), candidate_id, decision=decision, actor=actor  # type: ignore[arg-type]
    )
    return candidate.to_dict()


def promote_analysis(
    root: Path,
    candidate_id: str,
    *,
    actor: str = "human",
) -> dict[str, Any]:
    """Promote one human-approved compiler candidate through stable evidence."""

    root = canonical_data_root(root)
    candidate = load_candidate(root, candidate_id)
    if candidate is None:
        raise FileNotFoundError(candidate_id)
    if candidate.state == "promoted":
        return {"status": "already_promoted", "candidate": candidate.to_dict()}
    if candidate.state == "accepted":
        candidate = review_analysis_candidate(
            root, candidate_id, decision="promote", actor=actor
        )
    if candidate.state != "promotion_pending":
        raise ValueError(f"candidate must be accepted before promotion: {candidate.state}")

    from lwm.insights import load_processed_events
    from lwm.stable_promotion import evaluate_promotion, persist_promotion

    evaluated = evaluate_promotion(
        root,
        claim=candidate.claim,
        events=load_processed_events(root),
        evidence_ids=candidate.evidence_ids,
        actor=actor,
    )
    if not evaluated.promoted:
        return {
            "status": "withheld",
            "candidate": candidate.to_dict(),
            "claim_key": evaluated.claim_key,
            "reasons": list(evaluated.reasons),
        }

    page_type = {
        "workflow": "pattern",
        "relationship": "relationship",
        "conflict": "principle",
        "summary": "principle",
    }[candidate.kind]
    target = persist_promotion(evaluated, actor=actor, page_type=page_type)
    if target is None:
        return {
            "status": "withheld",
            "candidate": candidate.to_dict(),
            "claim_key": evaluated.claim_key,
            "reasons": ["promotion_persistence_failed"],
        }
    promoted = Candidate.from_dict({**candidate.to_dict(), "state": "promoted"})
    save_candidate(root, promoted)
    record_transition(
        root,
        candidate_id,
        from_state="promotion_pending",
        to_state="promoted",
        note="stable evidence promotion succeeded",
        evidence_hash=hashlib.sha256(
            json.dumps(sorted(candidate.evidence_ids)).encode("utf-8")
        ).hexdigest(),
        actor=actor,
    )
    return {
        "status": "promoted",
        "candidate": promoted.to_dict(),
        "claim_key": evaluated.claim_key,
        "target": str(target),
    }


def _verify_evidence_hashes(root: Path, receipt: dict[str, Any], reasons: list[str]) -> None:
    evidence = receipt.get("evidence_hashes")
    if not isinstance(evidence, dict):
        if receipt.get("schema_version") == 2:
            reasons.append("receipt_missing_evidence_hashes")
        return
    for raw_path, expected in sorted(evidence.items()):
        if not isinstance(raw_path, str) or not isinstance(expected, str):
            reasons.append(f"invalid_evidence_hash:{raw_path}")
            continue
        path = _safe_root_path(root, raw_path)
        if path is None or not path.is_file():
            reasons.append(f"evidence_missing:{raw_path}")
            continue
        try:
            actual = _sha256(path)
        except OSError:
            reasons.append(f"evidence_unreadable:{raw_path}")
            continue
        if actual != expected:
            reasons.append(f"evidence_hash_mismatch:{raw_path}")


def _verify_runtime_fields(root: Path, receipt: dict[str, Any], reasons: list[str]) -> None:
    module_path = str(receipt.get("runtime_module_path") or "")
    sys_path = receipt.get("runtime_sys_path")
    independent = receipt.get("runtime_import_independent")
    if module_path and "/Mobile Documents/" in module_path:
        reasons.append("runtime_module_imports_from_icloud")
    if isinstance(sys_path, list) and any("/Mobile Documents/" in str(item) for item in sys_path):
        reasons.append("runtime_sys_path_imports_from_icloud")
    if receipt.get("schema_version") == 2 and not module_path:
        reasons.append("receipt_missing_runtime_module_path")
    if receipt.get("schema_version") == 2 and independent is not True:
        reasons.append("runtime_import_not_proven_independent")

    manifest_path = str(receipt.get("runtime_manifest_path") or "")
    expected_manifest_hash = str(receipt.get("runtime_manifest_sha256") or "")
    if expected_manifest_hash:
        path = _safe_root_path(root, manifest_path) if manifest_path else None
        if not manifest_path:
            reasons.append("runtime_manifest_path_missing")
        elif path is None or not path.is_file():
            reasons.append("runtime_manifest_missing")
        else:
            try:
                if _sha256(path) != expected_manifest_hash:
                    reasons.append("runtime_manifest_hash_mismatch")
            except OSError:
                reasons.append("runtime_manifest_unreadable")


def _verify_quality_fields(root: Path, receipt: dict[str, Any], reasons: list[str], *, strict: bool) -> None:
    quality = receipt.get("quality") if isinstance(receipt.get("quality"), dict) else {}
    if quality.get("audit_ok") is not True:
        reasons.append("audit_not_ok")
    eval_pass = quality.get("eval_pass")
    eval_total = quality.get("eval_total")
    if not isinstance(eval_pass, int) or not isinstance(eval_total, int) or eval_total <= 0 or eval_pass != eval_total:
        reasons.append("eval_not_complete")
    if quality.get("context_ok") is not True:
        reasons.append("context_not_ok")
    health_hash = str(receipt.get("health_sha256") or "")
    health_snapshot_path = str(receipt.get("health_snapshot_path") or "")
    if health_snapshot_path:
        expected = f"state/receipts/health/{receipt.get('cycle_id')}.json"
        if health_snapshot_path != expected:
            reasons.append("health_snapshot_path_invalid")
            return
        health_path = _safe_root_path(root, health_snapshot_path)
        if health_path is None:
            reasons.append("health_snapshot_path_invalid")
            return
    else:
        health_path = root / "state" / "health.json"
    if not health_hash:
        reasons.append("health_hash_missing")
    elif not health_path.is_file():
        reasons.append("health_snapshot_missing")
    else:
        try:
            if _sha256(health_path) != health_hash:
                reasons.append("health_hash_mismatch")
            payload = json.loads(health_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and strict and payload.get("status") != "healthy":
                reasons.append(f"health_status:{payload.get('status')}")
        except (OSError, json.JSONDecodeError):
            reasons.append("health_snapshot_unreadable")

    eval_hash = str(receipt.get("eval_suite_sha256") or "")
    if not eval_hash:
        reasons.append("eval_suite_hash_missing")
    else:
        try:
            from importlib.resources import files as resource_files

            resource = resource_files("lwm.resources").joinpath("eval-suite.txt")
            if hashlib.sha256(resource.read_bytes()).hexdigest() != eval_hash:
                reasons.append("eval_suite_hash_mismatch")
        except (OSError, ModuleNotFoundError):
            reasons.append("eval_suite_unreadable")


def _verify_receipt_contract(root: Path, receipt: dict[str, Any], reasons: list[str], *, strict: bool) -> None:
    if receipt.get("schema_version") != 2:
        return
    _verify_evidence_hashes(root, receipt, reasons)
    _verify_runtime_fields(root, receipt, reasons)
    _verify_quality_fields(root, receipt, reasons, strict=strict)
    if strict and receipt.get("exit_code") != 0:
        reasons.append(f"receipt_exit_code:{receipt.get('exit_code')}")


def list_tools(root: Path, *, home: Path | None = None) -> list[dict[str, Any]]:
    registry = ToolRegistry.load(root)
    discovered = registry.discover(home)
    host_probes = registry.host_probe()
    rows: list[dict[str, Any]] = []
    for definition in registry.all():
        has_collectors = bool(definition.collector_modules)
        collector_importable = (
            has_collectors
            and all(
                _collector_importable(module)
                for module in definition.collector_modules
            )
        )
        has_observers = bool(definition.observer_modules)
        observer_importable = (
            has_observers
            and all(
                _collector_importable(module)
                for module in definition.observer_modules
            )
        )
        coverage = coverage_for_tool(
            root,
            tool=definition.tool_id,
            expected_project_id=None,
            configured=bool(discovered.get(definition.tool_id)),
            host_probe=host_probes.get(definition.tool_id, {}),
        )
        rows.append(
            {
                "tool_id": definition.tool_id,
                "display_name": definition.display_name,
                "surfaces": list(definition.surfaces),
                "capture_mode": definition.capture_mode,
                "delivery_mode": definition.delivery_mode,
                "proof_integrations": list(definition.proof_integrations),
                "collector_modules": list(definition.collector_modules),
                "observer_modules": list(definition.observer_modules),
                "collector_importable": collector_importable,
                "observer_importable": observer_importable,
                "collector_status": (
                    "ready"
                    if collector_importable
                    else "missing"
                    if has_collectors
                    else "not_applicable"
                ),
                "observer_status": (
                    "ready"
                    if observer_importable
                    else "missing"
                    if has_observers
                    else "not_applicable"
                ),
                "discovered": discovered.get(definition.tool_id, False),
                "configured": discovered.get(definition.tool_id, False),
                "host_probe": host_probes.get(definition.tool_id, {}),
                # Keep the registry/probe view aligned with `hub coverage`.
                # Configuration alone must never look like end-to-end support.
                "coverage_status": coverage.status,
                "delivery_status": coverage.delivery_status,
                "capture_status": coverage.capture_status,
                "capture_freshness": coverage.capture_freshness,
                "coverage_gaps": list(coverage.gaps),
                "status_reason": coverage.status_reason,
                "enabled": definition.enabled,
            }
        )
    return rows


def coverage_report(
    root: Path,
    *,
    tool: str | None = None,
    project_id: str | None = None,
    home: Path | None = None,
) -> dict[str, dict[str, Any]]:
    # Repository paths are access links after the data-owner migration. Work
    # from the physical owner so evidence paths and receipt stores resolve to
    # the same entity whether the caller uses the checkout or runtime path.
    root = canonical_data_root(root)
    registry = ToolRegistry.load(root)
    discovered = registry.discover(home)
    host_probes = registry.host_probe()
    definitions = [registry.resolve(tool)] if tool else list(registry.all())
    rows: dict[str, dict[str, Any]] = {}
    for definition in definitions:
        if definition is None:
            continue
        coverage = coverage_for_tool(
            root,
            tool=definition.tool_id,
            expected_project_id=project_id,
            configured=bool(discovered.get(definition.tool_id)),
            host_probe=host_probes.get(definition.tool_id, {}),
        )
        rows[definition.tool_id] = {
            **asdict(coverage),
            "configured": bool(discovered.get(definition.tool_id)),
            "host_probe": host_probes.get(definition.tool_id, {}),
            "collector_modules": list(definition.collector_modules),
            "observer_modules": list(definition.observer_modules),
            "capture_mode": definition.capture_mode,
            "delivery_mode": definition.delivery_mode,
            "proof_integrations": list(definition.proof_integrations),
        }
    return rows


def behavior_show(root: Path) -> dict[str, Any]:
    return behavior_contract.load(root).to_dict(include_text=True)


def behavior_verify(root: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    return behavior_contract.verify(root, expected_sha256=expected_sha256)


def verify_cycle(root: Path, cycle_id: str, *, strict: bool = False) -> dict[str, Any]:
    # Cycle receipts and their evidence belong to the runtime owner after
    # migration. Normalize the access link before validating relative paths.
    root = canonical_data_root(root)
    pointer_path = root / "state" / "receipts" / "latest-cycle.json"
    pointer: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
    reasons: list[str] = []
    if pointer_path.is_file():
        try:
            loaded = json.loads(pointer_path.read_text(encoding="utf-8"))
            pointer = loaded if isinstance(loaded, dict) else None
        except (OSError, json.JSONDecodeError):
            reasons.append("invalid_latest_pointer")
    if not pointer or pointer.get("cycle_id") != cycle_id:
        attempt_path = root / "state" / "receipts" / "last-attempt.json"
        try:
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            attempt = None
        if isinstance(attempt, dict) and attempt.get("cycle_id") == cycle_id:
            pointer = attempt
    if pointer is None:
        attempt = load_last_attempt(root)
        if isinstance(attempt, dict) and attempt.get("cycle_id") == cycle_id:
            pointer = {
                "cycle_id": cycle_id,
                "path": str(Path("state/receipts/cycles") / f"{cycle_id}.json"),
            }
    if pointer and pointer.get("path"):
        receipt_path = root / str(pointer["path"])
        try:
            loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt = loaded if isinstance(loaded, dict) else None
            expected_hash = str(pointer.get("receipt_sha256") or "")
            if not expected_hash:
                reasons.append("latest_pointer_missing_receipt_hash")
            actual_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            if expected_hash and expected_hash != actual_hash:
                reasons.append("receipt_hash_mismatch")
        except (OSError, json.JSONDecodeError):
            reasons.append("receipt_unreadable")
    if receipt is None:
        receipt = load_latest(root)
    if not receipt:
        reasons.append("no_receipt")
    elif receipt.get("cycle_id") != cycle_id:
        reasons.append(f"latest_cycle_mismatch:{receipt.get('cycle_id')}")
    elif receipt.get("schema_version") != 2:
        reasons.append("receipt_not_v2")
    elif receipt.get("core_status") == "failed_core":
        reasons.append("failed_core")
    elif strict and receipt.get("core_status") != "success":
        reasons.append(f"strict_core_status:{receipt.get('core_status')}")
    if receipt:
        _verify_receipt_contract(root, receipt, reasons, strict=strict)
    return {
        "valid": not reasons,
        "cycle_id": cycle_id,
        "reasons": reasons,
        "receipt": receipt,
        "pointer": pointer,
    }


__all__ = [
    "analyze_pending",
    "behavior_show",
    "behavior_verify",
    "coverage_report",
    "list_tools",
    "promote_analysis",
    "review_analysis",
    "verify_cycle",
]
