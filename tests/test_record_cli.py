"""Tests for ``lwm hub record`` argument-resolution branches.

Scope Lock:
- Solves: covers Branch 2 (--tool/--project only, no stdin), Branch 3
  (stdin JSON), and the closed-stdin regression where the previous
  implementation printed "empty stdin" instead of using the options.
- Does not solve: full ingest pipeline (covered elsewhere).
- Acceptance: 4 tests, exits 0 on the two happy paths; covers the
  empty-stdin-after-options regression.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lwm.cli import app


runner = CliRunner()


def _read_inbox(root: Path) -> list[dict]:
    inbox = root / "raw" / "events" / "inbox"
    if not inbox.is_dir():
        return []
    out: list[dict] = []
    for day in sorted(inbox.iterdir()):
        if not day.is_dir():
            continue
        for p in sorted(day.glob("*.json")):
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def test_record_options_only_succeeds_without_stdin(tmp_path: Path) -> None:
    """Calling with --tool + --project should land an event even when stdin is closed."""

    result = runner.invoke(
        app,
        [
            "hub",
            "record",
            "--root",
            str(tmp_path),
            "--tool",
            "shell",
            "--project",
            str(tmp_path),
            "--task",
            "options-only",
            "--type",
            "workflow_observation",
            "--tag",
            "audit",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "recorded ->" in result.output
    events = _read_inbox(tmp_path)
    assert len(events) == 1
    assert events[0]["tool"] == "shell"
    assert events[0]["task"] == "options-only"


def test_record_accepts_json_payload_positional(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "tool": "codex",
            "project_path": str(tmp_path),
            "event_type": "verification",
            "task": "positional json",
            "verification": ["ok"],
        }
    )
    result = runner.invoke(
        app,
        ["hub", "record", "--root", str(tmp_path), payload],
    )
    assert result.exit_code == 0, result.output
    events = _read_inbox(tmp_path)
    assert len(events) == 1 and events[0]["tool"] == "codex"


def test_record_rejects_empty_stdin_when_no_options(tmp_path: Path) -> None:
    """No options, no payload, stdin closed ⇒ helpful yellow error, exit 2."""

    result = runner.invoke(app, ["hub", "record", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "empty stdin" in result.output or "--tool" in result.output


def test_record_defaults_tool_to_shell(tmp_path: Path) -> None:
    """Only --project + --task (no --tool) should succeed with tool=shell."""

    result = runner.invoke(
        app,
        [
            "hub",
            "record",
            "--root",
            str(tmp_path),
            "--project",
            str(tmp_path),
            "--task",
            "default-tool-test",
        ],
    )
    assert result.exit_code == 0, result.output
