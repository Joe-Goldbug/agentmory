from __future__ import annotations

from pathlib import Path

from lwm.memory_api import retain


def test_retain_does_not_create_second_identical_inbox_event(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    first = retain(
        tmp_path,
        tool="shell",
        project_path=str(project),
        task="same checkpoint",
        event_type="checkpoint",
    )
    second = retain(
        tmp_path,
        tool="shell",
        project_path=str(project),
        task="same checkpoint",
        event_type="checkpoint",
    )

    files = list((tmp_path / "raw" / "events" / "inbox").rglob("*.json"))
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["existing_event_id"] == first["event"]["event_id"]
    assert len(files) == 1
