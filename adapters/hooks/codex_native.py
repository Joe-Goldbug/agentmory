"""Codex CLI native ``SessionStart``/``SessionEnd`` bridge.

The hook receives JSON on stdin and must emit JSON only on stdout.  It keeps
host prompt/transcript fields out of the persisted event and fails open so a
memory integration cannot break Codex itself.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from adapters.hooks._common import structured_handoff


ROOT_HINT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem")
)


def _project_path(payload: dict[str, Any]) -> str | None:
    for key in ("cwd", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _session_id(payload: dict[str, Any]) -> str | None:
    for key in ("session_id", "sessionId", "thread_id", "threadId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def handle_payload(
    payload: dict[str, Any], *, root: Path, phase: str
) -> dict[str, Any]:
    """Handle one Codex lifecycle payload without persisting host text."""

    normalized_phase = phase.strip().lower()
    project_path = _project_path(payload)
    session_id = _session_id(payload)
    if not project_path or not session_id:
        return {}
    host_proof = {
        "integration": "codex-hook",
        "event": phase,
        "session_id": session_id,
    }
    from lwm import lifecycle

    if normalized_phase == "sessionstart":
        result = lifecycle.start(
            root,
            tool="codex",
            project_path=project_path,
            session_id=session_id,
            source="native-hook",
            host_proof=host_proof,
        )
        if not result.context_markdown:
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": result.context_markdown,
            }
        }

    if normalized_phase == "sessionend":
        lifecycle.stop(
            root,
            tool="codex",
            project_path=project_path,
            session_id=session_id,
            task="Codex execution completed",
            handoff_summary=structured_handoff(payload),
            source="native-hook",
            host_proof=host_proof,
        )
        return {}

    raise ValueError(f"unsupported Codex hook phase: {phase}")


def _read_payload() -> dict[str, Any] | None:
    try:
        value = json.loads(sys.stdin.read() or "")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT_HINT)
    parser.add_argument(
        "--phase", choices=("SessionStart", "SessionEnd"), required=True
    )
    args = parser.parse_args()
    payload = _read_payload()
    if payload is None:
        print("{}")
        return 0
    try:
        print(json.dumps(handle_payload(payload, root=args.root.expanduser().resolve(), phase=args.phase), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"codex native hook failed: {exc}\n")
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
