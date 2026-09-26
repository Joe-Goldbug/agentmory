"""Antigravity ``hooks.json`` bridge.

Antigravity sends hook payloads on stdin and expects JSON on stdout.  The
adapter deliberately forwards only the workspace and conversation identity;
the model name and transcript paths are host metadata, not LLM-WorkMem
evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from adapters.hooks._common import structured_handoff


DEFAULT_ROOT = Path(
    os.environ.get("LWM_ROOT")
    or str(Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem")
)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _field(payload: Mapping[str, Any], *names: str) -> object:
    """Read Antigravity fields despite host JSON casing differences."""

    normalized = {
        re.sub(r"[^a-z0-9]", "", str(key).lower()): value
        for key, value in payload.items()
    }
    for name in names:
        value = normalized.get(re.sub(r"[^a-z0-9]", "", name.lower()))
        if value is not None:
            return value
    return None


def _project_path(payload: Mapping[str, Any]) -> str | None:
    workspaces = _field(
        payload, "workspacePaths", "workspacePath", "workspace_path", "CWD", "cwd"
    )
    if isinstance(workspaces, list):
        for value in workspaces:
            path = _text(value)
            if path:
                return path
    for key in (
        "workspacePath",
        "workspace_path",
        "projectPath",
        "project_path",
        "CWD",
        "cwd",
    ):
        path = _text(_field(payload, key))
        if path:
            return path
    # Antigravity CLI currently sends an empty workspacePaths array for a
    # normal print-mode session. Its subprocess cwd is the selected project.
    current_dir = _text(os.getcwd())
    return current_dir


def _session_id(payload: Mapping[str, Any]) -> str | None:
    return _text(
        _field(
            payload,
            "conversationId",
            "conversation_id",
            "ConversationID",
            "invocationId",
            "invocation_id",
        )
    )


def handle_payload(
    payload: Mapping[str, Any], *, root: Path, phase: str
) -> dict[str, Any]:
    """Handle one native Antigravity event.

    ``PreInvocation`` uses the lifecycle ``start`` phase so the returned
    context and its read receipt are bound to an actual host hook. ``Stop``
    uses the lifecycle ``stop`` phase for the write receipt.  The bridge
    response is intentionally reduced to the host's expected JSON shape.
    """

    if not isinstance(payload, Mapping):
        raise ValueError("hook payload must be a JSON object")
    project_path = _project_path(payload)
    session_id = _session_id(payload)
    if not project_path or not session_id:
        raise ValueError("workspace path and conversation id are required")

    normalized_phase = phase.strip().lower().replace("_", "-")
    if normalized_phase == "preinvocation":
        normalized_phase = "pre-invocation"
    task_id = f"antigravity:{session_id}"
    from lwm.session_bridge import dispatch

    if normalized_phase == "pre-invocation":
        response = dispatch(
            root.resolve(),
            {
                "phase": "start",
                "tool": "antigravity",
                "project_path": project_path,
                "session_id": session_id,
                "task_id": task_id,
                "source": "native-hook",
                "host_proof": {
                    "integration": "antigravity-hook",
                    "event": "PreInvocation",
                    "session_id": session_id,
                },
            },
            trusted_host=True,
        )
        context_markdown = str(response.get("context_markdown") or "").strip()
        if not context_markdown:
            return {}
        return {"injectSteps": [{"ephemeralMessage": context_markdown}]}

    if normalized_phase == "stop":
        handoff = structured_handoff(payload)
        dispatch(
            root.resolve(),
            {
                "phase": "stop",
                "tool": "antigravity",
                "project_path": project_path,
                "session_id": session_id,
                "task_id": task_id,
                "task": "Antigravity execution completed",
                "source": "native-hook",
                "host_proof": {
                    "integration": "antigravity-hook",
                    "event": "Stop",
                    "session_id": session_id,
                },
                **({"handoff": handoff} if handoff is not None else {}),
            },
            trusted_host=True,
        )
        # Antigravity's Stop contract requires a decision field. Any value
        # other than ``continue`` allows the host to terminate normally.
        return {"decision": "allow"}

    raise ValueError("phase must be PreInvocation or Stop")


def main() -> int:
    parser = argparse.ArgumentParser(prog="antigravity-native")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--phase", required=True, choices=("pre-invocation", "stop"))
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() or "{}"
        payload = json.loads(raw)
        result = handle_payload(payload, root=Path(args.root).expanduser(), phase=args.phase)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"antigravity native hook failed open: {exc}\n")
        result = {}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DEFAULT_ROOT", "handle_payload", "main"]
