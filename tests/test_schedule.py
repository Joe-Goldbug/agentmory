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
import json

import pytest

from lwm import behavior_contract
from lwm.harvest import materialize_runtime_layout, runtime_paths, write_schedule_bundle


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
    assert "sys.path.insert" not in text
    assert "hub" in text
    assert "run-supervisor" in text


def test_schedule_prefers_concrete_runtime_over_global_wrapper(tmp_path: Path) -> None:
    home = tmp_path / "home"
    runtime_launcher = (
        home
        / "Library"
        / "Application Support"
        / "llm-workmem-runtime"
        / "app"
        / "venv"
        / "bin"
        / "lwm"
    )
    runtime_launcher.parent.mkdir(parents=True)
    runtime_launcher.write_text("#!/bin/sh\n", encoding="utf-8")
    global_launcher = home / ".local" / "bin" / "lwm"
    global_launcher.parent.mkdir(parents=True)
    global_launcher.write_text("#!/bin/sh\n", encoding="utf-8")

    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.runtime-priority",
        home=home,
    )

    assert str(runtime_launcher) in bundle.plist_path.read_text(encoding="utf-8")
    assert str(global_launcher) not in bundle.plist_path.read_text(encoding="utf-8")


def test_schedule_does_not_fallback_to_global_wrapper(tmp_path: Path) -> None:
    home = tmp_path / "home"
    global_launcher = home / ".local" / "bin" / "lwm"
    global_launcher.parent.mkdir(parents=True)
    global_launcher.write_text("#!/bin/sh\n", encoding="utf-8")

    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.no-fallback",
        home=home,
    )

    expected_runtime = (
        home
        / "Library"
        / "Application Support"
        / "llm-workmem-runtime"
        / "app"
        / "venv"
        / "bin"
        / "lwm"
    )
    text = bundle.plist_path.read_text(encoding="utf-8")
    assert str(expected_runtime) in text
    assert str(global_launcher) not in text


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


def test_schedule_bundle_rejects_a_second_writer_label(tmp_path: Path) -> None:
    write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.owner-a",
        home=tmp_path / "home",
    )

    with pytest.raises(RuntimeError, match="scheduler owner"):
        write_schedule_bundle(
            tmp_path,
            label="com.ethan.lwm.owner-b",
            home=tmp_path / "home",
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
    assert bundle.runtime_root == runtime_paths(root=tmp_path, home=tmp_path / "home").data_root
    assert bundle.plist_path.is_file()


def test_schedule_bundle_does_not_migrate_repository_ownership(tmp_path: Path) -> None:
    root = tmp_path / "workmem"
    home = tmp_path / "home"
    (root / "wiki").mkdir(parents=True)
    (root / "state").mkdir()

    write_schedule_bundle(root, label="com.ethan.lwm.no-migration", home=home)

    assert not (root / "wiki").is_symlink()
    assert not (root / "state").is_symlink()
    assert (runtime_paths(root, home=home).data_root / "wiki").is_dir()


def test_schedule_bundle_does_not_mirror_source_code(tmp_path: Path) -> None:
    (tmp_path / "lwm").mkdir()
    (tmp_path / "lwm" / "current.py").write_text("CURRENT = True\n", encoding="utf-8")
    (tmp_path / "adapters").mkdir()
    (tmp_path / "adapters" / "current.py").write_text("CURRENT = True\n", encoding="utf-8")

    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.no-code-mirror",
        home=tmp_path / "home",
    )

    assert not (bundle.runtime_root / "lwm").exists()
    assert (bundle.runtime_root / "adapters" / "current.py").is_file()
    assert "run-supervisor" in bundle.runner_path.read_text(encoding="utf-8")


def test_schedule_bundle_snapshots_global_behavior_contract(tmp_path: Path) -> None:
    source = tmp_path / "GLOBAL.md"
    source.write_text("<!-- contract-version: 13 -->\n# Contract\n", encoding="utf-8")

    bundle = write_schedule_bundle(
        tmp_path,
        label="com.ethan.lwm.behavior-snapshot",
        home=tmp_path / "home",
    )

    snapshot = bundle.runtime_root / behavior_contract.SNAPSHOT_PATH
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert payload["version"] == "13"
    assert payload["source_path"] == str(source.resolve())
    assert payload["sha256"] == behavior_contract.load(
        tmp_path, contract_path=source
    ).sha256


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
    """Bootstrap uses RunAtLoad without killing its newly started cycle."""

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
    assert "kickstart" not in verbs
