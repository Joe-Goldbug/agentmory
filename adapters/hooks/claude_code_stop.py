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

import json
import os
import sys
from pathlib import Path

from adapters.hooks._common import structured_handoff

ROOT_HINT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem")
)


def _project_path(payload: dict) -> str | None:
    for key in ("cwd", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    workspace = payload.get("workspace")
    if isinstance(workspace, dict):
        value = workspace.get("project_dir")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _session_id(payload: dict) -> str | None:
    for key in ("session_id", "sessionId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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
    project_path = _project_path(hook_input)
    session_id = _session_id(hook_input)
    if not project_path or not session_id:
        return 0
    last_user = _last_user_text(hook_input)[:600]
    handoff_summary = structured_handoff(hook_input)
    task_id = hook_input.get("task_id")
    if task_id is None and handoff_summary:
        task_id = handoff_summary.get("task_id")
    try:
        from lwm.lifecycle import stop

        stop(
            ROOT_HINT,
            tool="claude-code",
            project_path=str(project_path),
            session_id=session_id,
            task_id=str(task_id) if task_id else None,
            task=last_user or "(no user text)",
            handoff_summary=handoff_summary,
            source="native-hook",
            host_proof={
                "integration": "claude-code-hook",
                "event": "Stop",
                "session_id": session_id,
            },
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"claude_code_stop hook failed: {exc}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
