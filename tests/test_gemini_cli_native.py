"""Contract tests for the Gemini CLI native lifecycle hook."""

from __future__ import annotations

import io
import json
import sys
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
        "cwd": str(project),
        "session_id": "gemini-session-1",
        "prompt": "do not persist this prompt",
    }


def test_session_start_injects_context_and_records_native_read(tmp_path: Path) -> None:
    from adapters.hooks.gemini_cli_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(_payload(project), root=root, phase="SessionStart")

    assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert result["hookSpecificOutput"]["additionalContext"]
    receipt = capabilities.load(root)["gemini-cli"]
    assert receipt["direction"] == "read"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"


def test_session_end_records_native_write_without_persisting_prompt(tmp_path: Path) -> None:
    from adapters.hooks.gemini_cli_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(_payload(project), root=root, phase="SessionEnd")

    assert result == {}
    receipt = capabilities.load(root)["gemini-cli"]
    assert receipt["direction"] == "write"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"
    events = list((root / "raw" / "events" / "inbox").rglob("*.json"))
    assert events
    assert all("do not persist this prompt" not in path.read_text(encoding="utf-8") for path in events)


def test_malformed_stdin_fails_open_with_empty_json(tmp_path: Path, monkeypatch, capsys) -> None:
    from adapters.hooks import gemini_cli_native

    monkeypatch.setattr(
        sys,
        "argv",
        ["gemini-native", "--root", str(tmp_path), "--phase", "SessionEnd"],
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))

    assert gemini_cli_native.main() == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_incomplete_host_payload_fails_open_without_writing_receipt(tmp_path: Path) -> None:
    from adapters.hooks.gemini_cli_native import handle_payload

    root = _seed_root(tmp_path / "root")

    assert handle_payload(
        {"prompt": "do not persist this prompt"},
        root=root,
        phase="SessionStart",
    ) == {}
    assert capabilities.load(root) == {}
    assert not list((root / "raw" / "events").rglob("*.json"))


def test_session_end_forwards_explicit_structured_handoff(
    tmp_path: Path, monkeypatch
) -> None:
    from adapters.hooks import gemini_cli_native

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()
    captured: dict[str, object] = {}

    def fake_stop(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("lwm.lifecycle.stop", fake_stop)
    handoff = {
        "task_id": "task-1",
        "objective": "finish the bounded fix",
        "current_state": "tests are green",
        "changes": ["updated the hook contract"],
        "verifications": ["focused tests passed"],
    }

    gemini_cli_native.handle_payload(
        {
            **_payload(project),
            "prompt": "must not become a handoff",
            "task_summary": handoff,
        },
        root=root,
        phase="SessionEnd",
    )

    assert captured["handoff_summary"] == handoff
