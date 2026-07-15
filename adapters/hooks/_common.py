"""Helper utilities shared by all IDE adapters."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

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
    source_root = str(Path(__file__).resolve().parent.parent.parent)
    env.setdefault("PYTHONPATH", source_root)
    if env.get("PYTHONPATH") and source_root not in env["PYTHONPATH"]:
        env["PYTHONPATH"] = source_root + ":" + env["PYTHONPATH"]
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if completed.returncode == 0:
        return 0
    sys.stderr.write(
        f"adapter record failed (rc={completed.returncode}): "
        f"{(completed.stderr or completed.stdout).strip()}\n"
    )
    return completed.returncode
