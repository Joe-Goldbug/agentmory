"""``lwm install-global`` end-to-end coverage.

Scope Lock:
- Solves: dry-run is a no-op, real install under a fake $HOME writes every
  adapter file once and on re-run idempotently refreshes them.
- Does not solve: native IDE plugin invocation.
- Acceptance: install-global exits 0, writes 11 files, second invocation
  reports no drift and does not duplicate user content.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lwm.cli import app


runner = CliRunner()


def _seed_root(tmp_path: Path) -> Path:
    """Create the bare minimum lwm tree so adapters can be installed."""

    (tmp_path / "llms.txt").write_text("# placeholder\n", encoding="utf-8")
    (tmp_path / "wiki" / "purpose.md").parent.mkdir(parents=True)
    (tmp_path / "wiki" / "overview.md").write_text("# overview\n", encoding="utf-8")
    (tmp_path / "llms-full.txt").write_text("# full\n", encoding="utf-8")
    (tmp_path / "llms.json").write_text("{}\n", encoding="utf-8")
    return tmp_path


def test_install_global_dry_run(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    fake_home = tmp_path / "home"
    result = runner.invoke(
        app,
        ["install-global", str(root), "--home", str(fake_home), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert not (fake_home / ".codex" / "AGENTS.md").exists()


def test_install_global_writes_all_adapters(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    fake_home = tmp_path / "home"
    result = runner.invoke(
        app,
        ["install-global", str(root), "--home", str(fake_home)],
    )
    assert result.exit_code == 0, result.output

    expected = [
        fake_home / ".codex" / "AGENTS.md",
        fake_home / "CLAUDE.md",
        fake_home / ".traerules",
        fake_home / ".kiro" / "steering" / "llm-workmem.md",
        fake_home / ".agents" / "AGENTS.md",
        fake_home / ".agents" / "GLOBAL.md",
        fake_home / ".cursor" / "rules" / "llm-workmem.mdc",
        fake_home / ".cursor" / ".cursorrules",
        fake_home / ".gemini" / "GEMINI.md",
        fake_home / ".copilot" / "instructions" / "llm-workmem.instructions.md",
        fake_home / ".config" / "opencode" / "AGENTS.md",
        fake_home / ".config" / "lwm" / "context.json",
    ]
    for path in expected:
        assert path.is_file(), f"missing {path}"
    vscode = (fake_home / ".copilot" / "instructions" / "llm-workmem.instructions.md").read_text(encoding="utf-8")
    assert 'applyTo: "**"' in vscode
    assert "lwm hub context" in vscode


def test_install_global_is_idempotent(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    fake_home = tmp_path / "home"
    runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    body_1 = (fake_home / "CLAUDE.md").read_text(encoding="utf-8")
    runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    body_2 = (fake_home / "CLAUDE.md").read_text(encoding="utf-8")
    # Block markers preserve outer user content; the inner block should
    # be byte-stable across re-runs.
    assert body_1 == body_2


def test_install_global_preserves_user_content(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    fake_home = tmp_path / "home"
    claude_md = fake_home / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    claude_md.write_text("# Ethan private rules\nALWAYS greet.\n", encoding="utf-8")
    runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    text = claude_md.read_text(encoding="utf-8")
    assert "Ethan private rules" in text
    assert "LLM-WIKI:START" in text
