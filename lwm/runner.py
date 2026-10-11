"""One installed-runtime cycle for the LLM-WorkMem LaunchAgent."""

from __future__ import annotations

import json
import hashlib
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lwm import lockfile
from lwm import lifecycle
from lwm.audit import AuditReport
from lwm.context import build as build_context
from lwm.export import write_ai_exports
from lwm.adapters import write_global_adapters
from lwm.cbmem_bridge import sync_registered_projects
from lwm.cycle_receipt import (
    CycleReceiptV2,
    SourceResult,
    StageResult,
    derive_core_status,
    make_cycle_id,
    write_cycle_receipt,
)
from lwm.ingest import run as ingest_run
from lwm.loop_state import begin_loop, close_loop, record_evaluation, write_state
from lwm.insights import load_processed_events
from lwm.memory_compiler import analyze_pending
from lwm.project_memory import rebuild_project_pages
from lwm.structured_candidates import generate_candidates, seed_analysis_candidates
from lwm.tool_registry import ToolRegistry, default_registry
from lwm.registry import load as load_projects
from lwm.watch import render_watch_report, run_watch


@dataclass(frozen=True)
class CycleRunReport:
    """The bounded cycle result before the immutable receipt is committed."""

    code: int
    sources: tuple[SourceResult, ...]
    stages: tuple[StageResult, ...]
    degraded_sources: tuple[str, ...] = ()
    quality_warning: bool = False
    context_ok: bool = True
    raw_writable: bool = True
    recall_ok: bool = True
    errors: tuple[str, ...] = ()
    counts: dict[str, int] | None = None
    audit_report: AuditReport | None = None
    context_output: str = ""
    analysis_report: dict[str, Any] | None = None


# Legacy alias kept so external tests still iterate ``runner.ADAPTER_MODULES``.
# The data now comes from the versioned Tool Registry. Hook-only tools have no
# polling module and are handled by their native hook or dedicated sweep.
def _adapter_modules_from_registry() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Materialize runner's adapter list from the versioned Tool Registry.

    Each enabled collector module becomes one tuple entry. A tool definition
    with multiple collectors therefore yields multiple real subprocesses.
    """

    registry = default_registry()
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for definition in registry.all():
        if not definition.enabled or not definition.collector_modules:
            continue
        for module in definition.collector_modules:
            extra: tuple[str, ...] = ()
            rows.append((definition.tool_id, module, extra))
    return tuple(rows)


def _adapter_modules_for(root: Path) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Resolve collectors from the root's persisted registry when present."""

    registry = ToolRegistry.load(root)
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for definition in registry.enabled():
        for module in definition.collector_modules:
            rows.append((definition.tool_id, module, ()))
    return tuple(rows)


def _observer_modules_for(root: Path) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Resolve read-only host observers from the persisted registry.

    Observers are separate from collectors because a native-hook host may
    still need a local metadata sweep, but that sweep must not be treated as
    a proof-producing integration.
    """

    registry = ToolRegistry.load(root)
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for definition in registry.enabled():
        for module in definition.observer_modules:
            rows.append((definition.tool_id, module, ()))
    return tuple(rows)


ADAPTER_MODULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    _adapter_modules_from_registry()
)


def _run_adapter(name: str, module: str, root: Path, extra: tuple[str, ...]) -> tuple[int, str]:
    project_paths: tuple[str | None, ...]
    if module in {
        "adapters.hooks.vscode_tasks",
        "adapters.hooks.cursor_tasks",
    }:
        # These collectors read a project-owned .llm-workmem/events.jsonl.
        # Running them without a registered project used to produce a parser
        # error and made a missing project look like a broken adapter.
        projects = load_projects(root)
        project_paths = tuple(
            str(row.get("canonical_path"))
            for row in projects.values()
            if isinstance(row, dict) and str(row.get("canonical_path") or "").strip()
        )
        if not project_paths:
            return 0, f"adapter {name}: no registered projects"
    else:
        project_paths = (None,)

    statuses: list[int] = []
    details: list[str] = []
    for project_path in project_paths:
        args = [sys.executable, "-I", "-m", module, "--root", str(root)]
        if extra:
            args.extend([extra[0], str(root)])
        if project_path is not None:
            args.extend(["--project", project_path])
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 1, f"adapter {name}: {exc}"
        statuses.append(result.returncode)
        detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")
        if detail:
            details.append(detail[:180])
    return (max(statuses) if statuses else 0), f"adapter {name}: {('; '.join(details))[:240] or 'ok'}"


def _sweep_shell_events(root: Path) -> int:
    shell_dir = root / "raw" / "shell"
    if not shell_dir.is_dir():
        return 0
    seen_path = root / "state" / "shell-session-events.json"
    try:
        payload = json.loads(seen_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = []
    seen = set(payload) if isinstance(payload, list) else set()
    rc = 0
    for jsonl in sorted(shell_dir.glob("*.jsonl")):
        for line_number, line in enumerate(
            jsonl.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                # Older shell hooks wrote plain-text history into this folder,
                # and an active hook can also leave a temporarily partial line.
                # Preserve that source evidence, but do not fail the whole cycle.
                continue
            try:
                # Keep compatibility with the old key format while using a
                # line-content key that cannot collapse repeated commands.
                legacy_key = ":".join(
                    str(value)
                    for value in (
                        jsonl.name,
                        payload.get("ts"),
                        payload.get("session"),
                        payload.get("command"),
                    )
                )
                event_key = f"{jsonl.name}:{line_number}:{hashlib.sha256(line.encode('utf-8')).hexdigest()}"
                if event_key in seen or legacy_key in seen:
                    continue
                project_path = str(payload.get("pwd") or root)
                session_id = str(payload.get("session") or jsonl.stem)
                tool = _shell_tool_for_command(
                    str(payload.get("command") or ""), root=root
                )
                lifecycle.start(
                    root,
                    tool=tool,
                    project_path=project_path,
                    session_id=session_id,
                    source="watcher-observed",
                )
                event = {
                    "tool": tool,
                    "project_path": project_path,
                    "session_id": session_id,
                    "event_type": "workflow_observation",
                    "task": payload.get("task") or payload.get("command", ""),
                    "importance": "project",
                    "privacy": "sanitized",
                    "source": {"kind": "shell-sweep", "path": jsonl.name},
                    "tags": ["shell"],
                }
                result = subprocess.run(
                    [sys.executable, "-I", "-m", "lwm.cli", "hub", "record", json.dumps(event), "--root", str(root)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                rc |= result.returncode
                if result.returncode == 0:
                    lifecycle.stop(
                        root,
                        tool=tool,
                        project_path=project_path,
                        session_id=session_id,
                        task="Shell command observed complete",
                        source="watcher-observed",
                    )
                    seen.add(event_key)
            except (OSError, subprocess.TimeoutExpired):
                rc |= 1
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return rc


def _shell_tool_for_command(command: str, *, root: Path | None = None) -> str:
    """Infer a registered CLI identity without retaining the full command.

    Alias resolution must come from the versioned registry, otherwise a new
    registered CLI can still be written as generic ``shell`` evidence.
    """

    registry = ToolRegistry.load(root) if root is not None else default_registry()
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for token in tokens[:6]:
        name = Path(token).name.lower()
        definition = registry.resolve(name)
        if definition and set(definition.surfaces).intersection({"cli", "shell"}):
            return definition.tool_id
    return "shell"


def _run_cycle_stages(root: Path) -> CycleRunReport:
    root = root.resolve()
    sources: list[SourceResult] = []
    stages: list[StageResult] = []
    degraded: list[str] = []
    errors: list[str] = []
    code = 0
    registry = ToolRegistry.load(root)
    for kind, modules in (
        ("collector", _adapter_modules_for(root)),
        ("observer", _observer_modules_for(root)),
    ):
        for name, module, extra in modules:
            adapter_rc, detail = _run_adapter(name, module, root, extra)
            print(detail)
            if kind == "observer":
                source_name = f"{name}:observer"
                if any(s.name == source_name for s in sources):
                    source_name = f"{source_name}:{module}"
            else:
                source_name = name if not any(s.name == name for s in sources) else f"{name}:{module}"
            if adapter_rc:
                degraded.append(name)
                errors.append(detail)
            sources.append(
                SourceResult(
                    name=source_name,
                    status="degraded" if adapter_rc else "ok",
                    detail=detail,
                    error=detail if adapter_rc else "",
                )
            )

    shell_rc = _sweep_shell_events(root)
    sources.append(
        SourceResult(
            name="shell",
            status="degraded" if shell_rc else "ok",
            detail="shell lifecycle sweep",
            error="shell sweep failed" if shell_rc else "",
        )
    )
    if shell_rc:
        degraded.append("shell")
        errors.append("shell sweep failed")

    for definition in registry.enabled():
        if (
            not definition.collector_modules
            and not definition.observer_modules
            and definition.capture_mode in {"native_hook", "shell_lifecycle"}
        ):
            sources.append(
                SourceResult(
                    name=definition.tool_id,
                    status="hook_only",
                    detail=f"captured by {definition.capture_mode}",
                )
            )

    cbmem_report = sync_registered_projects(root)
    print(f"cbmem: {cbmem_report.get('status')} projects={len(cbmem_report.get('projects', {}))}")
    cbmem_status = str(cbmem_report.get("status") or "unknown")
    if cbmem_report.get("projects") and cbmem_status in {"failed", "unavailable", "degraded"}:
        degraded.append("cbmem")
        errors.append(f"cbmem: {cbmem_status}")
    stages.append(StageResult(name="cbmem", status="degraded" if cbmem_status in {"failed", "unavailable", "degraded"} else "ok", detail=cbmem_status))

    ingest = ingest_run(root, with_lock=True)
    print(ingest.render())
    ingest_failed = bool(ingest.failed)
    if ingest.failed:
        code = max(code, 3)
        errors.append("ingest failed")
    stages.append(StageResult(name="ingest", status="failed" if ingest_failed else "ok", detail=ingest.render()))

    try:
        rebuild = rebuild_project_pages(root)
        stages.append(
            StageResult(
                name="project-rebuild",
                status="ok",
                detail=f"written={rebuild.pages_written} removed={rebuild.pages_removed}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        degraded.append("project-rebuild")
        errors.append(f"project-rebuild: {exc}")
        stages.append(StageResult(name="project-rebuild", status="degraded", error=str(exc)))

    try:
        processed_events = load_processed_events(root)
        candidate_paths = generate_candidates(root, processed_events)
        analysis_paths = seed_analysis_candidates(root, processed_events)
        stages.append(
            StageResult(
                name="candidate-synthesis",
                status="ok",
                detail=(
                    f"written={len(candidate_paths)} "
                    f"analysis_seeded={len(analysis_paths)}"
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001
        degraded.append("candidate-synthesis")
        errors.append(f"candidate-synthesis: {exc}")
        stages.append(StageResult(name="candidate-synthesis", status="degraded", error=str(exc)))

    analysis_report: dict[str, Any] | None = None
    try:
        # The compiler is optional: disabled or unavailable analysis must leave
        # deterministic memory and the core cycle usable.
        analysis_report = analyze_pending(root)
        analysis_status = str(analysis_report.get("status") or "analysis_pending")
        analysis_errors = list(analysis_report.get("errors") or [])
        dead_letter = list(analysis_report.get("dead_letter") or [])
        analysis_degraded = bool(analysis_errors or dead_letter)
        if analysis_degraded:
            degraded.append("analysis")
            errors.append(
                "analysis: "
                + ", ".join(
                    [str(item) for item in analysis_errors[:3] + dead_letter[:3]]
                )
            )
        stages.append(
            StageResult(
                name="optional-analysis",
                status="warning" if analysis_degraded else analysis_status,
                detail=(
                    f"analyzed={len(analysis_report.get('analyzed') or ())} "
                    f"deferred={len(analysis_report.get('deferred') or ())} "
                    f"dead_letter={len(dead_letter)}"
                ),
                error="; ".join(str(item) for item in analysis_errors[:3]),
            )
        )
    except Exception as exc:  # noqa: BLE001
        # A provider failure is an optional-stage warning, not a core failure.
        analysis_report = {"status": "error", "errors": [str(exc)]}
        degraded.append("analysis")
        errors.append(f"analysis: {exc}")
        stages.append(StageResult(name="optional-analysis", status="warning", error=str(exc)))

    watch = run_watch(root, eval_suite=None, eval_mode="standard")
    print(render_watch_report(watch))
    federation = getattr(watch, "federation", None) or {}
    if federation.get("status") == "error":
        degraded.append("memory-federation")
        errors.append(f"memory-federation: {federation.get('error', 'unknown error')}")
    stages.append(
        StageResult(
            name="memory-federation",
            status="degraded" if federation.get("status") == "error" else "ok",
            detail=(
                f"release={federation.get('release_id', 'none')} "
                f"active={federation.get('active', 0)} "
                f"conflicted={federation.get('conflicted', 0)}"
            ),
            error=str(federation.get("error", "")),
        )
    )
    context_ok = True
    context_output = ""
    try:
        context_smoke = build_context(root, tool="supervisor", project_path=None, format="json")
        context_ok = context_smoke.ok
        context_output = context_smoke.markdown
        if not context_ok:
            degraded.append("context")
            errors.append("context smoke returned empty output")
        stages.append(StageResult(name="context-smoke", status="ok" if context_ok else "degraded"))
    except Exception as exc:  # noqa: BLE001
        context_ok = False
        degraded.append("context")
        errors.append(f"context: {exc}")
        stages.append(StageResult(name="context-smoke", status="degraded", error=str(exc)))

    quality_warning = not bool(watch.audit.ok) or not context_ok
    if quality_warning:
        degraded.append("audit")
        errors.append("audit/eval quality checks did not pass")
    stages.append(StageResult(name="audit", status="degraded" if quality_warning else "ok", detail="watch completed"))

    try:
        export_report = write_ai_exports(root)
        stages.append(StageResult(name="exports", status="ok", detail=f"pages={export_report.pages}"))
    except Exception as exc:  # noqa: BLE001
        degraded.append("exports")
        errors.append(f"exports: {exc}")
        stages.append(StageResult(name="exports", status="degraded", error=str(exc)))

    try:
        write_global_adapters(root)
        stages.append(StageResult(name="adapter-render", status="ok"))
    except Exception as exc:  # noqa: BLE001
        degraded.append("adapter-render")
        errors.append(f"adapter-render: {exc}")
        stages.append(StageResult(name="adapter-render", status="degraded", error=str(exc)))

    raw_events = root / "raw" / "events" / "inbox"
    raw_writable = True
    try:
        raw_events.mkdir(parents=True, exist_ok=True)
        raw_writable = raw_events.is_dir()
    except OSError:
        raw_writable = False
    if not raw_writable:
        code = max(code, 1)
        errors.append("raw evidence inbox is not writable")

    processed_count = _ingest_count(ingest, "processed_count", "processed")
    rejected_count = _ingest_count(ingest, "rejected_count", "rejected")
    failed_count = _ingest_count(ingest, "failed_count", "failed")
    counts = {
        "processed": processed_count,
        "accepted": processed_count,
        "rejected": rejected_count,
        "failed": failed_count,
    }
    audit_report = watch.audit if isinstance(watch.audit, AuditReport) else None
    return CycleRunReport(
        code=code,
        sources=tuple(sources),
        stages=tuple(stages),
        degraded_sources=tuple(dict.fromkeys(degraded)),
        quality_warning=quality_warning,
        context_ok=context_ok,
        raw_writable=raw_writable,
        recall_ok=not ingest_failed,
        errors=tuple(errors),
        counts=counts,
        audit_report=audit_report,
        context_output=context_output,
        analysis_report=analysis_report,
    )


def _health_payload(root: Path) -> dict[str, Any]:
    path = root / "state" / "health.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _ingest_count(report: Any, count_attr: str, collection_attr: str) -> int:
    """Read an ingest count without confusing tuples or legacy test doubles."""

    value = getattr(report, count_attr, None)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    collection = getattr(report, collection_attr, ())
    if isinstance(collection, (tuple, list, set, dict)):
        return len(collection)
    return int(collection) if isinstance(collection, bool) else 0


def _loop_evidence(root: Path) -> tuple[str, ...]:
    candidates = (
        root / "state" / "health.json",
        root / "state" / "receipts" / "latest-cycle.json",
        root / "llms.txt",
        root / "llms.json",
    )
    return tuple(str(path.relative_to(root)) for path in candidates if path.is_file())


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _source_revision(root: Path) -> str:
    manifest = Path(sys.prefix).parent / "runtime-manifest.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        revision = str(payload.get("source_revision") or "")
        if revision and revision != "unknown":
            return revision
    except (OSError, json.JSONDecodeError):
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _runtime_probe() -> tuple[str, tuple[str, ...], bool]:
    try:
        import lwm

        module_path = str(Path(lwm.__file__).resolve())
    except (ImportError, OSError, AttributeError):
        return "", tuple(sys.path), False
    paths = tuple(str(Path(item).resolve()) if item else "" for item in sys.path)
    independent = "/Mobile Documents/" not in module_path and all(
        "/Mobile Documents/" not in item for item in paths
    )
    return module_path, paths, independent


def _eval_suite_hash() -> str:
    try:
        from lwm.eval import packaged_eval_suite

        return _sha256_bytes(packaged_eval_suite().read_bytes())
    except (OSError, ModuleNotFoundError):
        return ""


def _runtime_manifest_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "llm-workmem-runtime"
        / "app"
        / "runtime-manifest.json"
    )


def _write_context_artifact(root: Path, cycle_id: str, context_output: str) -> Path:
    target = root / "state" / "receipts" / "contexts" / f"{cycle_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "cycle_id": cycle_id,
        "format": "json",
        "content_sha256": _sha256_bytes(context_output.encode("utf-8")),
        "content": context_output,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _archive_health_snapshot(root: Path, cycle_id: str, health_path: Path) -> Path:
    target = root / "state" / "receipts" / "health" / f"{cycle_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(health_path.read_bytes())
    return target


def _evidence_hashes(root: Path, context_artifact: Path) -> dict[str, str]:
    candidates = [context_artifact]
    candidates.extend(sorted((root / "raw" / "events" / "processed").rglob("*.json")))
    candidates.extend(
        root / name
        for name in ("llms.txt", "llms-full.txt", "llms.json", "knowledge-digest.html")
    )
    candidates.append(root / "state" / "cbmem-health.json")
    hashes: dict[str, str] = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            hashes[path.resolve().relative_to(root.resolve()).as_posix()] = _sha256_file(path)
        except (OSError, ValueError):
            continue
    return hashes


def _commit_cycle_receipt(
    root: Path,
    report: CycleRunReport,
    *,
    cycle_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    health_sha256: str = "",
    health_snapshot_path: str = "",
    context_artifact: Path | None = None,
) -> Path:
    started_at = started_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    finished_at = finished_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    cycle_id = cycle_id or make_cycle_id()
    core_status = derive_core_status(
        raw_writable=report.raw_writable,
        all_recall_ok=report.recall_ok,
        receipt_committed=True,
        quality_warning=report.quality_warning,
        degraded_sources=report.degraded_sources,
    )
    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id=cycle_id,
        runtime_id=f"pid-{os.getpid()}",
        started_at=started_at,
        finished_at=finished_at,
        core_status=core_status,
        overall_status="degraded" if core_status == "success_with_warnings" else core_status,
        sources=report.sources,
        stages=report.stages,
        quality={
            "warning": report.quality_warning,
            "context_ok": report.context_ok,
            "audit_ok": bool(report.audit_report and report.audit_report.ok),
            "eval_pass": report.audit_report.eval_pass if isinstance(report.audit_report, AuditReport) else 0,
            "eval_total": report.audit_report.eval_total if isinstance(report.audit_report, AuditReport) else 0,
            "runtime_import_independent": _runtime_probe()[2],
        },
        analysis={
            "degraded_sources": list(report.degraded_sources),
            "compiler": report.analysis_report or {"status": "not_run"},
        },
        counts=report.counts or {},
        artifacts=("state/receipts/latest-cycle.json",),
        errors=report.errors,
        receipt_id=cycle_id,
        source_revision=_source_revision(root),
        runtime_manifest_path=str(_runtime_manifest_path()),
        runtime_manifest_sha256=(
            _sha256_file(_runtime_manifest_path())
            if _runtime_manifest_path().is_file()
            else ""
        ),
        runtime_module_path=_runtime_probe()[0],
        runtime_sys_path=_runtime_probe()[1],
        runtime_import_independent=_runtime_probe()[2],
        eval_suite_sha256=_eval_suite_hash(),
        context_sha256=(
            _sha256_bytes(report.context_output.encode("utf-8"))
            if report.context_output
            else ""
        ),
        health_sha256=health_sha256,
        health_snapshot_path=health_snapshot_path,
        evidence_hashes=_evidence_hashes(root, context_artifact) if context_artifact else {},
        exit_code=report.code,
    )
    return write_cycle_receipt(receipt, root)


def _run_cycle_unlocked(root: Path) -> int:
    """Run one bounded collection cycle after the writer lock is held."""

    root = root.resolve()
    started_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    loop = begin_loop(
        "scheduled memory refresh",
        constraints=("one bounded cycle", "preserve source evidence"),
        success_criteria=("audit passes", "health is healthy", "external evidence exists"),
        expected_observation="configured sources and runtime inputs are readable",
        expected_outcome="ingest, audit, export, and health leave fresh evidence",
    )
    write_state(root, loop)
    try:
        report = _run_cycle_stages(root)
        cycle_id = make_cycle_id()
        finished_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        context_artifact = _write_context_artifact(root, cycle_id, report.context_output)
        candidate_core = derive_core_status(
            raw_writable=report.raw_writable,
            all_recall_ok=report.recall_ok,
            receipt_committed=True,
            quality_warning=report.quality_warning,
            degraded_sources=report.degraded_sources,
        )
        previous = _health_payload(root)
        previous_cycle = previous.get("cycle") if isinstance(previous.get("cycle"), dict) else {}
        candidate_healthy = candidate_core == "success" and report.code == 0
        cycle_override = {
            "due": candidate_core not in {"success", "success_with_warnings"},
            "last_receipt_id": cycle_id,
            "last_status": candidate_core,
            "core_status": candidate_core,
            "last_success_at": finished_at if candidate_healthy else previous_cycle.get("last_success_at"),
            "context_smoke_ok": report.context_ok,
            "last_cycle_exit_code": report.code,
            "runtime_import_independent": _runtime_probe()[2],
            # The loop is closed after the health snapshot is written. Mark
            # this in-progress transaction explicitly so strict health does
            # not mistake the expected pre-close state for a failed loop.
            "loop_exit_state": "cycle_pending",
        }
        from lwm.health import collect_and_write

        if isinstance(report.audit_report, AuditReport):
            health = collect_and_write(
                root,
                strict=True,
                audit_report=report.audit_report,
                cycle_override=cycle_override,
            )
        else:
            health = collect_and_write(root, strict=True, cycle_override=cycle_override)
        print(health.render())
        health_path = root / "state" / "health.json"
        health_snapshot = _archive_health_snapshot(root, cycle_id, health_path)
        health_sha256 = _sha256_file(health_snapshot)
        receipt_path = _commit_cycle_receipt(
            root,
            report,
            cycle_id=cycle_id,
            started_at=started_at,
            finished_at=finished_at,
            health_sha256=health_sha256,
            health_snapshot_path=str(health_snapshot.relative_to(root)),
            context_artifact=context_artifact,
        )
        code = report.code
        if health.status == "failed":
            code = max(code, 1)
        if receipt_path.is_file():
            print(f"cycle receipt: {receipt_path}")
    except Exception as exc:  # noqa: BLE001
        failure = CycleRunReport(
            code=1,
            sources=(),
            stages=(StageResult(name="cycle", status="failed", error=str(exc)),),
            raw_writable=True,
            recall_ok=False,
            errors=(f"cycle exception: {exc}",),
            counts={"processed": 0, "accepted": 0, "rejected": 0, "failed": 1},
        )
        try:
            receipt_path = _commit_cycle_receipt(root, failure)
            print(f"cycle receipt: {receipt_path}")
        except Exception as receipt_exc:  # noqa: BLE001
            print(f"cycle receipt failed: {receipt_exc}")
        try:
            from lwm.health import collect_and_write

            collect_and_write(root)
        except Exception as health_exc:  # noqa: BLE001
            print(f"health failed after cycle exception: {health_exc}")
        evaluated = record_evaluation(
            loop,
            actual_observation=f"exception={exc}",
            actual_outcome="cycle failed and wrote a failed_core receipt",
            evidence=_loop_evidence(root),
            criteria_met=False,
            next_action="inspect the recorded exception and rerun the bounded cycle",
        )
        write_state(root, close_loop(evaluated, exit_state="human_required", human_gate=True))
        return 1

    payload = _health_payload(root)
    quality = payload.get("quality") if isinstance(payload.get("quality"), dict) else {}
    audit_ok = bool(quality.get("audit_ok"))
    health_status = str(payload.get("status") or "unknown")
    evidence = _loop_evidence(root)
    criteria_met = code == 0 and audit_ok and health_status == "healthy" and bool(evidence)
    actual = f"exit={code}; audit_ok={audit_ok}; health={health_status}; evidence={len(evidence)}"
    evaluated = record_evaluation(
        loop,
        actual_observation=actual,
        actual_outcome="verified scheduled refresh" if criteria_met else "verification incomplete",
        evidence=evidence,
        criteria_met=criteria_met,
        next_action="" if criteria_met else "inspect health, audit, and source/runtime evidence",
    )
    if criteria_met:
        exit_state = "completed_verified"
    elif not evidence or health_status == "unknown":
        exit_state = "human_required"
    else:
        exit_state = "continue"
    write_state(root, close_loop(evaluated, exit_state=exit_state, human_gate=exit_state == "human_required"))
    # A quality warning keeps the loop open for review but does not make the
    # scheduled process fail. Reserve non-zero exits for core failure or an
    # unknown state that genuinely needs human intervention.
    return max(code, 1) if exit_state == "human_required" else code


def run_cycle(root: Path) -> int:
    """Run one bounded collection cycle behind the shared cycle writer lock."""

    root = root.resolve()
    try:
        with lockfile.cycle_lock(root):
            return _run_cycle_unlocked(root)
    except lockfile.CycleLockBusyError as exc:
        # The supervisor or another explicit run-cycle already owns the write
        # boundary. Do not start a competing rebuild or receipt transaction.
        if exc.error:
            print(f"cycle lock unavailable: {exc}", file=sys.stderr)
            return 1
        return 0
