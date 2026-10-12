"""Launchd supervisor for the boot-and-six-hour full cycle."""

from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path

from lwm.cycle_state import is_due
from lwm import lockfile
from lwm.harvest import mutable_ownership_issues
from lwm.loop_state import begin_loop, close_loop, record_evaluation, write_state


FULL_INTERVAL_SECONDS = 21600
SCHEDULE_GRACE_SECONDS = 0


def _boot_id() -> str:
    if sys.platform != "darwin":
        return ""
    try:
        result = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _startup_due(root: Path) -> tuple[Path, dict[str, object], str]:
    path = root / "state" / "schedule-policy.json"
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return path, {}, ""
    if not isinstance(policy, dict) or not policy.get("run_on_boot"):
        return path, {}, ""
    boot_id = _boot_id()
    return path, policy, boot_id if boot_id and boot_id != policy.get("last_boot_id") else ""


def run_supervisor(root: Path, *, interval_seconds: int = FULL_INTERVAL_SECONDS, force: bool = False) -> int:
    """Run the single v2 cycle writer only when the full cycle is due.

    The lock surrounds both the not-due bookkeeping and the full cycle so
    concurrent launchd/file-wake invocations cannot become a second writer.
    """

    root = root.resolve()
    # Never let a scheduled write silently cross the data-owner boundary.
    # Task 9B must migrate and verify this path before a real cycle can run.
    if mutable_ownership_issues(root):
        return 2
    try:
        with lockfile.cycle_lock(root):
            policy_path, policy, boot_id = _startup_due(root)
            # Calendar checks coalesce on wake; the complete-cycle clock is
            # independent of these cheap checks and never runs early.
            due_interval = max(0, interval_seconds - SCHEDULE_GRACE_SECONDS)
            if not force and not boot_id and not is_due(root, interval_seconds=due_interval):
                loop = begin_loop(
                    "scheduled memory refresh",
                    success_criteria=("full cycle runs when due",),
                    expected_observation="the previous successful cycle is still within its interval",
                    expected_outcome="wait without overwriting the previous full-cycle evidence",
                )
                loop = record_evaluation(
                    loop,
                    actual_observation="full cycle not due",
                    actual_outcome="previous full-cycle evidence remains current",
                    evidence=("state/last-cycle.json",),
                    criteria_met=True,
                    next_action="wait for the next due window",
                )
                write_state(root, close_loop(loop, exit_state="continue", human_gate=False))
                # The latest cycle receipt binds health.json by hash. A
                # not-due wake must not invalidate that verified snapshot.
                return 0

            try:
                from lwm.runner import run_cycle

                code = run_cycle(root)
                if code == 0 and boot_id:
                    policy["last_boot_id"] = boot_id
                    temporary = policy_path.with_suffix(".tmp")
                    temporary.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
                    temporary.replace(policy_path)
            except Exception:  # noqa: BLE001
                return 1
            # run_cycle owns the health snapshot for a full cycle and hashes
            # that exact file into the immutable receipt. Rewriting health
            # here would invalidate the receipt immediately after commit.
            return code
    except lockfile.CycleLockBusyError as exc:
        # A second scheduler wake is expected during a running cycle. It does
        # no writes and exits cleanly so launchd does not retry it as a failure.
        if exc.error:
            print(f"supervisor cycle lock unavailable: {exc}", file=sys.stderr)
            return 1
        return 0


__all__ = ["FULL_INTERVAL_SECONDS", "run_supervisor"]
