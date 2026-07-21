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
import sys
from pathlib import Path

ROOT_HINT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem")
)


def main() -> int:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        hook_input = {}
    project_path = str(hook_input.get("cwd") or hook_input.get("project_path") or ".")
    session_id = str(hook_input.get("session_id") or hook_input.get("sessionId") or "unknown")
    try:
        from lwm.lifecycle import start

        result = start(
            ROOT_HINT,
            tool="claude-code",
            project_path=project_path,
            session_id=session_id,
            source="native-hook",
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
