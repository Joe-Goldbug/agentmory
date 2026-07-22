import json
from pathlib import Path

from lwm.capabilities import probe, record


def test_probe_distinguishes_configured_from_verified(tmp_path: Path) -> None:
    home = tmp_path / "home"
    target = home / ".codex" / "AGENTS.md"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")

    result = probe(tmp_path, home=home)
    assert result["codex"]["status"] == "configured_unverified"

    record(tmp_path, tool="codex", direction="read", source="lifecycle-hook")
    record(tmp_path, tool="codex", direction="write", source="lifecycle-hook")
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


def test_watcher_observed_lifecycle_receipts_are_eligible(tmp_path: Path) -> None:
    home = tmp_path / "home"
    target = home / "Library" / "Application Support" / "Code" / "User" / "prompts"
    target.mkdir(parents=True)
    (target / "copilot-workflow-memory.instructions.md").write_text(
        "LLM-WorkMem", encoding="utf-8"
    )
    record(tmp_path, tool="vscode", direction="read", source="watcher-observed")
    record(tmp_path, tool="vscode", direction="write", source="watcher-observed")

    assert probe(tmp_path, home=home)["vscode"]["status"] == "verified_bidirectional"


def test_probe_selects_matching_project_from_receipt_history(
    tmp_path: Path, monkeypatch
) -> None:
    home = tmp_path / "home"
    target = home / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")
    current = tmp_path / "current"
    current.mkdir()

    record(tmp_path, tool="claude-code", direction="read", project_id="other", source="native-hook")
    record(tmp_path, tool="claude-code", direction="write", project_id="other", source="native-hook")
    record(tmp_path, tool="claude-code", direction="read", project_id="current", source="native-hook")
    record(tmp_path, tool="claude-code", direction="write", project_id="current", source="native-hook")
    record(tmp_path, tool="claude-code", direction="read", project_id="current", source="cli-context")
    monkeypatch.setattr(
        "lwm.project_id.resolve_project_id",
        lambda _path: type("Resolution", (), {"project_id": "current"})(),
    )

    result = probe(tmp_path, home=home, project_path=current)

    assert result["claude-code"]["status"] == "verified_bidirectional"
