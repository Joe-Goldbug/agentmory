#!/usr/bin/env python3
"""Register Claude Code hooks for llm-workmem integration.

Adds SessionStart and Stop hooks to ~/.claude/settings.json so that
every Claude Code session automatically emits events into the central
hub inbox.

Usage:
    python install-claude-hook.py [--uninstall]
"""

from __future__ import annotations

import json
import argparse
import os
import shlex
import sys
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"

def _default_root() -> Path:
    return Path(
        os.environ.get("LWM_ROOT")
        or Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem"
    ).expanduser().resolve()


def _hooks(root: Path) -> dict[str, dict]:
    prefix = f"LWM_ROOT={shlex.quote(str(root))} {shlex.quote(sys.executable)} -I -m"
    return {
        "Stop": {
            "matcher": "",
            "hooks": [{"type": "command", "command": f"{prefix} adapters.hooks.claude_code_stop"}],
        },
        "SessionStart": {
            "matcher": "",
            "hooks": [{"type": "command", "command": f"{prefix} adapters.hooks.claude_code_session_start"}],
        },
    }


def install(root: Path | None = None) -> None:
    hooks_to_register = _hooks((root or _default_root()).expanduser().resolve())
    settings: dict = {}
    if SETTINGS.is_file():
        settings = json.loads(SETTINGS.read_text("utf-8"))

    hooks = settings.setdefault("hooks", {})
    changed = False
    for event_name, hook_def in hooks_to_register.items():
        existing = hooks.get(event_name, [])
        cmd = hook_def["hooks"][0]["command"]
        already = any(
            h.get("hooks", [{}])[0].get("command") == cmd
            for h in existing
            if isinstance(h, dict)
        )
        if not already:
            existing.append(hook_def)
            hooks[event_name] = existing
            changed = True
            print(f"  registered: hooks.{event_name}")

    if changed:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", "utf-8")
        print(f"written -> {SETTINGS}")
    else:
        print("already installed, no changes needed")


def uninstall(root: Path | None = None) -> None:
    hooks_to_register = _hooks((root or _default_root()).expanduser().resolve())
    if not SETTINGS.is_file():
        print("no settings file")
        return
    settings = json.loads(SETTINGS.read_text("utf-8"))
    hooks = settings.get("hooks", {})
    changed = False
    for event_name in hooks_to_register:
        if event_name in hooks:
            cmd = hooks_to_register[event_name]["hooks"][0]["command"]
            hooks[event_name] = [
                h for h in hooks[event_name]
                if not (isinstance(h, dict) and h.get("hooks", [{}])[0].get("command") == cmd)
            ]
            if not hooks[event_name]:
                del hooks[event_name]
            changed = True
            print(f"  removed: hooks.{event_name}")
    if changed:
        SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", "utf-8")
        print(f"written -> {SETTINGS}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=_default_root())
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    if args.uninstall:
        uninstall(args.root.expanduser().resolve())
    else:
        install(args.root.expanduser().resolve())
