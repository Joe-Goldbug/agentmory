"""Claude Code ``SessionStart`` hook → emit a session_start event.

Mirror of ``claude_code_stop.py`` for session start. Both hooks feed the
same ``event-index.json`` ledger so the dedup step can collapse them.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent.parent))

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_HINT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem")
)


def _render_context(project_path: str) -> str:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lwm.cli",
                "hub",
                "context",
                "--tool",
                "claude-code",
                "--project",
                project_path,
                "--limit",
                "6",
                str(ROOT_HINT),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        hook_input = {}
    project_path = str(hook_input.get("cwd") or hook_input.get("project_path") or ".")
    session_id = str(hook_input.get("session_id") or hook_input.get("sessionId") or "unknown")
    event = {
        "tool": "claude-code",
        "project_path": project_path,
        "session_id": session_id,
        "event_type": "session_start",
        "importance": "scratch",
        "privacy": "sanitized",
        "source": {"kind": "hook", "path": "claude-code/session-start"},
        "tags": ["claude-code", "session-start"],
    }
    try:
        from adapters.hooks._common import emit

        emit(ROOT_HINT, event)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"claude_code_session_start hook failed: {exc}\n")
    context = _render_context(project_path)
    if context:
        # Claude Code consumes this standard SessionStart hook response and
        # appends it to the model context for the newly opened session.
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": context,
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
