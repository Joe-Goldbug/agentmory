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


def test_render_all_writes_every_entity(tmp_path: Path) -> None:
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    written = render_all(tmp_path)
    assert {p.name for p in written} >= {f"{k}.md" for k in ENTITIES}


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
    assert "## Official interface" in text
    assert "## Fallback path" in text
    assert "## Install command" in text
    assert "## Current status" in text


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
