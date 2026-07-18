from datetime import datetime

from lwm.eval import matches_expected_slug, parse_eval_suite, run_recall_eval
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
