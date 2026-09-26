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

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(prog="lwm-shell-record")
    parser.add_argument("--task", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--tool", default="shell")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--handoff-id", default=None)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--change", action="append", default=[])
    parser.add_argument("--verification", action="append", default=[])
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--open-question", action="append", default=[])
    parser.add_argument("--type", default="workflow_observation")
    parser.add_argument("--importance", default="project")
    parser.add_argument(
        "--root",
        default=os.environ.get("LWM_ROOT")
        or str(Path.home() / "Library/Application Support/llm-workmem-runtime/llm-workmem"),
    )
    parser.add_argument("--event-type", dest="event_type", default=None)
    args = parser.parse_args()

    event = {
        "tool": args.tool,
        "project_path": str(Path(args.project).expanduser().resolve()),
        "event_type": args.event_type or args.type,
        "task": args.task,
        "decisions": args.decision,
        "changes": args.change,
        "verification": args.verification,
        "open_questions": args.open_question,
        "risks": args.risk,
        "importance": args.importance,
        "privacy": "sanitized",
        "source": {"kind": "shell-cli", "path": "lwm-shell-record"},
        "tags": [t for t in (args.tag or []) if t],
    }
    if args.task_id:
        event["task_id"] = args.task_id
    if args.handoff_id:
        event["handoff_id"] = args.handoff_id

    payload = json.dumps(event, ensure_ascii=False)
    cmd = [
        sys.executable,
        "-I",
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
