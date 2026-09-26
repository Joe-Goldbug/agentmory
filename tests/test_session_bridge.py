"""Shared session bridge contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lwm import capabilities
from lwm.cli import app
from lwm.session_bridge import dispatch, simulate_registry_contract
from lwm.tool_registry import default_registry


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    return project


def test_bridge_context_start_stop_share_canonical_contract(tmp_path: Path) -> None:
    project = _project(tmp_path)

    context = dispatch(
        tmp_path,
        {
            "phase": "context",
            "tool": "trae-solo",
            "project_path": str(project),
        },
    )
    assert context["tool"] == "trae"
    assert context["status"] == "ok"
    assert context["context_markdown"]

    started = dispatch(
        tmp_path,
        {
            "phase": "start",
            "tool": "trae-solo",
            "project_path": str(project),
            "session_id": "session-1",
            "task_id": "task-1",
        },
    )
    assert started["tool"] == "trae"
    assert started["event"]["event_type"] == "session_start"
    assert started["read_receipt"]["operation_id"].startswith("read:")
    assert started["verification_mode"] == "observed"

    stopped = dispatch(
        tmp_path,
        {
            "phase": "stop",
            "tool": "trae-solo",
            "project_path": str(project),
            "session_id": "session-1",
            "task_id": "task-1",
            "handoff": {
                "task_id": "task-1",
                "objective": "continue the shared work",
                "current_state": "bridge contract is implemented",
                "verifications": ["bridge test passed"],
                "next_action": "use the bridge from a native host",
            },
        },
    )
    assert stopped["tool"] == "trae"
    assert stopped["event"]["event_type"] == "session_summary"
    assert stopped["write_receipt"]["operation_id"].startswith("write:")
    assert stopped["handoff"]["created"] is True
    assert stopped["verification_mode"] == "observed"

    receipts = capabilities.load(tmp_path)
    assert "trae-solo" not in receipts
    assert receipts["trae"]["status"] == "observed"


def test_bridge_rejects_unknown_tool_and_invalid_source(tmp_path: Path) -> None:
    project = _project(tmp_path)
    try:
        dispatch(
            tmp_path,
            {"phase": "start", "tool": "not-registered", "project_path": str(project)},
        )
    except ValueError as exc:
        assert "unknown tool" in str(exc)
    else:
        raise AssertionError("unknown tool was accepted")

    try:
        dispatch(
            tmp_path,
            {
                "phase": "start",
                "tool": "codex",
                "project_path": str(project),
                "source": "pretend-native",
            },
        )
    except ValueError as exc:
        assert "unknown receipt source" in str(exc)
    else:
        raise AssertionError("invalid receipt source was accepted")


def test_bridge_requires_explicit_simulation_and_rejects_simulated_proof(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    observed = dispatch(
        tmp_path,
        {"phase": "start", "tool": "codex", "project_path": str(project)},
    )
    assert observed["verification_mode"] == "observed"
    assert observed["simulation"] is False

    try:
        dispatch(
            tmp_path,
            {
                "phase": "start",
                "tool": "codex",
                "project_path": str(project),
                "source": "native-hook",
                "simulation": True,
            },
        )
    except ValueError as exc:
        assert "simulation cannot use a proof source" in str(exc)
    else:
        raise AssertionError("simulation was allowed to claim a proof source")


def test_bridge_rejects_native_proof_without_registered_host_binding(tmp_path: Path) -> None:
    project = _project(tmp_path)
    try:
        dispatch(
            tmp_path,
            {
                "phase": "start",
                "tool": "opencode",
                "project_path": str(project),
                "session_id": "session-1",
                "source": "native-hook",
            },
            trusted_host=True,
        )
    except ValueError as exc:
        assert "host_proof is required" in str(exc)
    else:
        raise AssertionError("native bridge proof was accepted without host binding")


def test_public_bridge_rejects_registered_host_proof(tmp_path: Path) -> None:
    project = _project(tmp_path)
    try:
        dispatch(
            tmp_path,
            {
                "phase": "start",
                "tool": "opencode",
                "project_path": str(project),
                "session_id": "session-public-1",
                "source": "native-hook",
                "host_proof": {
                    "integration": "opencode-plugin",
                    "event": "session.created",
                    "session_id": "session-public-1",
                },
            },
        )
    except ValueError as exc:
        assert "trusted native host adapter" in str(exc)
    else:
        raise AssertionError("public bridge accepted a host proof claim")


def test_cli_bridge_accepts_registered_host_proof_only_for_trusted_child(
    tmp_path: Path, monkeypatch
) -> None:
    project = _project(tmp_path)
    request = {
        "phase": "start",
        "tool": "opencode",
        "project_path": str(project),
        "session_id": "session-cli-trusted-1",
        "source": "native-hook",
        "host_proof": {
            "integration": "opencode-plugin",
            "event": "session.created",
            "session_id": "session-cli-trusted-1",
        },
    }

    monkeypatch.setenv("LWM_HOST_BRIDGE", "1")
    response = CliRunner().invoke(
        app,
        ["hub", "bridge", json.dumps(request), "--root", str(tmp_path)],
    )
    assert response.exit_code == 0, response.output
    payload = json.loads(response.stdout)
    assert payload["verification_mode"] == "host-reported"
    assert payload["read_receipt"]["status"] == "verified"


def test_bridge_accepts_only_registered_opencode_host_proof(tmp_path: Path) -> None:
    project = _project(tmp_path)
    started = dispatch(
        tmp_path,
        {
            "phase": "start",
            "tool": "opencode",
            "project_path": str(project),
            "session_id": "session-1",
            "source": "native-hook",
            "host_proof": {
                "integration": "opencode-plugin",
                "event": "session.created",
                "session_id": "session-1",
            },
        },
        trusted_host=True,
    )
    assert started["verification_mode"] == "host-reported"
    assert started["host_proof"]["integration"] == "opencode-plugin"
    assert started["read_receipt"]["status"] == "verified"

    try:
        dispatch(
            tmp_path,
            {
                "phase": "start",
                "tool": "codex",
                "project_path": str(project),
                "session_id": "session-2",
                "source": "native-hook",
                "host_proof": {
                    "integration": "opencode-plugin",
                    "event": "session.created",
                    "session_id": "session-2",
                },
            },
            trusted_host=True,
        )
    except ValueError as exc:
        assert "not registered" in str(exc)
    else:
        raise AssertionError("unregistered host proof integration was accepted")


def test_bridge_accepts_registered_shell_host_proof(tmp_path: Path) -> None:
    project = _project(tmp_path)
    started = dispatch(
        tmp_path,
        {
            "phase": "start",
            "tool": "shell",
            "project_path": str(project),
            "session_id": "shell-session-1",
            "source": "native-hook",
            "host_proof": {
                "integration": "shell-hook",
                "event": "shell_session_start",
                "session_id": "shell-session-1",
            },
        },
        trusted_host=True,
    )
    assert started["verification_mode"] == "host-reported"
    assert started["read_receipt"]["status"] == "verified"

    stopped = dispatch(
        tmp_path,
        {
            "phase": "stop",
            "tool": "shell",
            "project_path": str(project),
            "session_id": "shell-session-1",
            "source": "native-hook",
            "host_proof": {
                "integration": "shell-hook",
                "event": "shell_session_end",
                "session_id": "shell-session-1",
            },
        },
        trusted_host=True,
    )
    assert stopped["verification_mode"] == "host-reported"
    assert stopped["write_receipt"]["status"] == "verified"


def test_simulated_registry_contract_covers_every_registered_tool(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = simulate_registry_contract(tmp_path, project)

    expected = {definition.tool_id for definition in default_registry().enabled()}
    actual = {row["tool"] for row in result["tools"]}
    assert result["all_contracts_pass"] is True
    assert result["verification_mode"] == "simulated"
    assert actual == expected
    assert all(row["context_status"] == "ok" for row in result["tools"])
    assert all(row["proof_claim"] == "not_proven" for row in result["tools"])


def test_simulated_registry_contract_does_not_write_to_requested_root(tmp_path: Path) -> None:
    project = _project(tmp_path)
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = simulate_registry_contract(tmp_path, project)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert result["all_contracts_pass"] is True
    assert after == before


def test_bridge_cli_accepts_json_and_contract_command_requires_simulation(tmp_path: Path) -> None:
    project = _project(tmp_path)
    runner = CliRunner()
    request = json.dumps(
        {"phase": "start", "tool": "cc", "project_path": str(project), "task_id": "task-1"}
    )
    response = runner.invoke(app, ["hub", "bridge", request, "--root", str(tmp_path)])
    assert response.exit_code == 0, response.output
    payload = json.loads(response.stdout)
    assert payload["tool"] == "claude-code"
    assert payload["status"] == "ok"

    markdown = runner.invoke(
        app,
        ["hub", "bridge", request, "--output", "markdown", "--root", str(tmp_path)],
    )
    assert markdown.exit_code == 0, markdown.output
    assert "LLM-WorkMem Context" in markdown.stdout
    assert not markdown.stdout.lstrip().startswith("{")

    refused = runner.invoke(
        app,
        ["hub", "bridge-contract", "--root", str(tmp_path), "--project", str(project)],
    )
    assert refused.exit_code == 2
    assert "--simulate" in refused.output

    simulated = runner.invoke(
        app,
        [
            "hub",
            "bridge-contract",
            "--simulate",
            "--root",
            str(tmp_path / "contract-root"),
            "--project",
            str(project),
        ],
    )
    assert simulated.exit_code == 0, simulated.output
    assert json.loads(simulated.stdout)["all_contracts_pass"] is True


def test_bridge_stop_cli_is_a_shell_friendly_wrapper_over_the_shared_bridge(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    runner = CliRunner()
    handoff = json.dumps(
        {
            "task_id": "task-stop",
            "objective": "finish the bridge integration",
            "current_state": "the shared bridge is active",
            "verifications": ["bridge stop test passed"],
            "next_action": "use the host integration",
        }
    )

    response = runner.invoke(
        app,
        [
            "hub",
            "bridge-stop",
            "--tool",
            "cc",
            "--project",
            str(project),
            "--task-id",
            "task-stop",
            "--handoff-json",
            handoff,
            "--root",
            str(tmp_path),
        ],
    )

    assert response.exit_code == 0, response.output
    payload = json.loads(response.stdout)
    assert payload["tool"] == "claude-code"
    assert payload["phase"] == "stop"
    assert payload["handoff"]["created"] is True
    assert payload["verification_mode"] == "observed"
