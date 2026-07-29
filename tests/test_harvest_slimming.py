"""Regression tests for bounded harvest snapshots and isolated schedules."""

from __future__ import annotations

from pathlib import Path

from lwm.dashboard import write_dashboard_html
from lwm.harvest import (
    SourceFileSpec,
    SourceGroupSpec,
    _compact_historical_harvest_pages,
    _iter_files,
    _render_group_page,
    _render_harvest_page,
    default_source_groups,
    harvest_sources,
    write_schedule_bundle,
)


def test_iter_files_skips_dependency_and_cache_trees(tmp_path: Path) -> None:
    source = tmp_path / "agents"
    useful = source / "coder" / "agent.md"
    dependency = source / "coder" / ".opencode" / "node_modules" / "pkg" / "index.js"
    cache = source / "coder" / "__pycache__" / "agent.pyc"
    useful.parent.mkdir(parents=True)
    useful.write_text("# Coder", encoding="utf-8")
    dependency.parent.mkdir(parents=True)
    dependency.write_text("large generated dependency", encoding="utf-8")
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"cache")

    captured = tuple(path.relative_to(source).as_posix() for path in _iter_files(source))

    assert captured == ("coder/agent.md",)


def test_generated_pages_summarize_large_source_sets(tmp_path: Path) -> None:
    group = SourceGroupSpec(
        key="minimax",
        title="MiniMax",
        target_page="wiki/entities/minimax.md",
        tags=("entity", "tool"),
        sources=(SourceFileSpec(tmp_path / "agents", "agents"),),
    )
    captured = tuple(
        (
            "minimax",
            "agents",
            f"raw/tool-snapshots/minimax/2026-07-23/agents/coder/file-{index:03}.md",
        )
        for index in range(100)
    )

    group_page = _render_group_page(group, "2026-07-23", group.sources, captured)
    harvest_page = _render_harvest_page(
        tmp_path,
        "2026-07-23",
        (group,),
        captured,
        (),
    )

    assert "100 snapshots" in group_page
    assert "100 snapshots" in harvest_page
    assert "file-099.md" not in group_page
    assert "file-099.md" not in harvest_page
    assert len(group_page) < 2_000
    assert len(harvest_page) < 4_000


def test_schedule_bundle_accepts_an_isolated_home(tmp_path: Path) -> None:
    root = tmp_path / "wiki"
    isolated_home = tmp_path / "home"

    bundle = write_schedule_bundle(
        root,
        label="com.ethan.lwm.isolated",
        interval_seconds=900,
        home=isolated_home,
    )

    assert bundle.runtime_root.is_relative_to(isolated_home)
    assert bundle.launch_agents_plist_path.is_relative_to(isolated_home)


def test_dashboard_prunes_pages_removed_from_the_wiki(tmp_path: Path) -> None:
    root = tmp_path / "workmem"
    wiki = root / "wiki"
    wiki.mkdir(parents=True)
    current = wiki / "current.md"
    retired = wiki / "retired.md"
    current.write_text("# Current", encoding="utf-8")
    retired.write_text("# Retired", encoding="utf-8")

    target = write_dashboard_html(root)
    pages = target.with_name("knowledge-digest.pages")
    retired_export = pages / "wiki__retired.html"
    assert retired_export.is_file()

    retired.unlink()
    write_dashboard_html(root)

    assert not retired_export.exists()
    assert (pages / "wiki__current.html").is_file()


def test_harvest_compacts_large_historical_pages_without_breaking_links(
    tmp_path: Path,
) -> None:
    insights = tmp_path / "wiki" / "insights"
    insights.mkdir(parents=True)
    old_page = insights / "tool-harvest-2026-07-22.md"
    current_page = insights / "tool-harvest-2026-07-23.md"
    old_page.write_text("# Tool Harvest\n" + ("old snapshot path\n" * 20_000), encoding="utf-8")
    current_page.write_text("# Current harvest", encoding="utf-8")

    compacted = _compact_historical_harvest_pages(
        tmp_path,
        current_stamp="2026-07-23",
    )

    assert compacted == (old_page,)
    assert old_page.is_file()
    assert old_page.stat().st_size < 2_000
    assert "raw/tool-snapshots/*/2026-07-22" in old_page.read_text(encoding="utf-8")
    assert current_page.read_text(encoding="utf-8") == "# Current harvest"


def test_default_sources_skip_full_conversation_archives() -> None:
    sources = {
        source.label
        for group in default_source_groups()
        for source in group.sources
    }

    assert "history.jsonl" not in sources
    assert "session-projects" not in sources
    assert "vscode-copilot-chat-sessions" not in sources


def test_harvest_uses_one_stable_current_page(
    tmp_path: Path, monkeypatch
) -> None:
    fake_home = tmp_path / "home"
    (fake_home / ".codex").mkdir(parents=True)
    (fake_home / ".codex" / "AGENTS.md").write_text("# Rules", encoding="utf-8")
    monkeypatch.setattr("lwm.harvest._home", lambda: fake_home)

    first = harvest_sources(tmp_path, compile_after_sync=False)
    second = harvest_sources(tmp_path, compile_after_sync=False)

    assert first.snapshot_page == tmp_path / "wiki" / "insights" / "current-harvest.md"
    assert second.snapshot_page == first.snapshot_page
    assert first.snapshot_page.is_file()
    assert not list((tmp_path / "wiki" / "insights").glob("tool-harvest-*.md"))
