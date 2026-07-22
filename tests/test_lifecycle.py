from __future__ import annotations

import json
import os
import time
from pathlib import Path

from lwm import capabilities, lifecycle
from adapters.hooks import vscode_sessions
from lwm.project_id import resolve_project_root


def _git_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    (project / "nested").mkdir()
    return project


def test_resolve_project_root_uses_git_toplevel_for_nested_path(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)

    def fake_git(cwd: Path, args: list[str]) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(project)
        return None

    monkeypatch.setattr("lwm.project_id._run_git", fake_git)
    assert resolve_project_root(project / "nested") == project.resolve()


def test_lifecycle_start_and_stop_write_canonical_hook_receipts(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)

    def fake_git(cwd: Path, args: list[str]) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(project)
        return None

    monkeypatch.setattr("lwm.project_id._run_git", fake_git)
    started = lifecycle.start(tmp_path, tool="claude-code", project_path=project / "nested")
    stopped = lifecycle.stop(tmp_path, tool="claude-code", project_path=project / "nested")

    assert started.project_path == str(project.resolve())
    assert stopped.project_path == str(project.resolve())
    receipts = capabilities.load(tmp_path)
    assert receipts["claude-code:read"]["source"] == "native-hook"
    assert receipts["claude-code:write"]["source"] == "native-hook"
    assert receipts["claude-code:read"]["project_id"] == receipts["claude-code:write"]["project_id"]


def test_probe_requires_matching_lifecycle_receipts_for_expected_project(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    target = home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")
    project = _git_project(tmp_path)

    def fake_git(cwd: Path, args: list[str]) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(project)
        return None

    monkeypatch.setattr("lwm.project_id._run_git", fake_git)
    capabilities.record(tmp_path, tool="claude-code", direction="read", project_id="wrong", source="cli-context")
    capabilities.record(tmp_path, tool="claude-code", direction="write", project_id="wrong", source="cli-record")

    result = capabilities.probe(tmp_path, home=home, project_path=project)
    assert result["claude-code"]["status"] == "configured_unverified"


def test_vscode_observer_records_local_session_boundaries(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)
    sessions = tmp_path / "sessions" / "one"
    sessions.mkdir(parents=True)
    (sessions / "workspace.yaml").write_text(f"git_root: {project}\n", encoding="utf-8")
    (sessions / "events.jsonl").write_text(
        '{"id":"start","type":"session.start","data":{"sessionId":"one"}}\n'
        '{"id":"idle","type":"session.idle","data":{"sessionId":"one"}}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["vscode-sessions", "--root", str(tmp_path), "--sessions", str(sessions.parent)])
    assert vscode_sessions.main() == 0
    receipts = capabilities.load(tmp_path)
    assert receipts["vscode:read"]["source"] == "watcher-observed"
    assert receipts["vscode:write"]["source"] == "watcher-observed"


def test_vscode_observer_reads_workspace_storage_transcript(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)
    storage = tmp_path / "workspaceStorage" / "one"
    transcript_dir = storage / "GitHub.copilot-chat" / "transcripts"
    transcript_dir.mkdir(parents=True)
    (storage / "workspace.json").write_text(
        json.dumps({"folder": project.as_uri()}), encoding="utf-8"
    )
    transcript = transcript_dir / "session-1.jsonl"
    transcript.write_text(
        json.dumps({"id": "start", "type": "session.start", "data": {"sessionId": "session-1"}})
        + "\n",
        encoding="utf-8",
    )
    old = time.time() - 120
    os.utime(transcript, (old, old))

    def fake_git(cwd: Path, args: list[str]) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(project)
        return None

    monkeypatch.setattr("lwm.project_id._run_git", fake_git)
    monkeypatch.setattr(
        "sys.argv",
        [
            "vscode-sessions",
            "--root",
            str(tmp_path),
            "--sessions",
            str(tmp_path / "missing-sessions"),
            "--workspace-storage",
            str(tmp_path / "workspaceStorage"),
        ],
    )

    assert vscode_sessions.main() == 0
    receipts = capabilities.load(tmp_path)
    assert receipts["vscode:read"]["source"] == "watcher-observed"
    assert receipts["vscode:write"]["source"] == "watcher-observed"
