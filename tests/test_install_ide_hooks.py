"""Tests for the IDE Level 1 hook installer.

Scope Lock:
- Solves: hook configs are written for Claude Code, Codex, Kiro, Trae
  under a fake $HOME; re-running is idempotent; unknown tools are
  silently ignored.
- Does not solve: VSCode (no hooks API), Antigravity (no public hooks).
- Acceptance: 5 tests cover each hook writer + dry-run + idempotency.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lwm import hooks_gen
from lwm.cli import app


runner = CliRunner()


def test_claude_code_hook_is_written(tmp_path: Path) -> None:
    install = hooks_gen.install_claude_code(tmp_path)
    body = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert "SessionStart" in body["hooks"]
    assert "Stop" in body["hooks"]


def test_codex_hook_is_written(tmp_path: Path) -> None:
    install = hooks_gen.install_codex(tmp_path)
    text = install.config_path.read_text(encoding="utf-8")
    assert "BEGIN LWM hook" in text
    assert "lwm hub record" in text


def test_kiro_writes_settings_and_steering(tmp_path: Path) -> None:
    install = hooks_gen.install_kiro(tmp_path)
    body = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert body["hooks"]["on"] == "session_start"
    steering = (tmp_path / ".kiro" / "steering" / "lwm.md").read_text(encoding="utf-8")
    assert "LLM-WorkMem inbound hook" in steering


def test_trae_hooks_list(tmp_path: Path) -> None:
    install = hooks_gen.install_trae(tmp_path)
    body = json.loads(install.config_path.read_text(encoding="utf-8"))
    matchers = {entry["matcher"] for entry in body["hooks"]}
    assert "task_start" in matchers and "task_end" in matchers


def test_minimax_hook_is_written(tmp_path: Path) -> None:
    install = hooks_gen.install_minimax(tmp_path)
    text = install.config_path.read_text(encoding="utf-8")
    assert "lwm hub record" in text
    assert "MINIMAX_API_KEY" in text
    assert "lwm-minimax-chat" in text
    import subprocess

    result = subprocess.run(["zsh", "-n", str(install.config_path)], check=False)
    assert result.returncode == 0


def test_install_ide_hooks_is_idempotent(tmp_path: Path) -> None:
    """Re-installing should be a no-op on the second run."""

    first = hooks_gen.install_ide_hooks(tmp_path)
    assert all("updated" in entry.detail for entry in first)
    second = hooks_gen.install_ide_hooks(tmp_path)
    assert all("already current" in entry.detail for entry in second)


def test_install_ide_hooks_ignores_unknown(tmp_path: Path) -> None:
    """Unknown tools are silently skipped (forward-compatible)."""

    installs = hooks_gen.install_ide_hooks(tmp_path, tools=("claude-code", "vscode-fake"))
    names = [entry.tool for entry in installs]
    assert names == ["claude-code"]


def test_install_ide_hooks_helper(tmp_path: Path) -> None:
    installs = hooks_gen.install_ide_hooks(tmp_path)
    tool_names = {entry.tool for entry in installs}
    assert tool_names == {"claude-code", "codex", "kiro", "trae", "minimax"}


def test_install_ide_hooks_cli_defaults_include_minimax(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "hub",
            "install-ide-hooks",
            str(tmp_path),
            "--home",
            str(tmp_path / "home"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "minimax:" in result.output
    assert (tmp_path / "home" / ".minimax" / "lwm-shell.sh").is_file()
