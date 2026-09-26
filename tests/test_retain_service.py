from __future__ import annotations

from pathlib import Path

from lwm import hub_service
from mcp.lwm_server import _call_tool


def test_canonical_retain_service_deduplicates_identical_events(tmp_path: Path) -> None:
    event = {
        "tool": "shell",
        "project_path": str(tmp_path),
        "event_type": "checkpoint",
        "task": "same checkpoint",
    }
    first = hub_service.retain_event(tmp_path, event)
    second = hub_service.retain_event(tmp_path, event)
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["existing_event_id"] == first["event_id"]


def test_mcp_retain_uses_same_duplicate_contract(tmp_path: Path) -> None:
    arguments = {
        "root": str(tmp_path),
        "event": {
            "tool": "gemini-cli",
            "project_path": str(tmp_path),
            "event_type": "checkpoint",
            "task": "same checkpoint",
        },
    }
    first = _call_tool("lwm_retain", arguments)
    second = _call_tool("lwm_retain", arguments)
    assert first["ingested"] is True
    assert first["duplicate"] is False
    assert second["ingested"] is False
    assert second["duplicate"] is True
    assert second["existing_event_id"] == first["event_id"]
