"""Deterministic closure checks for a completed LLM-WorkMem loop."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from lwm.cycle_state import read_receipt
from lwm.loop_state import read_active, read_last


@dataclass(frozen=True)
class ClosureReport:
    status: str
    checks: dict[str, str]
    failed_checks: tuple[str, ...]


def _readable(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return True


def _source_check(root: Path) -> str:
    package = root / "lwm"
    return "pass" if package.is_dir() and _readable(package / "__init__.py") else "blocked"


def _runtime_check(root: Path) -> str:
    package = root / "lwm"
    if not package.is_dir() or not _readable(package / "__init__.py"):
        return "blocked"
    environment = {**os.environ, "PYTHONPATH": str(root)}
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import lwm"],
            cwd=str(root),
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "blocked"
    return "pass" if result.returncode == 0 else "blocked"


def _export_check(root: Path) -> str:
    path = root / "llms.txt"
    return "pass" if path.is_file() and _readable(path) else "blocked"


def _evidence_check(root: Path) -> str:
    state = read_active(root) or read_last(root)
    if state is None or not state.evidence:
        return "blocked"
    return "pass" if all((root / path).is_file() for path in state.evidence) else "blocked"


def _loop_check(root: Path) -> str:
    state = read_active(root) or read_last(root)
    if state is None:
        return "blocked"
    if state.exit_state == "completed_verified":
        return "pass"
    if (
        state.exit_state == "continue"
        and state.criteria_met is True
        and state.actual_observation == "full cycle not due"
    ):
        return "pass"
    return "blocked" if state.exit_state in {"human_required", "blocked"} else "degraded"


def _receipt_check(root: Path) -> str:
    receipt = read_receipt(root)
    return "pass" if receipt and receipt.get("status") == "success" else "blocked"


def _launchd_check(label: str) -> str:
    try:
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "degraded"
    return "pass" if any(line.split() and line.split()[-1] == label for line in result.stdout.splitlines()) else "degraded"


def _health_check(root: Path) -> str:
    try:
        from lwm.health import collect

        return "pass" if collect(root, strict=True).status == "healthy" else "degraded"
    except (OSError, ValueError, json.JSONDecodeError):
        return "degraded"


def check_closure(
    root: Path,
    *,
    source_root: Path | None = None,
    runtime_root: Path | None = None,
    health_required: bool = True,
    launchd_required: bool = True,
    launchd_label: str = "com.ethan.lwm.harvest",
) -> ClosureReport:
    """Check whether the loop has enough evidence to close truthfully."""

    root = root.resolve()
    inferred_runtime = runtime_root
    if inferred_runtime is None:
        automation = root / "automation"
        inferred_runtime = automation.resolve().parent if automation.is_symlink() else root
    checks: dict[str, str] = {
        "loop": _loop_check(root),
        "evidence": _evidence_check(root),
        "source": _source_check((source_root or root).resolve()),
        "runtime": _runtime_check(inferred_runtime.resolve()),
        "export": _export_check(root),
        "receipt": _receipt_check(root),
        "health": _health_check(root) if health_required else "skipped",
        "launchd": _launchd_check(launchd_label) if launchd_required else "skipped",
    }
    failed = tuple(name for name, status in checks.items() if status == "blocked")
    degraded = any(status == "degraded" for status in checks.values())
    status = "blocked" if failed else "degraded" if degraded else "pass"
    return ClosureReport(status=status, checks=checks, failed_checks=failed)


__all__ = ["ClosureReport", "check_closure"]
