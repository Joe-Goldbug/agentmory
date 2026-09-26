"""Contract tests for the Cursor native lifecycle hook."""

from __future__ import annotations

from pathlib import Path

from lwm import capabilities


def _seed_root(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "llms.txt").write_text("# shared context\n", encoding="utf-8")
    (root / "llms-full.txt").write_text("# full context\n", encoding="utf-8")
    (root / "llms.json").write_text("{}\n", encoding="utf-8")
    (root / "wiki" / "purpose.md").parent.mkdir(parents=True)
    (root / "wiki" / "purpose.md").write_text("# purpose\n", encoding="utf-8")
    (root / "wiki" / "overview.md").write_text("# overview\n", encoding="utf-8")
    return root


def _payload(project: Path) -> dict[str, object]:
    return {
        "workspace_roots": [str(project)],
        "session_id": "cursor-session-1",
        "conversation_id": "cursor-conversation-1",
        "transcript_path": "/private/should-not-be-read.jsonl",
    }


def test_session_start_injects_context_and_records_native_read(tmp_path: Path) -> None:
    from adapters.hooks.cursor_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(_payload(project), root=root, phase="session-start")

    assert result["additional_context"]
    receipt = capabilities.load(root)["cursor"]
    assert receipt["direction"] == "read"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"


def test_session_end_records_native_write(tmp_path: Path) -> None:
    from adapters.hooks.cursor_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    assert handle_payload(_payload(project), root=root, phase="session-end") == {}
    receipt = capabilities.load(root)["cursor"]
    assert receipt["direction"] == "write"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"


def test_incomplete_host_payload_fails_open_without_writing_receipt(tmp_path: Path) -> None:
    from adapters.hooks.cursor_native import handle_payload

    root = _seed_root(tmp_path / "root")

    assert handle_payload({}, root=root, phase="session-start") == {}
    assert capabilities.load(root) == {}
