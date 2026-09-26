from __future__ import annotations

import json
import hashlib
from pathlib import Path

from typer.testing import CliRunner

from lwm.cli import app
from lwm.cycle_receipt import CycleReceiptV2, write_cycle_receipt
from lwm.eval import packaged_eval_suite
from lwm.hub_service import context_for_tool, coverage_report, list_tools, record_event, verify_cycle
from lwm.capabilities import record
from lwm.tool_registry import ToolDefinition, ToolRegistry


def test_hub_service_lists_real_tools_and_coverage(tmp_path: Path) -> None:
    tools = list_tools(tmp_path)
    assert any(row["tool_id"] == "codex" for row in tools)
    assert all("collector_modules" in row for row in tools)
    assert all("observer_modules" in row for row in tools)
    assert all("proof_integrations" in row for row in tools)
    assert all("configured" in row for row in tools)
    assert all("host_probe" in row for row in tools)
    assert all("coverage_status" in row for row in tools)
    assert all(row["status_reason"] for row in tools)
    assert next(row for row in tools if row["tool_id"] == "opencode")["proof_integrations"] == [
        "opencode-plugin"
    ]
    assert all(row["collector_status"] in {"ready", "missing", "not_applicable"} for row in tools)
    antigravity = next(row for row in tools if row["tool_id"] == "antigravity")
    assert antigravity["observer_modules"] == [
        "adapters.hooks.antigravity_sessions"
    ]
    assert antigravity["observer_status"] == "ready"
    assert all(
        row["collector_importable"] is False
        for row in tools
        if row["collector_status"] == "not_applicable"
    )
    coverage = coverage_report(tmp_path)
    assert "codex" in coverage
    assert coverage["codex"]["status"] != "verified_bidirectional"
    assert "host_probe" in coverage["codex"]
    assert "configured" in coverage["codex"]


def test_coverage_exposes_app_presence_without_promoting_proof(tmp_path: Path) -> None:
    app = tmp_path / "Demo.app"
    app.mkdir()
    config = tmp_path / ".demo" / "rules.md"
    config.parent.mkdir()
    config.write_text("LLM-WorkMem", encoding="utf-8")
    ToolRegistry(
        [
            ToolDefinition(
                tool_id="demo-app",
                display_name="Demo app",
                surfaces=("ide",),
                discovery_paths=(".demo",),
                host_commands=("demo",),
                host_app_paths=(str(app),),
            )
        ]
    ).save(tmp_path)

    row = coverage_report(tmp_path, home=tmp_path)["demo-app"]

    assert row["configured"] is True
    assert row["host_probe"]["status"] == "app_present"
    assert row["status"] == "partially_supported"
    assert row["delivery_status"] == "configured_unverified"
    listed = next(
        item for item in list_tools(tmp_path, home=tmp_path) if item["tool_id"] == "demo-app"
    )
    assert listed["coverage_status"] == "partially_supported"
    assert listed["status_reason"] == "The app is present; waiting for its first real lifecycle event."


def test_probe_isolates_missing_custom_collector(tmp_path: Path) -> None:
    ToolRegistry(
        [
            ToolDefinition(
                tool_id="broken-tool",
                display_name="Broken tool",
                surfaces=("cli",),
                discovery_paths=(".broken-tool",),
                collector_modules=("missing_parent_package.collector",),
            )
        ]
    ).save(tmp_path)

    row = next(item for item in list_tools(tmp_path) if item["tool_id"] == "broken-tool")
    assert row["collector_importable"] is False
    assert row["collector_status"] == "missing"


def test_coverage_normalizes_repository_access_path_to_runtime_owner(
    tmp_path: Path,
) -> None:
    owner = tmp_path / "owner"
    access = tmp_path / "checkout"
    home = tmp_path / "home"
    (owner / "raw" / "events").mkdir(parents=True)
    (owner / "wiki").mkdir()
    access.mkdir()
    for name in ("raw", "wiki", "state"):
        (access / name).symlink_to(owner / name, target_is_directory=True)
    target = home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")

    read_evidence = owner / "raw" / "events" / "read.json"
    write_evidence = owner / "raw" / "events" / "write.json"
    read_evidence.write_text("read\n", encoding="utf-8")
    write_evidence.write_text("write\n", encoding="utf-8")
    record(
        owner,
        tool="claude-code",
        direction="read",
        project_id="project-1",
        source="native-hook",
        evidence_path="raw/events/read.json",
        operation_id="read-1",
    )
    record(
        owner,
        tool="claude-code",
        direction="write",
        project_id="project-1",
        source="native-hook",
        evidence_path="raw/events/write.json",
        operation_id="write-1",
    )

    access_result = coverage_report(access, home=home)
    owner_result = coverage_report(owner, home=home)

    assert access_result["claude-code"]["delivery_status"] == "verified_bidirectional"
    assert access_result["claude-code"] == owner_result["claude-code"]


def test_write_and_context_services_normalize_repository_access_path(
    tmp_path: Path,
) -> None:
    owner = tmp_path / "owner"
    access = tmp_path / "checkout"
    project = tmp_path / "project"
    project.mkdir()
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    access.mkdir()
    for name in ("raw", "wiki", "state"):
        (access / name).symlink_to(owner / name, target_is_directory=True)

    recorded = record_event(
        access,
        {
            "tool": "shell",
            "project_path": str(project),
            "event_type": "workflow_observation",
            "task": "owner normalization smoke",
        },
    )
    assert Path(recorded["absolute_path"]).resolve().is_relative_to(owner.resolve())
    assert not Path(recorded["absolute_path"]).is_relative_to(access)

    report, receipt = context_for_tool(access, tool="shell", project_path=project)
    assert report.project_id
    assert receipt["direction"] == "read"
    assert (owner / "state" / "capability-receipts.json").is_file()


def test_verify_cycle_normalizes_repository_access_path_to_runtime_owner(
    tmp_path: Path,
) -> None:
    owner = tmp_path / "owner"
    access = tmp_path / "checkout"
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    access.mkdir()
    for name in ("raw", "wiki", "state"):
        (access / name).symlink_to(owner / name, target_is_directory=True)

    health_path = owner / "state" / "health.json"
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text('{"status":"healthy"}\n', encoding="utf-8")
    context_path = owner / "state" / "receipts" / "contexts" / "cycle-owner.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text('{"context":"verified"}\n', encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-owner",
        runtime_id="runtime-owner",
        started_at="2026-08-01T00:00:00+00:00",
        finished_at="2026-08-01T00:01:00+00:00",
        core_status="success",
        overall_status="success",
        quality={"audit_ok": True, "eval_pass": 2, "eval_total": 2, "context_ok": True},
        runtime_module_path="/private/tmp/lwm-runtime/site-packages/lwm/__init__.py",
        runtime_sys_path=("/private/tmp/lwm-runtime/site-packages",),
        runtime_import_independent=True,
        eval_suite_sha256=hashlib.sha256(packaged_eval_suite().read_bytes()).hexdigest(),
        health_sha256=digest(health_path),
        evidence_hashes={
            "state/receipts/contexts/cycle-owner.json": digest(context_path)
        },
        exit_code=0,
    )
    write_cycle_receipt(receipt, owner)

    result = verify_cycle(access, "cycle-owner", strict=True)

    assert result["valid"] is True, result


def test_cli_exposes_tools_coverage_behavior_and_cycle_verification(tmp_path: Path) -> None:
    runner = CliRunner()
    tools = runner.invoke(app, ["hub", "tools", "list", "--root", str(tmp_path), "--json"])
    assert tools.exit_code == 0, tools.output
    assert any(row["tool_id"] == "codex" for row in json.loads(tools.stdout))

    probe = runner.invoke(app, ["hub", "tools", "probe", "--root", str(tmp_path), "--json"])
    assert probe.exit_code == 0, probe.output
    assert any(row["tool_id"] == "codex" for row in json.loads(probe.stdout))

    coverage = runner.invoke(app, ["hub", "coverage", "--root", str(tmp_path), "--json"])
    assert coverage.exit_code == 0, coverage.output
    assert "codex" in json.loads(coverage.stdout)

    behavior = runner.invoke(app, ["hub", "behavior", "show", "--root", str(tmp_path), "--json"])
    assert behavior.exit_code == 0, behavior.output
    assert "sha256" in json.loads(behavior.stdout)

    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-test",
        runtime_id="runtime-test",
        started_at="2026-08-01T00:00:00+00:00",
        finished_at="2026-08-01T00:01:00+00:00",
        core_status="success",
        overall_status="success",
    )
    write_cycle_receipt(receipt, tmp_path)
    verified = runner.invoke(app, ["hub", "verify-cycle", "cycle-test", "--root", str(tmp_path), "--strict"])
    assert verified.exit_code == 1, verified.output
    assert "receipt_missing_runtime_module_path" in verified.output
    verified_latest = runner.invoke(app, ["hub", "verify-cycle", str(tmp_path), "--strict"])
    assert verified_latest.exit_code == 1, verified_latest.output

    rebuild = runner.invoke(app, ["hub", "rebuild-projects", str(tmp_path), "--dry-run"])
    assert rebuild.exit_code == 0, rebuild.output
    assert json.loads(rebuild.stdout)["dry_run"] is True


def test_strict_cycle_verification_checks_the_full_evidence_contract(tmp_path: Path) -> None:
    health_path = tmp_path / "state" / "health.json"
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text('{"status":"healthy"}\n', encoding="utf-8")
    context_path = tmp_path / "state" / "receipts" / "contexts" / "cycle-valid.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text('{"context":"verified"}\n', encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-valid",
        runtime_id="runtime-test",
        started_at="2026-08-01T00:00:00+00:00",
        finished_at="2026-08-01T00:01:00+00:00",
        core_status="success",
        overall_status="success",
        quality={"audit_ok": True, "eval_pass": 2, "eval_total": 2, "context_ok": True},
        runtime_module_path="/private/tmp/lwm-runtime/site-packages/lwm/__init__.py",
        runtime_sys_path=("/private/tmp/lwm-runtime/site-packages",),
        runtime_import_independent=True,
        eval_suite_sha256=hashlib.sha256(packaged_eval_suite().read_bytes()).hexdigest(),
        health_sha256=digest(health_path),
        evidence_hashes={"state/receipts/contexts/cycle-valid.json": digest(context_path)},
        exit_code=0,
    )
    write_cycle_receipt(receipt, tmp_path)

    result = CliRunner().invoke(
        app, ["hub", "verify-cycle", "cycle-valid", "--root", str(tmp_path), "--strict"]
    )

    assert result.exit_code == 0, result.output


def test_cycle_verification_uses_immutable_health_snapshot(tmp_path: Path) -> None:
    health_path = tmp_path / "state" / "health.json"
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text('{"status":"healthy"}\n', encoding="utf-8")
    from lwm.runner import _archive_health_snapshot

    archived = _archive_health_snapshot(tmp_path, "cycle-archived", health_path)
    context_path = tmp_path / "state" / "receipts" / "contexts" / "cycle-archived.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text('{"context":"verified"}\n', encoding="utf-8")
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-archived",
        runtime_id="runtime-test",
        started_at="2026-08-01T00:00:00+00:00",
        finished_at="2026-08-01T00:01:00+00:00",
        core_status="success",
        overall_status="success",
        quality={"audit_ok": True, "eval_pass": 2, "eval_total": 2, "context_ok": True},
        runtime_module_path="/private/tmp/lwm-runtime/site-packages/lwm/__init__.py",
        runtime_sys_path=("/private/tmp/lwm-runtime/site-packages",),
        runtime_import_independent=True,
        eval_suite_sha256=hashlib.sha256(packaged_eval_suite().read_bytes()).hexdigest(),
        health_sha256=digest(archived),
        health_snapshot_path=str(archived.relative_to(tmp_path)),
        evidence_hashes={str(context_path.relative_to(tmp_path)): digest(context_path)},
        exit_code=0,
    )
    write_cycle_receipt(receipt, tmp_path)
    health_path.write_text('{"status":"degraded"}\n', encoding="utf-8")

    result = verify_cycle(tmp_path, "cycle-archived", strict=True)

    assert result["valid"] is True, result["reasons"]


def test_cycle_verification_reads_warning_cycle_from_last_attempt_pointer(tmp_path: Path) -> None:
    health_path = tmp_path / "state" / "health.json"
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text('{"status":"healthy"}\n', encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    receipt = CycleReceiptV2(
        schema_version=2,
        cycle_id="cycle-warning",
        runtime_id="runtime-test",
        started_at="2026-08-01T00:00:00+00:00",
        finished_at="2026-08-01T00:01:00+00:00",
        core_status="success_with_warnings",
        overall_status="degraded",
        quality={"audit_ok": True, "eval_pass": 2, "eval_total": 2, "context_ok": True},
        runtime_module_path="/private/tmp/lwm-runtime/site-packages/lwm/__init__.py",
        runtime_sys_path=("/private/tmp/lwm-runtime/site-packages",),
        runtime_import_independent=True,
        eval_suite_sha256=hashlib.sha256(packaged_eval_suite().read_bytes()).hexdigest(),
        health_sha256=digest(health_path),
        exit_code=0,
    )
    write_cycle_receipt(receipt, tmp_path)

    result = CliRunner().invoke(
        app, ["hub", "verify-cycle", "cycle-warning", "--root", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "latest_pointer_missing_receipt_hash" not in result.output
