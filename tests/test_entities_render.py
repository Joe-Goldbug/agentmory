"""Tests for the ``scripts/render_entities.py`` idempotent rewriter.

Scope Lock:
- Solves: writing ``## Official interface`` / ``## Fallback path`` /
  ``## Install command`` / ``## Current status`` sections into every
  wiki entity page; idempotent re-runs must not duplicate or wipe
  user-edited prose above the managed block.
- Does not solve: Markdown diff rendering.
- Acceptance: 4 tests, including idempotency and user-content preservation.
"""

from __future__ import annotations

from pathlib import Path

from scripts.render_entities import render_all, render_entity_page, ENTITIES
from lwm.tool_registry import default_registry


def test_render_all_writes_every_entity(tmp_path: Path) -> None:
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    written = render_all(tmp_path)
    assert {p.name for p in written} >= {f"{k}.md" for k in ENTITIES}
    assert {"opencode.md", "cursor.md", "minimax.md", "gemini-cli.md"}.issubset(
        {p.name for p in written}
    )


def test_entity_contract_covers_every_registered_tool() -> None:
    entity_key_for_tool = {"trae": "trae-solo"}
    missing = {
        entity_key_for_tool.get(definition.tool_id, definition.tool_id)
        for definition in default_registry().all()
    } - set(ENTITIES)
    assert missing == set()


def test_render_writes_required_sections(tmp_path: Path) -> None:
    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "codex.md"
    seed.write_text(
        "---\ntitle: Codex CLI\ntype: entity\n---\n\n# Codex\n",
        encoding="utf-8",
    )
    render_entity_page(tmp_path, "codex", ENTITIES["codex"])
    text = seed.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "\n---\n" in text
    assert "## Official interface" in text
    assert "## Fallback path" in text
    assert "## Install command" in text
    assert "## Current status" in text


def test_render_adds_frontmatter_to_legacy_entity_page(tmp_path: Path) -> None:
    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "codex.md"
    seed.write_text(
        "# Codex\n\n## Notes from team\n\nKeep the local bridge bounded.\n",
        encoding="utf-8",
    )

    render_entity_page(tmp_path, "codex", ENTITIES["codex"])

    text = seed.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "title: Codex CLI" in text
    assert "type: entity" in text
    assert "# Codex" in text
    assert "Keep the local bridge bounded." in text


def test_render_repairs_joined_legacy_frontmatter(tmp_path: Path) -> None:
    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "codex.md"
    seed.write_text(
        "---\n"
        "title: Codex CLI\n"
        "type: entity\n"
        "tags: [entity, tool]\n"
        "sources: [raw/tool-snapshots/codex/current/agents.md]\n"
        "updated: 2026-08-01T00:00:00+08:00\n"
        "---Codex\n\n"
        "Keep the historical body.\n",
        encoding="utf-8",
    )

    render_entity_page(tmp_path, "codex", ENTITIES["codex"])

    text = seed.read_text(encoding="utf-8")
    assert "\n---\nCodex\n\nKeep the historical body." in text
    assert "---Codex" not in text


def test_render_repairs_joined_type_and_updated_keys(tmp_path: Path) -> None:
    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "gemini-cli.md"
    seed.write_text(
        "---\n"
        "title: Gemini CLI\n"
        "type: entityupdated: 2026-08-01T00:00:00+08:00\n"
        "---placeholder\n",
        encoding="utf-8",
    )

    render_entity_page(tmp_path, "gemini-cli", ENTITIES["gemini-cli"])

    text = seed.read_text(encoding="utf-8")
    assert "type: entity\n" in text
    assert "tags: [entity, tool, gemini-cli]" in text
    assert "sources: [raw/tool-snapshots/gemini-cli/current]" in text
    assert "updated: " in text
    assert "type: entityupdated:" not in text
    assert "\n---\nplaceholder\n" in text


def test_render_is_idempotent(tmp_path: Path) -> None:
    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "codex.md"
    seed.write_text(
        "---\ntitle: Codex CLI\ntype: entity\n---\n\n# Codex\n",
        encoding="utf-8",
    )
    render_entity_page(tmp_path, "codex", ENTITIES["codex"])
    first = seed.read_text(encoding="utf-8")
    render_entity_page(tmp_path, "codex", ENTITIES["codex"])
    second = seed.read_text(encoding="utf-8")
    assert first.count("## Official interface") == 1
    # ``# heading lines`` outside the managed block must be preserved.
    assert "# Codex" in second


def test_render_preserves_user_sections(tmp_path: Path) -> None:
    """Anything outside the managed H2 sections must survive a rewrite."""

    entities_dir = tmp_path / "wiki" / "entities"
    entities_dir.mkdir(parents=True)
    seed = entities_dir / "codex.md"
    seed.write_text(
        "---\n"
        "title: Codex CLI\n"
        "type: entity\n"
        "---\n\n"
        "# Codex\n\n"
        "## Notes from team\n\n"
        "Always run lint before commit.\n",
        encoding="utf-8",
    )
    render_entity_page(tmp_path, "codex", ENTITIES["codex"])
    text = seed.read_text(encoding="utf-8")
    assert "## Notes from team" in text
    assert "Always run lint before commit." in text


def test_entity_status_does_not_claim_unverified_native_hooks() -> None:
    assert "Companion native bridge is available" in ENTITIES["kiro"]["status"]
    assert "start/stop proof is verified" in ENTITIES["kiro"]["status"]
    assert "real host receipt" in ENTITIES["kiro"]["fallback"]
    assert "public native Kiro hook" in ENTITIES["kiro"]["official"]
    assert "no native Codex hook" in ENTITIES["codex"]["status"]
    assert "Companion native bridge is available" in ENTITIES["vscode"]["status"]
    assert "start/stop proof is verified" in ENTITIES["vscode"]["status"]
    assert "MCP bridge" in ENTITIES["minimax"]["status"]
    assert "remains unverified" in ENTITIES["minimax"]["status"]
