"""Trae ``.traerules`` file watcher → emit workflow_observation events.

Trae loads project rules from ``.traerules`` (or the global
``~/.traerules``). This adapter emits a workflow_observation event
whenever the file changes. The body of the file (first 600 chars) is
recorded so curators know what rule was changed.
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


def _snippet(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:600]


def emit(root: Path, path: Path) -> int:
    body = _snippet(path)
    event = {
        "tool": "trae",
        "project_path": str(root),
        "event_type": "workflow_observation",
        "task": f"updated {path.name}",
        "importance": "project",
        "privacy": "sanitized",
        "source": {"kind": "file-watch", "path": str(path)},
        "files_touched": [str(path)],
        "tags": ["trae", "rules"],
    }
    event["task"] = body or event["task"]
    try:
        from adapters.hooks._common import emit
    except ImportError:
        return 1
    return emit(root, event)


def main() -> int:
    parser = argparse.ArgumentParser(prog="trae-attach")
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--rules",
        default=os.environ.get("TRAE_RULES_FILE", str(Path.home() / ".traerules")),
        help="Path to .traerules file.",
    )
    parser.add_argument("--settle", type=float, default=2.0)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    rule_path = Path(args.rules).expanduser()
    if not rule_path.is_file():
        return 0
    cutoff = time.time() - args.settle
    try:
        mtime = rule_path.stat().st_mtime
    except OSError:
        return 0
    if mtime < cutoff:
        return 0
    return emit(root, rule_path)


if __name__ == "__main__":
    sys.exit(main())
