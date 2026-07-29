from __future__ import annotations

from pathlib import Path

from lwm.compile import compile_raw_sources


def test_compile_excludes_operational_event_tool_and_cbmem_snapshots(
    tmp_path: Path,
) -> None:
    (tmp_path / "wiki").mkdir()
    for rel in (
        "events/processed/2026-07-28/event.json",
        "tool-snapshots/codex/current/AGENTS.md",
        "cbmem-snapshots/current/project/index.json",
    ):
        path = tmp_path / "raw" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("operational", encoding="utf-8")

    report = compile_raw_sources(tmp_path)

    assert report.compiled == ()
    summaries = list((tmp_path / "wiki" / "summaries").glob("*.md"))
    assert summaries == []


def test_compile_prunes_old_operational_index_rows(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text(
        "## Summaries\n\n"
        "| [[source-events-old]] | Compiled from raw/events/processed/x.json | 2026-07-27 |\n"
        "| [[source-migrations-keep]] | Compiled from raw/migrations/keep.md | 2026-07-27 |\n",
        encoding="utf-8",
    )
    (tmp_path / "raw").mkdir()

    compile_raw_sources(tmp_path)

    index = (wiki / "index.md").read_text(encoding="utf-8")
    assert "source-events-old" not in index
    assert "source-migrations-keep" in index
