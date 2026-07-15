"""Kiro steering file watcher → emit workflow_observation events.

Kiro reads ``~/.kiro/steering/<name>.md`` for project steering files.
This adapter runs once (timer / LaunchAgent) and emits one event per
modified steering file with the file's first paragraph as the task
description. The data is light on purpose — Kiro has no transcript
export — but a curated steering change IS a meaningful "work event".
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent.parent))

import argparse
import os
import sys
import time
from pathlib import Path


def _read_first_paragraph(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    paragraph = text.split("\n\n", 1)[0].strip()
    return paragraph[:600]


def emit(root: Path, path: Path) -> int:
    body = _read_first_paragraph(path)
    event = {
        "tool": "kiro",
        "project_path": str(root),
        "event_type": "workflow_observation",
        "task": body or f"updated steering {path.name}",
        "importance": "project",
        "privacy": "sanitized",
        "source": {"kind": "file-watch", "path": str(path)},
        "files_touched": [str(path)],
        "tags": ["kiro", "steering"],
    }
    try:
        from adapters.hooks._common import emit
    except ImportError:
        return 1
    return emit(root, event)


def main() -> int:
    parser = argparse.ArgumentParser(prog="kiro-steering-watch")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--steering",
        default=os.environ.get("KIRO_STEERING_DIR", str(Path.home() / ".kiro" / "steering")),
    )
    parser.add_argument("--settle", type=float, default=2.0, help="Files newer than N seconds.")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    steering = Path(args.steering).expanduser()
    if not steering.is_dir():
        print(f"no steering dir: {steering}", file=sys.stderr)
        return 0
    cutoff = time.time() - args.settle
    rc = 0
    for path in sorted(steering.glob("*.md")):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        rc |= emit(root, path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
