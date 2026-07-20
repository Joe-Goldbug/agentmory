from __future__ import annotations

from pathlib import Path

import lwm.health as health
import lwm.runner as runner
from lwm.loop_state import read_last


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
    def write_healthy(root: Path) -> _Health:
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


def test_runner_records_human_gate_when_health_proof_is_unknown(tmp_path: Path, monkeypatch) -> None:
    _stub_cycle(monkeypatch)
    def write_unknown(root: Path):
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
