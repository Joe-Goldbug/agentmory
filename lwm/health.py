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
from lwm.audit import run_audit
from lwm.cycle_state import is_due, read_receipt
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


def _audit_summary(root: Path) -> dict[str, Any]:
    try:
        report = run_audit(root, eval_suite=None, eval_mode="quick")
    except Exception as exc:  # noqa: BLE001
        return {"audit_ok": False, "error": str(exc)}
    return {
        "audit_ok": bool(report.ok),
        "issues": int(report.analysis_errors + report.schema_issues + report.review_items),
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
    if infra.get("audit", {}).get("error") or not quality.get("audit_ok"):
        return STATUS_FAILED
    cycle = snapshot.get("cycle", {})
    if strict:
        if cycle.get("last_status") == "failed":
            return STATUS_FAILED
        if cycle.get("due") or not cycle.get("last_success_at"):
            return STATUS_DEGRADED
        if cycle.get("loop_exit_state") in {None, "human_required", "blocked"}:
            return STATUS_DEGRADED
        if quality.get("cbmem", {}).get("status") not in {"healthy", "not_configured"}:
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


def collect(root: Path, *, strict: bool = False) -> HealthSnapshot:
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
    receipt = read_receipt(root)
    loop_state = read_active(root) or read_last(root)
    rejection_breakdown = _rejection_breakdown(root)
    cycle = {
        "due": is_due(root),
        "last_status": receipt.get("status") if receipt else None,
        "last_success_at": receipt.get("finished_at") if receipt and receipt.get("status") == "success" else None,
        "last_receipt_id": receipt.get("receipt_id") if receipt else None,
        "last_reason": receipt.get("reason") if receipt else None,
        "loop_id": loop_state.loop_id if loop_state else None,
        "loop_phase": loop_state.phase if loop_state else None,
        "loop_exit_state": loop_state.exit_state if loop_state else None,
        "loop_objective": loop_state.objective if loop_state else None,
        "loop_next_action": loop_state.next_action if loop_state else None,
        "loop_evidence_count": len(loop_state.evidence) if loop_state else 0,
        "loop_human_gate": loop_state.human_gate if loop_state else False,
    }
    last_processed = _last_processed_at(inbox.events_root(root))
    health_path = root / "state" / "health.json"
    last_health_mtime = (
        datetime.fromtimestamp(health_path.stat().st_mtime, tz=timezone.utc).isoformat()
        if health_path.is_file()
        else None
    )
    snapshot_dict: dict[str, Any] = {
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "infrastructure": {
            "launchd": _launchd_status(),
            "last_health_json_mtime": last_health_mtime,
            "pid": os.getpid(),
        },
        "data_flow": {
            "last_processed_at": last_processed,
            "event_index_entries": len(index),
        },
        "cycle": cycle,
        "inbox_counts": counts,
        "quality": {
            **_audit_summary(root),
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
        "capabilities": capabilities.summary(root, project_path=root),
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


def collect_and_write(root: Path, *, now: datetime | None = None, strict: bool = False) -> HealthSnapshot:
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
    snapshot = collect(root, strict=strict)
    health_path = root / "state" / "health.json"
    payload = {
        "status": snapshot.status,
        "checked_at": snapshot.checked_at,
        "infrastructure": snapshot.infrastructure,
        "data_flow": snapshot.data_flow,
        "cycle": snapshot.cycle,
        "capabilities": snapshot.capabilities,
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
