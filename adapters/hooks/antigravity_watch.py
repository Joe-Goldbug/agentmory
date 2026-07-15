"""Antigravity brain/task watcher → emit workflow_observation events.

Antigravity stores brain / task notes under ``~/.agents/brain`` and
``~/.agents/tasks``. The adapter diffs the directory against a stamp
file and emits an event per new or modified markdown note.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent.parent))

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


STAMP_FILENAME = ".lwm-antigravity-state.json"


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
        data = path.read_bytes()
    except OSError:
        return ""
    return hashlib.sha1(data).hexdigest()


def _first_paragraph(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text.split("\n\n", 1)[0].strip()[:600]


def main() -> int:
    parser = argparse.ArgumentParser(prog="antigravity-watch")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--brain",
        default=os.environ.get("ANTIGRAVITY_BRAIN_DIR", str(Path.home() / ".agents" / "brain")),
    )
    parser.add_argument(
        "--tasks",
        default=os.environ.get("ANTIGRAVITY_TASKS_DIR", str(Path.home() / ".agents" / "tasks")),
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    state = _load_state(root)
    new_state: dict[str, str] = dict(state)
    rc = 0

    for source in (args.brain, args.tasks):
        path = Path(source).expanduser()
        if not path.is_dir():
            continue
        for note in sorted(path.glob("*.md")):
            digest = _digest(note)
            key = str(note)
            if new_state.get(key) == digest:
                continue
            new_state[key] = digest
            event = {
                "tool": "antigravity",
                "project_path": str(root),
                "event_type": "workflow_observation",
                "task": _first_paragraph(note) or f"updated {note.name}",
                "importance": "project",
                "privacy": "sanitized",
                "source": {"kind": "file-watch", "path": str(note)},
                "files_touched": [str(note)],
                "tags": ["antigravity", note.parent.name],
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
