import json

from lwm.memory_compiler import Candidate, load_candidate, save_candidate
from lwm.structured_candidates import build_relationship_candidates, build_workflow_candidates


def events():
    return [{"event_id": f"e-{i}", "event_type": "project_status", "tool": "codex",
             "project_id": f"p-{i % 2}", "task": "Observed codex turn results",
             "risks": ["Assistant report (unverified): useful project observation"],
             "open_questions": ["Task completion and claim support are unknown unless explicitly verified."],
             "tags": ["codex", "structured-summary"]} for i in range(4)]


def test_transport_metadata_and_generic_reports_do_not_create_model_jobs():
    assert build_relationship_candidates(events()) == []
    assert build_workflow_candidates(events()) == []


def test_concrete_work_remains_eligible_even_with_generic_native_title():
    rows = events()
    for row in rows:
        row.update(changes=["Validate refund replay identity"], verification=["Replay test passed"],
                   tags=["codex", "refund-idempotency"])
    assert len(build_workflow_candidates(rows)) == 1
    assert len(build_relationship_candidates(rows)) == 1


def test_retirement_preserves_sources_and_reviewed_records_and_is_idempotent(tmp_path):
    from lwm.queue_compaction import compact_analysis_queue
    for key, state in [("pending", "pending_analysis"), ("approved", "accepted")]:
        save_candidate(tmp_path, Candidate(candidate_id=key, kind="relationship",
            claim="The `codex` pattern may connect these projects", scope=("p",),
            evidence_ids=("source",), context="", uncertainty="", validity="unknown", state=state))
    raw = tmp_path / "raw/source.json"
    raw.parent.mkdir()
    raw.write_text('{"valuable": true}')
    before = raw.read_bytes()
    result = compact_analysis_queue(tmp_path)
    assert result["retired"] == ["pending"]
    assert load_candidate(tmp_path, "pending").state == "retired"
    assert load_candidate(tmp_path, "approved").state == "accepted"
    assert raw.read_bytes() == before
    assert compact_analysis_queue(tmp_path)["retired"] == []


def test_order_only_duplicate_has_one_canonical_root(tmp_path):
    from lwm.queue_compaction import compact_analysis_queue
    for key, evidence in [("a", ("e1", "e2")), ("b", ("e2", "e1"))]:
        save_candidate(tmp_path, Candidate(candidate_id=key, kind="relationship", claim="Shared retry policy",
            scope=("p",), evidence_ids=evidence, context="same", uncertainty="unknown", validity="unknown",
            state="pending_analysis"))
    result = compact_analysis_queue(tmp_path)
    assert result["retired"] == ["b"]
    mapping = json.loads((tmp_path / "state/analysis/compaction.json").read_text())
    assert mapping["retired"]["b"]["replacement_id"] == "a"
    assert load_candidate(tmp_path, "b").evidence_ids == ("e2", "e1")


def test_human_corrected_metadata_candidate_is_protected(tmp_path):
    from lwm.queue_compaction import compact_analysis_queue
    save_candidate(tmp_path, Candidate(candidate_id="human", kind="relationship",
        claim="The `codex` pattern may connect these projects", scope=("p",), evidence_ids=("e",),
        context="User correction: compare tool handoffs", uncertainty="", validity="unknown", state="pending_analysis"))
    review = tmp_path / "state/candidates/human.json"
    review.parent.mkdir(parents=True)
    review.write_text(json.dumps({"state": "corrected", "correction": "compare tool handoffs"}))
    assert compact_analysis_queue(tmp_path)["retired"] == []


def test_same_sources_with_different_questions_or_counterevidence_are_not_merged(tmp_path):
    from lwm.queue_compaction import compact_analysis_queue
    for key, claim, counters in [
        ("a", "Why did the check fail?", ()),
        ("b", "What should happen next?", ()),
        ("c", "Why did the check fail?", ("counter",)),
    ]:
        save_candidate(tmp_path, Candidate(
            candidate_id=key, kind="workflow", claim=claim, scope=("p",),
            evidence_ids=("e1", "e2"), counterevidence_ids=counters,
            context="same", uncertainty="unknown", validity="unknown",
            state="pending_analysis"))
    assert compact_analysis_queue(tmp_path)["retired"] == []
