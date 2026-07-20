from pathlib import Path

from lwm.capabilities import probe, record


def test_probe_distinguishes_configured_from_verified(tmp_path: Path) -> None:
    home = tmp_path / "home"
    target = home / ".codex" / "AGENTS.md"
    target.parent.mkdir(parents=True)
    target.write_text("LLM-WorkMem", encoding="utf-8")

    result = probe(tmp_path, home=home)
    assert result["codex"]["status"] == "configured_unverified"

    record(tmp_path, tool="codex", direction="read", source="test")
    record(tmp_path, tool="codex", direction="write", source="test")
    assert probe(tmp_path, home=home)["codex"]["status"] == "verified_bidirectional"
