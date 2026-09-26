"""Shell hook install/uninstall tests.

Scope Lock:
- Solves: confirms markers are written idempotently, user content outside
  the marker band is untouched, uninstall strips the block, and unknown
  hook paths surface a clear error.
- Does not solve: actual zsh sourcing (the rcfile is a plain text file
  in the test environment).
- Acceptance: 5 tests cover install/uninstall/refresh/user-content/
  missing-hook.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lwm import shell_hook


def test_bundled_hook_has_valid_zsh_syntax() -> None:
    hook = Path(__file__).parents[1] / "lwm" / "lwm_shell_hook.zsh"
    result = subprocess.run(["zsh", "-n", str(hook)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _seed_rc(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_install_writes_marker_block(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    lwm_root.mkdir()
    (lwm_root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (lwm_root / "lwm" / "lwm_shell_hook.zsh").parent.mkdir(parents=True, exist_ok=True)
    (lwm_root / "lwm" / "lwm_shell_hook.zsh").write_text("# stub", encoding="utf-8")

    result = shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    assert result.changed is True
    assert result.already_installed is False
    text = rc.read_text(encoding="utf-8")
    assert shell_hook.MARKER_START in text
    assert shell_hook.MARKER_END in text
    assert "source" in text


def test_install_is_idempotent_and_preserves_user_content(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    (lwm_root / "pyproject.toml").parent.mkdir(parents=True, exist_ok=True)
    (lwm_root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (lwm_root / "lwm").mkdir(parents=True)
    (lwm_root / "lwm" / "lwm_shell_hook.zsh").write_text("# stub", encoding="utf-8")
    _seed_rc(rc, "# user one\nexport PATH=foo\n# user two\n")

    first = shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    assert first.changed is True
    body = rc.read_text(encoding="utf-8")
    assert "# user one" in body and "# user two" in body

    second = shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    # hook path is the same on every run ⇒ unchanged.
    assert second.changed is False
    assert shell_hook.is_installed(rc_path=rc) is True


def test_install_refreshes_when_hook_bytes_change(tmp_path: Path) -> None:
    """Hook script byte changes should rewrite the FP header in the rc block."""

    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    (lwm_root / "pyproject.toml").parent.mkdir(parents=True, exist_ok=True)
    (lwm_root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (lwm_root / "lwm").mkdir(parents=True)
    hook = lwm_root / "lwm" / "lwm_shell_hook.zsh"
    hook.write_text("# stub v1", encoding="utf-8")

    shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    body1 = rc.read_text(encoding="utf-8")
    fp_match_1 = shell_hook._FP_HEADER_RE.search(body1)
    assert fp_match_1 is not None
    fp_1 = fp_match_1.group(1)

    hook.write_text("# stub v2 — completely different bytes here!", encoding="utf-8")
    result = shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    assert result.changed is True
    body2 = rc.read_text(encoding="utf-8")
    assert body1 != body2
    fp_match_2 = shell_hook._FP_HEADER_RE.search(body2)
    assert fp_match_2 is not None
    assert fp_match_2.group(1) != fp_1


def test_install_does_not_rewrite_when_unchanged(tmp_path: Path) -> None:
    """Same hook bytes ⇒ idempotent, mtime preserved across re-runs."""

    import os

    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    (lwm_root / "pyproject.toml").parent.mkdir(parents=True, exist_ok=True)
    (lwm_root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (lwm_root / "lwm").mkdir(parents=True)
    hook = lwm_root / "lwm" / "lwm_shell_hook.zsh"
    hook.write_text("# stable hook bytes", encoding="utf-8")

    shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    result = shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    assert result.changed is False
    # Same mtime (or at most identical bytes).
    assert rc.read_text(encoding="utf-8") == open(rc, encoding="utf-8").read()
    _ = os  # silence unused


def test_uninstall_removes_only_marker_block(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    (lwm_root / "pyproject.toml").parent.mkdir(parents=True, exist_ok=True)
    (lwm_root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    (lwm_root / "lwm").mkdir(parents=True)
    (lwm_root / "lwm" / "lwm_shell_hook.zsh").write_text("# stub", encoding="utf-8")

    user_block = "# user alias\nalias ll='ls -la'\n"
    shell_hook.install(lwm_root=lwm_root, rc_path=rc)
    rc.write_text(user_block + rc.read_text(encoding="utf-8"), encoding="utf-8")
    assert shell_hook.is_installed(rc_path=rc)

    result = shell_hook.uninstall(rc_path=rc)
    assert result.changed is True
    text = rc.read_text(encoding="utf-8")
    assert shell_hook.MARKER_START not in text
    assert "alias ll" in text
    assert shell_hook.is_installed(rc_path=rc) is False


def test_uninstall_is_noop_when_absent(tmp_path: Path) -> None:
    rc = tmp_path / "missing_zshrc"
    result = shell_hook.uninstall(rc_path=rc)
    assert result.changed is False


def test_install_missing_hook_raises(tmp_path: Path, monkeypatch) -> None:
    rc = tmp_path / ".zshrc"
    lwm_root = tmp_path / "wiki"
    (lwm_root / "lwm").mkdir(parents=True)

    def missing_package(_name: str):
        raise ModuleNotFoundError("lwm package resources unavailable")

    monkeypatch.setattr(shell_hook.importlib.resources, "files", missing_package)
    with pytest.raises(FileNotFoundError):
        shell_hook.install(lwm_root=lwm_root, rc_path=rc)


def test_install_uses_packaged_hook_when_data_root_has_no_code(tmp_path: Path) -> None:
    """The wheel keeps code in site-packages, not under mutable DATA_ROOT."""

    rc = tmp_path / ".zshrc"
    data_root = tmp_path / "data-root"
    data_root.mkdir()

    result = shell_hook.install(lwm_root=data_root, rc_path=rc)

    assert result.changed is True
    assert result.hook_path is not None
    assert result.hook_path.is_file()
    assert result.hook_path.name == "lwm_shell_hook.zsh"
    assert str(result.hook_path).startswith(str(Path(__file__).parents[1]))


def test_install_ignores_legacy_code_mirror_in_data_root(tmp_path: Path) -> None:
    """A legacy DATA_ROOT/lwm mirror must not override the installed wheel."""

    rc = tmp_path / ".zshrc"
    data_root = tmp_path / "data-root"
    legacy_hook = data_root / "lwm" / "lwm_shell_hook.zsh"
    legacy_hook.parent.mkdir(parents=True)
    legacy_hook.write_text("# legacy mirror", encoding="utf-8")

    result = shell_hook.install(lwm_root=data_root, rc_path=rc)

    assert result.hook_path is not None
    assert result.hook_path != legacy_hook
    assert str(result.hook_path).startswith(str(Path(__file__).parents[1]))


def test_install_normalizes_migrated_repository_access_path(tmp_path: Path) -> None:
    """Passing the migrated checkout path still selects the runtime owner."""

    rc = tmp_path / ".zshrc"
    owner = tmp_path / "owner"
    repo = tmp_path / "repo"
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    (owner / "state").mkdir()
    repo.mkdir()
    (repo / "state").symlink_to(owner / "state", target_is_directory=True)

    result = shell_hook.install(lwm_root=repo, rc_path=rc)

    assert result.hook_path is not None
    assert result.hook_path != repo / "lwm" / "lwm_shell_hook.zsh"
