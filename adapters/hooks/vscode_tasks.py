"""VSCode → central event adapter (Level 3 CLI + Level 2 file-tail).

VSCode does not expose official hooks. The hub expects a project-level
companion ``.llm-workmem/events.jsonl`` that any extension or shell
helper may append to. This adapter tails that file:

* New lines append events to the in-box.
* Old lines are skipped via a content cursor persisted to a sibling
  ``.lwm-cursor`` file.

If the file is missing, the adapter is a no-op.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CURSOR_FILENAME = ".lwm-cursor"


def _cursor_path(project_dir: Path) -> Path:
    return project_dir / CURSOR_FILENAME


def _load_cursor(project_dir: Path) -> int:
    cur = _cursor_path(project_dir)
    if not cur.is_file():
        return 0
    try:
        return int(cur.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _save_cursor(project_dir: Path, value: int) -> None:
    cur = _cursor_path(project_dir)
    cur.write_text(str(value), encoding="utf-8")


def _event_log_path(project_dir: Path) -> Path:
    return project_dir / ".llm-workmem" / "events.jsonl"


def process_project(root: Path, project: Path, *, tool: str = "vscode") -> int:
    """Tail one project's explicit companion event log for a named tool.

    VS Code and Cursor do not expose a shared public lifecycle hook. The
    project companion file is therefore an explicit integration surface, not
    proof that the IDE emitted a native callback.
    """

    if not project.is_dir():
        return 0
    log = _event_log_path(project)
    if not log.is_file():
        return 0
    cursor = _load_cursor(project)
    try:
        text = log.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {log}: {exc}", file=sys.stderr)
        return 1
    lines = text.splitlines()
    new_lines = lines[cursor:]
    rc = 0
    for entry in new_lines:
        try:
            event = json.loads(entry)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        try:
            from adapters.hooks._common import emit
        except ImportError:
            return 1
        event.setdefault("project_path", str(project))
        event.setdefault("tool", tool)
        event.setdefault("importance", "project")
        event.setdefault("privacy", "sanitized")
        event.setdefault("source", {"kind": f"{tool}-tasks", "path": str(log)})
        event.setdefault(
            "event_type",
            str(event.get("event_type") or "workflow_observation"),
        )
        event.setdefault("tags", [tool])
        rc |= emit(root, event)
    _save_cursor(project, len(lines))
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(prog="vscode-tasks")
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
    )


if __name__ == "__main__":
    sys.exit(main())
