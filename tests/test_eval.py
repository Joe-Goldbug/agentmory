from datetime import datetime
from dataclasses import replace

import lwm.eval as eval_module
from lwm.evidence import build_evidence_item
from lwm.eval import matches_expected_slug, parse_eval_suite, run_eval, run_recall_eval
from lwm.project_id import record_project


def test_eval_parser_accepts_b2_evidence_contract(tmp_path):
    suite = tmp_path / "suite.txt"
    suite.write_text("current state|slug|scheduler|git-a|partial|true\n", encoding="utf-8")
    case = parse_eval_suite(suite)[0]
    assert case.expected_fact == "scheduler"
    assert case.expected_project == "git-a"
    assert case.expected_coverage == "partial"
    assert case.expect_conflict is True


def test_eval_accepts_stable_wildcard_for_dated_page() -> None:
    assert matches_expected_slug("tool-harvest-2026-07-12", "tool-harvest-*")
    assert not matches_expected_slug("memory-governance", "tool-harvest-*")


def test_stable_page_eval_ignores_generated_unified_view(tmp_path):
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "memory-governance.md").write_text(
        "---\ntitle: Memory Governance\ntype: concept\ntags: [memory, governance]\n---\n"
        "# Memory Governance\nworkflow memory governance model\n",
        encoding="utf-8",
    )
    unified_dir = tmp_path / "wiki" / "unified"
    unified_dir.mkdir(parents=True)
    (unified_dir / "workflow-memory.md").write_text(
        "---\ntitle: Unified Workflow Memory\ntype: unified-memory\n"
        "tags: [workflow, memory, governance]\n---\n"
        "# Unified Workflow Memory\nworkflow memory governance model\n",
        encoding="utf-8",
    )
    suite = tmp_path / "suite.txt"
    suite.write_text("workflow memory governance model|memory-governance\n", encoding="utf-8")
    report = run_eval(tmp_path, suite)
    assert report.pass_count == 1


def test_recall_eval_reports_scope_and_fact_separately(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    project_id = record_project(tmp_path, project).project_id
    event_dir = tmp_path / "raw" / "events" / "processed" / "2026-07-18"
    event_dir.mkdir(parents=True)
    (event_dir / "event.json").write_text(
        '{"event_id":"event-1","timestamp":"2026-07-18T12:00:00+08:00",'
        f'"tool":"shell","project_path":"{project}","project_id":"{project_id}",'
        '"event_type":"decision","importance":"project","privacy":"sanitized",'
        '"task":"scheduler evidence","decisions":["scheduler evidence"],'
        '"verification":[]}',
        encoding="utf-8",
    )
    suite = tmp_path / "suite.txt"
    suite.write_text(
        f"scheduler|unused|scheduler|{project_id}|complete|false\n", encoding="utf-8"
    )
    report = run_recall_eval(
        tmp_path,
        suite,
        project_path=str(project),
        now=datetime.fromisoformat("2026-07-19T12:00:00+08:00"),
    )
    assert report.total == 1
    assert report.results[0].fact_match is True
    assert report.results[0].project_match is True
    assert report.results[0].coverage_match is True


def test_recall_eval_rejects_cross_project_evidence_even_when_packet_scope_matches(tmp_path, monkeypatch):
    suite = tmp_path / "suite.txt"
    suite.write_text("scheduler|unused|scheduler|project-a|complete|false\n", encoding="utf-8")
    packet = eval_module.build_recall_packet(tmp_path, "scheduler")
    other_project_item = build_evidence_item(
        {
            "fact_id": "foreign-fact",
            "project_id": "project-b",
            "statement": "scheduler",
            "source_paths": ["project-b/record.md"],
        }
    )
    monkeypatch.setattr(
        eval_module,
        "build_recall_packet",
        lambda *args, **kwargs: replace(
            packet,
            project_id="project-a",
            evidence=(other_project_item,),
            coverage="complete",
        ),
    )
    report = run_recall_eval(tmp_path, suite)
    assert report.results[0].fact_match is True
    assert report.results[0].project_match is False
    assert report.pass_count == 0
