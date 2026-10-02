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
import json
import os
import subprocess

from typer.testing import CliRunner

from lwm.adapters import _bridge_context_command, write_global_adapters
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
    assert not (root / "adapters").exists()


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
        fake_home / ".cursor" / "hooks.json",
        fake_home / ".gemini" / "GEMINI.md",
        fake_home / "Library" / "Application Support" / "Code" / "User" / "prompts" / "llm-workmem.instructions.md",
        fake_home / ".config" / "opencode" / "AGENTS.md",
        fake_home / ".config" / "lwm" / "context.json",
        fake_home / ".local" / "bin" / "lwm",
    ]
    for path in expected:
        assert path.is_file(), f"missing {path}"
    vscode = (fake_home / "Library" / "Application Support" / "Code" / "User" / "prompts" / "llm-workmem.instructions.md").read_text(encoding="utf-8")
    assert 'applyTo: "**"' in vscode
    assert "lwm hub bridge" in vscode
    claude = (fake_home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "shared personal behavior contract" in claude
    assert "Project memory, handoffs, Recall and review candidates are auxiliary evidence" in claude
    assert "Do not run a second startup fetch" in claude
    assert "When the task depends on historical decisions" in claude
    assert "Skip unchanged-state write-back" in claude
    assert "**On session start**" not in claude
    for path, tool in {
        fake_home / ".codex" / "AGENTS.md": "codex",
        fake_home / ".claude" / "CLAUDE.md": "claude-code",
        fake_home / ".config" / "opencode" / "AGENTS.md": "opencode",
        fake_home / ".agents" / "AGENTS.md": "antigravity",
        fake_home / ".minimax" / "agents" / "coder" / "agent.md": "minimax",
    }.items():
        text = path.read_text(encoding="utf-8")
        assert f"bridge-stop --tool {tool}" in text
        assert "<your-tool-name>" not in text
    launcher = (fake_home / ".local" / "bin" / "lwm").read_text(encoding="utf-8")
    assert 'exec "${python_bin}" -I -m lwm.cli "$@"' in launcher
    assert "-m lwm.cli" in launcher
    assert str(fake_home / "Library" / "Application Support" / "llm-workmem-runtime" / "app" / "venv" / "bin" / "python") in launcher
    assert str(root / "automation" / "app" / "venv" / "bin" / "python") not in launcher
    minimax_mcp = json.loads(
        (fake_home / ".minimax" / "mcp" / "mcp.json").read_text(encoding="utf-8")
    )
    minimax_server = minimax_mcp["mcpServers"]["llm-workmem"]
    assert minimax_server["env"]["LWM_MCP_TOOL"] == "minimax"
    assert minimax_server["env"]["LWM_MCP_INTEGRATION"] == "minimax-mcp"
    gemini_settings = json.loads(
        (fake_home / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    gemini_server = gemini_settings["mcpServers"]["llm-workmem"]
    assert gemini_server["env"]["LWM_MCP_TOOL"] == "gemini-cli"
    assert gemini_server["env"]["LWM_MCP_INTEGRATION"] == "gemini-cli-mcp"
    cursor_hooks = json.loads(
        (fake_home / ".cursor" / "hooks.json").read_text(encoding="utf-8")
    )
    assert cursor_hooks["version"] == 1
    assert set(cursor_hooks["hooks"]) >= {"sessionStart", "sessionEnd"}
    assert all(
        "adapters.hooks.cursor_native" in item["command"]
        for event in ("sessionStart", "sessionEnd")
        for item in cursor_hooks["hooks"][event]
    )


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


def test_install_global_normalizes_migrated_repository_access_path(tmp_path: Path) -> None:
    owner = tmp_path / "owner"
    repo = tmp_path / "repo"
    fake_home = tmp_path / "home"
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    (owner / "state").mkdir()
    repo.mkdir()
    (repo / "state").symlink_to(owner / "state", target_is_directory=True)

    result = runner.invoke(
        app, ["install-global", str(repo), "--home", str(fake_home)]
    )

    assert result.exit_code == 0, result.output
    context = json.loads(
        (fake_home / ".config" / "lwm" / "context.json").read_text()
    )
    assert context["wiki_root"] == str(owner.resolve())


def test_install_global_normalizes_legacy_kiro_context_command(tmp_path: Path) -> None:
    root_path = tmp_path / "runtime" / "llm-workmem"
    root_path.mkdir(parents=True)
    root = _seed_root(root_path)
    fake_home = tmp_path / "home"
    kiro = fake_home / ".kiro" / "steering" / "llm-workmem.md"
    kiro.parent.mkdir(parents=True)
    legacy = "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
    kiro.write_text(
        f"# User rules\n\nlwm hub context --tool kiro \"{legacy}\"\n\n# Keep this\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["install-global", str(root), "--home", str(fake_home)]
    )

    assert result.exit_code == 0, result.output
    text = kiro.read_text(encoding="utf-8")
    assert f'lwm hub context --tool kiro "{root.resolve()}"' in text
    assert legacy not in text
    assert "# User rules" in text
    assert "# Keep this" in text


def test_install_global_merges_antigravity_hooks_without_overwriting_user_hooks(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    root = _seed_root(runtime)
    fake_home = tmp_path / "home"
    hooks_path = fake_home / ".gemini" / "config" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(
        json.dumps(
            {
                "user-lint": {
                    "PostToolUse": [{"matcher": "run_command", "hooks": [{"command": "./lint.sh"}]}]
                },
                "settings": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    first = runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    assert first.exit_code == 0, first.output
    payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert payload["settings"] == {"enabled": False}
    assert payload["user-lint"]["PostToolUse"][0]["hooks"][0]["command"] == "./lint.sh"
    assert set(payload["llm-workmem"]) == {"PreInvocation", "Stop"}
    for handlers in payload["llm-workmem"].values():
        command = handlers[0]["command"]
        assert "adapters.hooks.antigravity_native" in command
        assert str(root.resolve()) in command
        assert "Mobile Documents" not in command

    body_1 = hooks_path.read_text(encoding="utf-8")
    second = runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    assert second.exit_code == 0, second.output
    assert hooks_path.read_text(encoding="utf-8") == body_1


def test_install_global_merges_codex_and_gemini_hooks_without_overwriting_user_settings(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    root = _seed_root(runtime)
    fake_home = tmp_path / "home"
    codex_path = fake_home / ".codex" / "hooks.json"
    codex_path.parent.mkdir(parents=True)
    codex_path.write_text(
        json.dumps(
            {
                "user-hook": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "./user-hook.sh"}]}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    gemini_path = fake_home / ".gemini" / "settings.json"
    gemini_path.parent.mkdir(parents=True)
    gemini_path.write_text(
        json.dumps({"mcpServers": {"keep": {"command": "keep"}}}),
        encoding="utf-8",
    )

    first = runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    assert first.exit_code == 0, first.output

    codex = json.loads(codex_path.read_text(encoding="utf-8"))
    assert codex["user-hook"]["UserPromptSubmit"][0]["hooks"][0]["command"] == "./user-hook.sh"
    assert set(codex["hooks"]) == {"SessionStart", "SessionEnd"}
    for groups in codex["hooks"].values():
        assert any("adapters.hooks.codex_native" in item["command"] for group in groups for item in group["hooks"])

    gemini = json.loads(gemini_path.read_text(encoding="utf-8"))
    assert gemini["mcpServers"]["keep"] == {"command": "keep"}
    assert gemini["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_TOOL"] == "gemini-cli"
    assert gemini["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_INTEGRATION"] == "gemini-cli-mcp"
    assert set(gemini["hooks"]) == {"SessionStart", "SessionEnd"}
    for groups in gemini["hooks"].values():
        assert any("adapters.hooks.gemini_cli_native" in item["command"] for group in groups for item in group["hooks"])

    body_1 = codex_path.read_text(encoding="utf-8") + gemini_path.read_text(encoding="utf-8")
    second = runner.invoke(app, ["install-global", str(root), "--home", str(fake_home)])
    assert second.exit_code == 0, second.output
    body_2 = codex_path.read_text(encoding="utf-8") + gemini_path.read_text(encoding="utf-8")
    assert body_2 == body_1


def test_generated_commands_quote_iCloud_style_spaces(tmp_path: Path) -> None:
    root = tmp_path / "work memory"
    root.mkdir()
    root = _seed_root(root)
    write_global_adapters(root)
    text = (root / "adapters" / "AGENTS.md").read_text(encoding="utf-8")
    quoted_root = f"'{root.resolve()}'"
    assert f"hub bridge --output markdown --root {quoted_root}" in text
    assert f"--root {quoted_root}" in text


def test_generated_context_command_escapes_quotes_in_pwd(tmp_path: Path) -> None:
    root_path = tmp_path / 'work "memory'
    root_path.mkdir()
    root = _seed_root(root_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_lwm = fake_bin / "lwm"
    fake_lwm.write_text("#!/bin/sh\ncat\n", encoding="utf-8")
    fake_lwm.chmod(0o755)
    command = _bridge_context_command(root, tool="codex")
    project = tmp_path / 'project "quoted"'
    project.mkdir()
    result = subprocess.run(
        ["zsh", "-c", command],
        cwd=project,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "phase": "context",
        "tool": "codex",
        "project_path": str(project),
    }
