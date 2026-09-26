"""Non-destructive runtime staging and packaged-resource contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from importlib.resources import files

from lwm import harvest
from lwm.eval import packaged_eval_suite, parse_eval_suite
from lwm.migration import MigrationApprovalError, apply_data_owner_migration, tree_hash


def test_package_boundary_excludes_workstation_outputs() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    for pattern in (
        '"raw/**"',
        '"state/**"',
        '"global/**"',
        '"projects/**"',
        '".codebase-memory/**"',
        '".lwm-*-state.json"',
        '"lwiki-sources.json"',
        '"lwm-sources.json"',
        '"AGENTS.md"',
        '"GLOBAL.md"',
        '"docs/migration/**"',
    ):
        assert pattern in text, pattern

    for pattern in (
        '"adapters/*.md"',
        '"adapters/*.mdc"',
        '"adapters/*.sh"',
        '"adapters/traerules"',
        '"adapters/adapter-manifest.json"',
    ):
        assert text.count(pattern) >= 2, pattern


def test_hook_sources_do_not_reintroduce_checkout_imports() -> None:
    hooks_dir = Path(__file__).parents[1] / "adapters" / "hooks"
    for path in hooks_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "sys.path.insert" not in text, path
    common = (hooks_dir / "_common.py").read_text(encoding="utf-8")
    assert "source_root" not in common


def test_user_wrapper_forces_isolated_runtime_import() -> None:
    wrapper = Path(__file__).parents[1] / "scripts" / "lwm-user-wrapper.sh"
    assert '"$PYTHON_BIN" -I -m lwm.cli "$@"' in wrapper.read_text(encoding="utf-8")


def test_hook_emit_removes_iCloud_checkout_from_child_environment(
    monkeypatch, tmp_path: Path
) -> None:
    from adapters.hooks import _common

    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args[0]
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setenv(
        "PYTHONPATH",
        "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem:/private/tmp/allowed",
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _common.emit(tmp_path, {"tool": "shell", "event_type": "workflow_observation"}) == 0
    assert captured["args"][1:4] == ["-I", "-m", "lwm.cli"]
    child_env = captured["env"]
    assert isinstance(child_env, dict)
    assert "Mobile Documents" not in str(child_env.get("PYTHONPATH", ""))
    assert "/private/tmp/allowed" in str(child_env.get("PYTHONPATH", ""))


def test_packaged_eval_suite_is_readable_and_non_empty() -> None:
    resource = packaged_eval_suite()
    text = resource.read_text(encoding="utf-8")
    assert text.strip()
    assert len(parse_eval_suite(resource)) == 2
    assert files("lwm.resources").joinpath("eval-suite.txt").is_file()


def test_runtime_paths_keep_app_and_data_separate(tmp_path: Path) -> None:
    paths = harvest.runtime_paths(tmp_path / "LLM-WorkMem", home=tmp_path / "home")
    assert paths.runtime_base == tmp_path / "home" / "Library" / "Application Support" / "llm-workmem-runtime"
    assert paths.app_venv == paths.runtime_base / "app" / "venv"
    assert paths.data_root == paths.runtime_base / "llm-workmem"
    assert paths.state_root == paths.data_root / "state"


def test_runtime_data_root_is_not_derived_from_checkout_name(tmp_path: Path) -> None:
    paths = harvest.runtime_paths(tmp_path / "another-checkout", home=tmp_path / "home")

    assert paths.data_root == paths.runtime_base / "llm-workmem"


def test_runtime_manifest_writer_emits_parseable_hash_entries(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "write-runtime-manifest.py"
    output = tmp_path / "runtime-manifest.json"
    first = "a" * 64
    second = "b" * 64
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--runtime-id",
            "runtime-test",
            "--source-revision",
            "revision",
            "--source-dirty-hash",
            "dirty",
            "--source-root",
            "/tmp/source with spaces",
            "--runtime-root",
            "/tmp/runtime",
            "--python",
            "/tmp/python",
            "--wheel",
            "lwm.whl",
            "--import-probe",
            json.dumps({"module": "/tmp/site-packages/lwm/__init__.py"}),
        ],
        input=f"{first}  adapters/file with spaces.py\n{second}  lwm/__init__.py\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["file_hashes"] == [
        f"{first}  adapters/file with spaces.py",
        f"{second}  lwm/__init__.py",
    ]


def test_runtime_manifest_writer_rejects_malformed_hash_lines(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "write-runtime-manifest.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(tmp_path / "runtime-manifest.json"),
            "--runtime-id",
            "runtime-test",
            "--source-revision",
            "revision",
            "--source-dirty-hash",
            "dirty",
            "--source-root",
            "/tmp/source",
            "--runtime-root",
            "/tmp/runtime",
            "--python",
            "/tmp/python",
            "--wheel",
            "lwm.whl",
            "--import-probe",
            "{}",
        ],
        input="not-a-hash  lwm/__init__.py\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "invalid manifest hash line" in result.stderr


def test_materialize_rebinds_console_scripts_after_staging_swap() -> None:
    script = Path(__file__).parents[1] / "scripts" / "materialize-runtime.sh"
    text = script.read_text(encoding="utf-8")

    assert 'export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"' in text
    assert 'SCRIPT_PATH="${BASH_SOURCE[0]}"' in text
    assert "dirname \"${BASH_SOURCE[0]}\"" not in text
    assert '"$APP_DIR/venv/bin/python" -m pip install --quiet --no-deps --force-reinstall' in text
    assert 'PROBE_JSON="$("$APP_DIR/venv/bin/python" -I -c' in text
    assert 'uv pip install --python "$STAGING_DIR/venv/bin/python" "$WHEEL_FILE"' in text
    assert '"$STAGING_DIR/venv/bin/python" -m pip install --quiet "$WHEEL_FILE"' in text
    assert 'WHEEL_FILE="${LWM_WHEEL_FILE:-}"' in text
    assert 'cp "$AUDITED_WHEEL_ABS" "$WHEEL_TARGET"' in text
    assert 'archived wheel' in text
    assert 'using audited wheel' in text
    assert 'retire-legacy-dream-writer.sh' in text


def test_legacy_dream_writer_is_backed_up_and_fail_closed(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "retire-legacy-dream-writer.sh"
    runtime = tmp_path / "runtime"
    dream = runtime / "bin" / "lwm-dream.sh"
    dream.parent.mkdir(parents=True)
    dream.write_text("#!/bin/sh\necho legacy writer\n", encoding="utf-8")
    dream.chmod(0o755)

    result = subprocess.run(
        ["bash", str(script), str(runtime)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    backups = tuple((runtime / "backups" / "legacy-writers").glob("*.bak"))
    assert len(backups) == 1
    retired = dream.read_text(encoding="utf-8")
    assert "LLM-WORKMEM-RETIRED-DREAM-WRITER" in retired
    assert "hub promote --auto" not in retired

    executed = subprocess.run([str(dream)], text=True, capture_output=True, check=False)
    assert executed.returncode == 2
    assert "retired" in executed.stderr


def test_runtime_staging_installs_declared_wheel_dependencies(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        command = [str(item) for item in command]
        calls.append(command)
        if "wheel" in command:
            output_dir = Path(command[command.index("-w") + 1])
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "lwm-test.whl").write_bytes(b"wheel")
        stdout = "revision\n" if command[:3] == ["git", "-C", str(tmp_path)] else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(harvest.shutil, "which", lambda _: None)
    monkeypatch.setattr(harvest.subprocess, "run", fake_run)
    monkeypatch.setattr(
        harvest,
        "verify_runtime_import",
        lambda _: (True, {"module": "/tmp/site-packages/lwm/__init__.py"}),
    )

    harvest.build_runtime_app_staging(tmp_path, home=tmp_path / "home")

    installs = [call for call in calls if "pip" in call and "install" in call]
    assert len(installs) == 1
    assert installs[0][3:5] == ["install", "--quiet"]
    assert Path(installs[0][-1]).name == "lwm-test.whl"
    assert "--no-deps" not in installs[0]


def test_ownership_preview_does_not_modify_paths(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    (root / "wiki").mkdir(parents=True)
    (root / "adapters").mkdir()
    before = (root / "wiki").is_symlink()

    report = harvest.plan_mutable_ownership_migration(root, home=tmp_path / "home")

    assert report["changes_applied"] is False
    assert (root / "wiki").is_symlink() is before
    assert report["observed"]["wiki"]["source_exists"] is True
    assert "adapters" not in report["observed"]


def test_data_layout_migration_requires_explicit_approval(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "event.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="requires approved=True"):
        harvest.materialize_data_layout(root, home=tmp_path / "home")


def test_approved_data_layout_migration_moves_only_temp_data_owner(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    home = tmp_path / "home"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "event.json").write_text("{}\n", encoding="utf-8")
    (root / "state").mkdir()
    (root / "state" / "health.json").write_text("{\"status\": \"old\"}\n", encoding="utf-8")
    (root / "adapters").mkdir()
    (root / "adapters" / "AGENTS.md").write_text("# adapter\n", encoding="utf-8")
    runtime_state = harvest.runtime_paths(root, home=home).state_root
    runtime_state.parent.mkdir(parents=True, exist_ok=True)
    runtime_state.symlink_to(root / "state", target_is_directory=True)

    runtime_root = harvest.materialize_data_layout(root, home=home, approved=True)

    assert (root / "raw").is_symlink()
    assert (root / "adapters").is_dir()
    assert not (root / "adapters").is_symlink()
    assert (runtime_root / "raw" / "event.json").read_text(encoding="utf-8") == "{}\n"
    assert (runtime_root / "state").is_dir()
    assert not (runtime_root / "state").is_symlink()
    assert (root / "state").is_symlink()
    assert (root / "state").resolve() == (runtime_root / "state").resolve()
    assert (runtime_root / "state" / "health.json").read_text(encoding="utf-8") == "{\"status\": \"old\"}\n"


def test_mutable_ownership_issues_detects_external_symlink(tmp_path: Path) -> None:
    external = tmp_path / "external-state"
    external.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "state").symlink_to(external, target_is_directory=True)

    issues = harvest.mutable_ownership_issues(root)

    assert issues == (f"state: outside data root ({external})",)


def test_mutable_ownership_issues_accepts_migrated_data_root_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "root"
    root.mkdir()
    data_root = harvest.runtime_paths(root).data_root
    data_root.mkdir(parents=True)

    for name in ("wiki", "raw", "automation", "state"):
        (data_root / name).mkdir()
        (root / name).symlink_to(data_root / name, target_is_directory=True)
    for name in ("llms.txt", "llms-full.txt", "llms.json"):
        (data_root / name).touch()
        (root / name).symlink_to(data_root / name)

    assert harvest.mutable_ownership_issues(root) == ()


def test_runtime_import_probe_rejects_icloud_paths(monkeypatch, tmp_path: Path) -> None:
    payload = {
        "module": str(tmp_path / "venv" / "lib" / "site-packages" / "lwm" / "__init__.py"),
        "path": [],
    }
    completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload), stderr="")
    monkeypatch.setattr(harvest.subprocess, "run", lambda *args, **kwargs: completed)

    valid, probe = harvest.verify_runtime_import(tmp_path / "venv" / "bin" / "python")

    assert valid is True
    assert probe["independent"] is True

    payload["module"] = "/Users/ethan/Library/Mobile Documents/source/lwm/__init__.py"
    completed.stdout = json.dumps(payload)
    valid, probe = harvest.verify_runtime_import(tmp_path / "venv" / "bin" / "python")
    assert valid is False
    assert probe["icloud_on_path"]


def _write_test_migration_manifest(
    root: Path, home: Path, output: Path, backup_archive: Path
) -> tuple[Path, str]:
    runtime_base = harvest.runtime_paths(root, home=home).runtime_base
    data_root = runtime_base / "llm-workmem"
    runtime_raw = data_root / "raw"
    runtime_state = data_root / "state"
    runtime_raw.mkdir(parents=True, exist_ok=True)
    runtime_state.parent.mkdir(parents=True, exist_ok=True)
    runtime_state.symlink_to(root / "state", target_is_directory=True)
    entries = []
    for entry_type, path in (
        ("data_entity", runtime_raw),
        ("data_entity", runtime_state),
        ("repository_access_path", root / "raw"),
        ("repository_access_path", root / "state"),
    ):
        entries.append(
            {
                "path": str(path),
                "type": entry_type,
                "exists": path.exists() or path.is_symlink(),
                "current_sha256": tree_hash(path),
                "action": "test",
                "target_owner": str(data_root),
                "backup": str(backup_archive),
                "rollback": "test",
            }
        )
    payload = {
        "schema_version": 1,
        "source_revision": "",
        "source_dirty_hash": "",
        "root": str(root.resolve()),
        "runtime_base": str(runtime_base.resolve()),
        "data_root": str(data_root.resolve()),
        "read_only": True,
        "entry_count": len(entries),
        "entries": entries,
        "preview_artifacts": {
            "backup_archive": {
                "kind": "rollback_archive",
                "path": str(backup_archive),
                "exists": True,
                "sha256": tree_hash(backup_archive),
            }
        },
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return output, f"lwm9b-{digest[:16]}"


def test_manifest_bound_migration_rejects_wrong_approval(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    home = tmp_path / "home"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "event.json").write_text("{}\n", encoding="utf-8")
    (root / "state").mkdir()
    backup = tmp_path / "backup.tar.gz"
    backup.write_bytes(b"backup")
    manifest, approval_id = _write_test_migration_manifest(
        root, home, tmp_path / "manifest.json", backup
    )

    with pytest.raises(MigrationApprovalError, match="approval id mismatch"):
        apply_data_owner_migration(
            manifest,
            approval_id + "-wrong",
            root=root,
            runtime_base=harvest.runtime_paths(root, home=home).runtime_base,
            home=home,
        )


def test_manifest_bound_migration_rejects_data_drift(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    home = tmp_path / "home"
    (root / "raw").mkdir(parents=True)
    event = root / "raw" / "event.json"
    event.write_text("{}\n", encoding="utf-8")
    (root / "state").mkdir()
    backup = tmp_path / "backup.tar.gz"
    backup.write_bytes(b"backup")
    manifest, approval_id = _write_test_migration_manifest(
        root, home, tmp_path / "manifest.json", backup
    )
    event.write_text("{\"changed\": true}\n", encoding="utf-8")

    with pytest.raises(MigrationApprovalError, match="changed since preview"):
        apply_data_owner_migration(
            manifest,
            approval_id,
            root=root,
            runtime_base=harvest.runtime_paths(root, home=home).runtime_base,
            home=home,
        )


def test_manifest_bound_migration_applies_only_to_temp_data_owner(tmp_path: Path) -> None:
    root = tmp_path / "LLM-WorkMem"
    home = tmp_path / "home"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "event.json").write_text("{}\n", encoding="utf-8")
    (root / "state").mkdir()
    (root / "state" / "health.json").write_text("{}\n", encoding="utf-8")
    (root / "adapters").mkdir()
    (root / "adapters" / "AGENTS.md").write_text("# adapter\n", encoding="utf-8")
    backup = tmp_path / "backup.tar.gz"
    backup.write_bytes(b"backup")
    manifest, approval_id = _write_test_migration_manifest(
        root, home, tmp_path / "manifest.json", backup
    )

    report = apply_data_owner_migration(
        manifest,
        approval_id,
        root=root,
        runtime_base=harvest.runtime_paths(root, home=home).runtime_base,
        home=home,
    )

    assert report["applied"] is True
    runtime_root = harvest.runtime_paths(root, home=home).data_root
    assert (runtime_root / "state").is_dir()
    assert not (runtime_root / "state").is_symlink()
    assert (root / "state").is_symlink()
    assert (root / "state").resolve() == (runtime_root / "state").resolve()
    assert (root / "adapters").is_dir()
    assert not (root / "adapters").is_symlink()
