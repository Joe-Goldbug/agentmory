"""Codex exporter: turn ``~/.codex/sessions/*.jsonl`` into central events.

Codex (the CLI) writes per-session transcripts under
``~/.codex/sessions/`` with one JSON object per line. This adapter runs
on a timer (LaunchAgent or watch trigger) and emits a
``workflow_observation`` event per session that captures the user
prompt and the last assistant reply. It mirrors the level-3 model used
by the shell adapter: explicit, audited, deterministic.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent.parent))

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _entry_text(entry: dict[str, Any]) -> str:
    msg = entry.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "output_text"}:
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool:{block.get('name', '?')}]")
        return "\n".join(p for p in parts if p)
    return ""


def _summarize_session(path: Path) -> dict[str, Any]:
    entries = _read_jsonl(path)
    if not entries:
        return {}
    user_prompts = [e for e in entries if e.get("type") == "user"]
    assistant_msgs = [e for e in entries if e.get("type") == "assistant"]
    first_prompt = _entry_text(user_prompts[0]) if user_prompts else ""
    last_reply = _entry_text(assistant_msgs[-1]) if assistant_msgs else ""
    return {
        "first_prompt": first_prompt[:400],
        "last_reply": last_reply[:400],
        "tool_calls": sum(
            1
            for e in entries
            for blk in ((e.get("message") or {}).get("content") or [])
            if isinstance(blk, dict) and blk.get("type") == "tool_use"
        ),
        "entry_count": len(entries),
    }


def emit_session(root: Path, session_path: Path) -> int:
    summary = _summarize_session(session_path)
    if not summary:
        return 0
    event = {
        "tool": "codex",
        "project_path": str(root),
        "session_id": session_path.stem,
        "event_type": "workflow_observation",
        "task": summary["first_prompt"] or "(no user prompt)",
        "verification": [],
        "decisions": [],
        "changes": [],
        "importance": "project",
        "privacy": "sanitized",
        "source": {"kind": "file-watch", "path": str(session_path)},
        "tags": ["codex", "session-summary"],
    }
    try:
        from adapters.hooks._common import emit

        return emit(root, event)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"codex adapter failed: {exc}\n")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="codex-export")
    parser.add_argument("--root", required=True, help="Wiki/WorkMem root.")
    parser.add_argument(
        "--sessions",
        default=os.environ.get("CODEX_SESSIONS_DIR", str(Path.home() / ".codex" / "sessions")),
        help="Directory containing Codex session JSONL files.",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    sessions = Path(args.sessions).expanduser()
    if not sessions.is_dir():
        print(f"no sessions dir: {sessions}", file=sys.stderr)
        return 0
    rc = 0
    for session in sorted(sessions.glob("**/*.jsonl")):
        rc |= emit_session(root, session)
    return rc


if __name__ == "__main__":
    sys.exit(main())
