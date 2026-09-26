"""Helper utilities shared by all IDE adapters."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

_SENSITIVE_PATH_RE = re.compile(
    r"(^|/)(?:\.env(?:\.[^/]+)?|credentials|id_rsa|id_ed25519|secrets?(?:/|$)|tokens?(?:/|$))",
    re.IGNORECASE,
)


def redact_paths(paths: Iterable[str]) -> list[str]:
    """Return ``paths`` with any sensitive entry replaced by ``<REDACTED:path>``."""

    out: list[str] = []
    for raw in paths:
        p = str(raw)
        if _SENSITIVE_PATH_RE.search(p):
            out.append("<REDACTED:path>")
        else:
            out.append(p)
    return out


def structured_handoff(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return only an explicit structured handoff object from host input.

    Ordinary task, prompt, and transcript fields are intentionally ignored;
    lifecycle hooks may forward a handoff only when the host names one of the
    supported structured fields.
    """

    for key in ("handoff", "handoff_summary", "task_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return None


def emit(
    root: Optional[Path],
    event: dict[str, Any],
    *,
    root_env: str = "LWM_ROOT",
) -> int:
    """Emit an event by invoking the central record CLI.

    Returns 0 on success, non-zero otherwise. Prints a short error to
    stderr if the recording path fails — adapters stay non-blocking.
    """

    target_root = root or Path(os.environ.get(root_env) or ".").expanduser()
    payload = json.dumps(event, ensure_ascii=False)
    cmd = [
        sys.executable,
        "-I",
        "-m",
        "lwm.cli",
        "hub",
        "record",
        payload,
        "--root",
        str(target_root.resolve()),
    ]
    try:
        import subprocess
    except ImportError:
        return 1
    env = dict(os.environ)
    # Hooks are shipped in the installed wheel. Never derive an import path
    # from this helper's source location: on the development machine that
    # location is the iCloud checkout and would break runtime independence.
    python_path = env.get("PYTHONPATH")
    if python_path:
        safe_entries = [
            entry for entry in python_path.split(os.pathsep)
            if "Mobile Documents" not in entry
        ]
        if safe_entries:
            env["PYTHONPATH"] = os.pathsep.join(safe_entries)
        else:
            env.pop("PYTHONPATH", None)
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if completed.returncode == 0:
        return 0
    sys.stderr.write(
        f"adapter record failed (rc={completed.returncode}): "
        f"{(completed.stderr or completed.stdout).strip()}\n"
    )
    return completed.returncode
