"""One installed-runtime cycle for the LLM-WorkMem LaunchAgent."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lwm.adapters import write_global_adapters
from lwm.ingest import run as ingest_run
from lwm.watch import render_watch_report, run_watch
from lwm.cbmem_bridge import sync_registered_projects


ADAPTER_MODULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("codex", "adapters.hooks.codex_export", ()),
    ("kiro", "adapters.hooks.kiro_steering_watch", ()),
    ("trae", "adapters.hooks.trae_attach", ()),
    ("antigravity", "adapters.hooks.antigravity_watch", ()),
    ("minimax", "adapters.hooks.minimax_attach", ()),
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
    rc = 0
    for jsonl in sorted(shell_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines()[-1:]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
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
            except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
                rc |= 1
    return rc


def run_cycle(root: Path) -> int:
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
