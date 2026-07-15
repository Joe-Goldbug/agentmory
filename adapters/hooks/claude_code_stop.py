"""Claude Code ``Stop`` hook → emit a session_summary event.

Claude Code invokes hooks via ``claude-code`` CLI which passes hook
context as JSON on stdin. The hook is configured in
``~/.claude/settings.json``::

    {
      "hooks": {
        "Stop": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "python /path/to/adapters/hooks/claude_code_stop.py"
              }
            ]
          }
        ]
      }
    }

The hook reads the captured transcript (last user message + last
assistant message) and emits a single ``session_summary`` event into
the central in-box. Failures are swallowed: a broken memory bridge
must never break a Claude Code session.
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


def _safe_load_stdin() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _last_user_text(hook_input: dict) -> str:
    """Best-effort: grab the last user message from the hook input."""

    messages = hook_input.get("messages") or []
    for entry in reversed(messages):
        role = entry.get("role") or entry.get("type")
        if role in {"user", "human"}:
            content = entry.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                        parts.append(str(block.get("text", "")))
                return "\n".join(p for p in parts if p).strip()
    transcript = hook_input.get("transcript")
    if isinstance(transcript, list) and transcript:
        tail = transcript[-1]
        if isinstance(tail, dict):
            msg = tail.get("message") or tail
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, str):
                return content.strip()
    return ""


def main() -> int:
    hook_input = _safe_load_stdin()
    project_path = (
        hook_input.get("cwd")
        or hook_input.get("project_path")
        or str(hook_input.get("workspace", {}).get("project_dir") or ROOT_HINT)
    )
    session_id = str(hook_input.get("session_id") or hook_input.get("sessionId") or "unknown")
    last_user = _last_user_text(hook_input)[:600]
    decisions = list(hook_input.get("decisions") or [])
    changes = list(hook_input.get("changes") or [])
    verification = list(hook_input.get("verification") or [])

    event = {
        "tool": "claude-code",
        "tool_version": str(hook_input.get("claude_code_version") or ""),
        "project_path": str(project_path),
        "session_id": session_id,
        "event_type": "session_summary",
        "task": last_user or "(no user text)",
        "decisions": decisions,
        "changes": changes,
        "verification": verification,
        "importance": "project",
        "privacy": "sanitized",
        "source": {"kind": "hook", "path": "claude-code/stop"},
        "tags": ["claude-code"],
    }
    try:
        from adapters.hooks._common import emit

        return emit(ROOT_HINT, event)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"claude_code_stop hook failed: {exc}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
