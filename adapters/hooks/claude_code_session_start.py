"""Claude Code ``SessionStart`` hook → emit a session_start event.

Mirror of ``claude_code_stop.py`` for session start. Both hooks feed the
same ``event-index.json`` ledger so the dedup step can collapse them.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_HINT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem")
)


def _project_path(payload: dict) -> str | None:
    for key in ("cwd", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _session_id(payload: dict) -> str | None:
    for key in ("session_id", "sessionId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        hook_input = {}
    project_path = _project_path(hook_input)
    session_id = _session_id(hook_input)
    if not project_path or not session_id:
        return 0
    try:
        from lwm.lifecycle import start

        result = start(
            ROOT_HINT,
            tool="claude-code",
            project_path=project_path,
            session_id=session_id,
            source="native-hook",
            host_proof={
                "integration": "claude-code-hook",
                "event": "SessionStart",
                "session_id": session_id,
            },
        )
        context = result.context_markdown
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"claude_code_session_start hook failed: {exc}\n")
        context = ""
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
