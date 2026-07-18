"""Capability registry and receipts for real tool connectivity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KNOWN_TOOLS = (
    "codex",
    "claude-code",
    "opencode",
    "shell",
    "vscode",
    "kiro",
    "antigravity",
    "trae",
    "trae-solo",
    "minimax",
)


def _path(root: Path) -> Path:
    return root / "state" / "capability-receipts.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(root: Path) -> dict[str, dict[str, Any]]:
    path = _path(root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def record(
    root: Path,
    *,
    tool: str,
    direction: str,
    project_id: str | None = None,
    source: str = "unknown",
    detail: str = "",
) -> dict[str, Any]:
    if direction not in {"read", "write"}:
        raise ValueError("direction must be read or write")
    key = f"{tool}:{direction}"
    payload = load(root)
    payload[key] = {
        "tool": tool,
        "direction": direction,
        "project_id": project_id,
        "source": source,
        "detail": detail,
        "status": "verified",
        "recorded_at": _now(),
    }
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload[key]


def summary(root: Path) -> dict[str, dict[str, Any]]:
    payload = load(root)
    out: dict[str, dict[str, Any]] = {}
    for tool in KNOWN_TOOLS:
        reads = payload.get(f"{tool}:read")
        writes = payload.get(f"{tool}:write")
        out[tool] = {
            "read": reads if isinstance(reads, dict) else {"status": "unverified"},
            "write": writes if isinstance(writes, dict) else {"status": "unverified"},
            "bidirectional": bool(reads and writes),
        }
    return out


__all__ = ["KNOWN_TOOLS", "load", "record", "summary"]
