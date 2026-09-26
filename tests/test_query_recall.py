from datetime import date
from pathlib import Path

from lwm.query import _recall_plan, _tokenize, run_query


def _page(root: Path, name: str, body: str) -> None:
    path = root / "wiki" / "concepts" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"title: {name}\n"
        "type: concept\n"
        "tags: [workflow, memory]\n"
        "sources: [raw/source.md]\n"
        "updated: 2026-07-15\n"
        "---\n\n"
        f"# {name}\n\n{body}\n",
        encoding="utf-8",
    )


def test_tokenize_supports_chinese_queries() -> None:
    tokens = _tokenize("我的工作流记忆")
    assert "工作" in tokens
    assert "工作流" in tokens
    assert "记忆" in tokens


def test_recall_plan_adds_time_and_current_state_checks() -> None:
    plan = _recall_plan("当前项目上周什么时候完成验证？")
    assert plan.dimensions == ("semantic", "time", "current_state", "project")
    assert any("exact timestamp" in check for check in plan.checks)
    assert any("latest verified state" in check for check in plan.checks)


def test_chinese_query_returns_evidence_and_recall_plan(tmp_path: Path) -> None:
    root = tmp_path
    _page(root, "工作流记忆", "当前项目的工作流记忆必须先分析，再执行，最后验证。")

    report = run_query(root, "当前项目的工作流记忆", mode="deep")

    assert report.hits
    assert report.hits[0].page.title == "工作流记忆"
    assert report.plan is not None
    assert "current_state" in report.plan.dimensions


def test_specific_slug_beats_repeated_terms_in_synthesis_page(tmp_path: Path) -> None:
    _page(tmp_path, "tool-harvest", "Tool harvest automation workflow.")
    unified = tmp_path / "wiki" / "unified" / "workflow-memory.md"
    unified.parent.mkdir(parents=True, exist_ok=True)
    unified.write_text(
        "---\n"
        "title: Unified Workflow Memory\n"
        "type: unified-memory\n"
        "tags: [workflow, memory, unified-memory]\n"
        "updated: 2026-08-16\n"
        "---\n\n"
        "# Unified Workflow Memory\n\n"
        "tool harvest automation workflow tool harvest automation workflow\n",
        encoding="utf-8",
    )

    report = run_query(tmp_path, "tool harvest automation workflow", limit=3)

    assert report.hits[0].page.slug == "tool-harvest"


def test_old_exact_slug_beats_fresh_generic_tool_page(tmp_path: Path) -> None:
    _page(tmp_path, "tool-harvest", "Tool harvest automation workflow.")
    generic = tmp_path / "wiki" / "concepts" / "github-copilot.md"
    generic.write_text(
        "---\n"
        "title: GitHub Copilot\n"
        "type: entity\n"
        "tags: [tool, copilot, workflow]\n"
        f"updated: {date.today().isoformat()}\n"
        "---\n\n"
        "Tool harvest automation workflow. Tool harvest automation workflow.\n",
        encoding="utf-8",
    )

    report = run_query(tmp_path, "tool harvest automation workflow", limit=3)

    assert report.hits[0].page.slug == "tool-harvest"
