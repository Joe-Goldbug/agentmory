from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from adapters.hooks import (
    antigravity_sessions,
    kiro_sessions,
    trae_sessions,
    vscode_sessions,
)
from lwm import capabilities, lifecycle, runner
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


def test_kiro_observer_records_local_session_boundaries(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)
    sessions_root = tmp_path / "workspace-sessions"
    workspace_sessions = sessions_root / "encoded-workspace"
    workspace_sessions.mkdir(parents=True)
    session_id = "session-1"
    (workspace_sessions / "sessions.json").write_text(
        json.dumps(
            [
                {
                    "sessionId": session_id,
                    "title": "Test",
                    "workspaceDirectory": str(project),
                }
            ]
        ),
        encoding="utf-8",
    )
    session_path = workspace_sessions / f"{session_id}.json"
    session_path.write_text("{}", encoding="utf-8")
    old = time.time() - 120
    os.utime(session_path, (old, old))

    monkeypatch.setattr(
        "sys.argv",
        [
            "kiro-sessions",
            "--root",
            str(tmp_path),
            "--sessions-root",
            str(sessions_root),
        ],
    )
    assert kiro_sessions.main() == 0
    receipts = capabilities.load(tmp_path)
    assert receipts["kiro:read"]["source"] == "watcher-observed"
    assert receipts["kiro:write"]["source"] == "watcher-observed"


def test_antigravity_observer_records_local_session_boundaries(
    tmp_path: Path, monkeypatch
) -> None:
    project = _git_project(tmp_path)
    metadata = tmp_path / "conversation_metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "conversations": {
                    "session-1": {
                        "summary": {
                            "ID": "session-1",
                            "UpdatedAt": "2020-01-01T00:00:00Z",
                            "WorkspaceURIs": [project.as_uri()],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "antigravity-sessions",
            "--root",
            str(tmp_path),
            "--metadata",
            str(metadata),
        ],
    )
    assert antigravity_sessions.main() == 0
    receipts = capabilities.load(tmp_path)
    assert receipts["antigravity:read"]["source"] == "watcher-observed"
    assert receipts["antigravity:write"]["source"] == "watcher-observed"


def test_trae_observer_records_local_session_boundaries(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    storage = tmp_path / "workspaceStorage"
    workspace_dir = storage / "workspace-1"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "workspace.json").write_text(
        json.dumps({"folder": project.as_uri()}), encoding="utf-8"
    )
    database = workspace_dir / "state.vscdb"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)")
    connection.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
        ("icube_session_agent_map", json.dumps({"session-1": "solo_agent"})),
    )
    connection.commit()
    connection.close()
    old = time.time() - 120
    os.utime(database, (old, old))

    seen: set[str] = set()
    trae_sessions.observe(
        tmp_path,
        storage,
        "trae",
        seen,
        settle_seconds=30.0,
    )
    receipts = capabilities.load(tmp_path)
    assert receipts["trae:read"]["source"] == "watcher-observed"
    assert receipts["trae:write"]["source"] == "watcher-observed"


def test_shell_sweep_records_observed_lifecycle(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)
    shell_dir = tmp_path / "raw" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "2026-07-22.jsonl").write_text(
        json.dumps(
            {
                "ts": 1,
                "pwd": str(project),
                "session": "shell-1",
                "command": "print verification",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "lwm.runner.subprocess.run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )
    assert runner._sweep_shell_events(tmp_path) == 0
    receipts = capabilities.load(tmp_path)
    assert receipts["shell:read"]["source"] == "watcher-observed"
    assert receipts["shell:write"]["source"] == "watcher-observed"
