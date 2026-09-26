"""Tests for the real Antigravity hooks.json bridge."""

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
    (root / "wiki").mkdir(parents=True)
    (root / "wiki" / "purpose.md").write_text("# purpose\n", encoding="utf-8")
    (root / "wiki" / "overview.md").write_text("# overview\n", encoding="utf-8")
    return root


def _payload(project: Path) -> dict[str, object]:
    return {
        "conversationId": "conversation-1",
        "workspacePaths": [str(project)],
        "modelName": "test",
    }


def test_pre_invocation_injects_context_and_records_native_read(tmp_path: Path) -> None:
    from adapters.hooks.antigravity_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(_payload(project), root=root, phase="PreInvocation")

    assert result["injectSteps"]
    assert result["injectSteps"][0]["ephemeralMessage"]
    receipt = capabilities.load(root)["antigravity"]
    assert receipt["direction"] == "read"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"


def test_host_field_casing_variants_are_accepted(tmp_path: Path) -> None:
    from adapters.hooks.antigravity_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(
        {
            "ConversationId": "conversation-uppercase",
            "WorkspacePath": str(project),
        },
        root=root,
        phase="PreInvocation",
    )

    assert result["injectSteps"]
    assert capabilities.load(root)["antigravity"]["direction"] == "read"


def test_empty_workspace_list_uses_cli_working_directory(
    tmp_path: Path, monkeypatch
) -> None:
    from adapters.hooks.antigravity_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    result = handle_payload(
        {"conversationId": "conversation-cwd", "workspacePaths": []},
        root=root,
        phase="PreInvocation",
    )

    assert result["injectSteps"]
    assert capabilities.load(root)["antigravity"]["direction"] == "read"


def test_stop_records_native_write_without_persisting_host_text(tmp_path: Path) -> None:
    from adapters.hooks.antigravity_native import handle_payload

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()

    result = handle_payload(_payload(project), root=root, phase="Stop")

    assert result == {"decision": "allow"}
    receipt = capabilities.load(root)["antigravity"]
    assert receipt["direction"] == "write"
    assert receipt["source"] == "native-hook"
    assert receipt["status"] == "verified"
    events = list((root / "raw" / "events" / "inbox").rglob("*.json"))
    assert events
    assert all("modelName" not in path.read_text(encoding="utf-8") for path in events)


def test_malformed_stdin_fails_open_with_empty_json(tmp_path: Path, monkeypatch, capsys) -> None:
    from adapters.hooks import antigravity_native

    monkeypatch.setattr(
        sys,
        "argv",
        ["antigravity-native", "--root", str(tmp_path), "--phase", "stop"],
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))

    assert antigravity_native.main() == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_stop_forwards_explicit_structured_handoff(
    tmp_path: Path, monkeypatch
) -> None:
    from adapters.hooks import antigravity_native
    from lwm import session_bridge

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()
    captured: dict[str, object] = {}

    def fake_dispatch(root, request, **kwargs):
        captured.update(request)
        return {}

    monkeypatch.setattr(session_bridge, "dispatch", fake_dispatch)
    handoff = {
        "task_id": "task-1",
        "objective": "finish the bounded fix",
        "current_state": "tests are green",
        "changes": ["updated the hook contract"],
        "verifications": ["focused tests passed"],
    }

    antigravity_native.handle_payload(
        {
            **_payload(project),
            "handoff_summary": handoff,
            "prompt": "must not become a handoff",
        },
        root=root,
        phase="Stop",
    )

    assert captured["handoff"] == handoff
