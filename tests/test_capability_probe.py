import json
from pathlib import Path

from lwm.capabilities import (
    NATIVE_RECEIPT_SOURCES,
    _latest_receipt,
    load,
    probe,
    record,
)
from lwm.capability_proof import latest_proof_receipts
from lwm.capability_proof import capability_status
from lwm.tool_registry import ToolDefinition, ToolRegistry


def test_empty_session_end_does_not_hide_published_work(tmp_path: Path) -> None:
    from lwm.events import make_event
    from lwm.project_memory import project_page_path

    work = make_event(tool="codex", project_path="/work", project_id="p",
                      event_type="bugfix", importance="project",
                      changes=["Fixed clock"], verification=["clock test PASS"])
    relative = f"raw/events/processed/2026-10-11/{work['event_id']}.json"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(work))
    page = project_page_path(tmp_path, "p")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"Source: {work['event_id']}")
    record(tmp_path, tool="codex", direction="write", project_id="p",
           source="native-hook", evidence_path=relative, operation_id="work-1")
    end = make_event(tool="codex", project_path="/work", project_id="p",
                     event_type="session_summary", importance="scratch")
    end_relative = f"raw/events/processed/2026-10-11/{end['event_id']}.json"
    (tmp_path / end_relative).write_text(json.dumps(end))
    record(tmp_path, tool="codex", direction="write", project_id="p",
           source="native-hook", evidence_path=end_relative, operation_id="end-1")
    assert probe(tmp_path, home=tmp_path / "home")["codex"]["useful_memory_status"] == "published"
    # Rejected evidence can never sustain a published claim.
    path.unlink()
    assert probe(tmp_path, home=tmp_path / "home")["codex"]["useful_memory_status"] == "operational_only"


def _evidence(root: Path, relative: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("evidence\n", encoding="utf-8")
    return relative


def test_probe_distinguishes_configured_from_verified(tmp_path: Path) -> None:
    home = tmp_path / "home"
    target = home / ".codex" / "AGENTS.md"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")

    result = probe(tmp_path, home=home)
    assert result["codex"]["status"] == "configured_unverified"

    record(tmp_path, tool="codex", direction="read", source="lifecycle-hook", evidence_path=_evidence(tmp_path, "events/read.json"), operation_id="read-1")
    record(tmp_path, tool="codex", direction="write", source="lifecycle-hook", evidence_path=_evidence(tmp_path, "events/write.json"), operation_id="write-1")
    assert probe(tmp_path, home=home)["codex"]["status"] == "verified_bidirectional"


def test_probe_follows_registered_opencode_plugin_and_vscode_instruction(tmp_path: Path) -> None:
    home = tmp_path / "home"
    opencode = home / ".config" / "opencode"
    opencode.mkdir(parents=True)
    (opencode / "AGENTS.md").write_text("LLM-WorkMem", encoding="utf-8")
    plugin = tmp_path / "source" / "integrations" / "opencode" / "lwm-workmem.ts"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("plugin", encoding="utf-8")
    (opencode / "opencode.json").write_text(
        json.dumps({"plugin": [str(plugin)]}), encoding="utf-8"
    )
    prompts = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "copilot-workflow-memory.instructions.md").write_text(
        "LLM-WorkMem", encoding="utf-8"
    )

    result = probe(tmp_path, home=home)

    assert result["opencode"]["installed"] is True
    assert result["vscode"]["installed"] is True


def test_legacy_capability_facade_normalizes_repository_access_path(
    tmp_path: Path,
) -> None:
    owner = tmp_path / "owner"
    access = tmp_path / "checkout"
    home = tmp_path / "home"
    (owner / "raw").mkdir(parents=True)
    (owner / "wiki").mkdir()
    access.mkdir()
    for name in ("raw", "wiki", "state"):
        (access / name).symlink_to(owner / name, target_is_directory=True)
    target = home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")
    (owner / "raw" / "events").mkdir(parents=True)
    (owner / "raw" / "events" / "read.json").write_text("evidence\n", encoding="utf-8")
    (owner / "raw" / "events" / "write.json").write_text("evidence\n", encoding="utf-8")

    record(
        access,
        tool="claude-code",
        direction="read",
        project_id="project-1",
        source="native-hook",
        evidence_path="raw/events/read.json",
        operation_id="read-1",
    )
    record(
        access,
        tool="claude-code",
        direction="write",
        project_id="project-1",
        source="native-hook",
        evidence_path="raw/events/write.json",
        operation_id="write-1",
    )

    result = probe(access, home=home)

    assert result["claude-code"]["status"] == "verified_bidirectional"


def test_capability_facade_uses_persisted_registry_aliases(tmp_path: Path) -> None:
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="custom-cli",
                display_name="Custom CLI",
                aliases=("mycli",),
                surfaces=("cli",),
                discovery_paths=(".mycli",),
            )
        ]
    )
    registry.save(tmp_path)
    home = tmp_path / "home"
    target = home / ".mycli"
    target.parent.mkdir(parents=True)
    target.write_text("configured", encoding="utf-8")

    result = probe(tmp_path, home=home)
    assert result["custom-cli"]["installed"] is True
    receipt = record(
        tmp_path,
        tool="mycli",
        direction="write",
        source="watcher-observed",
    )
    assert receipt["tool"] == "custom-cli"


def test_watcher_observed_receipts_never_reach_verified_status(tmp_path: Path) -> None:
    """Spec §3.5: watcher observation must never produce verified_*.status."""
    home = tmp_path / "home"
    target = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
    target.mkdir(parents=True)
    (target / "copilot-workflow-memory.instructions.md").write_text(
        "LLM-WorkMem", encoding="utf-8"
    )
    record(tmp_path, tool="vscode", direction="read", source="watcher-observed")
    record(tmp_path, tool="vscode", direction="write", source="watcher-observed")

    status = probe(tmp_path, home=home)["vscode"]["status"]
    assert not status.startswith("verified_"), status
    assert status in {
        "observed_read",
        "observed_write",
        "observed_read_only",
        "configured_unverified",
    }


def test_probe_selects_matching_project_from_receipt_history(
    tmp_path: Path, monkeypatch
) -> None:
    home = tmp_path / "home"
    target = home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")
    current = tmp_path / "current"
    current.mkdir()

    record(tmp_path, tool="claude-code", direction="read", project_id="other", source="native-hook", evidence_path=_evidence(tmp_path, "other/read.json"), operation_id="other-read")
    record(tmp_path, tool="claude-code", direction="write", project_id="other", source="native-hook", evidence_path=_evidence(tmp_path, "other/write.json"), operation_id="other-write")
    record(tmp_path, tool="claude-code", direction="read", project_id="current", source="native-hook", evidence_path=_evidence(tmp_path, "current/read.json"), operation_id="current-read")
    record(tmp_path, tool="claude-code", direction="write", project_id="current", source="native-hook", evidence_path=_evidence(tmp_path, "current/write.json"), operation_id="current-write")
    record(tmp_path, tool="claude-code", direction="read", project_id="current", source="cli-context")
    monkeypatch.setattr(
        "lwm.project_id.resolve_project_id",
        lambda _path: type("Resolution", (), {"project_id": "current"})(),
    )

    result = probe(tmp_path, home=home, project_path=current)

    assert result["claude-code"]["status"] == "verified_bidirectional"


def test_latest_proof_receipts_recovers_when_aggregate_index_is_stale(
    tmp_path: Path,
) -> None:
    record(
        tmp_path,
        tool="vscode",
        direction="read",
        project_id="project-1",
        source="ide-extension",
        evidence_path=_evidence(tmp_path, "raw/events/read.json"),
        operation_id="read-1",
    )
    record(
        tmp_path,
        tool="vscode",
        direction="write",
        project_id="project-1",
        source="ide-extension",
        evidence_path=_evidence(tmp_path, "raw/events/write.json"),
        operation_id="write-1",
    )

    # Simulate a concurrent stale aggregate writer. Per-tool receipts are the
    # append-only recovery source and must keep the proof visible.
    (tmp_path / "state" / "capability-receipts.json").write_text(
        json.dumps({"_history": {"vscode": []}}), encoding="utf-8"
    )

    read, write = latest_proof_receipts(
        tmp_path, tool="vscode", expected_project_id="project-1"
    )

    assert read is not None and read.operation_id == "read-1"
    assert write is not None and write.operation_id == "write-1"


def test_receipt_history_preserves_projects_during_repeated_updates(tmp_path: Path) -> None:
    record(tmp_path, tool="codex", direction="write", project_id="target", source="lifecycle-hook")
    for index in range(150):
        record(
            tmp_path,
            tool="codex",
            direction="write",
            project_id=f"other-{index}",
            source="watcher-observed",
        )
    receipt = _latest_receipt(
        load(tmp_path),
        "codex:write",
        "target",
        allowed_sources=NATIVE_RECEIPT_SOURCES,
    )
    assert receipt is not None
    assert receipt["project_id"] == "target"


def test_receipt_operation_id_cannot_escape_tool_receipt_directory(tmp_path: Path) -> None:
    record(
        tmp_path,
        tool="codex/../../outside",
        direction="write",
        source="explicit-smoke",
        evidence_path=_evidence(tmp_path, "smoke/write.json"),
        operation_id="../escape/operation-1",
    )

    receipt_files = tuple((tmp_path / "state" / "receipts" / "tools").rglob("*.json"))
    assert receipt_files
    assert all(path.resolve().is_relative_to((tmp_path / "state" / "receipts" / "tools").resolve()) for path in receipt_files)
    assert not (tmp_path / "state" / "receipts" / "escape" / "operation-1.json").exists()


def test_explicit_smoke_with_evidence_remains_observation_only(tmp_path: Path) -> None:
    evidence_path = _evidence(tmp_path, "smoke/read.json")

    receipt = record(
        tmp_path,
        tool="codex",
        direction="read",
        source="explicit-smoke",
        evidence_path=evidence_path,
        operation_id="smoke-read-1",
    )

    assert receipt["status"] == "observed"
    assert capability_status(
        read_receipt=receipt,
        write_receipt=None,
        expected_project_id=None,
    ) == "observed_read"
    assert latest_proof_receipts(tmp_path, tool="codex") == (None, None)
