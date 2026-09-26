"""Tool Registry + Capability Proof contract tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Architecture And Interfaces / 2. Tool Registry
      -> Implementation Changes / 3. Tool Registry, automatic capture,
         and behavior contract

Verifies:

* the registry is a versioned data structure, not a hard-coded module list;
* every registered tool exposes discovery paths, capture mode, and delivery
  mode;
* aliases resolve to the canonical tool id;
* capability proof distinguishes *proof* sources from *observation* sources;
* watcher observation can never produce ``verified_*``;
* a proof receipt carries the required project / operation / evidence
  fields and survives a round-trip through the store.
"""

from __future__ import annotations

import json
import importlib
from datetime import datetime, timezone
from pathlib import Path


from lwm.capability_proof import (
    ALL_RECEIPT_SOURCES,
    OBSERVATION_RECEIPT_SOURCES,
    PROOF_RECEIPT_SOURCES,
    capability_status,
    is_proof_source,
    is_within_window,
    latest_proof_receipts,
    load as load_receipts,
    record as record_proof,
)
from lwm.tool_registry import (
    REGISTRY_VERSION,
    ToolCoverage,
    ToolDefinition,
    ToolRegistry,
    default_registry,
)


def _evidence(root: Path, relative: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("evidence\n", encoding="utf-8")
    return relative


# ---------------------------------------------------------------------------
# Registry shape and version
# ---------------------------------------------------------------------------


def test_registry_is_versioned_and_loadable() -> None:
    assert REGISTRY_VERSION >= 2
    registry = default_registry()
    assert registry.version == REGISTRY_VERSION
    assert len(registry.all()) >= 11


def test_registry_discovery_matches_installed_adapter_locations(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".minimax" / "v2" / "sqlite").mkdir(parents=True)
    (home / ".minimax" / "v2" / "sqlite" / "runtime-state.sqlite").write_text("", encoding="utf-8")
    (home / ".gemini" / "GEMINI.md").parent.mkdir(parents=True)
    (home / ".gemini" / "GEMINI.md").write_text("# Gemini", encoding="utf-8")

    discovered = default_registry().discover(home)

    assert discovered["minimax"] is True
    assert discovered["gemini-cli"] is True
    assert discovered["cursor"] is False


def test_registry_host_probe_distinguishes_app_and_executable_presence(tmp_path: Path) -> None:
    app = tmp_path / "Demo.app"
    app.mkdir()
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="demo-app",
                display_name="Demo app",
                surfaces=("ide",),
                discovery_paths=(".demo",),
                host_commands=("demo",),
                host_app_paths=(str(app),),
            ),
            ToolDefinition(
                tool_id="demo-shell",
                display_name="Demo shell",
                surfaces=("shell",),
                discovery_paths=(".demo-shell",),
            ),
        ]
    )
    probes = registry.host_probe(path_lookup={"demo-app": "/missing/demo"})

    assert probes["demo-app"] == {
        "status": "app_present",
        "locator": str(app),
        "checked_commands": ["demo"],
        "checked_app_paths": [str(app)],
    }
    assert probes["demo-shell"]["status"] == "not_applicable"


def test_registry_host_probe_accepts_an_executable_override(tmp_path: Path) -> None:
    executable = tmp_path / "demo"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="demo-cli",
                display_name="Demo CLI",
                surfaces=("cli",),
                discovery_paths=(".demo-cli",),
                host_commands=("demo",),
            )
        ]
    )

    probe = registry.host_probe(path_lookup={"demo-cli": str(executable)})["demo-cli"]

    assert probe["status"] == "available"
    assert probe["locator"] == str(executable)


def test_minimax_uses_mcp_as_primary_delivery_mode() -> None:
    definition = default_registry().resolve("minimax")

    assert definition is not None
    assert definition.delivery_mode == "mcp"


def test_every_tool_exposes_required_fields() -> None:
    registry = default_registry()
    for definition in registry.all():
        assert definition.tool_id and isinstance(definition.tool_id, str)
        assert definition.display_name
        assert definition.surfaces, definition.tool_id
        assert all(s in {"ide", "cli", "shell"} for s in definition.surfaces)
        assert definition.discovery_paths, definition.tool_id
        assert isinstance(definition.host_commands, tuple)
        assert isinstance(definition.host_app_paths, tuple)
        assert definition.capture_mode in {
            "native_hook",
            "session_adapter",
            "file_tail",
            "shell_lifecycle",
        }
        assert definition.delivery_mode in {
            "native_hook",
            "instruction_pointer",
            "mcp",
            "shell_context",
        }
        assert isinstance(definition.collector_modules, tuple)
        assert isinstance(definition.observer_modules, tuple)
        assert isinstance(definition.proof_integrations, tuple)
        if definition.collector_modules:
            assert definition.adapter_module == definition.collector_modules[0]
        else:
            assert definition.adapter_module is None


def test_registry_host_probe_fields_survive_persistence(tmp_path: Path) -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="persisted-host",
                display_name="Persisted host",
                surfaces=("cli",),
                discovery_paths=(".persisted-host",),
                host_commands=("persisted-host",),
                host_app_paths=("/Applications/Persisted.app",),
            )
        ]
    )
    registry.save(tmp_path)

    loaded = ToolRegistry.load(tmp_path).resolve("persisted-host")

    assert loaded is not None
    assert loaded.host_commands == ("persisted-host",)
    assert loaded.host_app_paths == ("/Applications/Persisted.app",)


def test_registered_modules_are_real_and_hook_only_tools_are_explicit() -> None:
    """The runner must never invoke the old fictional ``lwm.adapters.*`` modules."""

    registry = default_registry()
    assert registry.resolve("cursor").collector_modules == ("adapters.hooks.cursor_tasks",)
    assert registry.resolve("antigravity").observer_modules == (
        "adapters.hooks.antigravity_sessions",
    )
    for definition in registry.all():
        for module in definition.collector_modules:
            assert importlib.util.find_spec(module) is not None, (
                definition.tool_id,
                module,
            )
        for module in definition.observer_modules:
            assert importlib.util.find_spec(module) is not None, (
                definition.tool_id,
                module,
            )
        if definition.capture_mode == "native_hook" and not definition.observer_modules:
            assert not definition.collector_modules, definition.tool_id
        if definition.collector_modules:
            assert definition.adapter_module == definition.collector_modules[0]
        else:
            assert definition.adapter_module is None


def test_aliases_resolve_to_canonical_tool_id() -> None:
    registry = default_registry()
    assert registry.resolve("Claude Code").tool_id == "claude-code"
    assert registry.resolve("claude").tool_id == "claude-code"
    assert registry.resolve("cc").tool_id == "claude-code"
    assert registry.resolve("AGY").tool_id == "antigravity"
    assert registry.resolve("unknown-tool") is None


def test_proof_integrations_are_explicitly_bound_to_native_hosts() -> None:
    registry = default_registry()
    assert registry.resolve("claude-code").proof_integrations == ("claude-code-hook",)
    assert registry.resolve("opencode").proof_integrations == ("opencode-plugin",)
    assert registry.resolve("codex").proof_integrations == ("codex-hook",)
    assert registry.resolve("shell").proof_integrations == ("shell-hook",)
    assert registry.resolve("cursor").proof_integrations == (
        "cursor-extension",
        "cursor-hook",
    )
    assert registry.resolve("minimax").proof_integrations == ("minimax-mcp",)
    assert registry.resolve("gemini-cli").proof_integrations == (
        "gemini-cli-hook",
        "gemini-cli-mcp",
    )


def test_registry_override_replaces_old_alias_index() -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="claude-code",
                display_name="Claude Code override",
                aliases=("only-claude",),
                surfaces=("cli",),
                discovery_paths=(".claude",),
            )
        ]
    )
    assert registry.resolve("only-claude").tool_id == "claude-code"
    assert registry.resolve("cc") is None


def test_registry_round_trips_through_disk() -> None:
    root = Path("/tmp/lwm-registry-test")
    root.mkdir(exist_ok=True)
    target = root / "tool-registry.json"
    if target.exists():
        target.unlink()
    registry = default_registry()
    registry.save(root, path=target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["version"] == REGISTRY_VERSION
    reloaded = ToolRegistry.load(root, path=target)
    assert {d.tool_id for d in reloaded.all()} == {
        d.tool_id for d in registry.all()
    }


def test_legacy_registry_row_inherits_new_proof_binding(tmp_path: Path) -> None:
    target = tmp_path / "state" / "tool-registry.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "version": 2,
                "definitions": [
                    {
                        "tool_id": "claude-code",
                        "display_name": "Claude Code",
                        "aliases": ["claude"],
                        "surfaces": ["cli"],
                        "discovery_paths": [".claude"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    registry = ToolRegistry.load(tmp_path)
    assert registry.resolve("claude").proof_integrations == ("claude-code-hook",)


def test_persisted_definition_overrides_default_definition(tmp_path: Path) -> None:
    override = ToolDefinition(
        tool_id="codex",
        display_name="Codex disabled for test",
        surfaces=("cli",),
        discovery_paths=(".codex/AGENTS.md",),
        capture_mode="session_adapter",
        delivery_mode="instruction_pointer",
        enabled=False,
    )
    ToolRegistry([override]).save(tmp_path)

    loaded = ToolRegistry.load(tmp_path)
    assert loaded.resolve("codex") is not None
    assert loaded.resolve("codex").enabled is False


def test_new_tool_does_not_modify_core_admission() -> None:
    """Spec §2: a new tool must only add a registry row and an adapter."""

    registry = default_registry()
    before = {d.tool_id for d in registry.all()}
    extra = ToolDefinition(
        tool_id="notebooklm",
        display_name="NotebookLM",
        surfaces=("cli",),
        discovery_paths=(".config/notebooklm/AGENTS.md",),
        capture_mode="session_adapter",
        delivery_mode="instruction_pointer",
        adapter_module="lwm.adapters.notebooklm",
    )
    registry._add(extra)  # noqa: SLF001 — internal contract check
    assert {d.tool_id for d in registry.all()} == before | {"notebooklm"}


# ---------------------------------------------------------------------------
# Capability proof semantics
# ---------------------------------------------------------------------------


def test_proof_sources_and_observation_sources_are_disjoint() -> None:
    assert PROOF_RECEIPT_SOURCES.isdisjoint(OBSERVATION_RECEIPT_SOURCES)
    assert PROOF_RECEIPT_SOURCES | OBSERVATION_RECEIPT_SOURCES == ALL_RECEIPT_SOURCES


def test_watcher_observed_is_not_a_proof_source() -> None:
    assert not is_proof_source("watcher-observed")
    assert not is_proof_source("cli-context")
    assert not is_proof_source("file-probe")


def test_capability_status_watcher_only_never_verified() -> None:
    observed_read = {
        "source": "watcher-observed",
        "direction": "read",
        "project_id": "p1",
        "timestamp": "2026-07-31T01:00:00+00:00",
    }
    observed_write = {**observed_read, "direction": "write"}
    assert capability_status(
        read_receipt=observed_read,
        write_receipt=observed_write,
        expected_project_id="p1",
    ) == "observed_read_only"
    assert capability_status(
        read_receipt=observed_read,
        write_receipt=None,
        expected_project_id="p1",
    ) == "observed_read"
    assert capability_status(
        read_receipt=None,
        write_receipt=observed_write,
        expected_project_id="p1",
    ) == "observed_write"


def test_capability_status_proof_requires_project_match() -> None:
    proof = {
        "source": "native-hook",
        "direction": "read",
        "project_id": "other",
        "timestamp": "2026-07-31T01:00:00+00:00",
    }
    assert (
        capability_status(
            read_receipt=proof,
            write_receipt=None,
            expected_project_id="current",
        )
        == "configured_unverified"
    )


def test_capability_status_proof_within_window_is_verified() -> None:
    from datetime import datetime, timedelta, timezone

    ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    proof = {
        "source": "lifecycle-hook",
        "direction": "read",
        "project_id": "p1",
        "timestamp": ts,
        "status": "verified",
        "evidence_path": "raw/events/processed/p1.json",
        "operation_id": "op-read",
    }
    assert (
        capability_status(
            read_receipt=proof,
            write_receipt={**proof, "direction": "write"},
            expected_project_id="p1",
        )
        == "verified_bidirectional"
    )


def test_capability_status_stale_proof_demoted_to_observation() -> None:
    stale = {
        "source": "native-hook",
        "direction": "read",
        "project_id": "p1",
        "timestamp": "2020-01-01T00:00:00+00:00",
    }
    status = capability_status(
        read_receipt=stale,
        write_receipt=None,
        expected_project_id="p1",
    )
    assert not status.startswith("verified_"), status


def test_record_persists_required_fields(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path, "raw/events/processed/2026-07-31/abc.json")
    record_proof(
        tmp_path,
        tool="claude-code",
        direction="read",
        project_id="p1",
        source="native-hook",
        evidence_path=evidence,
        operation_id="op-1",
        detail="SessionStart hook",
    )
    payload = load_receipts(tmp_path)
    assert "claude-code" in payload
    entry = payload["claude-code"]
    assert entry["project_id"] == "p1"
    assert entry["source"] == "native-hook"
    assert entry["operation_id"] == "op-1"
    assert entry["evidence_path"].endswith("abc.json")
    assert is_within_window(entry)

    per_tool = tmp_path / "state" / "receipts" / "tools" / "claude-code" / "op-1.json"
    assert per_tool.is_file()


def test_record_rejects_observation_source_as_proof() -> None:
    record_proof(
        Path("/tmp/lwm-rp-1"),
        tool="claude-code",
        direction="read",
        project_id="p1",
        source="watcher-observed",
        evidence_path="x",
        operation_id="op-2",
    )
    payload = load_receipts(Path("/tmp/lwm-rp-1"))
    assert payload["claude-code"]["status"] == "observed"


def test_proof_without_evidence_is_observation_only(tmp_path: Path) -> None:
    record_proof(
        tmp_path,
        tool="codex",
        direction="read",
        project_id="p1",
        source="native-hook",
        evidence_path="",
        operation_id="",
    )
    payload = load_receipts(tmp_path)
    assert payload["codex"]["status"] == "observed"


def test_proof_path_must_be_existing_and_owned_by_root(tmp_path: Path) -> None:
    record_proof(
        tmp_path,
        tool="codex",
        direction="read",
        project_id="p1",
        source="native-hook",
        evidence_path="missing/read.json",
        operation_id="missing-read",
    )
    outside = tmp_path.parent / "outside-evidence.json"
    outside.write_text("outside\n", encoding="utf-8")
    record_proof(
        tmp_path,
        tool="codex",
        direction="write",
        project_id="p1",
        source="native-hook",
        evidence_path=str(outside),
        operation_id="outside-write",
    )
    payload = load_receipts(tmp_path)
    assert payload["codex"]["status"] == "observed"
    assert all(item["status"] == "observed" for item in payload["_history"]["codex"])


def test_deleted_evidence_is_removed_from_latest_proof_view(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text("proof\n", encoding="utf-8")
    record_proof(
        tmp_path,
        tool="codex",
        direction="read",
        project_id="p1",
        source="native-hook",
        evidence_path="evidence.json",
        operation_id="read-1",
    )
    evidence.unlink()
    read, write = latest_proof_receipts(tmp_path, tool="codex", expected_project_id="p1")
    assert read is None
    assert write is None


def test_event_evidence_survives_inbox_to_processed_relocation(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path, "raw/events/inbox/2026-07-31/event.json")
    record_proof(
        tmp_path,
        tool="opencode",
        direction="read",
        project_id="p1",
        source="native-hook",
        evidence_path=evidence,
        operation_id="read-event",
    )
    processed = tmp_path / "raw" / "events" / "processed" / "2026-07-31" / "event.json"
    processed.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / evidence).rename(processed)

    read, write = latest_proof_receipts(
        tmp_path, tool="opencode", expected_project_id="p1"
    )
    assert read is not None
    assert read.status == "verified"
    assert write is None


def test_latest_proof_receipts_filters_by_project() -> None:
    root = Path("/tmp/lwm-rp-2")
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir()
    _evidence(root, "x")
    _evidence(root, "y")
    record_proof(
        root,
        tool="codex",
        direction="read",
        project_id="other",
        source="native-hook",
        evidence_path="x",
        operation_id="op-other-r",
    )
    record_proof(
        root,
        tool="codex",
        direction="write",
        project_id="current",
        source="lifecycle-hook",
        evidence_path="y",
        operation_id="op-current-w",
    )
    read, write = latest_proof_receipts(root, tool="codex", expected_project_id="current")
    assert read is None
    assert write is not None
    assert write.project_id == "current"


def test_receipt_history_capped_at_250() -> None:
    root = Path("/tmp/lwm-rp-3")
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir()
    for index in range(300):
        evidence = _evidence(root, f"e/{index}")
        record_proof(
            root,
            tool="claude-code",
            direction="read",
            project_id="p1",
            source="native-hook",
            evidence_path=evidence,
            operation_id=f"op-{index}",
        )
    payload = load_receipts(root)
    assert len(payload["_history"]["claude-code"]) == 250


# ---------------------------------------------------------------------------
# Coverage view
# ---------------------------------------------------------------------------


def test_coverage_for_tool_reports_truthful_status(tmp_path: Path) -> None:
    home = tmp_path / "home"
    prompts = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "llm-workmem.instructions.md").write_text("LLM-WorkMem", encoding="utf-8")

    from lwm.capability_proof import coverage_for_tool

    coverage = coverage_for_tool(
        tmp_path, tool="vscode", expected_project_id=None, configured=True
    )
    assert isinstance(coverage, ToolCoverage)
    assert coverage.tool_id == "vscode"
    assert coverage.status in {
        "partially_supported",
        "supported",
        "pending_integration",
        "unsupported",
    }
    assert coverage.status_reason
    assert not coverage.gaps or "no_proof_receipts" in coverage.gaps


def test_coverage_reason_explains_missing_host_proof(tmp_path: Path) -> None:
    from lwm.capability_proof import coverage_for_tool

    coverage = coverage_for_tool(
        tmp_path,
        tool="gemini-cli",
        expected_project_id=None,
        configured=True,
        host_probe={"status": "app_present"},
    )

    assert coverage.status == "partially_supported"
    assert coverage.status_reason == (
        "The app is present; waiting for its first real lifecycle event."
    )


def test_coverage_uses_source_event_for_capture_and_isolates_project(tmp_path: Path) -> None:
    from lwm.capability_proof import coverage_for_tool

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    event_dir = tmp_path / "raw" / "events" / "processed"
    event_dir.mkdir(parents=True)
    (event_dir / "capture.json").write_text(
        json.dumps(
            {
                "tool": "vscode",
                "project_id": "current",
                "event_type": "session_start",
                "timestamp": timestamp,
            }
        ),
        encoding="utf-8",
    )

    current = coverage_for_tool(
        tmp_path,
        tool="vscode",
        expected_project_id="current",
        configured=True,
    )
    other = coverage_for_tool(
        tmp_path,
        tool="vscode",
        expected_project_id="other",
        configured=True,
    )
    assert current.last_capture_at == timestamp
    assert current.capture_freshness == "fresh"
    assert current.capture_status == "ok"
    assert other.last_capture_at is None
    assert other.capture_freshness == "missing"
    assert "no_capture_event" in other.gaps


def test_coverage_ignores_durable_verification_as_capture(tmp_path: Path) -> None:
    from lwm.capability_proof import coverage_for_tool

    event_dir = tmp_path / "raw" / "events" / "inbox"
    event_dir.mkdir(parents=True)
    (event_dir / "verification.json").write_text(
        json.dumps(
            {
                "tool": "codex",
                "project_id": "current",
                "event_type": "verification",
                "timestamp": "2099-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    coverage = coverage_for_tool(
        tmp_path,
        tool="codex",
        expected_project_id="current",
        configured=True,
    )

    assert coverage.last_capture_at is None
    assert coverage.capture_freshness == "missing"
    assert "no_capture_event" in coverage.gaps


# ---------------------------------------------------------------------------
# Backwards compatibility surface
# ---------------------------------------------------------------------------


def test_legacy_capabilities_module_exports_public_api() -> None:
    from lwm import capabilities

    for name in (
        "KNOWN_TOOLS",
        "NATIVE_RECEIPT_SOURCES",
        "TOOL_TARGETS",
        "load",
        "probe",
        "record",
        "summary",
    ):
        assert hasattr(capabilities, name), name


def test_legacy_native_sources_no_longer_contain_watcher() -> None:
    from lwm.capabilities import NATIVE_RECEIPT_SOURCES

    assert "watcher-observed" not in NATIVE_RECEIPT_SOURCES
    assert {"native-hook", "lifecycle-hook"}.issubset(NATIVE_RECEIPT_SOURCES)


def test_legacy_record_keeps_old_callers_working(tmp_path: Path) -> None:
    from lwm.capabilities import record, load as legacy_load

    record(tmp_path, tool="claude-code", direction="read", source="native-hook")
    payload = legacy_load(tmp_path)
    assert "claude-code" in payload
    assert payload["claude-code"]["direction"] == "read"
