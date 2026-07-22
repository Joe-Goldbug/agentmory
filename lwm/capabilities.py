"""Capability registry and receipts for real tool connectivity."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
    "claude-code": (".claude/settings.json",),
    "opencode": (".config/opencode/AGENTS.md", ".config/opencode/plugins/llm-workmem.ts"),
    "shell": (".zshrc",),
    "vscode": (
        "Library/Application Support/Code/User/prompts/llm-workmem.instructions.md",
    ),
    "kiro": (".kiro/steering/llm-workmem.md",),
    "antigravity": (".agents/AGENTS.md", ".agents/GLOBAL.md"),
    "trae": (".traerules",),
    "trae-solo": (".traerules",),
    "minimax": (".minimax/agents/coder/agent.md",),
}


def _tool_targets(tool: str, home: Path) -> tuple[Path, ...]:
    """Resolve adapter files from the current real installation paths."""
    if tool == "opencode":
        config_root = home / ".config" / "opencode"
        agents = config_root / "AGENTS.md"
        plugin_candidates: list[Path] = [config_root / "plugins" / "llm-workmem.ts"]
        config_path = config_root / "opencode.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            plugins = config.get("plugin", []) if isinstance(config, dict) else []
            if isinstance(plugins, list):
                for plugin in plugins:
                    if not isinstance(plugin, str) or "lwm-workmem" not in plugin.lower():
                        continue
                    candidate = Path(plugin).expanduser()
                    if not candidate.is_absolute():
                        candidate = config_root / candidate
                    plugin_candidates.insert(0, candidate)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        plugin = next(
            (candidate for candidate in plugin_candidates if candidate.is_file()),
            plugin_candidates[0],
        )
        return (agents, plugin)

    if tool == "vscode":
        prompts = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
        candidates = (
            prompts / "llm-workmem.instructions.md",
            prompts / "copilot-workflow-memory.instructions.md",
        )
        installed = tuple(path for path in candidates if path.is_file())
        return installed or (candidates[0],)

    return tuple(home / relative for relative in TOOL_TARGETS.get(tool, ()))


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
        history = payload.get("_history")
        if not isinstance(history, dict):
            history = {}
        previous = payload.get(key)
        entries = history.get(key)
        if not isinstance(entries, list):
            entries = [previous] if isinstance(previous, dict) else []
        entries = [item for item in entries if isinstance(item, dict)]
        entries.append(entry)
        history[key] = entries[-100:]
        payload["_history"] = history
        payload[key] = entry
        path = _path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as exc:
        return {**entry, "status": "unavailable", "error": str(exc)}
    return entry


def _latest_receipt(
    payload: dict[str, Any], key: str, expected_project_id: str | None
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    current = payload.get(key)
    if isinstance(current, dict):
        candidates.append(current)
    history = payload.get("_history")
    if isinstance(history, dict) and isinstance(history.get(key), list):
        candidates.extend(item for item in history[key] if isinstance(item, dict))
    if expected_project_id:
        candidates = [
            item for item in candidates if item.get("project_id") == expected_project_id
        ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: str(item.get("recorded_at", "")))


def summary(
    root: Path, *, project_path: str | Path | None = None
) -> dict[str, dict[str, Any]]:
    payload = load(root)
    installed = probe(root, project_path=project_path)
    out: dict[str, dict[str, Any]] = {}
    for tool in KNOWN_TOOLS:
        reads = _latest_receipt(payload, f"{tool}:read", None)
        writes = _latest_receipt(payload, f"{tool}:write", None)
        read = installed[tool]["read_receipt"] or {"status": "unverified"}
        write = installed[tool]["write_receipt"] or {"status": "unverified"}
        out[tool] = {
            "configuration": installed[tool]["status"],
            "installed": installed[tool]["installed"],
            "targets": installed[tool]["targets"],
            "read": read if isinstance(read, dict) else {"status": "unverified"},
            "write": write if isinstance(write, dict) else {"status": "unverified"},
            "bidirectional": (
                installed[tool]["status"] == "verified_bidirectional"
                if project_path is not None
                else bool(
                    reads
                    and writes
                    and reads.get("status") == "verified"
                    and writes.get("status") == "verified"
                )
            ),
        }
    return out


def _is_fresh_native(receipt: Any, expected_project_id: str | None) -> bool:
    if not isinstance(receipt, dict) or receipt.get("status") != "verified":
        return False
    if receipt.get("source") not in {"native-hook", "lifecycle-hook", "watcher-observed"}:
        return False
    if expected_project_id and receipt.get("project_id") != expected_project_id:
        return False
    try:
        recorded = datetime.fromisoformat(str(receipt["recorded_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    return recorded >= datetime.now(timezone.utc) - timedelta(days=14)


def probe(
    root: Path,
    *,
    home: Path | None = None,
    project_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Check configuration separately from real read/write receipts.

    A present instruction file proves only that an adapter is installed. A
    verified receipt is required before claiming that a tool actually read or
    wrote the hub.
    """
    home = (home or Path.home()).expanduser().resolve()
    receipts = load(root)
    expected_project_id = None
    if project_path is not None:
        from lwm.project_id import resolve_project_id

        expected_project_id = resolve_project_id(project_path).project_id
    out: dict[str, dict[str, Any]] = {}
    for tool in KNOWN_TOOLS:
        targets = list(_tool_targets(tool, home))
        installed = bool(targets) and all(path.is_file() for path in targets)
        readable = installed and all(path.stat().st_size > 0 for path in targets)
        read_receipt = _latest_receipt(receipts, f"{tool}:read", expected_project_id)
        write_receipt = _latest_receipt(receipts, f"{tool}:write", expected_project_id)
        read_verified = _is_fresh_native(read_receipt, expected_project_id)
        write_verified = _is_fresh_native(write_receipt, expected_project_id)
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
            "expected_project_id": expected_project_id,
        }
    return out


__all__ = ["KNOWN_TOOLS", "TOOL_TARGETS", "load", "record", "probe", "summary"]
