"""Tests for the IDE Level 1 hook installer.

Scope Lock:
- Solves: Claude Code/OpenCode/Codex/Gemini native configs are written only
  where the contract is supported; Kiro and Trae report their observer
  fallback without inventing native hook files; re-running is idempotent;
  unknown tools are silently ignored.
- Does not solve: real host firing for the VS Code-compatible companion,
  Cursor/Trae companions, or Antigravity; package/config reachability is not
  bidirectional proof.
- Acceptance: 5 tests cover each hook writer + dry-run + idempotency.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lwm import hooks_gen
from lwm.cli import app
from lwm.tool_registry import default_registry


runner = CliRunner()


def test_claude_code_hook_is_written(tmp_path: Path) -> None:
    install = hooks_gen.install_claude_code(tmp_path)
    body = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert "SessionStart" in body["hooks"]
    assert "Stop" in body["hooks"]


def test_claude_hook_uses_the_requested_home(tmp_path: Path) -> None:
    fake_home = tmp_path / "fake home"
    install = hooks_gen.install_claude_code(fake_home, root=tmp_path / "workmem")
    body = json.loads(install.config_path.read_text(encoding="utf-8"))
    command = body["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert str(fake_home / "Library" / "Application Support" / "llm-workmem-runtime") in command
    assert " -I -m " in command
    assert str(Path.home() / "Library" / "Application Support" / "llm-workmem-runtime") not in command


def test_codex_writes_native_hook_without_trust_mutation(tmp_path: Path) -> None:
    install = hooks_gen.install_codex(tmp_path, root=tmp_path / "workmem")
    assert install.config_path == tmp_path / ".codex" / "hooks.json"
    payload = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert set(payload["hooks"]) == {"SessionStart", "SessionEnd"}
    assert all(" -I -m " in groups[0]["hooks"][0]["command"] for groups in payload["hooks"].values())
    assert "native hooks" in install.detail
    assert "user approval" in install.detail


def test_cursor_writes_native_session_hooks(tmp_path: Path) -> None:
    install = hooks_gen.install_cursor(tmp_path, root=tmp_path / "workmem")
    payload = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert set(payload["hooks"]) >= {"sessionStart", "sessionEnd"}
    assert all(
        "adapters.hooks.cursor_native" in item["command"]
        for event in ("sessionStart", "sessionEnd")
        for item in payload["hooks"][event]
    )
    assert "native hooks" in install.detail


def test_codex_replaces_only_legacy_generated_stop_hook(tmp_path: Path) -> None:
    path = tmp_path / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python -m adapters.hooks.codex_native --phase Stop",
                                }
                            ],
                        },
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "./user-owned-stop-hook",
                                }
                            ],
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    hooks_gen.install_codex(tmp_path, root=tmp_path / "workmem")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload["hooks"]) == {"SessionStart", "SessionEnd", "Stop"}
    assert any(
        item["command"] == "./user-owned-stop-hook"
        for group in payload["hooks"]["Stop"]
        for item in group["hooks"]
    )
    assert all(
        "--phase Stop" not in item["command"]
        for group in payload["hooks"]["Stop"]
        for item in group["hooks"]
    )


def test_gemini_cli_writes_native_hooks(tmp_path: Path) -> None:
    install = hooks_gen.install_gemini_cli(tmp_path, root=tmp_path / "workmem")
    payload = json.loads(install.config_path.read_text(encoding="utf-8"))
    assert set(payload["hooks"]) == {"SessionStart", "SessionEnd"}
    assert all(
        "matcher" not in group
        for groups in payload["hooks"].values()
        for group in groups
        if any("gemini_cli_native" in item["command"] for item in group["hooks"])
    )
    assert all(" -I -m " in groups[0]["hooks"][0]["command"] for groups in payload["hooks"].values())
    assert "mcp.lwm_server" in payload["mcpServers"]["llm-workmem"]["args"]
    assert payload["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_TOOL"] == "gemini-cli"
    assert payload["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_INTEGRATION"] == "gemini-cli-mcp"
    assert "native hooks" in install.detail


def test_gemini_mcp_install_preserves_existing_servers(tmp_path: Path) -> None:
    settings = tmp_path / ".gemini" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        json.dumps({"mcpServers": {"codegraph": {"command": "keep-me"}}}),
        encoding="utf-8",
    )

    hooks_gen.install_gemini_cli(tmp_path, root=tmp_path / "workmem")
    payload = json.loads(settings.read_text(encoding="utf-8"))

    assert payload["mcpServers"]["codegraph"] == {"command": "keep-me"}
    assert "llm-workmem" in payload["mcpServers"]


def test_antigravity_writes_native_hooks(tmp_path: Path) -> None:
    install = hooks_gen.install_antigravity(tmp_path, root=tmp_path / "workmem")
    payload = json.loads(install.config_path.read_text(encoding="utf-8"))

    assert install.config_path == tmp_path / ".gemini" / "config" / "hooks.json"
    assert set(payload["llm-workmem"]) == {"PreInvocation", "Stop"}
    for handlers in payload["llm-workmem"].values():
        command = handlers[0]["command"]
        assert "adapters.hooks.antigravity_native" in command
        assert " -I -m " in command
        assert str((tmp_path / "workmem").resolve()) in command
    assert "native hooks" in install.detail


def test_kiro_writes_canonical_steering(tmp_path: Path) -> None:
    install = hooks_gen.install_kiro(tmp_path)
    assert install.config_path == tmp_path / ".kiro" / "steering" / "llm-workmem.md"
    assert install.config_path.is_file()
    assert "preserved settings" in install.detail
    steering = install.config_path.read_text(encoding="utf-8")
    assert "LLM-WorkMem inbound hook" in steering
    assert "no verified public session-lifecycle hook" in steering


def test_kiro_installer_path_matches_registry_discovery(tmp_path: Path) -> None:
    hooks_gen.install_kiro(tmp_path)

    discovered = default_registry().discover(tmp_path)

    assert discovered["kiro"] is True


def test_trae_does_not_write_unverified_hook_json(tmp_path: Path) -> None:
    install = hooks_gen.install_trae(tmp_path)
    assert install.config_path == tmp_path / ".traerules"
    assert not (tmp_path / ".trae" / "hooks.json").exists()
    assert "no verified native hook" in install.detail


def test_minimax_hook_is_written(tmp_path: Path) -> None:
    workmem_root = tmp_path / "workmem"
    install = hooks_gen.install_minimax(tmp_path, root=workmem_root)
    text = install.config_path.read_text(encoding="utf-8")
    assert "lwm hub record" in text
    assert "MINIMAX_API_KEY" in text
    assert "lwm-minimax-chat" in text
    assert "Mobile Documents" not in text
    assert "llm-workmem-runtime/llm-workmem" in text
    import subprocess

    result = subprocess.run(["zsh", "-n", str(install.config_path)], check=False)
    assert result.returncode == 0

    mcp_path = tmp_path / ".minimax" / "mcp" / "mcp.json"
    mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    assert mcp["mcpServers"]["llm-workmem"]["args"][-1] == str(workmem_root)
    assert "mcp.lwm_server" in mcp["mcpServers"]["llm-workmem"]["args"]
    assert mcp["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_TOOL"] == "minimax"
    assert mcp["mcpServers"]["llm-workmem"]["env"]["LWM_MCP_INTEGRATION"] == "minimax-mcp"


def test_minimax_mcp_install_preserves_existing_servers(tmp_path: Path) -> None:
    mcp_path = tmp_path / ".minimax" / "mcp" / "mcp.json"
    mcp_path.parent.mkdir(parents=True)
    mcp_path.write_text(
        json.dumps(
            {
                "mcpServers": {"matrix": {"command": "keep-me"}},
                "userSetting": "preserve-me",
            }
        ),
        encoding="utf-8",
    )

    hooks_gen.install_minimax(tmp_path, root=tmp_path / "workmem")
    payload = json.loads(mcp_path.read_text(encoding="utf-8"))

    assert payload["mcpServers"]["matrix"] == {"command": "keep-me"}
    assert payload["userSetting"] == "preserve-me"
    assert "llm-workmem" in payload["mcpServers"]


def test_opencode_plugin_handles_start_and_end(tmp_path: Path) -> None:
    install = hooks_gen.install_opencode(tmp_path, root=tmp_path / "workmem")
    text = install.config_path.read_text(encoding="utf-8")
    assert "session.created" in text
    assert "session.idle" in text
    assert "session.error" in text
    assert 'event: async ({ event })' in text
    assert 'event.type === "session.idle" || event.type === "session.error"' in text
    assert "properties?.sessionID" in text
    assert "properties?.info?.id" in text
    assert "experimental.session.compacting" in text
    assert "output.context.push(context)" in text
    assert "hub bridge" in text
    assert 'phase: "context"' in text
    assert 'source: "native-hook"' in text
    assert 'integration: "opencode-plugin"' in text
    assert 'host_proof:' in text
    assert "process.env.LWM_ROOT" in text
    assert "process.env.LWM_BIN" in text
    assert "Mobile Documents" not in text
    config = json.loads((tmp_path / ".config" / "opencode" / "opencode.json").read_text())
    assert str(install.config_path) in config["plugin"]


def test_opencode_install_preserves_registered_plugin(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "opencode"
    config_dir.mkdir(parents=True)
    target = tmp_path / "custom" / "lwm-workmem.ts"
    target.parent.mkdir()
    target.write_text("custom plugin with context and summary", encoding="utf-8")
    (config_dir / "opencode.json").write_text(
        json.dumps({"plugin": [str(target)]}), encoding="utf-8"
    )

    install = hooks_gen.install_opencode(tmp_path, root=tmp_path / "workmem")

    assert install.config_path == target
    assert target.read_text(encoding="utf-8") == "custom plugin with context and summary"


def test_opencode_install_migrates_known_checkout_plugin_to_canonical_path(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "opencode"
    config_dir.mkdir(parents=True)
    checkout_plugin = tmp_path / "checkout" / "integrations" / "opencode" / "lwm-workmem.ts"
    checkout_plugin.parent.mkdir(parents=True)
    checkout_plugin.write_text(
        "export const LlmWorkmemPlugin = async () => {}\n// hub bridge\n",
        encoding="utf-8",
    )
    other_plugin = "opencode-vibeguard"
    (config_dir / "opencode.json").write_text(
        json.dumps({"plugin": [str(checkout_plugin), other_plugin]}),
        encoding="utf-8",
    )

    install = hooks_gen.install_opencode(tmp_path, root=tmp_path / "workmem")
    config = json.loads((config_dir / "opencode.json").read_text(encoding="utf-8"))
    canonical = tmp_path / ".config" / "opencode" / "plugins" / "llm-workmem.ts"

    assert install.config_path == canonical
    assert canonical.is_file()
    assert str(canonical) in config["plugin"]
    assert str(checkout_plugin) not in config["plugin"]
    assert other_plugin in config["plugin"]
    assert "process.env.LWM_ROOT" in canonical.read_text(encoding="utf-8")


def test_opencode_install_migrates_legacy_reference_path(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "opencode"
    config_dir.mkdir(parents=True)
    legacy_root = tmp_path / "checkout" / "LLM-WorkMem"
    runtime_root = tmp_path / "runtime" / "llm-workmem"
    config_path = config_dir / "opencode.json"
    config_path.write_text(
        json.dumps(
            {
                "references": {
                    "llm-workmem": {
                        "path": str(legacy_root),
                        "description": "keep this description",
                    },
                    "other-reference": {"path": str(tmp_path / "other")},
                },
                "plugin": ["opencode-vibeguard"],
            }
        ),
        encoding="utf-8",
    )

    hooks_gen.install_opencode(tmp_path, root=runtime_root)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["references"]["llm-workmem"]["path"] == str(runtime_root)
    assert config["references"]["llm-workmem"]["description"] == "keep this description"
    assert config["references"]["other-reference"]["path"] == str(tmp_path / "other")


def test_install_ide_hooks_is_idempotent(tmp_path: Path) -> None:
    """Re-installing should be a no-op on the second run."""

    first = hooks_gen.install_ide_hooks(tmp_path)
    assert any("updated" in entry.detail for entry in first)
    second = hooks_gen.install_ide_hooks(tmp_path)
    assert all(
        "already current" in entry.detail
        or "preserved settings" in entry.detail
        or "no verified native hook" in entry.detail
        for entry in second
    )


def test_install_ide_hooks_ignores_unknown(tmp_path: Path) -> None:
    """Unknown tools are silently skipped (forward-compatible)."""

    installs = hooks_gen.install_ide_hooks(tmp_path, tools=("claude-code", "vscode-fake"))
    names = [entry.tool for entry in installs]
    assert names == ["claude-code"]


def test_install_ide_hooks_helper(tmp_path: Path) -> None:
    installs = hooks_gen.install_ide_hooks(tmp_path)
    tool_names = {entry.tool for entry in installs}
    assert tool_names == {
        "claude-code",
        "codex",
        "cursor",
        "kiro",
        "opencode",
        "trae",
        "minimax",
        "gemini-cli",
        "antigravity",
    }


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
    assert "gemini-cli:" in result.output
    assert "antigravity:" in result.output
    assert (tmp_path / "home" / ".minimax" / "lwm-shell.sh").is_file()
    assert (tmp_path / "home" / ".gemini" / "settings.json").is_file()
    assert (tmp_path / "home" / ".gemini" / "config" / "hooks.json").is_file()


def test_legacy_claude_installer_has_no_machine_path() -> None:
    script = (Path(__file__).parents[1] / "adapters" / "hooks" / "install-claude-hook.py").read_text(encoding="utf-8")
    assert "Mobile Documents" not in script
    assert "--root" in script
    assert " -I -m" in script


def test_ide_hooks_normalize_migrated_repository_access_path(tmp_path: Path) -> None:
    owner = tmp_path / "owner"
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    (owner / "state").mkdir()
    repo.mkdir()
    (repo / "state").symlink_to(owner / "state", target_is_directory=True)

    installs = hooks_gen.install_ide_hooks(
        home, root=repo, tools=("claude-code",)
    )
    body = json.loads((home / ".claude" / "settings.json").read_text())
    command = body["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    assert installs
    assert str(owner) in command
    assert str(repo) not in command
