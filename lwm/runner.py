"""One installed-runtime cycle for the LLM-WorkMem LaunchAgent."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lwm import lifecycle
from lwm.adapters import write_global_adapters
from lwm.cbmem_bridge import sync_registered_projects
from lwm.ingest import run as ingest_run
from lwm.loop_state import begin_loop, close_loop, record_evaluation, write_state
from lwm.watch import render_watch_report, run_watch


ADAPTER_MODULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("codex", "adapters.hooks.codex_export", ()),
    ("kiro", "adapters.hooks.kiro_steering_watch", ()),
    ("kiro-sessions", "adapters.hooks.kiro_sessions", ()),
    ("trae", "adapters.hooks.trae_attach", ()),
    ("trae-sessions", "adapters.hooks.trae_sessions", ()),
    ("antigravity", "adapters.hooks.antigravity_watch", ()),
    ("antigravity-sessions", "adapters.hooks.antigravity_sessions", ()),
    ("minimax", "adapters.hooks.minimax_attach", ()),
    ("minimax-sessions", "adapters.hooks.minimax_sessions", ()),
    ("vscode-sessions", "adapters.hooks.vscode_sessions", ()),
    ("vscode", "adapters.hooks.vscode_tasks", ("--project",)),
)


def _run_adapter(name: str, module: str, root: Path, extra: tuple[str, ...]) -> tuple[int, str]:
    args = [sys.executable, "-m", module, "--root", str(root)]
    if extra:
        args.extend([extra[0], str(root)])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"adapter {name}: {exc}"
    detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")[:240]
    return result.returncode, f"adapter {name}: {detail or 'ok'}"


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
        for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines()[-1:]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                event_key = ":".join(
                    str(value)
                    for value in (
                        jsonl.name,
                        payload.get("ts"),
                        payload.get("session"),
                        payload.get("command"),
                    )
                )
                if event_key in seen:
                    continue
                project_path = str(payload.get("pwd") or root)
                session_id = str(payload.get("session") or jsonl.stem)
                lifecycle.start(
                    root,
                    tool="shell",
                    project_path=project_path,
                    session_id=session_id,
                    source="watcher-observed",
                )
                event = {
                    "tool": "shell",
                    "project_path": payload.get("pwd", str(root)),
                    "event_type": "workflow_observation",
                    "task": payload.get("task") or payload.get("command", ""),
                    "importance": "project",
                    "privacy": "sanitized",
                    "source": {"kind": "shell-sweep", "path": jsonl.name},
                    "tags": ["shell"],
                }
                result = subprocess.run(
                    [sys.executable, "-m", "lwm.cli", "hub", "record", json.dumps(event), "--root", str(root)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                rc |= result.returncode
                if result.returncode == 0:
                    lifecycle.stop(
                        root,
                        tool="shell",
                        project_path=project_path,
                        session_id=session_id,
                        task="Shell command observed complete",
                        source="watcher-observed",
                    )
                    seen.add(event_key)
            except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
                rc |= 1
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
    return rc


def _run_cycle_stages(root: Path) -> int:
    root = root.resolve()
    rc = 0
    for name, module, extra in ADAPTER_MODULES:
        adapter_rc, detail = _run_adapter(name, module, root, extra)
        print(detail)
        rc |= adapter_rc
    rc |= _sweep_shell_events(root)

    cbmem_report = sync_registered_projects(root)
    print(f"cbmem: {cbmem_report.get('status')} projects={len(cbmem_report.get('projects', {}))}")
    if cbmem_report.get("projects") and cbmem_report.get("status") in {"failed", "unavailable", "degraded"}:
        rc |= 1

    ingest = ingest_run(root, with_lock=True)
    print(ingest.render())
    if ingest.failed:
        rc |= 3

    watch = run_watch(root, eval_suite=root / "wiki" / "eval-suite.txt", eval_mode="standard")
    print(render_watch_report(watch))
    if not watch.audit.ok:
        rc |= 1

    write_global_adapters(root)
    from lwm.health import collect_and_write

    health = collect_and_write(root)
    print(health.render())
    if health.status == "failed":
        rc |= 1
    return rc


def _health_payload(root: Path) -> dict[str, Any]:
    path = root / "state" / "health.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _loop_evidence(root: Path) -> tuple[str, ...]:
    candidates = (root / "state" / "health.json", root / "llms.txt", root / "llms.json")
    return tuple(str(path.relative_to(root)) for path in candidates if path.is_file())


def run_cycle(root: Path) -> int:
    """Run one bounded collection cycle and persist prediction/evaluation state."""

    root = root.resolve()
    loop = begin_loop(
        "scheduled memory refresh",
        constraints=("one bounded cycle", "preserve source evidence"),
        success_criteria=("audit passes", "health is healthy", "external evidence exists"),
        expected_observation="configured sources and runtime inputs are readable",
        expected_outcome="ingest, audit, export, and health leave fresh evidence",
    )
    write_state(root, loop)
    try:
        code = _run_cycle_stages(root)
    except Exception as exc:  # noqa: BLE001
        evaluated = record_evaluation(
            loop,
            actual_observation=f"exception={exc}",
            actual_outcome="cycle interrupted before external verification",
            evidence=_loop_evidence(root),
            criteria_met=False,
            next_action="inspect the recorded exception and rerun the bounded cycle",
        )
        write_state(root, close_loop(evaluated, exit_state="human_required", human_gate=True))
        raise

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
    return code if exit_state == "completed_verified" else max(code, 1)
