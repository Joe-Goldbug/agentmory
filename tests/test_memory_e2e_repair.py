"""F14 isolated product acceptance, never a suite against a user's live wiki.

Real deterministic ingest/context/review/federation/export APIs, no models or
host sessions. Passing these checks does not prove actual IDE delivery,
production memory correctness, or scheduling.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lwm import context, hub_service, ingest
from lwm.eval import packaged_eval_suite, parse_eval_suite, run_eval, run_recall_eval
from lwm.export import write_ai_exports
from lwm.memory_compiler import Candidate, save_candidate
from lwm.memory_federation import compile_federated_memory, load_published_memory
from lwm.project_memory import append_event, rebuild_project_pages


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "hub"
    root.mkdir()
    (root / "GLOBAL.md").write_text(
        "# Canonical behavior\nHuman approval is required before publication.\n",
        encoding="utf-8",
    )
    projects = [tmp_path / "Photodos", tmp_path / "OtherProduct"]
    for project in projects:
        project.mkdir()
    return root, projects[0], projects[1]


def _record(root, project, event_id, **overrides):
    return hub_service.retain_event(
        root,
        {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "codex",
            "project_path": str(project),
            "event_type": "bugfix",
            "task": "Photodos mobile touch repair",
            "changes": [f"Change {i}: " + "bounded rendering detail " * 12 for i in range(5)],
            "verification": [
                "Node.js syntax check passed across all HTML files",
                "SHA-256 hash match confirmed across 5 files",
                "git push origin main succeeded",
            ],
            "risks": ["Real-device touch behavior remains unverified"],
            "session_id": "same-session",
            **overrides,
        },
    )


def _read(root, project, tool="opencode"):
    # This composes the actual Context payload, not a simulated IDE delivery.
    return context.build(root, tool=tool, project_path=str(project))


def test_accepted_meaningful_work_is_shared_and_other_project_is_isolated(workspace):
    root, project, other = workspace
    first = _record(root, project, "touch-repair")
    second = _record(
        root,
        project,
        "touch-decision",
        tool="opencode",
        event_type="decision",
        task="Photodos calm mode decision",
        changes=[],
        decisions=["Keep calm mode separate from hard mode"],
    )
    foreign = _record(
        root,
        other,
        "other-work",
        task="OTHER-PROJECT-ONLY deployment",
        changes=["OTHER-PROJECT-ONLY deployment change"],
    )
    report = ingest.run(root)
    assert set(report.processed) == {"touch-repair", "touch-decision", "other-work"}
    assert not report.failed and not report.rejected
    project_id = first["event"]["project_id"]
    other_id = foreign["event"]["project_id"]
    assert project_id != other_id
    save_candidate(
        root,
        Candidate(
            candidate_id="accepted-touch",
            kind="summary",
            claim="Photodos touch repair verified",
            scope=(project_id,),
            evidence_ids=(first["event_id"], second["event_id"]),
            state="analyzed",
        ),
    )
    save_candidate(
        root,
        Candidate(
            candidate_id="foreign-finding",
            kind="summary",
            claim="OTHER-PROJECT-ONLY finding",
            scope=(other_id,),
            evidence_ids=(foreign["event_id"],),
            state="analyzed",
        ),
    )
    before = _read(root, project)
    assert before.data["accepted_analysis_candidates"] == []
    for candidate_id in ("accepted-touch", "foreign-finding"):
        hub_service.review_analysis(root, candidate_id, decision="accept", actor="human-test")

    for tool in ("opencode", "codex"):
        shared = _read(root, project, tool)
        assert shared.project_id == project_id
        assert [row["candidate_id"] for row in shared.data["accepted_analysis_candidates"]] == [
            "accepted-touch"
        ]
        assert "Keep calm mode separate from hard mode" in shared.markdown
        assert "Photodos touch repair verified" in shared.markdown
        for verification in first["event"]["verification"]:
            assert verification in " ".join(shared.data["project"]["verifications"])
        assert "Real-device touch behavior remains unverified" in shared.markdown
        assert "touch-repair" in shared.markdown
        assert "raw/events/processed/" in shared.markdown
        assert "OTHER-PROJECT-ONLY" not in shared.markdown
        assert all(row["project_id"] == project_id for row in shared.data["recent_activity"])
    other_context = _read(root, other)
    assert "OTHER-PROJECT-ONLY finding" in other_context.markdown
    assert "Photodos touch repair verified" not in other_context.markdown
    # A later round in the same session must remain distinct from replay.
    page = root / "wiki/projects" / f"{project_id}.md"
    original = page.read_bytes()
    append_event(root, first["event"])
    assert page.read_bytes() == original
    rebuild_project_pages(root)
    assert page.read_bytes() == original
    exports = write_ai_exports(root)
    output = exports.llms_full_txt.read_text(encoding="utf-8")
    for verification in first["event"]["verification"]:
        assert verification in output
    manifest = json.loads(exports.llms_json.read_text(encoding="utf-8"))
    assert any(row["slug"] == project_id for row in manifest["pages"])


def test_privacy_and_bad_file_do_not_publish_or_hide_valid_work(workspace):
    root, project, _ = workspace
    good = _record(root, project, "good-work")
    secret = "sk-" + "X" * 32
    _record(root, project, "private-work", task="PRIVATE-ONLY configuration " + secret)
    _record(
        root,
        project,
        "lifecycle",
        event_type="session_start",
        task="(no task)",
        changes=[],
        verification=[],
        risks=[],
    )
    inbox = Path(good["absolute_path"]).parent
    broken = inbox / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    result = ingest.run(root)
    assert "good-work" in result.processed
    reasons = dict(result.rejected)
    assert reasons["private-work"] == "privacy"
    assert reasons["broken"] == "invalid-json"
    assert not result.failed
    rejected = list((root / "raw/events/rejected").rglob("broken.json"))
    assert len(rejected) == 1
    assert (
        rejected[0].with_suffix(".json.reason").read_text(encoding="utf-8").strip()
        == "invalid-json"
    )
    shared = _read(root, project)
    assert "PRIVATE-ONLY" not in shared.markdown
    assert secret not in shared.markdown
    assert shared.data["project"]["status"] == ["(no status yet)"]
    output = write_ai_exports(root).llms_full_txt.read_text(encoding="utf-8")
    assert "PRIVATE-ONLY" not in output and secret not in output
    assert "Node.js syntax check passed across all HTML files" in output


def _snapshot(root, tool, statement):
    path = root / "raw/tool-snapshots" / tool / "current/agents.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    path.write_text(
        f"---\nscope: global\nupdated: {today}\n---\n# Global workflow\n- {statement}\n",
        encoding="utf-8",
    )
    return path


def test_latest_native_rule_retires_old_rule_in_actual_publication_and_context(workspace):
    root, project, _ = workspace
    old = "Workflow: retain the legacy workflow rule"
    new = "Workflow: retain only the latest source-backed workflow rule"
    path = _snapshot(root, "opencode", old)
    first = compile_federated_memory(root)
    old_claims = load_published_memory(root)["claims"]
    assert any(row["statement"] == old for row in old_claims)
    _snapshot(root, "opencode", new)
    second = compile_federated_memory(root)
    published = load_published_memory(root)
    assert second["release_id"] != first["release_id"]
    assert published["release_id"] == second["release_id"]
    assert [row["statement"] for row in published["claims"]] == [new]
    assert published["claims"][0]["source_path"] == str(path)
    shared = _read(root, project, "codex")
    assert new in shared.markdown and old not in shared.markdown
    page = (root / "wiki/unified/workflow-memory.md").read_text(encoding="utf-8")
    assert new in page and old not in page and second["release_id"] in page
    exports = write_ai_exports(root)
    output = exports.llms_full_txt.read_text(encoding="utf-8")
    assert new in output and old not in output
    pointer = json.loads((root / "state/federation/release.json").read_text(encoding="utf-8"))
    release = json.loads((root / pointer["path"]).read_text(encoding="utf-8"))
    assert any(row["statement"] == old and row["status"] == "archived" for row in release["claims"])


def test_native_conflict_is_visible_but_cannot_replace_canonical_behavior(workspace):
    root, project, _ = workspace
    canonical = (root / "GLOBAL.md").read_bytes()
    left = "Model choice: use MiniMax for local speed"
    right = "Model choice: use OpenAI for local speed"
    _snapshot(root, "opencode", left)
    _snapshot(root, "codex", right)
    compile_federated_memory(root)
    published = load_published_memory(root)
    assert published["claims"] == []
    assert {row["statement"] for row in published["conflicts"]} == {left, right}
    shared = _read(root, project)
    assert shared.data["unified_memory"]["claims"] == []
    assert left in shared.markdown and right in shared.markdown
    assert shared.data["behavior_contract"]["sha256"] == hashlib.sha256(canonical).hexdigest()
    assert (root / "GLOBAL.md").read_bytes() == canonical
    publication = (root / "wiki/unified/workflow-memory.md").read_text(encoding="utf-8")
    assert left not in publication and right not in publication
    conflict_page = (root / "wiki/unified/conflicts.md").read_text(encoding="utf-8")
    assert left in conflict_page and right in conflict_page


def test_source_backed_eval_checks_real_verification_and_isolation(workspace):
    root, project, other = workspace
    retained = _record(root, project, "photodos-check")
    _record(
        root,
        other,
        "other-check",
        task="OTHER-PROJECT-ONLY verification",
        changes=["OTHER-PROJECT-ONLY change"],
    )
    assert not ingest.run(root).failed
    project_id = retained["event"]["project_id"]
    suite = root / "acceptance.txt"
    row = (
        f"Photodos|unused|Photodos mobile touch repair|{project_id}|complete|false|"
        "raw/events/processed/*/photodos-check.json|OTHER-PROJECT-ONLY|"
        "SHA-256 hash match confirmed across 5 files\n"
    )
    suite.write_text(row, encoding="utf-8")
    result = run_recall_eval(root, suite, project_path=str(project))
    assert result.total == result.pass_count == 1
    # A missing actual verification must fail even though the fact matches.
    suite.write_text(
        row.replace(
            "SHA-256 hash match confirmed across 5 files", "real-device touch validation passed"
        ),
        encoding="utf-8",
    )
    failed = run_recall_eval(root, suite, project_path=str(project))
    assert failed.results[0].fact_match is True
    assert failed.results[0].verification_match is False
    assert failed.pass_count == 0


def test_live_suite_never_requires_private_product_fixtures_in_empty_wiki(tmp_path):
    cases = parse_eval_suite(packaged_eval_suite())
    assert len(cases) == 2
    assert all(case.expected_project is None and case.expected_fact is None for case in cases)
    report = run_eval(tmp_path, packaged_eval_suite())
    assert report.total == 2
    assert report.pass_count == 0  # Honest no-hit smoke result, not a product failure.
    assert not (tmp_path / "state").exists()
