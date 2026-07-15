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
import sys
from pathlib import Path

ROOT = Path(
    "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
)
SETTINGS = Path.home() / ".claude" / "settings.json"

HOOKS_TO_REGISTER = {
    "Stop": {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f"{sys.executable} {ROOT / 'adapters' / 'hooks' / 'claude_code_stop.py'}",
            }
        ],
    },
    "SessionStart": {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f"{sys.executable} {ROOT / 'adapters' / 'hooks' / 'claude_code_session_start.py'}",
            }
        ],
    },
}


def install() -> None:
    settings: dict = {}
    if SETTINGS.is_file():
        settings = json.loads(SETTINGS.read_text("utf-8"))

    hooks = settings.setdefault("hooks", {})
    changed = False
    for event_name, hook_def in HOOKS_TO_REGISTER.items():
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


def uninstall() -> None:
    if not SETTINGS.is_file():
        print("no settings file")
        return
    settings = json.loads(SETTINGS.read_text("utf-8"))
    hooks = settings.get("hooks", {})
    changed = False
    for event_name in HOOKS_TO_REGISTER:
        if event_name in hooks:
            cmd = HOOKS_TO_REGISTER[event_name]["hooks"][0]["command"]
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
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
