"""Contract tests for the VS Code-compatible LLM-WorkMem companion."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from lwm.ide_companion import host_command, package_companion
from lwm.tool_registry import default_registry
from typer.testing import CliRunner
from lwm.cli import app


ROOT = Path(__file__).resolve().parents[1]
COMPANION = ROOT / "integrations" / "ide-companion"
runner = CliRunner()


def test_companion_declares_activation_commands_and_tool_overrides() -> None:
    package = json.loads((COMPANION / "package.json").read_text(encoding="utf-8"))

    assert package["main"] == "extension.js"
    assert "onStartupFinished" in package["activationEvents"]
    commands = {item["command"] for item in package["contributes"]["commands"]}
    assert commands == {
        "llm-workmem.startSession",
        "llm-workmem.stopSession",
        "llm-workmem.deliverContext",
    }
    properties = package["contributes"]["configuration"]["properties"]
    assert properties["llmWorkmem.toolId"]["default"] == "vscode"
    assert properties["llmWorkmem.integration"]["default"] == "vscode-extension"
    assert "kiro" in properties["llmWorkmem.toolId"]["enum"]
    assert "kiro-extension" in properties["llmWorkmem.integration"]["enum"]


def test_companion_uses_host_bound_bridge_without_persisting_host_text() -> None:
    source = (COMPANION / "extension.js").read_text(encoding="utf-8")

    assert '["hub", "bridge"' in source
    assert '"ide-extension"' in source
    assert "native-instruction-file-ready" in source
    assert "context_sha256" in source
    assert "host_proof" in source
    assert 'LWM_HOST_BRIDGE: "1"' in source
    assert "workspaceFolders" in source
    assert "prompt" not in source.lower()
    assert "transcript" not in source.lower()
    assert "completion" not in source.lower()


def test_vscode_family_registry_rows_allow_only_the_companion_proof() -> None:
    registry = default_registry()

    for tool, integration in (
        ("vscode", "vscode-extension"),
        ("cursor", "cursor-extension"),
        ("trae", "trae-extension"),
        ("kiro", "kiro-extension"),
        ):
            definition = registry.resolve(tool)
            assert definition is not None
            expected = (
                ("cursor-extension", "cursor-hook")
                if tool == "cursor"
                else (integration,)
            )
            assert definition.proof_integrations == expected


def test_wheel_build_includes_the_companion_as_a_runtime_resource() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"integrations/ide-companion" = "lwm/resources/ide-companion"' in pyproject


def test_package_companion_sets_the_canonical_identity_for_each_host(tmp_path: Path) -> None:
    for tool, integration in (
        ("vscode", "vscode-extension"),
        ("cursor", "cursor-extension"),
        ("trae", "trae-extension"),
        ("kiro", "kiro-extension"),
    ):
        output = tmp_path / f"{tool}.vsix"
        package_companion(output, tool=tool)
        with ZipFile(output) as archive:
            package = json.loads(archive.read("extension/package.json"))
        properties = package["contributes"]["configuration"]["properties"]
        assert properties["llmWorkmem.toolId"]["default"] == tool
        assert properties["llmWorkmem.integration"]["default"] == integration


def test_host_command_is_read_only_resolution_and_unknown_hosts_fail() -> None:
    assert host_command("not-a-real-tool", path_lookup={}) is None
    assert host_command("vscode", path_lookup={"vscode": "/tmp/code"}) == ("/tmp/code",)
    assert host_command("kiro", path_lookup={"kiro": "/tmp/kiro"}) == ("/tmp/kiro",)


def test_cli_companion_dry_run_does_not_install(monkeypatch) -> None:
    monkeypatch.setattr(
        "lwm.ide_companion.host_command",
        lambda tool, path_lookup=None: ("/tmp/fake-host",),
    )

    result = runner.invoke(
        app,
        ["hub", "install-ide-companion", "--tool", "trae", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "no files were written" in result.stdout
