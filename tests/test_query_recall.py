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
