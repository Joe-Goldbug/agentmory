from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lwm.cli import app
from lwm.project_id import record_project


runner = CliRunner()


def _seed_event(root: Path, project: Path, project_id: str) -> None:
    path = root / "raw" / "events" / "processed" / "2026-07-18"
    path.mkdir(parents=True)
    (path / "event.json").write_text(
        json.dumps(
            {
                "event_id": "event-cli",
                "timestamp": "2026-07-18T12:00:00+08:00",
                "tool": "codex",
                "project_path": str(project),
                "project_id": project_id,
                "event_type": "decision",
                "importance": "project",
                "privacy": "sanitized",
                "task": "CLI evidence decision",
                "decisions": ["CLI evidence decision"],
                "verification": ["manual test"],
            }
        ),
        encoding="utf-8",
    )


def test_cli_recall_returns_packet_json(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    project_id = record_project(tmp_path, project).project_id
    _seed_event(tmp_path, project, project_id)

    result = runner.invoke(
        app,
        [
            "hub",
            "recall",
            "CLI evidence decision",
            "--project",
            str(project),
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["packet"]["scope"] == "project"
    assert payload["packet"]["evidence"][0]["fact_id"] == "event-cli"


def test_cli_recall_can_render_markdown(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "hub",
            "recall",
            "全局规则",
            "--format",
            "markdown",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "# Recall Packet" in result.output
    assert "global-only" in result.output
