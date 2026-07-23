"""Schedule bundle tests: ``lwm schedule`` write paths and load stub.

Scope Lock:
- Solves: proves ``write_schedule_bundle`` writes a usable plist + script
  without touching the real user's LaunchAgents.
- Does not solve: actually registering with launchctl (only verified
  indirectly via ``subprocess.run`` monkeypatching).
- Acceptance: bundle paths exist, plist starts with the right label and
  has an interval that matches the requested seconds.
"""

from __future__ import annotations

from pathlib import Path

from lwm.harvest import materialize_runtime_layout, write_schedule_bundle


def _slug(name: str) -> str:
    from lwm.harvest import _slugify

    return _slugify(name)


def test_write_schedule_bundle_writes_all_files(tmp_path: Path) -> None:
    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.test",
        interval_seconds=3600,
        home=tmp_path / "home",
    )
    assert bundle.script_path.is_file()
    assert bundle.runner_path.is_file()
    assert bundle.launch_runner_path.is_file()
    assert bundle.plist_path.is_file()
    assert bundle.launch_agents_plist_path.is_file()
    text = bundle.plist_path.read_text(encoding="utf-8")
    assert "com.ethan.lwm.test" in text
    assert "<integer>3600</integer>" in text


def test_schedule_runner_uses_local_runtime_copy(tmp_path: Path) -> None:
    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.local",
        interval_seconds=900,
        home=tmp_path / "home",
    )
    text = bundle.runner_path.read_text(encoding="utf-8")
    assert "SOURCE_ROOT" not in text
    assert "sys.path.insert(0, str(ROOT))" in text


def test_schedule_bundle_is_idempotent(tmp_path: Path) -> None:
    """Re-running with the same label should rewrite the same plist contents."""

    first = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.idem",
        interval_seconds=7200,
        home=tmp_path / "home",
    )
    second = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.idem",
        interval_seconds=7200,
        home=tmp_path / "home",
    )
    assert first.plist_path.read_text(encoding="utf-8") == second.plist_path.read_text(
        encoding="utf-8"
    )


def test_schedule_bundle_runtime_layout(tmp_path: Path) -> None:
    """Runtime workspace under ``~/Library/Application Support`` mirrors the mutable roots.

    The directory layout stays inside an isolated test HOME so the suite never
    creates persistent data in the user's real ``Application Support``.
    """

    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.rt",
        interval_seconds=10800,
        home=tmp_path / "home",
    )
    assert bundle.runtime_root.is_dir()
    assert bundle.runtime_root.name  # non-empty name
    # The package itself copies whatever exists in ``root / lwm``; tmp_path has
    # no such dir so we can only assert that no exception was raised.
    assert bundle.plist_path.is_file()


def test_runtime_code_and_adapters_are_mirrored_without_deleted_residue(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workmem"
    home = tmp_path / "home"
    (root / "lwm").mkdir(parents=True)
    (root / "adapters").mkdir()
    (root / "lwm" / "current.py").write_text("CURRENT = True\n", encoding="utf-8")
    (root / "adapters" / "current.md").write_text("# Current\n", encoding="utf-8")

    runtime = materialize_runtime_layout(root, home=home)
    (runtime / "lwm" / "removed.py").write_text("OLD = True\n", encoding="utf-8")
    (runtime / "adapters" / "removed.md").write_text("# Old\n", encoding="utf-8")

    materialize_runtime_layout(root, home=home)

    assert not (runtime / "lwm" / "removed.py").exists()
    assert not (runtime / "adapters" / "removed.md").exists()
    assert (runtime / "lwm" / "current.py").is_file()
    assert (runtime / "adapters" / "current.md").is_file()


def test_load_schedule_bundle_invokes_launchctl(
    tmp_path: Path, monkeypatch
) -> None:
    """``load_schedule_bundle`` should bootout, bootstrap, kickstart via subprocess."""

    import lwm.harvest as harvest_module

    calls: list[tuple[str, tuple]] = []

    def _fake_run(cmd, check=False, capture_output=False, text=False, **_):
        from unittest.mock import MagicMock

        calls.append((cmd[0], tuple(cmd)))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    monkeypatch.setattr(harvest_module.subprocess, "run", _fake_run)
    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.load",
        interval_seconds=3600,
        home=tmp_path / "home",
    )
    harvest_module.load_schedule_bundle(bundle)
    verbs = [c[1][1] for c in calls if len(c[1]) > 1]
    assert "bootout" in verbs
    assert "bootstrap" in verbs
    assert "kickstart" in verbs
