"""Minimax agent rules watcher → emit workflow_observation events.

Minimax exposes per-agent rule files under
``~/.minimax/agents/<name>/agent.md``. This adapter diffs the directory
against a content hash stamp and emits an event per changed file. The
goal is the same as Trae/Kiro/Antigravity: light footprint, no chat
transcript access required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


STAMP_FILENAME = ".lwm-minimax-state.json"


def _load_state(root: Path) -> dict[str, str]:
    stamp = root / STAMP_FILENAME
    if not stamp.is_file():
        return {}
    try:
        return json.loads(stamp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(root: Path, state: dict[str, str]) -> None:
    stamp = root / STAMP_FILENAME
    stamp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _digest(path: Path) -> str:
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _first_paragraph(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text.split("\n\n", 1)[0].strip()[:600]


def main() -> int:
    parser = argparse.ArgumentParser(prog="minimax-attach")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--agents",
        default=os.environ.get("MINIMAX_AGENTS_DIR", str(Path.home() / ".minimax" / "agents")),
    )
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    agents = Path(args.agents).expanduser()
    if not agents.is_dir():
        return 0

    state = _load_state(root)
    new_state: dict[str, str] = dict(state)
    rc = 0
    for rule in sorted(agents.glob("**/agent.md")):
        digest = _digest(rule)
        key = str(rule)
        if new_state.get(key) == digest:
            continue
        new_state[key] = digest
        event = {
            "tool": "minimax",
            "project_path": str(root),
            "event_type": "workflow_observation",
            "task": _first_paragraph(rule) or f"updated {rule.name}",
            "importance": "project",
            "privacy": "sanitized",
            "source": {"kind": "file-watch", "path": str(rule)},
            "files_touched": [str(rule)],
            "tags": ["minimax", "agent-rules"],
        }
        try:
            from adapters.hooks._common import emit
        except ImportError:
            return 1
        rc |= emit(root, event)
    _save_state(root, new_state)
    return rc


if __name__ == "__main__":
    sys.exit(main())
