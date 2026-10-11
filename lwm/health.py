"""Health snapshot for the central hub.

Three layers:

1. Infrastructure — launchd loaded?, last exit code, health.json mtime.
2. Data flow — inbox size, processed/rejected/failed counts, last event
   per tool.
3. Quality — wiki audit pass, llms.txt mtime, privacy rejection rate.

Output goes to stdout (``lwm health``) AND to ``state/health.json``
for downstream tools.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lwm import dedup, inbox
from lwm import capabilities
from lwm.audit import AuditReport, run_audit
from lwm.cycle_state import is_due, read_receipt
from lwm.cycle_receipt import load_last_attempt, load_latest
from lwm.eval import packaged_eval_suite
from lwm.loop_state import read_active, read_last


STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ToolSync:
    tool: str
    last_event_at: str | None
    last_event_type: str | None
    last_project_id: str | None
    event_count: int

    def render(self) -> str:
        when = self.last_event_at or "never"
        return (
            f"{self.tool}: last_event={when} "
            f"type={self.last_event_type or 'n/a'} "
            f"project={self.last_project_id or 'n/a'} "
            f"count={self.event_count}"
        )


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    checked_at: str
    infrastructure: dict[str, Any]
    data_flow: dict[str, Any]
    cycle: dict[str, Any]
    capabilities: dict[str, dict[str, Any]]
    quality: dict[str, Any]
    tools: tuple[ToolSync, ...]
    inbox_counts: dict[str, int]
    capabilities_scope: str = "all_projects"

    def render(self) -> str:
        lines = [f"# LLM-WorkMem Health — {self.status}", ""]
        lines.append(f"checked_at: {self.checked_at}")
        lines.append("")
        lines.append("## Infrastructure")
        for key, value in self.infrastructure.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("## Data Flow")
        lines.append(
            f"- inbox={self.inbox_counts['inbox']} "
            f"processed={self.inbox_counts['processed']} "
            f"rejected={self.inbox_counts['rejected']} "
            f"failed={self.inbox_counts['failed']}"
        )
        if self.data_flow.get("last_processed_at"):
            lines.append(f"- last_processed_at: {self.data_flow['last_processed_at']}")
        lines.append(f"- cycle: {self.cycle}")
        for line in self.tools:
            lines.append(f"- {line.render()}")
        lines.append("")
        lines.append(f"capabilities_scope: {self.capabilities_scope}")
        lines.append("## Quality")
        for key, value in self.quality.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)


def _launchd_status(label: str = "com.ethan.lwm.harvest") -> dict[str, Any]:
    """Best-effort: query launchctl for the bundled harvest agent."""

    if not shutil_which("launchctl"):
        return {"loaded": False, "label": label, "present": False}
    try:
        completed = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"loaded": False, "label": label, "present": False}
    pid = exit_code = None
    for line in completed.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[-1] == label:
            if parts[0].isdigit():
                pid = int(parts[0])
            if len(parts) >= 3 and parts[1].isdigit():
                exit_code = int(parts[1])
            launchd = {
                "loaded": True,
                "label": label,
                "pid": pid,
                "last_exit_code": exit_code,
                "has_history": False,
            }
            if pid and pid > 0:
                return launchd
            return _launchd_status_from_print(label, launchd)
    return _launchd_status_from_print(label, {"loaded": False, "label": label})


def _launchd_status_from_print(label: str, base: dict[str, Any]) -> dict[str, Any]:
    """Fallback when ``launchctl list`` shows an idle job or no PID."""

    try:
        completed = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return base
    if completed.returncode != 0:
        return base
    payload = completed.stdout
    history = {
        "loaded": True,
        "label": label,
        "has_history": "runs =" in payload or "last exit code =" in payload,
        "running": "state = running" in payload,
    }
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if line.startswith("last exit code ="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                history["last_exit_code"] = int(value)
        elif line.startswith("runs ="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                history["runs"] = int(value)
        elif line.startswith("pid ="):
            value = line.split("=", 1)[1].strip()
            if value.isdigit():
                history["pid"] = int(value)
    return {**base, **history}


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def _stale_test_launch_agents(*, home: Path | None = None) -> tuple[str, ...]:
    """Return generated LaunchAgents that still target pytest runtime roots."""

    base = home if home is not None else Path(os.environ.get("HOME", str(Path.home())))
    launch_agents = base / "Library" / "LaunchAgents"
    if not launch_agents.is_dir():
        return ()
    stale: list[str] = []
    for plist in sorted(launch_agents.glob("com.ethan.lwm.*.plist")):
        try:
            text = plist.read_text(encoding="utf-8")
        except OSError:
            continue
        if "/llm-workmem-runtime/test_" in text:
            stale.append(str(plist))
    return tuple(stale)


def _tool_sync(index: dict[str, dict[str, Any]]) -> tuple[ToolSync, ...]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for entry in index.values():
        tool = str(entry.get("tool") or "unknown")
        by_tool.setdefault(tool, []).append(entry)
    out: list[ToolSync] = []
    for tool, rows in sorted(by_tool.items()):
        rows.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        latest = rows[0]
        out.append(
            ToolSync(
                tool=tool,
                last_event_at=str(latest.get("timestamp") or ""),
                last_event_type=str(latest.get("event_type") or ""),
                last_project_id=str(latest.get("project_id") or ""),
                event_count=len(rows),
            )
        )
    return tuple(out)


def _audit_summary(root: Path, audit_report: AuditReport | None = None) -> dict[str, Any]:
    try:
        report = audit_report or run_audit(
            root,
            eval_suite=packaged_eval_suite(),
            eval_mode="quick",
        )
    except Exception as exc:  # noqa: BLE001
        return {"audit_ok": False, "eval_verified": False, "error": str(exc)}
    return {
        "audit_ok": bool(report.ok),
        "issues": int(report.analysis_errors + report.schema_issues + report.review_items),
        "issue_breakdown": {
            "analysis_errors": report.analysis_errors,
            "schema_issues": report.schema_issues,
            "review_items": report.review_items,
        },
        "source_gaps": {
            "local": report.source_gaps_local,
            "external": report.source_gaps_external,
        },
        "eval_pass": report.eval_pass,
        "eval_total": report.eval_total,
        "eval_verified": report.eval_total > 0,
    }


def _llms_txt_state(root: Path) -> dict[str, Any]:
    path = root / "llms.txt"
    if not path.is_file():
        return {"exists": False}
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return {"exists": True, "size_bytes": stat.st_size, "mtime": mtime}


def _cbmem_state(root: Path) -> dict[str, Any]:
    path = root / "state" / "cbmem-health.json"
    if not path.is_file():
        return {"status": "unverified"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid"}
    if not isinstance(payload, dict):
        return {"status": "invalid"}
    return {
        "status": payload.get("status", "unknown"),
        "projects": len(payload.get("projects", {})) if isinstance(payload.get("projects"), dict) else 0,
        "checked_at": payload.get("checked_at"),
    }


def _privacy_rejection_rate(inbox_counts: dict[str, int]) -> float:
    total_seen = inbox_counts["processed"] + inbox_counts["rejected"] + inbox_counts["failed"]
    if total_seen == 0:
        return 0.0
    return inbox_counts["rejected"] / total_seen


def _rejection_breakdown(root: Path) -> dict[str, int]:
    """Count quarantine reasons instead of treating every rejection as privacy."""

    counts: dict[str, int] = {}
    rejected = inbox.events_root(root) / "rejected"
    if not rejected.is_dir():
        return counts
    for reason_file in rejected.rglob("*.json.reason"):
        try:
            reason = reason_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if reason.startswith("privacy:"):
            key = "privacy_blocked"
        elif reason.startswith("duplicate:"):
            key = "duplicate"
        elif reason.startswith("invalid") or "." in reason.split(":", 1)[0]:
            key = "invalid"
        else:
            key = "other"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _privacy_rate_from_breakdown(breakdown: dict[str, int], counts: dict[str, int]) -> float:
    total = counts["processed"] + counts["rejected"] + counts["failed"]
    return (breakdown.get("privacy_blocked", 0) / total) if total else 0.0


def _classify(snapshot: dict[str, Any], *, strict: bool = False) -> str:
    infra = snapshot["infrastructure"]
    data = snapshot["data_flow"]
    quality = snapshot["quality"]
    if infra.get("stale_test_launch_agents"):
        return STATUS_FAILED
    if quality.get("error"):
        return STATUS_FAILED
    cycle = snapshot.get("cycle", {})
    if cycle.get("last_status") in {"failed", "failed_core"} or cycle.get("core_status") == "failed_core":
        return STATUS_FAILED
    if infra.get("schedule_expected", "launchd" in infra) and not infra.get("launchd", {}).get("loaded"):
        return STATUS_DEGRADED
    if not quality.get("audit_ok"):
        # Review candidates and source gaps are quality work, not evidence-core
        # corruption. Keep the hub usable and visible as degraded; only the
        # explicit core/runtime failures below may make strict health fail.
        return STATUS_DEGRADED
    cycle = snapshot.get("cycle", {})
    if strict:
        if cycle.get("last_status") in {"failed", "failed_core"} or cycle.get("core_status") == "failed_core":
            return STATUS_FAILED
        if cycle.get("due") or not cycle.get("last_success_at"):
            return STATUS_DEGRADED
        if not quality.get("eval_verified"):
            return STATUS_DEGRADED
        if quality.get("eval_total", 0) <= 0 or quality.get("eval_pass") != quality.get("eval_total"):
            return STATUS_DEGRADED
        if cycle.get("context_smoke_ok") is not True:
            return STATUS_DEGRADED
        if cycle.get("last_cycle_exit_code") != 0:
            return STATUS_DEGRADED
        if cycle.get("runtime_import_independent") is not True:
            return STATUS_DEGRADED
        if data.get("last_cycle_failed", 0) != 0:
            return STATUS_DEGRADED
        if cycle.get("loop_exit_state") in {None, "human_required", "blocked"}:
            return STATUS_DEGRADED
        if quality.get("cbmem", {}).get("status") not in {"healthy", "not_configured"}:
            return STATUS_DEGRADED
        if cycle.get("last_status") == "success_with_warnings":
            return STATUS_DEGRADED
    if inbox_counts(snapshot)["inbox"] > 100:
        return STATUS_DEGRADED
    if data.get("last_processed_at") is None and inbox_counts(snapshot)["inbox"] > 0:
        return STATUS_DEGRADED
    return STATUS_HEALTHY


def inbox_counts(snapshot: dict[str, Any]) -> dict[str, int]:
    return snapshot.get("inbox_counts", {})  # type: ignore[return-value]


def _last_processed_at(events_root_path: Path) -> str | None:
    base = events_root_path / "processed"
    if not base.is_dir():
        return None
    candidates: list[tuple[str, Path]] = []
    for day_dir in base.iterdir():
        if not day_dir.is_dir():
            continue
        for path in day_dir.glob("*.json"):
            candidates.append((path.name, path))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[0][0]


def collect(
    root: Path,
    *,
    strict: bool = False,
    audit_report: AuditReport | None = None,
    cycle_override: dict[str, Any] | None = None,
) -> HealthSnapshot:
    root = root.resolve()
    status_inbox = inbox.inbox_status(root)
    counts = {
        "inbox": status_inbox.inbox,
        "processed": status_inbox.processed,
        "rejected": status_inbox.rejected,
        "failed": status_inbox.failed,
    }
    index = dedup.load_event_index(root)
    tools = _tool_sync(index)
    v2_receipt = load_latest(root)
    last_attempt = load_last_attempt(root)
    receipt = read_receipt(root)
    loop_state = read_active(root) or read_last(root)
    rejection_breakdown = _rejection_breakdown(root)
    receipt_is_v2 = (
        isinstance(v2_receipt, dict)
        and v2_receipt.get("schema_version") == 2
    ) or (
        isinstance(last_attempt, dict)
        and last_attempt.get("schema_version") == 2
    )
    def cycle_time(value: dict[str, Any]) -> float:
        try:
            parsed = datetime.fromisoformat(str(value.get("finished_at") or "").replace("Z", "+00:00"))
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).timestamp()
        except (ValueError, TypeError):
            return 0.0

    v2_candidates = [value for value in (v2_receipt, last_attempt)
                     if isinstance(value, dict) and value.get("schema_version") == 2]
    latest_cycle = max(v2_candidates, key=cycle_time) if v2_candidates else receipt
    latest_cycle_is_attempt = latest_cycle is last_attempt and isinstance(last_attempt, dict)
    latest_status = (
        latest_cycle.get("core_status")
        if receipt_is_v2
        else latest_cycle.get("status") if latest_cycle else None
    ) if isinstance(latest_cycle, dict) else None
    latest_finished = (
        latest_cycle.get("finished_at") if isinstance(latest_cycle, dict) else None
    )
    latest_quality = (
        latest_cycle.get("quality")
        if receipt_is_v2 and isinstance(latest_cycle, dict)
        else None
    )
    if not isinstance(latest_quality, dict):
        latest_quality = {}
    cycle = {
        "due": is_due(root),
        "last_status": latest_status,
        "core_status": latest_cycle.get("core_status") if receipt_is_v2 else None,
        "receipt_schema_version": 2 if receipt_is_v2 else 1 if receipt else None,
        "last_success_at": (
            v2_receipt.get("finished_at") if isinstance(v2_receipt, dict)
            and v2_receipt.get("core_status") == "success"
            else latest_finished if latest_status == "success" else None
        ),
        "last_receipt_id": (
            latest_cycle.get("receipt_id") or latest_cycle.get("cycle_id")
            if isinstance(latest_cycle, dict)
            else None
        ),
        "last_reason": latest_cycle.get("reason") if isinstance(latest_cycle, dict) else None,
        "loop_id": loop_state.loop_id if loop_state else None,
        "loop_phase": loop_state.phase if loop_state else None,
        "loop_exit_state": loop_state.exit_state if loop_state else None,
        "loop_objective": loop_state.objective if loop_state else None,
        "loop_next_action": loop_state.next_action if loop_state else None,
        "loop_evidence_count": len(loop_state.evidence) if loop_state else 0,
        "loop_human_gate": loop_state.human_gate if loop_state else False,
        "last_attempt_id": last_attempt.get("cycle_id") if isinstance(last_attempt, dict) else None,
        "last_attempt_status": last_attempt.get("core_status") if isinstance(last_attempt, dict) else None,
        "last_attempt_is_current": latest_cycle_is_attempt,
        "context_smoke_ok": latest_quality.get("context_ok"),
        "last_cycle_exit_code": latest_cycle.get("exit_code") if receipt_is_v2 else None,
        "runtime_import_independent": (
            latest_cycle.get("runtime_import_independent") if receipt_is_v2 else None
        ),
    }
    if cycle_override:
        cycle.update(cycle_override)
    last_processed = _last_processed_at(inbox.events_root(root))
    health_path = root / "state" / "health.json"
    last_health_mtime = (
        datetime.fromtimestamp(health_path.stat().st_mtime, tz=timezone.utc).isoformat()
        if health_path.is_file()
        else None
    )
    audit_summary = (
        _audit_summary(root, audit_report)
        if audit_report is not None
        else _audit_summary(root)
    )
    snapshot_dict: dict[str, Any] = {
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "infrastructure": {
            "launchd": _launchd_status(),
            "schedule_expected": (root / "state" / "scheduler-owner.json").is_file(),
            "stale_test_launch_agents": _stale_test_launch_agents(),
            "last_health_json_mtime": last_health_mtime,
            "pid": os.getpid(),
        },
        "data_flow": {
            "last_processed_at": last_processed,
            "event_index_entries": len(index),
            "last_cycle_failed": counts["failed"],
        },
        "cycle": cycle,
        "inbox_counts": counts,
        "quality": {
            **audit_summary,
            "llms_txt": _llms_txt_state(root),
            "privacy_rejection_rate": _privacy_rate_from_breakdown(rejection_breakdown, counts),
            "rejection_breakdown": rejection_breakdown,
            "cbmem": _cbmem_state(root),
        },
        "tools": [
            {
                "tool": t.tool,
                "last_event_at": t.last_event_at,
                "last_event_type": t.last_event_type,
                "last_project_id": t.last_project_id,
                "event_count": t.event_count,
            }
            for t in tools
        ],
        # Health is a runtime-wide host view, not a project-scoped report.
        # Project-specific proof remains available through `hub coverage
        # --project-id`; filtering here made healthy host receipts appear
        # unverified simply because they belonged to another project.
        "capabilities": capabilities.summary(root, project_path=None),
        "capabilities_scope": "all_projects",
    }
    status = _classify(snapshot_dict, strict=strict)
    return HealthSnapshot(
        status=status,
        checked_at=snapshot_dict["checked_at"],
        infrastructure=snapshot_dict["infrastructure"],
        data_flow=snapshot_dict["data_flow"],
        cycle=cycle,
        capabilities=snapshot_dict["capabilities"],
        quality=snapshot_dict["quality"],
        tools=tools,
        inbox_counts=counts,
        capabilities_scope=str(snapshot_dict["capabilities_scope"]),
    )


def write_snapshot(snapshot: HealthSnapshot) -> Path:
    target = snapshot.infrastructure.get("root_dir", Path(".")) / "state" / "health.json"
    # Caller is responsible for passing root; we recover from the data
    # field if present, otherwise fall back to current dir.
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "infrastructure": snapshot.infrastructure,
        "data_flow": snapshot.data_flow,
        "cycle": snapshot.cycle,
        "capabilities": snapshot.capabilities,
        "capabilities_scope": snapshot.capabilities_scope,
        "inbox_counts": snapshot.inbox_counts,
        "quality": snapshot.quality,
        "tools": [
            {
                "tool": t.tool,
                "last_event_at": t.last_event_at,
                "last_event_type": t.last_event_type,
                "last_project_id": t.last_project_id,
                "event_count": t.event_count,
            }
            for t in snapshot.tools
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def collect_and_write(
    root: Path,
    *,
    now: datetime | None = None,
    strict: bool = False,
    audit_report: AuditReport | None = None,
    cycle_override: dict[str, Any] | None = None,
) -> HealthSnapshot:
    """Snapshot the system and persist ``state/health.json`` + side files."""

    # Always keep ``state/promotion-state.json`` present so consumers can
    # rely on it existing. Initialise with an empty approved/rejected
    # list if we have not seen any promotion yet.
    from lwm import promote as _promote

    state_path = _promote._promotion_state_path(root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if not state_path.is_file():
        _promote.save_promotion_state(
            root, {"approved": [], "rejected": []}
        )
    snapshot = collect(
        root,
        strict=strict,
        audit_report=audit_report,
        cycle_override=cycle_override,
    )
    health_path = root / "state" / "health.json"
    payload = {
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "infrastructure": snapshot.infrastructure,
        "data_flow": snapshot.data_flow,
        "cycle": snapshot.cycle,
        "capabilities": snapshot.capabilities,
        "capabilities_scope": snapshot.capabilities_scope,
        "inbox_counts": snapshot.inbox_counts,
        "quality": snapshot.quality,
        "tools": [
            {
                "tool": t.tool,
                "last_event_at": t.last_event_at,
                "last_event_type": t.last_event_type,
                "last_project_id": t.last_project_id,
                "event_count": t.event_count,
            }
            for t in snapshot.tools
        ],
    }
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Also keep `infrastructure` aware of the root path for write_snapshot.
    return HealthSnapshot(
        status=snapshot.status,
        checked_at=snapshot.checked_at,
        infrastructure={**snapshot.infrastructure, "root_dir": str(root)},
        data_flow=snapshot.data_flow,
        cycle=snapshot.cycle,
        capabilities=snapshot.capabilities,
        quality=snapshot.quality,
        tools=snapshot.tools,
        inbox_counts=snapshot.inbox_counts,
        capabilities_scope=snapshot.capabilities_scope,
    )


__all__ = [
    "HealthSnapshot",
    "STATUS_DEGRADED",
    "STATUS_FAILED",
    "STATUS_HEALTHY",
    "STATUS_UNKNOWN",
    "ToolSync",
    "collect",
    "collect_and_write",
    "write_snapshot",
]
