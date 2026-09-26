from __future__ import annotations

from pathlib import Path
import subprocess

import lwm.health as health
import lwm.runner as runner
from lwm import lockfile
from lwm.loop_state import read_active, read_last
from lwm.cycle_receipt import load_last_attempt, load_latest
from lwm.registry import register
from lwm.tool_registry import ToolDefinition, ToolRegistry


class _Ingest:
    failed = False

    def render(self) -> str:
        return "ingest ok"


class _Watch:
    class audit:
        ok = True


class _Health:
    status = "healthy"

    def render(self) -> str:
        return "healthy"


def _stub_cycle(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_run_adapter", lambda *args: (0, "adapter ok"))
    monkeypatch.setattr(runner, "_sweep_shell_events", lambda root: 0)
    monkeypatch.setattr(runner, "sync_registered_projects", lambda root: {"status": "healthy", "projects": {}})
    monkeypatch.setattr(runner, "ingest_run", lambda root, with_lock=True: _Ingest())
    monkeypatch.setattr(runner, "run_watch", lambda *args, **kwargs: _Watch())
    monkeypatch.setattr(runner, "render_watch_report", lambda watch: "watch ok")
    monkeypatch.setattr(runner, "write_global_adapters", lambda root: None)
    monkeypatch.setattr(
        runner,
        "analyze_pending",
        lambda root: {"status": "disabled", "analyzed": [], "deferred": [], "dead_letter": [], "errors": []},
    )
    def write_healthy(root: Path, **kwargs) -> _Health:
        state = root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "health.json").write_text(
            '{"status":"healthy","quality":{"audit_ok":true}}\n', encoding="utf-8"
        )
        return _Health()

    monkeypatch.setattr(health, "collect_and_write", write_healthy)


def test_runner_records_verified_completion_when_cycle_and_audit_succeed(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_cycle(monkeypatch)

    assert runner.run_cycle(tmp_path) == 0
    state = read_last(tmp_path)
    assert state is not None
    assert state.exit_state == "completed_verified"
    assert "audit" in state.actual_observation


def test_successful_cycle_health_does_not_inherit_previous_due_state(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_cycle(monkeypatch)
    observed = {}

    def capture_health(root: Path, **kwargs) -> _Health:
        observed.update(kwargs["cycle_override"])
        state = root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "health.json").write_text(
            '{"status":"healthy","quality":{"audit_ok":true}}\n', encoding="utf-8"
        )
        return _Health()

    monkeypatch.setattr(health, "collect_and_write", capture_health)

    assert runner.run_cycle(tmp_path) == 0
    assert observed["due"] is False
    assert observed["last_success_at"]


def test_run_cycle_skips_when_the_shared_writer_lock_is_held(
    tmp_path: Path, monkeypatch
) -> None:
    held = lockfile.try_acquire_cycle(tmp_path)
    assert held.acquired is True
    monkeypatch.setattr(
        runner,
        "_run_cycle_unlocked",
        lambda _root: (_ for _ in ()).throw(AssertionError("cycle must not enter")),
    )

    assert runner.run_cycle(tmp_path) == 0
    assert lockfile.release_cycle(tmp_path) is True


def test_run_cycle_fails_when_cycle_lock_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        lockfile,
        "try_acquire_cycle",
        lambda _root, **_kwargs: lockfile.LockResult(
            acquired=False,
            info=None,
            existing=None,
            error="cycle lock open failed: Operation not permitted",
        ),
    )

    assert runner.run_cycle(tmp_path) == 1


def test_runner_records_human_gate_when_health_proof_is_unknown(tmp_path: Path, monkeypatch) -> None:
    _stub_cycle(monkeypatch)
    def write_unknown(root: Path, **kwargs):
        state = root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "health.json").write_text(
            '{"status":"unknown","quality":{"audit_ok":true}}\n', encoding="utf-8"
        )
        return type("Unknown", (), {"status": "unknown", "render": lambda self: "unknown"})()

    monkeypatch.setattr(health, "collect_and_write", write_unknown)

    assert runner.run_cycle(tmp_path) != 0
    state = read_last(tmp_path)
    assert state is not None
    assert state.exit_state == "human_required"
    assert state.human_gate is True


def test_quality_warning_keeps_cycle_degraded_but_returns_success(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_cycle(monkeypatch)

    class WarningWatch:
        class audit:
            ok = False

    class DegradedHealth:
        status = "degraded"

        def render(self) -> str:
            return "degraded"

    monkeypatch.setattr(runner, "run_watch", lambda *args, **kwargs: WarningWatch())

    def write_degraded(root: Path, **kwargs) -> DegradedHealth:
        state = root / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "health.json").write_text(
            '{"status":"degraded","quality":{"audit_ok":false}}\n',
            encoding="utf-8",
        )
        return DegradedHealth()

    monkeypatch.setattr(health, "collect_and_write", write_degraded)

    assert runner.run_cycle(tmp_path) == 0
    state = read_active(tmp_path)
    assert state is not None
    assert state.exit_state == "continue"


def test_optional_adapter_failure_is_recorded_as_warning_not_core_failure(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_cycle(monkeypatch)

    def fail_adapter(name: str, module: str, root: Path, extra: tuple[str, ...]):
        if name == "vscode":
            return 1, "adapter vscode: unavailable"
        return 0, f"adapter {name}: ok"

    monkeypatch.setattr(runner, "_run_adapter", fail_adapter)

    assert runner.run_cycle(tmp_path) == 0
    receipt = load_last_attempt(tmp_path)
    assert receipt is not None
    assert receipt["schema_version"] == 2
    assert receipt["core_status"] == "success_with_warnings"
    assert any(source["name"] == "vscode" and source["status"] == "degraded"
               for source in receipt["sources"])


def test_shell_sweep_ignores_legacy_non_json_tail(tmp_path: Path, monkeypatch) -> None:
    shell_dir = tmp_path / "raw" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "legacy.jsonl").write_text("legacy shell history line\n", encoding="utf-8")
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record must not run")),
    )

    assert runner._sweep_shell_events(tmp_path) == 0
    assert (tmp_path / "state" / "shell-session-events.json").read_text(encoding="utf-8") == "[]"


def test_shell_sweep_keeps_valid_record_failure_visible(tmp_path: Path, monkeypatch) -> None:
    shell_dir = tmp_path / "raw" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "current.jsonl").write_text(
        '{"ts":1,"session":"s1","pwd":"/tmp","command":"git status"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(runner.lifecycle, "start", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=2),
    )

    assert runner._sweep_shell_events(tmp_path) == 2


def test_shell_sweep_processes_all_lines_and_identifies_registered_cli(
    tmp_path: Path, monkeypatch
) -> None:
    shell_dir = tmp_path / "raw" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "current.jsonl").write_text(
        "\n".join(
            [
                '{"ts":1,"session":"s1","pwd":"/tmp","command":"gemini --resume"}',
                '{"ts":2,"session":"s1","pwd":"/tmp","command":"opencode run"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    lifecycle_calls: list[tuple[str, str]] = []

    def record_lifecycle(*args, **kwargs):
        lifecycle_calls.append((kwargs["tool"], kwargs["source"]))

    monkeypatch.setattr(runner.lifecycle, "start", record_lifecycle)
    monkeypatch.setattr(runner.lifecycle, "stop", record_lifecycle)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=0),
    )

    assert runner._sweep_shell_events(tmp_path) == 0
    assert lifecycle_calls == [
        ("gemini-cli", "watcher-observed"),
        ("gemini-cli", "watcher-observed"),
        ("opencode", "watcher-observed"),
        ("opencode", "watcher-observed"),
    ]


def test_shell_tool_identity_uses_registry_aliases() -> None:
    assert runner._shell_tool_for_command("agy run") == "antigravity"
    assert runner._shell_tool_for_command("m3 --prompt hello") == "minimax"
    assert runner._shell_tool_for_command("claude --help") == "claude-code"
    assert runner._shell_tool_for_command("cc --help") == "claude-code"
    assert runner._shell_tool_for_command("python -m pytest") == "shell"


def test_shell_tool_identity_uses_persisted_registry_aliases(tmp_path: Path) -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="custom-cli",
                display_name="Custom CLI",
                aliases=("mycli",),
                surfaces=("cli",),
                discovery_paths=(".mycli",),
            )
        ]
    )
    registry.save(tmp_path)

    assert runner._shell_tool_for_command("mycli run", root=tmp_path) == "custom-cli"


def test_runner_resolves_registered_observers_separately_from_collectors(
    tmp_path: Path,
) -> None:
    observers = runner._observer_modules_for(tmp_path)

    assert ("antigravity", "adapters.hooks.antigravity_sessions", ()) in observers
    assert all(
        row not in runner._adapter_modules_for(tmp_path)
        for row in observers
    )


def test_cycle_executes_registered_observer_module(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(runner, "_adapter_modules_for", lambda root: ())
    monkeypatch.setattr(
        runner,
        "_observer_modules_for",
        lambda root: (("antigravity", "adapters.hooks.antigravity_sessions", ()),),
    )
    monkeypatch.setattr(
        runner,
        "_run_adapter",
        lambda name, module, root, extra: (calls.append((name, module)) or (0, "observer ok")),
    )
    monkeypatch.setattr(
        runner,
        "_sweep_shell_events",
        lambda root: 0,
    )
    monkeypatch.setattr(
        runner,
        "sync_registered_projects",
        lambda root: {"status": "healthy", "projects": {}},
    )
    monkeypatch.setattr(runner, "ingest_run", lambda root, with_lock=True: _Ingest())
    monkeypatch.setattr(
        runner,
        "rebuild_project_pages",
        lambda root: type("Rebuild", (), {"pages_written": 0, "pages_removed": 0})(),
    )
    monkeypatch.setattr(runner, "load_processed_events", lambda root: [])
    monkeypatch.setattr(runner, "generate_candidates", lambda root, events: ())
    monkeypatch.setattr(runner, "seed_analysis_candidates", lambda root, events: ())
    monkeypatch.setattr(
        runner,
        "analyze_pending",
        lambda root: {"status": "disabled", "analyzed": [], "deferred": [], "dead_letter": [], "errors": []},
    )
    monkeypatch.setattr(runner, "run_watch", lambda *args, **kwargs: _Watch())
    monkeypatch.setattr(runner, "render_watch_report", lambda watch: "watch ok")
    monkeypatch.setattr(
        runner,
        "build_context",
        lambda *args, **kwargs: type("Context", (), {"ok": True, "markdown": "context"})(),
    )
    monkeypatch.setattr(
        runner,
        "write_ai_exports",
        lambda root: type("Exports", (), {"pages": 0})(),
    )
    monkeypatch.setattr(runner, "write_global_adapters", lambda root: None)

    report = runner._run_cycle_stages(tmp_path)

    assert calls == [("antigravity", "adapters.hooks.antigravity_sessions")]
    assert any(source.name == "antigravity:observer" for source in report.sources)


def test_runner_uses_ingest_count_properties_when_committing_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    _stub_cycle(monkeypatch)

    assert runner.run_cycle(tmp_path) == 0
    receipt = load_latest(tmp_path)
    assert receipt is not None
    assert receipt["counts"] == {"processed": 0, "accepted": 0, "rejected": 0, "failed": 0}


def test_vscode_task_collector_receives_each_registered_project(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    register(tmp_path, project)
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    code, detail = runner._run_adapter(
        "vscode", "adapters.hooks.vscode_tasks", tmp_path, ()
    )

    assert code == 0
    assert "vscode" in detail
    assert len(calls) == 1
    assert calls[0][1:4] == ["-I", "-m", "adapters.hooks.vscode_tasks"]
    assert calls[0][-2:] == ["--project", str(project.resolve())]


def test_runner_commits_failed_core_receipt_when_stage_crashes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_run_cycle_stages",
        lambda root: (_ for _ in ()).throw(RuntimeError("stage boom")),
    )

    assert runner.run_cycle(tmp_path) == 1
    receipt = load_last_attempt(tmp_path)
    assert receipt is not None
    assert receipt["core_status"] == "failed_core"
    assert any("stage boom" in error for error in receipt["errors"])


def test_runner_records_optional_analysis_in_cycle_receipt(tmp_path: Path, monkeypatch) -> None:
    _stub_cycle(monkeypatch)
    monkeypatch.setattr(
        runner,
        "analyze_pending",
        lambda root: {"status": "ok", "analyzed": ["candidate-1"], "deferred": [], "dead_letter": [], "errors": []},
    )

    assert runner.run_cycle(tmp_path) == 0
    receipt = load_latest(tmp_path)
    assert receipt is not None
    assert receipt["analysis"]["compiler"]["analyzed"] == ["candidate-1"]
    assert any(stage["name"] == "optional-analysis" for stage in receipt["stages"])
