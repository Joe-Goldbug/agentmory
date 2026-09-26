"""Cursor project companion event adapter.

Cursor is a VS Code family IDE, but its local session storage is not a stable
public lifecycle API. This adapter only consumes the explicit project contract
``.llm-workmem/events.jsonl``. It never interprets Cursor database or
transcript files as native proof.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.hooks.vscode_tasks import process_project


def main() -> int:
    parser = argparse.ArgumentParser(prog="cursor-tasks")
    parser.add_argument("--root", required=True, help="Wiki/WorkMem root.")
    parser.add_argument(
        "--project",
        required=True,
        help="Project directory that owns .llm-workmem/events.jsonl.",
    )
    args = parser.parse_args()
    return process_project(
        Path(args.root).expanduser().resolve(),
        Path(args.project).expanduser().resolve(),
        tool="cursor",
    )


if __name__ == "__main__":
    raise SystemExit(main())
