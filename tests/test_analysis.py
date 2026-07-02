"""Tests for wiki graph analysis."""

from pathlib import Path

from typer.testing import CliRunner

from lwm.analysis import analyze_wiki, render_analysis_report, write_analysis_report
from lwm.cli import app

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


def test_analyze_write_report(tmp_path: Path) -> None:
    target = _build_sample_wiki(tmp_path)
    analysis = analyze_wiki(target)
    out_path = write_analysis_report(target, analysis)
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert "Knowledge Radar" in content
    assert "Wiki Analysis" in content
