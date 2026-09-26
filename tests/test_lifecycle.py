from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from adapters.hooks import (
    antigravity_sessions,
    cursor_tasks,
    kiro_sessions,
    minimax_sessions,
    trae_sessions,
    vscode_sessions,
)
from lwm import capabilities, lifecycle, runner
from lwm.project_id import resolve_project_root
from lwm.tool_registry import ToolDefinition, ToolRegistry


def _git_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    (project / "nested").mkdir()
    return project


def test_trae_sessions_script_imports_from_outside_project(tmp_path: Path) -> None:
    script = Path(trae_sessions.__file__).resolve()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "trae-sessions" in result.stdout


def test_kiro_sessions_script_imports_from_outside_project(tmp_path: Path) -> None:
    script = Path(kiro_sessions.__file__).resolve()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "kiro-sessions" in result.stdout


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
    started = lifecycle.start(
        tmp_path,
        tool="claude-code",
        project_path=project / "nested",
        session_id="claude-session-1",
        source="native-hook",
        host_proof={
            "integration": "claude-code-hook",
            "event": "SessionStart",
            "session_id": "claude-session-1",
        },
    )
    stopped = lifecycle.stop(
        tmp_path,
        tool="claude-code",
        project_path=project / "nested",
        session_id="claude-session-1",
        source="native-hook",
        host_proof={
            "integration": "claude-code-hook",
            "event": "Stop",
            "session_id": "claude-session-1",
        },
    )

    assert started.project_path == str(project.resolve())
    assert stopped.project_path == str(project.resolve())
    receipts = capabilities.load(tmp_path)
    assert receipts["claude-code"]["source"] == "native-hook"
    assert receipts["claude-code"]["direction"] == "write"
    assert receipts["claude-code"]["project_id"] == started.project_id


def test_lifecycle_rejects_unbound_native_proof_before_writing(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    try:
        lifecycle.start(
            tmp_path,
            tool="claude-code",
            project_path=project,
            session_id="session-1",
            source="native-hook",
        )
    except ValueError as exc:
        assert "host_proof is required" in str(exc)
    else:
        raise AssertionError("unbound native proof was accepted")
    assert not (tmp_path / "raw" / "events").exists()


def test_lifecycle_default_is_observation_only(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    lifecycle.start(tmp_path, tool="codex", project_path=project)
    receipts = capabilities.load(tmp_path)
    assert receipts["codex"]["source"] == "watcher-observed"
    assert receipts["codex"]["status"] == "observed"


def test_lifecycle_alias_is_stored_under_canonical_tool_id(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    started = lifecycle.start(
        tmp_path,
        tool="trae-solo",
        project_path=project,
        source="watcher-observed",
    )
    event = json.loads(started.event_path.read_text(encoding="utf-8"))
    receipts = capabilities.load(tmp_path)
    assert event["tool"] == "trae"
    assert "trae-solo" not in receipts
    assert receipts["trae"]["tool"] == "trae"


def test_lifecycle_uses_persisted_registry_aliases(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    ToolRegistry(
        [
            ToolDefinition(
                tool_id="custom-cli",
                display_name="Custom CLI",
                aliases=("mycli",),
                surfaces=("cli",),
                discovery_paths=(".mycli",),
            )
        ]
    ).save(tmp_path)

    started = lifecycle.start(
        tmp_path,
        tool="mycli",
        project_path=project,
        source="watcher-observed",
    )
    event = json.loads(started.event_path.read_text(encoding="utf-8"))
    assert event["tool"] == "custom-cli"


def test_lifecycle_stop_creates_handoff_only_from_structured_summary(
    tmp_path: Path, monkeypatch
) -> None:
    project = _git_project(tmp_path)

    def fake_git(cwd: Path, args: list[str]) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(project)
        return None

    monkeypatch.setattr("lwm.project_id._run_git", fake_git)
    without_summary = lifecycle.stop(
        tmp_path,
        tool="claude-code",
        project_path=project,
        task_id="task-1",
        task="raw prompt remains operational only",
    )
    assert without_summary.handoff_created is False
    assert not (tmp_path / "state" / "handoffs").exists()

    with_summary = lifecycle.stop(
        tmp_path,
        tool="claude-code",
        project_path=project,
        task_id="task-1",
        task="raw prompt remains operational only",
        handoff_summary={
            "objective": "complete the bounded handoff path",
            "current_state": "tests are being added",
            "next_action": "run focused tests",
        },
    )
    assert with_summary.handoff_created is True
    assert with_summary.handoff_id
    event_files = list((tmp_path / "raw" / "events" / "inbox").rglob("*.json"))
    event_payloads = [
        json.loads(path.read_text(encoding="utf-8")) for path in event_files
    ]
    structured = [
        event for event in event_payloads if event.get("event_type") == "bugfix"
    ]
    assert len(structured) == 0

    durable_stop = lifecycle.stop(
        tmp_path,
        tool="claude-code",
        project_path=project,
        task_id="task-1",
        handoff_summary={
            "objective": "complete the bounded handoff path",
            "current_state": "implementation verified",
            "changes": ["persist structured stop evidence"],
            "verifications": ["focused tests pass"],
        },
    )
    assert durable_stop.handoff_created is True
    all_events = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (tmp_path / "raw" / "events" / "inbox").rglob("*.json")
    ]
    durable = [event for event in all_events if event.get("event_type") == "bugfix"]
    assert len(durable) == 1
    assert durable[0]["handoff_id"] == durable_stop.handoff_id
    assert durable[0]["task_id"] == "task-1"


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
    capabilities.record(
        tmp_path,
        tool="claude-code",
        direction="read",
        project_id="other-project",
        source="native-hook",
    )
    capabilities.record(
        tmp_path,
        tool="claude-code",
        direction="write",
        project_id="other-project",
        source="native-hook",
    )

    result = capabilities.probe(tmp_path, home=home, project_path=project)
    # Mismatched project_id receipts must not yield verified_bidirectional.
    assert result["claude-code"]["status"] in {
        "configured_unverified",
        "observed_read",
        "observed_write",
    }
    assert not result["claude-code"]["status"].startswith("verified_bidirectional")


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
    assert receipts["vscode"]["source"] == "watcher-observed"
    assert receipts["vscode"]["source"] == "watcher-observed"


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
    assert receipts["vscode"]["source"] == "watcher-observed"
    assert receipts["vscode"]["source"] == "watcher-observed"


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
    assert receipts["kiro"]["source"] == "watcher-observed"
    assert receipts["kiro"]["source"] == "watcher-observed"


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
    assert receipts["antigravity"]["source"] == "watcher-observed"
    assert receipts["antigravity"]["source"] == "watcher-observed"


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
    assert receipts["trae"]["source"] == "watcher-observed"
    assert receipts["trae"]["source"] == "watcher-observed"


def test_trae_observer_resolves_indirect_workspace_file(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    storage = tmp_path / "workspaceStorage"
    workspace_dir = storage / "workspace-1"
    workspace_dir.mkdir(parents=True)
    workspace_file = tmp_path / "workspaces" / "project.code-workspace"
    workspace_file.parent.mkdir()
    workspace_file.write_text(
        json.dumps({"folders": [{"path": f"../{project.name}"}]}),
        encoding="utf-8",
    )
    (workspace_dir / "workspace.json").write_text(
        json.dumps({"workspace": workspace_file.as_uri()}), encoding="utf-8"
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

    trae_sessions.observe(
        tmp_path,
        storage,
        "trae-solo",
        set(),
        settle_seconds=0.0,
    )
    receipts = capabilities.load(tmp_path)
    assert trae_sessions._workspace(workspace_dir / "workspace.json") == str(project)
    assert receipts["trae"]["source"] == "watcher-observed"
    assert receipts["trae"]["source"] == "watcher-observed"


def test_minimax_observer_records_finished_session_boundaries(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    database = tmp_path / "runtime-state.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE local_runtime_sessions "
        "(session_id TEXT PRIMARY KEY, record_json TEXT, updated_at_ms INTEGER)"
    )
    connection.execute(
        "INSERT INTO local_runtime_sessions VALUES (?, ?, ?)",
        (
            "session-1",
            json.dumps(
                {
                    "sessionId": "session-1",
                    "workspaceDir": str(project),
                    "status": "finished",
                }
            ),
            1,
        ),
    )
    connection.commit()
    connection.close()

    minimax_sessions.observe(tmp_path, database, set())
    receipts = capabilities.load(tmp_path)
    assert receipts["minimax"]["source"] == "watcher-observed"
    assert receipts["minimax"]["source"] == "watcher-observed"


def test_cursor_project_companion_uses_cursor_identity(tmp_path: Path, monkeypatch) -> None:
    project = _git_project(tmp_path)
    log = project / ".llm-workmem" / "events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(
        json.dumps({"event_type": "workflow_observation", "task": "cursor task"}) + "\n",
        encoding="utf-8",
    )
    emitted: list[dict] = []
    monkeypatch.setattr(
        "adapters.hooks._common.emit",
        lambda root, event: emitted.append(event) or 0,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cursor-tasks",
            "--root",
            str(tmp_path),
            "--project",
            str(project),
        ],
    )

    assert cursor_tasks.main() == 0
    assert emitted[0]["tool"] == "cursor"
    assert emitted[0]["source"]["kind"] == "cursor-tasks"


def test_trae_solo_route_fallback_records_session_boundaries(tmp_path: Path) -> None:
    project = _git_project(tmp_path)
    storage = tmp_path / "workspaceStorage"
    workspace_dir = storage / "workspace-1"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "workspace.json").write_text(
        json.dumps({"folder": project.as_uri()}), encoding="utf-8"
    )
    state_database = workspace_dir / "state.vscdb"
    connection = sqlite3.connect(state_database)
    connection.execute("CREATE TABLE ItemTable (key TEXT, value BLOB)")
    connection.commit()
    connection.close()
    global_database = tmp_path / "global-state.vscdb"
    connection = sqlite3.connect(global_database)
    connection.execute("CREATE TABLE ItemTable (key TEXT, value BLOB)")
    connection.execute(
        "INSERT INTO ItemTable VALUES (?, ?)",
        ("solo-lite:route:user", "/session/solo-session-1"),
    )
    connection.commit()
    connection.close()

    trae_sessions.observe_solo_route(
        tmp_path,
        storage,
        global_database,
        set(),
        settle_seconds=0.0,
    )
    receipts = capabilities.load(tmp_path)
    assert receipts["trae"]["source"] == "watcher-observed"
    assert receipts["trae"]["source"] == "watcher-observed"


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
    assert receipts["shell"]["source"] == "watcher-observed"
    assert receipts["shell"]["source"] == "watcher-observed"
