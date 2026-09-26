"""Cursor native ``sessionStart``/``sessionEnd`` bridge.

Cursor sends hook input as JSON on stdin and expects JSON on stdout. The
adapter forwards only the workspace and session identity; transcript, model,
and user metadata remain host-owned and are never persisted.
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
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        for value in roots:
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("cwd", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _session_id(payload: dict[str, Any]) -> str | None:
    for key in ("session_id", "conversation_id", "sessionId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def handle_payload(
    payload: dict[str, Any], *, root: Path, phase: str
) -> dict[str, Any]:
    """Handle one Cursor lifecycle payload without persisting host text."""

    normalized_phase = phase.strip().lower().replace("_", "-")
    project_path = _project_path(payload)
    session_id = _session_id(payload)
    if not project_path or not session_id:
        return {}

    host_proof = {
        "integration": "cursor-hook",
        "event": phase,
        "session_id": session_id,
    }
    from lwm import lifecycle

    if normalized_phase == "session-start":
        result = lifecycle.start(
            root,
            tool="cursor",
            project_path=project_path,
            session_id=session_id,
            source="native-hook",
            host_proof=host_proof,
        )
        if not result.context_markdown:
            return {}
        return {"additional_context": result.context_markdown}

    if normalized_phase == "session-end":
        lifecycle.stop(
            root,
            tool="cursor",
            project_path=project_path,
            session_id=session_id,
            task="Cursor agent session ended",
            handoff_summary=structured_handoff(payload),
            source="native-hook",
            host_proof=host_proof,
        )
        return {}

    raise ValueError(f"unsupported Cursor hook phase: {phase}")


def _read_payload() -> dict[str, Any] | None:
    try:
        value = json.loads((sys.stdin.read() or "").lstrip("\ufeff"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(prog="cursor-native")
    parser.add_argument("--root", type=Path, default=ROOT_HINT)
    parser.add_argument(
        "--phase", choices=("session-start", "session-end"), required=True
    )
    args = parser.parse_args()
    payload = _read_payload()
    if payload is None:
        print("{}")
        return 0
    try:
        result = handle_payload(
            payload, root=args.root.expanduser().resolve(), phase=args.phase
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"cursor native hook failed: {exc}\n")
        result = {}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ROOT_HINT", "handle_payload", "main"]
