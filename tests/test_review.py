"""Tests for source-gap provenance in the review queue."""

from pathlib import Path

from lwm.review import build_review_report, render_review_report


def test_review_preserves_missing_source_prefix_and_adds_scope(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki" / "concepts"
    wiki.mkdir(parents=True)
    external = tmp_path.parent / "historical.md"
    (wiki / "gap.md").write_text(
        f"""---
title: Gap
type: concept
tags: [concept]
sources: [raw/missing.md, {external}]
updated: 2026-08-16
---
# Gap
""",
        encoding="utf-8",
    )

    report = build_review_report(tmp_path)
    rendered = render_review_report(report)

    assert "missing-source | scope=local |" in rendered
    assert "missing-source | scope=external |" in rendered
    assert len([item for item in report.items if item.startswith("missing-source")]) == 2
