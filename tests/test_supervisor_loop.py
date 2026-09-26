from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

from lwm import supervisor
from lwm import lockfile
from lwm.cycle_receipt import CycleReceiptV2, write_cycle_receipt
from lwm.cycle_state import begin, finish, read_receipt, write_receipt
from lwm.health import collect
from lwm.loop_state import read_active


def test_not_due_supervisor_preserves_last_full_evidence_and_records_loop(tmp_path: Path) -> None:
    previous = finish(begin("full", "due"), status="success")
    write_receipt(tmp_path, previous)
    health_path = tmp_path / "state" / "health.json"
    health_path.write_text('{"status":"healthy"}\n', encoding="utf-8")

    assert supervisor.run_supervisor(tmp_path) == 0
    state = read_active(tmp_path)
    assert state is not None
    assert state.exit_state == "continue"
    assert state.next_action == "wait for the next due window"
    assert read_receipt(tmp_path)["receipt_id"] == previous.receipt_id
    assert health_path.read_text(encoding="utf-8") == '{"status":"healthy"}\n'


def test_scheduled_wake_allows_previous_cycle_runtime(tmp_path: Path, monkeypatch) -> None:
    finished = datetime.now(timezone.utc) - timedelta(seconds=43200 - 120)
    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-before-scheduled-wake",
        runtime_id="runtime-test",
        started_at=(finished - timedelta(minutes=2)).isoformat(),
        finished_at=finished.isoformat(),
        core_status="success",
        overall_status="success",
    )
    write_cycle_receipt(receipt, tmp_path)
    calls: list[Path] = []
    monkeypatch.setattr("lwm.runner.run_cycle", lambda root: calls.append(root) or 0)

    assert supervisor.run_supervisor(tmp_path) == 0
    assert calls == [tmp_path.resolve()]


def test_health_reports_loop_exit_for_an_empty_root(tmp_path: Path) -> None:
    snapshot = collect(tmp_path, strict=True)
    assert snapshot.cycle["loop_exit_state"] in {None, "continue", "human_required", "blocked"}


def test_supervisor_skips_when_another_cycle_holds_the_lock(tmp_path: Path, monkeypatch) -> None:
    held = lockfile.try_acquire_cycle(tmp_path)
    assert held.acquired is True

    def unexpected_cycle(_root: Path) -> int:
        raise AssertionError("a second supervisor must not enter the cycle")

    monkeypatch.setattr("lwm.runner.run_cycle", unexpected_cycle)
    assert supervisor.run_supervisor(tmp_path, force=True) == 0

    assert lockfile.cycle_lock_path(tmp_path).is_file()
    assert lockfile.release_cycle(tmp_path) is True


def test_supervisor_fails_when_cycle_lock_cannot_be_opened(tmp_path: Path, monkeypatch) -> None:
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

    assert supervisor.run_supervisor(tmp_path, force=True) == 1


def test_supervisor_does_not_rewrite_health_after_full_cycle(tmp_path: Path, monkeypatch) -> None:
    health_calls: list[tuple[Path, ...]] = []

    def fake_cycle(_root: Path) -> int:
        return 0

    def unexpected_health(*args, **_kwargs):
        health_calls.append(tuple(args))
        raise AssertionError("full-cycle health is already committed by run_cycle")

    monkeypatch.setattr("lwm.runner.run_cycle", fake_cycle)
    monkeypatch.setattr("lwm.health.collect_and_write", unexpected_health)

    assert supervisor.run_supervisor(tmp_path, force=True) == 0
    assert health_calls == []


def test_supervisor_refuses_external_mutable_owner(tmp_path: Path, monkeypatch) -> None:
    external = tmp_path / "external-state"
    external.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "state").symlink_to(external, target_is_directory=True)

    def unexpected_cycle(_root: Path) -> int:
        raise AssertionError("ownership boundary must block the cycle first")

    monkeypatch.setattr("lwm.runner.run_cycle", unexpected_cycle)

    assert supervisor.run_supervisor(root, force=True) == 2
    assert not (external / "health.json").exists()
    assert not lockfile.cycle_lock_path(root).exists()


def test_cycle_lock_is_atomic_and_released_after_supervisor_error(tmp_path: Path, monkeypatch) -> None:
    first = lockfile.try_acquire_cycle(tmp_path)
    assert first.acquired is True
    second = lockfile.try_acquire_cycle(tmp_path)
    assert second.acquired is False
    assert second.existing is not None
    assert second.existing.pid == first.info.pid
    assert lockfile.release_cycle(tmp_path) is True

    def failing_cycle(_root: Path) -> int:
        raise RuntimeError("cycle failure")

    monkeypatch.setattr("lwm.runner.run_cycle", failing_cycle)
    assert supervisor.run_supervisor(tmp_path, force=True) == 1
    assert not lockfile.cycle_lock_path(tmp_path).exists()


def test_cycle_lock_does_not_reclaim_a_recent_incomplete_marker(tmp_path: Path) -> None:
    path = lockfile.cycle_lock_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    result = lockfile.try_acquire_cycle(tmp_path)

    assert result.acquired is False
    assert path.is_file()
