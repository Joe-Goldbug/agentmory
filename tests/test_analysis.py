"""Tests for wiki graph analysis."""

from pathlib import Path

from typer.testing import CliRunner

from lwm.analysis import analyze_wiki, collect_wiki_pages, render_analysis_report, write_analysis_report
from lwm.cli import app
from lwm.schema import validate_schema

runner = CliRunner()


def _build_sample_wiki(root: Path) -> Path:
    target = root / "sample"
    r = runner.invoke(app, ["init", str(target), "-d", "Sample"])
    assert r.exit_code == 0, r.output

    (target / "raw" / "source-a.md").write_text("alpha", encoding="utf-8")
    (target / "wiki" / "concepts" / "alpha.md").write_text(
        """---
title: Alpha
type: concept
tags: [concept]
sources: [raw/source-a.md]
updated: 2026-05-14
---

# Alpha

See [[beta]].
""",
        encoding="utf-8",
    )
    (target / "wiki" / "concepts" / "beta.md").write_text(
        """---
title: Beta
type: concept
tags: [concept]
sources: [raw/missing.md]
updated: 2026-05-14
---

# Beta
""",
        encoding="utf-8",
    )
    (target / "wiki" / "concepts" / "gamma.md").write_text(
        """---
title: Gamma
type: concept
tags: [concept]
sources: []
updated: 2026-05-14
---

# Gamma
""",
        encoding="utf-8",
    )
    return target


def test_analyze_finds_hubs_orphans_and_missing_sources(tmp_path: Path) -> None:
    target = _build_sample_wiki(tmp_path)
    analysis = analyze_wiki(target)
    assert any(page.endswith("gamma.md") for page in analysis.orphan_pages)
    assert any(page.endswith("beta.md") for page, _ in analysis.missing_sources)
    assert any(page.endswith("beta.md") for page, inbound, _ in analysis.hub_pages)

    report = render_analysis_report(analysis)
    assert "Broken links" in report
    assert "Missing Sources" in report
    assert "Orphans" in report


def test_analysis_classifies_local_and_external_source_gaps(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki" / "concepts"
    wiki.mkdir(parents=True)
    external = tmp_path.parent / "historical-codex.md"
    (wiki / "gaps.md").write_text(
        f"""---
title: Gaps
type: concept
tags: [concept]
sources: [raw/not-here.md, {external}]
updated: 2026-08-16
---
# Gaps
""",
        encoding="utf-8",
    )

    analysis = analyze_wiki(tmp_path)

    assert {(gap.source, gap.scope) for gap in analysis.source_gaps} == {
        ("raw/not-here.md", "local"),
        (str(external), "external"),
    }
    report = render_analysis_report(analysis)
    assert "Local missing: 1" in report
    assert "External missing: 1" in report


def test_analyze_write_report(tmp_path: Path) -> None:
    target = _build_sample_wiki(tmp_path)
    analysis = analyze_wiki(target)
    out_path = write_analysis_report(target, analysis)
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert "Knowledge Radar" in content
    assert "Wiki Analysis" in content


def test_generated_recurring_principle_is_not_a_structural_orphan(tmp_path: Path) -> None:
    target = tmp_path / "workmem"
    global_dir = target / "wiki" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "recurring-tag-migration-across-2-projects.md").write_text(
        """---
title: Recurring tag `migration` across 2 projects
type: principle
tags: [global, migration]
sources: []
updated: 2026-07-23
---

# Recurring migration tag
""",
        encoding="utf-8",
    )
    (global_dir / "manual-principle.md").write_text(
        """---
title: Manual Principle
type: principle
tags: [global]
sources: []
updated: 2026-07-23
---

# Manual Principle
""",
        encoding="utf-8",
    )

    analysis = analyze_wiki(target)

    assert "wiki/global/recurring-tag-migration-across-2-projects.md" not in analysis.orphan_pages
    assert "wiki/global/manual-principle.md" in analysis.orphan_pages


def test_analysis_excludes_archives_and_generated_radar(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    active = wiki / "concepts"
    archived = wiki / "review" / "_archive_2026-07-30-noise"
    active.mkdir(parents=True)
    archived.mkdir(parents=True)
    body = "---\ntitle: Same\ntype: concept\ntags: [concept]\nsources: []\n---\n# Same\n"
    (active / "same.md").write_text(body, encoding="utf-8")
    (archived / "same.md").write_text(body, encoding="utf-8")
    (wiki / "insights").mkdir(parents=True)
    (wiki / "insights" / "current-radar.md").write_text(
        "---\ntitle: Radar\ntype: insight\nsources: []\n---\n# Radar\n\n[[missing-old-page]]\n",
        encoding="utf-8",
    )

    analysis = analyze_wiki(tmp_path)

    assert not analysis.duplicate_slugs
    assert not any(page == "wiki/insights/current-radar.md" for page, _ in analysis.broken_links)


def test_analysis_ignores_generated_source_summaries_but_keeps_curated_summary_pages(
    tmp_path: Path,
) -> None:
    wiki = tmp_path / "wiki"
    concepts = wiki / "concepts"
    summaries = wiki / "summaries"
    concepts.mkdir(parents=True)
    summaries.mkdir(parents=True)
    page = "---\ntitle: Page\ntype: concept\ntags: [concept]\nsources: []\nupdated: 2026-08-06\n---\n# Page\n\n[[source-shell-2026-08-01]] [[lwm-cbmem-cheatsheet]]\n"
    (concepts / "page.md").write_text(page, encoding="utf-8")
    summary = "---\ntitle: lwm cbmem Cheatsheet\ntype: summary\ntags: [summary, reference]\nsources: []\nupdated: 2026-08-06\n---\n# Cheatsheet\n"
    (summaries / "source-shell-2026-08-01.md").write_text(summary, encoding="utf-8")
    (summaries / "lwm-cbmem-cheatsheet.md").write_text(summary, encoding="utf-8")

    analysis = analyze_wiki(tmp_path)

    assert not analysis.broken_links
    assert "wiki/summaries/source-shell-2026-08-01.md" not in {
        item.rel_path for item in analysis.pages
    }
    assert "wiki/summaries/lwm-cbmem-cheatsheet.md" in {
        item.rel_path for item in analysis.pages
    }


def test_analysis_parses_multiline_frontmatter_lists(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki" / "review"
    wiki.mkdir(parents=True)
    (wiki / "conflict.md").write_text(
        """---
title: Conflict Report
type: review
tags:
  - conflict
  - review
sources:
  - raw/events/processed
updated: 2026-08-16
---
# Conflict Report
""",
        encoding="utf-8",
    )

    pages = collect_wiki_pages(tmp_path)

    assert pages[0].tags == ("conflict", "review")
    assert pages[0].sources == ("raw/events/processed",)
    assert validate_schema(tmp_path).issues == ()


def test_analysis_resolves_root_relative_and_absolute_sources(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki" / "concepts"
    wiki.mkdir(parents=True)
    (tmp_path / "wiki" / "insights").mkdir()
    external = tmp_path / "external.md"
    external.write_text("source\n", encoding="utf-8")
    (wiki / "sources.md").write_text(
        f"""---
title: Sources
type: concept
tags: [concept]
sources: [wiki/insights, {external}]
updated: 2026-08-16
---
# Sources
""",
        encoding="utf-8",
    )

    analysis = analyze_wiki(tmp_path)

    assert analysis.missing_sources == ()
