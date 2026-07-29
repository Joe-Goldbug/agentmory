from __future__ import annotations

from pathlib import Path

from lwm.export import write_ai_exports


def _page(root: Path, rel: str, title: str, page_type: str) -> None:
    path = root / "wiki" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title}\ntype: {page_type}\ntags: [{page_type}]\n"
        "sources: []\nupdated: 2026-07-28\n---\n\n"
        f"# {title}\n\n{title} content.\n",
        encoding="utf-8",
    )


def test_compact_export_excludes_generated_noise(tmp_path: Path) -> None:
    _page(tmp_path, "purpose.md", "Purpose", "purpose")
    _page(tmp_path, "overview.md", "Overview", "overview")
    _page(tmp_path, "global/rule.md", "Rule", "principle")
    _page(tmp_path, "projects/git-demo.md", "Project", "project")
    _page(tmp_path, "insights/current-radar.md", "Radar", "insight")
    _page(tmp_path, "review/candidates-2026-07-28.md", "Candidate", "review")
    _page(tmp_path, "summaries/source-old.md", "Old Source", "summary")

    write_ai_exports(tmp_path)

    compact = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    full = (tmp_path / "llms-full.txt").read_text(encoding="utf-8")
    assert "wiki/purpose.md" in compact
    assert "wiki/projects/git-demo.md" in compact
    assert "current-radar.md" not in compact
    assert "candidates-2026-07-28.md" not in compact
    assert "source-old.md" not in compact
    assert "current-radar.md" not in full
