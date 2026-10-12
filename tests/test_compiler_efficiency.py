"""Offline compiler efficiency checks; all state is isolated in tmp_path."""

import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from lwm import memory_compiler as compiler


def config():
    return compiler.AnalysisConfig(
        enabled=True, base_url="http://localhost/v1", api_key="", model="offline",
        timeout_seconds=1, daily_token_budget=20_000, max_attempts=1,
    )


def candidate(**overrides):
    return replace(compiler.Candidate(
        candidate_id="root", kind="workflow", claim="Inspect scoped checks",
        scope=("p2", "p1"), evidence_ids=("b", "a"), counterevidence_ids=("c",),
        created_at="2026-10-10T00:00:00+00:00",
    ), **overrides)


def event(eid, **overrides):
    return {
        "event_id": eid, "project_id": "p1", "tool": "codex",
        "event_type": "decision", "task": "Inspect scoped checks",
        "decisions": ["Keep explicit checks"], "status": "active",
        "timestamp": "2026-10-10T00:00:00+00:00", **overrides,
    }


def test_evidence_order_reuses_actual_provider_cache(tmp_path, monkeypatch):
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=200, content=b"", json=lambda: {
            "choices": [{"message": {"content": json.dumps({"claim": "Scoped checks"})}}],
            "usage": {"total_tokens": 100},
        })

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(HTTPError=OSError, post=post))
    rows = [event("b"), event("a"), event("c")]
    first, coverage = compiler.build_analysis_request(candidate(), rows)
    second, other = compiler.build_analysis_request(
        candidate(evidence_ids=("a", "b"), scope=("p1", "p2")), list(reversed(rows)),
    )
    assert first == second and coverage == other
    assert compiler.classify_with_provider(config(), prompt=first, evidence=rows, cache_root=tmp_path)[0]
    result, reason = compiler.classify_with_provider(
        config(), prompt=second, evidence=list(reversed(rows)), cache_root=tmp_path,
    )
    assert result and reason == "cache_hit" and len(calls) == 1


@pytest.mark.parametrize("max_chars", [800, 24])
def test_exact_uncertainty_compaction_preserves_custom_questions_and_metadata(max_chars):
    default = compiler.DEFAULT_UNCERTAINTY_QUESTION
    rows = [event("a", open_questions=[default] * 20 + ["Which check failed?"],
                  counterevidence_ids=["c"], verification=["FAIL: scoped check"]),
            event("b", open_questions=default), event("c", status="failed")]
    original = json.dumps(rows, sort_keys=True)
    prompt, coverage = compiler.build_analysis_request(candidate(), rows, max_chars=max_chars)
    payload = json.loads(prompt)
    assert prompt.count(default) == 1
    a, b, c = payload["evidence"]
    assert a["open_questions"] == ["Which check failed?"]
    assert a["completion_support"] == b["completion_support"] == "unverified"
    assert a["verification"] == ["FAIL: scoped check"]
    assert a["counterevidence_ids"] == ["c"] and c["status"] == "failed"
    assert payload["candidate"]["counterevidence_ids"] == ["c"]
    assert payload["candidate"]["scope"] == ["p1", "p2"]
    assert coverage["complete"] and json.dumps(rows, sort_keys=True) == original
    # Existing validation hashes remain byte-for-byte compatible with v4.
    safe = compiler.sanitize_evidence(rows)
    legacy_hash = hashlib.sha256(json.dumps(
        sorted(safe, key=lambda row: row["event_id"]), sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()
    assert compiler._hash_evidence(safe) == legacy_hash
    assert safe[0]["open_questions"][0] == default


def test_near_match_question_is_not_replaced():
    custom = compiler.DEFAULT_UNCERTAINTY_QUESTION + " Check deployment first."
    prompt, _ = compiler.build_analysis_request(candidate(evidence_ids=("a",), counterevidence_ids=()),
                                                [event("a", open_questions=[custom])])
    row = json.loads(prompt)["evidence"][0]
    assert row["open_questions"] == [custom]
    assert "completion_support" not in row


def test_reordered_seed_keeps_analyzed_state_and_hash(tmp_path):
    saved = candidate(state="analyzed", analysis_evidence_hash="legacy-hash", analysis_inputs=("leaf",))
    compiler.save_candidate(tmp_path, saved)
    compiler.seed_candidate(tmp_path, candidate(evidence_ids=("a", "b")))
    assert compiler.load_candidate(tmp_path, "root") == saved
    compiler.seed_candidate(tmp_path, candidate(evidence_ids=("a",), counterevidence_ids=("b", "c")))
    assert compiler.load_candidate(tmp_path, "root").state == "pending_analysis"


def test_admission_estimate_labels_do_not_change_arithmetic(tmp_path):
    text = "\u4e2d\u6587"
    assert compiler.estimate_tokens(text) == len(json.dumps((text,), ensure_ascii=False).encode())
    info = compiler.analysis_usability(tmp_path, config=config(), check_provider=False)
    assert info["daily_token_budget"] == 20_000
    assert info["admission_estimate_basis"] == "serialized_utf8_bytes_not_actual_tokens"
    assert compiler.reserve_daily_budget(tmp_path, token_count=20_000, budget=20_000)
    assert not compiler.reserve_daily_budget(tmp_path, token_count=1, budget=20_000)


def test_priority_ages_roots_and_prefers_complete_useful_small_tasks():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    events = {eid: event(eid) for eid in ("a", "b", "c")}
    fresh = candidate(candidate_id="small", evidence_ids=("a",), counterevidence_ids=())
    large = candidate(candidate_id="large", context="x" * 20_000)
    missing = replace(fresh, candidate_id="missing", evidence_ids=("absent",))
    old = replace(large, candidate_id="old", created_at="2026-10-01T00:00:00+00:00")
    oldest = replace(large, candidate_id="oldest", created_at="2026-09-01T00:00:00+00:00")
    decision = replace(fresh, candidate_id="decision", kind="summary")
    def key(item):
        return compiler._pending_priority(item, events, config(), now)
    assert key(oldest) < key(old) < key(fresh) < key(large)
    assert key(decision) < key(missing)
    assert key(fresh) < key(candidate())
    assert key(replace(fresh, created_at="invalid"))[0] == 1


def test_pending_dispatch_order_and_coverage_remain_complete(tmp_path, monkeypatch):
    rows = [event(eid) for eid in ("a", "b", "c")]
    base = tmp_path / "raw/events/processed"
    base.mkdir(parents=True)
    for row in rows:
        (base / f"{row['event_id']}.json").write_text(json.dumps(row))
    compiler.save_candidate(tmp_path, candidate(candidate_id="larger"))
    compiler.save_candidate(tmp_path, candidate(candidate_id="small", evidence_ids=("a",), counterevidence_ids=()))
    calls = []

    def provider(cfg, **kwargs):
        calls.append(json.loads(kwargs["prompt"]))
        return {"claim": "Scoped checks"}, ""

    monkeypatch.setattr(compiler, "classify_with_provider", provider)
    report = compiler.analyze_pending(tmp_path, config=config(), now=datetime(2026, 10, 11, tzinfo=timezone.utc))
    assert report["analyzed"] == ["small", "larger"]
    assert calls[1]["candidate"]["counterevidence_ids"] == ["c"]
    assert calls[1]["candidate"]["scope"] == ["p1", "p2"]
    assert report["coverage"]["larger"]["delivered_ids"] == ["a", "b", "c"]
    assert report["coverage"]["larger"]["admission_estimate_basis"] == compiler.ADMISSION_ESTIMATE_BASIS
