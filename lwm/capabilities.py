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

TOOL_TARGETS = {
    "codex": (".codex/AGENTS.md",),
    "claude-code": (".claude/CLAUDE.md",),
    "opencode": (".config/opencode/AGENTS.md",),
    "shell": (".zshrc",),
    "vscode": (".copilot/instructions/llm-workmem.instructions.md",),
    "kiro": (".kiro/steering/llm-workmem.md",),
    "antigravity": (".agents/AGENTS.md", ".agents/GLOBAL.md"),
    "trae": (".traerules",),
    "trae-solo": (".traerules",),
    "minimax": (".minimax/agents/coder/agent.md",),
}


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
    entry = {
        "tool": tool,
        "direction": direction,
        "project_id": project_id,
        "source": source,
        "detail": detail,
        "status": "verified",
        "recorded_at": _now(),
    }
    try:
        payload = load(root)
        payload[key] = entry
        path = _path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as exc:
        return {**entry, "status": "unavailable", "error": str(exc)}
    return entry


def summary(root: Path) -> dict[str, dict[str, Any]]:
    payload = load(root)
    installed = probe(root)
    out: dict[str, dict[str, Any]] = {}
    for tool in KNOWN_TOOLS:
        reads = payload.get(f"{tool}:read")
        writes = payload.get(f"{tool}:write")
        out[tool] = {
            "configuration": installed[tool]["status"],
            "installed": installed[tool]["installed"],
            "targets": installed[tool]["targets"],
            "read": reads if isinstance(reads, dict) else {"status": "unverified"},
            "write": writes if isinstance(writes, dict) else {"status": "unverified"},
            "bidirectional": bool(
                reads and writes and reads.get("status") == "verified" and writes.get("status") == "verified"
            ),
        }
    return out


def probe(root: Path, *, home: Path | None = None) -> dict[str, dict[str, Any]]:
    """Check configuration separately from real read/write receipts.

    A present instruction file proves only that an adapter is installed. A
    verified receipt is required before claiming that a tool actually read or
    wrote the hub.
    """
    home = (home or Path.home()).expanduser().resolve()
    receipts = load(root)
    out: dict[str, dict[str, Any]] = {}
    for tool in KNOWN_TOOLS:
        targets = [home / relative for relative in TOOL_TARGETS.get(tool, ())]
        installed = bool(targets) and all(path.is_file() for path in targets)
        readable = installed and all(path.stat().st_size > 0 for path in targets)
        read_receipt = receipts.get(f"{tool}:read")
        write_receipt = receipts.get(f"{tool}:write")
        read_verified = isinstance(read_receipt, dict) and read_receipt.get("status") == "verified"
        write_verified = isinstance(write_receipt, dict) and write_receipt.get("status") == "verified"
        if read_verified and write_verified:
            status = "verified_bidirectional"
        elif read_verified:
            status = "verified_read_only"
        elif installed and readable:
            status = "configured_unverified"
        else:
            status = "not_configured"
        out[tool] = {
            "status": status,
            "installed": installed,
            "targets": [str(path) for path in targets],
            "read_receipt": read_receipt if isinstance(read_receipt, dict) else None,
            "write_receipt": write_receipt if isinstance(write_receipt, dict) else None,
        }
    return out


__all__ = ["KNOWN_TOOLS", "TOOL_TARGETS", "load", "record", "probe", "summary"]
