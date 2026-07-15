"""Shell ``lwm-shell-record`` helper.

Usage from zsh:

    lwm-shell-record --task "ran migration" --tag auth,migration
    lwm-shell-record --task "..." --verification "tests pass"

Implements the Level 3 CLI entry point so shell users can drop curated
work notes into the in-box without saving raw commands. Sensitive path
filtering is applied by the central privacy filter (not here) so a
misbehaving shell adapter cannot leak password values into the ledger.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent.parent))

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(prog="lwm-shell-record")
    parser.add_argument("--task", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--change", action="append", default=[])
    parser.add_argument("--verification", action="append", default=[])
    parser.add_argument("--open-question", action="append", default=[])
    parser.add_argument("--type", default="workflow_observation")
    parser.add_argument("--importance", default="project")
    parser.add_argument(
        "--root",
        default=os.environ.get("LWM_ROOT")
        or str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"),
    )
    parser.add_argument("--event-type", dest="event_type", default=None)
    args = parser.parse_args()

    event = {
        "tool": "shell",
        "project_path": str(Path(args.project).expanduser().resolve()),
        "event_type": args.event_type or args.type,
        "task": args.task,
        "decisions": args.decision,
        "changes": args.change,
        "verification": args.verification,
        "open_questions": args.open_question,
        "importance": args.importance,
        "privacy": "sanitized",
        "source": {"kind": "shell-cli", "path": "lwm-shell-record"},
        "tags": [t for t in (args.tag or []) if t],
    }

    payload = json.dumps(event, ensure_ascii=False)
    cmd = [
        sys.executable,
        "-m",
        "lwm.cli",
        "hub",
        "record",
        payload,
        "--root",
        str(Path(args.root).expanduser().resolve()),
    ]
    import subprocess

    completed = subprocess.run(cmd)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
