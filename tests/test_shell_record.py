from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _read_events(root: Path) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "raw" / "events" / "inbox").glob("*/*.json"))
    ]


def test_shell_record_preserves_registered_tool_and_structured_identity(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "adapters.hooks.shell_record",
            "--root",
            str(tmp_path),
            "--tool",
            "gemini-cli",
            "--project",
            str(tmp_path),
            "--task",
            "finished review",
            "--task-id",
            "task-1",
            "--handoff-id",
            "handoff-1",
            "--change",
            "updated adapter",
            "--verification",
            "tests passed",
            "--risk",
            "live proof pending",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    event = _read_events(tmp_path)[0]
    assert event["tool"] == "gemini-cli"
    assert event["task_id"] == "task-1"
    assert event["handoff_id"] == "handoff-1"
    assert event["changes"] == ["updated adapter"]
    assert event["verification"] == ["tests passed"]
    assert event["risks"] == ["live proof pending"]
