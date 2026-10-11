"""Offline bounded map/reduce regressions; HTTP is replaced before dispatch."""

import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from lwm import memory_compiler as compiler


def config(**overrides):
    return replace(
        compiler.AnalysisConfig(
            enabled=True, base_url="http://localhost/v1", api_key="", model="offline",
            timeout_seconds=1, daily_token_budget=20_000, max_attempts=1,
            request_token_budget=16_000,
        ),
        **overrides,
    )


def seed(root, count=160):
    events = [
        {
            "event_id": f"source-{i:04d}", "project_id": f"project-{i % 2}",
            "tool": "codex", "event_type": "decision", "task": "Check scoped refresh",
            "decisions": ["Inspect the refresh state"],
            "verification": ["PASS: scoped refresh", "FAIL: stale refresh persists"],
            "risks": ["Counterexample: stale refresh"],
        }
        for i in range(count)
    ]
    base = root / "raw/events/processed"
    base.mkdir(parents=True)
    for event in events:
        (base / f"{event['event_id']}.json").write_text(json.dumps(event))
    candidate = compiler.Candidate(
        candidate_id="large-parent", kind="workflow", claim="Scoped refresh observations",
        scope=("project-0", "project-1"),
        evidence_ids=tuple(event["event_id"] for event in events[:-1]),
        counterevidence_ids=(events[-1]["event_id"],),
    )
    compiler.save_candidate(root, candidate)
    return candidate, events


def provider(monkeypatch, calls, *, fail_leaf=False, reclassify=False):
    def post(url, **kwargs):
        request = json.loads(kwargs["json"]["messages"][1]["content"])
        calls.append(request)
        assert compiler.estimate_tokens(
            kwargs["json"]["messages"][1]["content"]
        ) + compiler.OUTPUT_TOKEN_ALLOWANCE <= 16_000
        is_merge = request.get("stage") == "merge"
        if fail_leaf and not is_merge:
            return SimpleNamespace(status_code=500)
        candidate = request["candidate"]
        support = list(candidate["evidence_ids"])
        counter = list(candidate["counterevidence_ids"])
        if reclassify and not is_merge and len(support) > 1:
            counter.append(support.pop())
        result = {
            "claim": "Merged scoped refresh" if is_merge else "Mapped scoped refresh",
            "context": "Inspect state; PASS check plus FAIL stale refresh persists.",
            "uncertainty": "Counterexample: stale refresh; limited to supplied projects.",
            "evidence_ids": support, "counterevidence_ids": counter,
        }
        return SimpleNamespace(
            status_code=200, content=b"",
            json=lambda: {"choices": [{"message": {"content": json.dumps(result)}}]},
        )
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(HTTPError=OSError, post=post))


def next_day(root):
    path = root / compiler.USAGE_PATH
    if path.exists():
        usage = json.loads(path.read_text())
        usage["date"] = "2000-01-01"
        path.write_text(json.dumps(usage))


def finish(root, cfg, rounds=100):
    reports = []
    for _ in range(rounds):
        report = compiler.analyze_pending(root, config=cfg)
        reports.append(report)
        assert (root / compiler.USAGE_PATH).exists(), "No bounded analysis work was dispatched"
        usage = json.loads((root / compiler.USAGE_PATH).read_text())
        assert usage["used_tokens"] <= cfg.daily_token_budget
        if compiler.load_candidate(root, "large-parent").state == "analyzed":
            return reports
        assert report["coverage"]["large-parent"]["complete"] is False
        next_day(root)
    pytest.fail("Large candidate did not make bounded progress to a real merge")


def test_oversized_collection_progresses_and_really_merges_all_sources(tmp_path, monkeypatch):
    original, events = seed(tmp_path)
    prompt, _ = compiler.build_analysis_request(original, events, max_chars=24)
    assert compiler.estimate_tokens(prompt) + 1200 > 16_000
    calls = []
    provider(monkeypatch, calls, reclassify=True)
    reports = finish(tmp_path, config())
    result = compiler.load_candidate(tmp_path, original.candidate_id)
    assert result.claim == "Merged scoped refresh"
    assert result.scope == original.scope
    assert set(result.evidence_ids) | set(result.counterevidence_ids) == {
        event["event_id"] for event in events
    }
    assert set(original.counterevidence_ids) <= set(result.counterevidence_ids)
    assert len(result.counterevidence_ids) > 1
    assert not set(result.evidence_ids) & set(result.counterevidence_ids)
    maps = [call for call in calls if call.get("stage") != "merge"]
    merges = [call for call in calls if call.get("stage") == "merge"]
    assert len(maps) > 2 and len(merges) > 1
    assert all(len(call["evidence"]) <= 2 for call in merges)
    assert all("FAIL: stale refresh persists" in str(call) for call in maps)
    assert all("Counterexample: stale refresh" in str(call) for call in merges)
    assert reports[-1]["coverage"][original.candidate_id]["complete"] is True
    suggestions = compiler.load_analysis_suggestions(tmp_path)
    assert any(row["candidate_id"] == original.candidate_id for row in suggestions)
    assert all(row["status"] == "inferred" and row["approval"] == "unapproved"
               for row in suggestions)
    assert compiler.load_accepted_analysis_candidates(tmp_path) == []
    assert not (tmp_path / "wiki/global").exists()


def test_batches_resume_without_resending_completed_sources(tmp_path, monkeypatch):
    seed(tmp_path)
    calls = []
    provider(monkeypatch, calls)
    first = compiler.analyze_pending(tmp_path, config=config())
    assert first["analyzed"]
    assert compiler.load_candidate(tmp_path, "large-parent").state == "pending_analysis"
    nodes = sorted((tmp_path / compiler.ANALYSIS_DIR).glob("*.json"))
    completed = {path.stem: path.read_bytes() for path in nodes
                 if compiler.load_candidate(tmp_path, path.stem).state == "analyzed"}
    sent = len(calls)
    compiler.analyze_pending(tmp_path, config=config())
    assert len(calls) == sent
    assert all((tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes() == data
               for cid, data in completed.items())
    next_day(tmp_path)
    finish(tmp_path, config())
    maps = [call for call in calls if call.get("stage") != "merge"]
    assert len({json.dumps(call, sort_keys=True) for call in maps}) == len(maps)


def test_cache_can_restore_a_batch_even_when_daily_budget_is_exhausted(tmp_path, monkeypatch):
    seed(tmp_path)
    calls = []
    provider(monkeypatch, calls)
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["analyzed"]
    cid = report["analyzed"][0]
    child = compiler.load_candidate(tmp_path, cid)
    seed_fields = calls[0]["candidate"]
    compiler.save_candidate(tmp_path, compiler.Candidate.from_dict({
        **child.to_dict(), **seed_fields, "state": "pending_analysis",
    }))
    usage = json.loads((tmp_path / compiler.USAGE_PATH).read_text())
    usage["used_tokens"] = 20_000
    (tmp_path / compiler.USAGE_PATH).write_text(json.dumps(usage))
    sent = len(calls)
    compiler.analyze_pending(tmp_path, config=config())
    assert compiler.load_candidate(tmp_path, cid).state == "analyzed"
    assert len(calls) == sent
    assert json.loads((tmp_path / compiler.USAGE_PATH).read_text())["used_tokens"] == 20_000


@pytest.mark.parametrize("gap", ["missing", "withdrawn", "operational"])
def test_missing_or_inadmissible_source_cannot_complete_parent(tmp_path, monkeypatch, gap):
    original, _ = seed(tmp_path)
    calls = []
    provider(monkeypatch, calls)
    compiler.analyze_pending(tmp_path, config=config())
    path = tmp_path / "raw/events/processed" / f"{original.counterevidence_ids[0]}.json"
    if gap == "missing":
        path.unlink()
    else:
        event = json.loads(path.read_text())
        event.update({"status": "withdrawn"} if gap == "withdrawn"
                     else {"event_type": "session_start"})
        path.write_text(json.dumps(event))
    next_day(tmp_path)
    report = compiler.analyze_pending(tmp_path, config=config())
    assert compiler.load_candidate(tmp_path, original.candidate_id).state == "pending_analysis"
    coverage = report["coverage"][original.candidate_id]
    assert coverage["complete"] is False and coverage["delivered_ids"] == []
    assert coverage["missing_ids"] == list(original.counterevidence_ids)
    assert not any(call.get("stage") == "merge" for call in calls)


def test_failed_batch_is_not_a_complete_synthesis(tmp_path, monkeypatch):
    seed(tmp_path)
    calls = []
    provider(monkeypatch, calls, fail_leaf=True)
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["dead_letter"]
    assert compiler.load_candidate(tmp_path, "large-parent").state == "dead_letter"
    assert report["coverage"]["large-parent"]["complete"] is False
    assert report["coverage"]["large-parent"]["reason"] == "analysis_dependency_failed"
    next_day(tmp_path)
    compiler.analyze_pending(tmp_path, config=config())
    assert not any(call.get("stage") == "merge" for call in calls)


def test_unsplittable_envelope_reports_error_without_dispatch(tmp_path, monkeypatch):
    seed(tmp_path, count=2)
    monkeypatch.setattr(compiler, "classify_with_provider",
                        lambda *a, **k: pytest.fail("unbounded dispatch"))
    report = compiler.analyze_pending(tmp_path, config=config(request_token_budget=1300))
    assert report["errors"]
    assert report["coverage"]["large-parent"]["complete"] is False
    assert not (tmp_path / compiler.USAGE_PATH).exists()


def leaves(root, plan):
    return {cid: compiler.load_candidate(root, cid) for cid in plan
            if not compiler.load_candidate(root, cid).analysis_inputs}


def test_new_id_before_old_sort_order_reuses_pending_and_analyzed_leaves(tmp_path, monkeypatch):
    original, events = seed(tmp_path)
    calls = []
    provider(monkeypatch, calls)
    compiler.analyze_pending(tmp_path, config=config())
    old_plan = compiler._analysis_batch_plan(tmp_path, original, events, config())
    old_leaves = leaves(tmp_path, old_plan)
    assert {leaf.state for leaf in old_leaves.values()} == {"analyzed", "pending_analysis"}
    completed_ids = {eid for leaf in old_leaves.values() if leaf.state == "analyzed"
                     for eid in (*leaf.evidence_ids, *leaf.counterevidence_ids)}
    snapshots = {cid: (tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes()
                 for cid in old_leaves}
    added = {**events[0], "event_id": "000-new-uuid"}
    (tmp_path / "raw/events/processed/000-new-uuid.json").write_text(json.dumps(added))
    grown = replace(original, evidence_ids=(added["event_id"], *original.evidence_ids))
    compiler.seed_candidate(tmp_path, grown)
    new_plan = compiler._analysis_batch_plan(tmp_path, grown, [added, *events], config())
    new_leaves = leaves(tmp_path, new_plan)
    assert set(old_leaves) <= set(new_leaves)
    assert len(new_leaves) == len(old_leaves) + 1
    assert all((tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes() == data
               for cid, data in snapshots.items())
    sent = len(calls)
    next_day(tmp_path)
    finish(tmp_path, config())
    assert all(not completed_ids.intersection(row["event_id"] for row in call["evidence"])
               for call in calls[sent:] if call.get("stage") != "merge")


@pytest.mark.parametrize("change", ["full_hash", "withdrawn", "counter_partition",
                                    "kind", "claim", "context"])
def test_leaf_reuse_requires_current_sources_and_matching_seed(tmp_path, change):
    original, events = seed(tmp_path)
    events[0]["decisions"] = ["unchanged prefix " * 100 + "old tail"]
    old_plan = compiler._analysis_batch_plan(tmp_path, original, events, config())
    old_leaves = leaves(tmp_path, old_plan)
    changed_id = events[0]["event_id"]
    affected = {cid for cid, leaf in old_leaves.items() if changed_id in leaf.evidence_ids}
    if change == "full_hash":
        events[0] = {**events[0], "decisions": ["unchanged prefix " * 100 + "new tail"]}
    elif change == "withdrawn":
        events[0] = {**events[0], "status": "withdrawn"}
    elif change == "counter_partition":
        original = replace(original, evidence_ids=original.evidence_ids[1:],
                           counterevidence_ids=(*original.counterevidence_ids, changed_id))
    else:
        original = replace(original, **{change: "relationship" if change == "kind"
                                      else "Changed semantic seed"})
    new_plan = compiler._analysis_batch_plan(tmp_path, original, events, config())
    assert affected.isdisjoint(leaves(tmp_path, new_plan))
    if change in {"kind", "claim", "context"}:
        assert set(old_leaves).isdisjoint(leaves(tmp_path, new_plan))


@pytest.mark.parametrize("used", [8000, 19999])
def test_codex_reserves_request_estimate_not_global_ceiling(tmp_path, monkeypatch, used):
    original, _ = seed(tmp_path, count=2)
    cfg = config(provider="codex_cli", command="/usr/bin/codex")
    compiler.reserve_daily_budget(tmp_path, token_count=used, budget=20_000)
    calls = []

    def classify(config, *, prompt, cache_root, reserved_tokens):
        calls.append(reserved_tokens)
        request = json.loads(prompt)["candidate"]
        return {**request, "claim": "Bounded observation"}, ""

    monkeypatch.setattr(compiler, "classify_with_codex_cli", classify)
    report = compiler.analyze_pending(tmp_path, config=cfg)
    coverage = report["coverage"][original.candidate_id]
    usage = json.loads((tmp_path / compiler.USAGE_PATH).read_text())
    if used == 8000:
        assert report["analyzed"] == [original.candidate_id]
        assert calls == [coverage["estimated_tokens"]]
        assert calls[0] < 12000 < cfg.request_token_budget
        assert usage["used_tokens"] == used + calls[0]
    else:
        assert not calls and usage["used_tokens"] == used
        assert coverage["reason"] == "daily_budget_exceeded"
    assert report["usability"]["hard_provider_token_cap"] is False
    assert report["usability"]["budget_policy"] == "reserve_input_estimate_and_output_allowance"


def test_lower_budget_repartitions_pending_leaves_and_finishes(tmp_path, monkeypatch):
    original, events = seed(tmp_path)
    calls = []
    provider(monkeypatch, calls, reclassify=True)
    compiler.analyze_pending(tmp_path, config=config())
    old_plan = compiler._analysis_batch_plan(
        tmp_path, compiler.load_candidate(tmp_path, original.candidate_id), events, config()
    )
    old_leaves = leaves(tmp_path, old_plan)
    completed = {cid: (tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes()
                 for cid, leaf in old_leaves.items() if leaf.state == "analyzed"}
    assert completed
    small = config(request_token_budget=5000)
    incompatible = set()
    for cid, leaf in old_leaves.items():
        if leaf.state != "pending_analysis":
            continue
        ids = set(leaf.evidence_ids) | set(leaf.counterevidence_ids)
        prompt, _ = compiler._bounded_analysis_request(
            leaf, [event for event in events if event["event_id"] in ids], small
        )
        if compiler.estimate_tokens(prompt) + 1200 > small.request_token_budget:
            incompatible.add(cid)
    assert incompatible
    new_plan = compiler._analysis_batch_plan(
        tmp_path, compiler.load_candidate(tmp_path, original.candidate_id), events, small
    )
    assert incompatible.isdisjoint(new_plan)
    assert set(completed) <= set(new_plan)
    assert all((tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes() == snapshot
               for cid, snapshot in completed.items())
    sent = len(calls)
    next_day(tmp_path)
    finish(tmp_path, small)
    result = compiler.load_candidate(tmp_path, original.candidate_id)
    assert set(result.evidence_ids) | set(result.counterevidence_ids) == {
        event["event_id"] for event in events
    }
    assert set(original.counterevidence_ids) <= set(result.counterevidence_ids)
    completed_ids = {eid for cid in completed for eid in (
        *old_leaves[cid].evidence_ids, *old_leaves[cid].counterevidence_ids
    )}
    assert all(not completed_ids.intersection(row["event_id"] for row in call["evidence"])
               for call in calls[sent:] if call.get("stage") != "merge")


def reachable_candidates(root):
    candidates = {path.stem: compiler.load_candidate(root, path.stem)
                  for path in (root / compiler.ANALYSIS_DIR).glob("*.json")}
    todo = [cid for cid, item in candidates.items() if item.state != "retired" and (
        not item.analysis_parent_id or item.state not in {"pending_analysis", "retry_wait"}
    )]
    reachable = set()
    while todo:
        cid = todo.pop()
        if cid in reachable:
            continue
        reachable.add(cid)
        if cid in candidates:
            todo.extend(candidates[cid].analysis_inputs)
    return candidates, reachable


def test_replanning_retires_only_unreachable_unprocessed_reducers(tmp_path):
    original, events = seed(tmp_path)
    compiler._analysis_batch_plan(tmp_path, original, events, config())
    candidates, _ = reachable_candidates(tmp_path)
    old_reducers = [item for item in candidates.values() if item.analysis_inputs
                    and item.analysis_parent_id]
    assert len(old_reducers) >= 2
    protected = replace(old_reducers[0], state="analyzed")
    compiler.save_candidate(tmp_path, protected)
    human = replace(old_reducers[1], candidate_id="human-accepted", state="accepted")
    compiler.save_candidate(tmp_path, human)
    protected_snapshots = {item.candidate_id: (tmp_path / compiler.ANALYSIS_DIR /
                           f"{item.candidate_id}.json").read_bytes()
                           for item in [protected, human]}
    raw_snapshots = {path: path.read_bytes() for path in
                     (tmp_path / "raw/events/processed").glob("*.json")}
    receipt = tmp_path / "state/receipts/keep.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("keep receipt")
    current = compiler.load_candidate(tmp_path, original.candidate_id)
    for i in range(8):
        added = {**events[0], "event_id": f"000-added-{i}"}
        events = [added, *events]
        current = replace(current, evidence_ids=(added["event_id"], *current.evidence_ids))
        compiler._analysis_batch_plan(tmp_path, current, events, config())
        current = compiler.load_candidate(tmp_path, original.candidate_id)
        candidates, reachable = reachable_candidates(tmp_path)
        assert not [item for cid, item in candidates.items() if cid not in reachable
                    and item.analysis_inputs and item.analysis_parent_id
                    and item.state in {"pending_analysis", "retry_wait"}]
    assert all((tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes() == snapshot
               for cid, snapshot in protected_snapshots.items())
    assert all(path.read_bytes() == snapshot for path, snapshot in raw_snapshots.items())
    assert receipt.read_text() == "keep receipt"
    transitions = [json.loads(line) for path in (tmp_path / compiler.TRANSITIONS_DIR).glob("*.jsonl")
                   for line in path.read_text().splitlines()]
    assert any(row["to"] == "retired" for row in transitions)
    last_transition = {row["candidate_id"]: row["to"] for row in transitions}
    for row in transitions:
        if row["to"] == "retired":
            path = tmp_path / compiler.ANALYSIS_DIR / f"{row['candidate_id']}.json"
            assert path.is_file()
            assert compiler.load_candidate(tmp_path, row["candidate_id"]).state == last_transition[
                row["candidate_id"]
            ]
    assert any(item.state == "retired" for item in candidates.values())


def test_retired_reducer_can_rejoin_identical_current_plan(tmp_path, monkeypatch):
    original, events = seed(tmp_path)
    old_plan = compiler._analysis_batch_plan(tmp_path, original, events, config())
    grown = original
    expanded = list(events)
    for i in range(2):
        added = {**events[0], "event_id": f"000-added-{i}"}
        grown = replace(grown, evidence_ids=(added["event_id"], *grown.evidence_ids))
        expanded.insert(0, added)
        compiler._analysis_batch_plan(tmp_path, grown, expanded, config())
    retired = {cid for cid in old_plan
               if (item := compiler.load_candidate(tmp_path, cid)) and item.state == "retired"}
    assert retired
    restored = compiler._analysis_batch_plan(tmp_path, original, events, config())
    assert retired <= set(restored)
    assert all(compiler.load_candidate(tmp_path, cid).state == "pending_analysis" for cid in retired)
    calls = []
    provider(monkeypatch, calls, reclassify=True)
    finish(tmp_path, config())
    assert compiler.load_candidate(tmp_path, original.candidate_id).state == "analyzed"


def ready_merge(root, *, long_child=False, huge_scope=False):
    parent, events = seed(root, count=2)
    scope = ("project-0", "project-1") if not huge_scope else tuple(
        f"project-{i:04d}" for i in range(1000)
    )
    children = []
    for i, event in enumerate(events):
        child = replace(
            parent, candidate_id=f"batch-ready-{i}", analysis_parent_id=parent.candidate_id,
            evidence_ids=(event["event_id"],) if i == 0 else (),
            counterevidence_ids=(event["event_id"],) if i == 1 else (), state="analyzed",
            claim="x" * 9000 if long_child else "Scoped observation",
            context="PASS and FAIL: scoped checks", uncertainty="Preserve failed checks",
            scope=scope, analysis_evidence_hash=compiler._hash_evidence(
                compiler.sanitize_evidence([event])
            ),
        )
        compiler.save_candidate(root, child)
        children.append(child)
    parent = replace(parent, analysis_inputs=tuple(child.candidate_id for child in children),
                     scope=scope)
    compiler.save_candidate(root, parent)
    return parent, events, children


@pytest.mark.parametrize("mode", ["long_child", "huge_scope"])
def test_unmergeable_complete_children_fail_explicitly_once(tmp_path, monkeypatch, mode):
    parent, _, children = ready_merge(tmp_path, **{mode: True})
    monkeypatch.setattr(compiler, "_analysis_batch_plan", lambda *a: [])
    monkeypatch.setattr(compiler, "classify_with_provider",
                        lambda *a, **k: pytest.fail("unbounded merge dispatched"))
    snapshots = {child.candidate_id: (tmp_path / compiler.ANALYSIS_DIR /
                 f"{child.candidate_id}.json").read_bytes() for child in children}
    report = compiler.analyze_pending(tmp_path, config=config())
    reason = "merge_summary_limits_exceeded" if mode == "long_child" else "merge_budget_exceeded"
    assert compiler.load_candidate(tmp_path, parent.candidate_id).state == "dead_letter"
    assert report["coverage"][parent.candidate_id]["reason"] == reason
    dead = json.loads((tmp_path / compiler.DEAD_LETTER_DIR /
                      f"{parent.candidate_id}.json").read_text())
    assert reason in dead["reason"]
    assert report["coverage"][parent.candidate_id]["action"]
    assert all((tmp_path / compiler.ANALYSIS_DIR / f"{cid}.json").read_bytes() == snapshot
               for cid, snapshot in snapshots.items())
    second = compiler.analyze_pending(tmp_path, config=config())
    assert parent.candidate_id not in second["deferred"]
    assert parent.candidate_id not in second["coverage"]
    assert not (tmp_path / compiler.USAGE_PATH).exists()


@pytest.mark.parametrize("field", ["claim", "context", "uncertainty"])
def test_oversized_result_text_is_rejected_without_truncating(tmp_path, monkeypatch, field):
    parent, _ = seed(tmp_path, count=2)

    def classify(*args, **kwargs):
        return {"claim": "Scoped observation", field: "x" * 9000,
                "evidence_ids": list(parent.evidence_ids),
                "counterevidence_ids": list(parent.counterevidence_ids)}, ""

    monkeypatch.setattr(compiler, "classify_with_provider", classify)
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["dead_letter"] == [parent.candidate_id]
    dead = json.loads((tmp_path / compiler.DEAD_LETTER_DIR /
                      f"{parent.candidate_id}.json").read_text())
    assert dead["reason"] == f"provider_{field}_limit_exceeded"
    stored = compiler.load_candidate(tmp_path, parent.candidate_id)
    assert stored.claim == parent.claim
    assert stored.evidence_ids == parent.evidence_ids
    assert stored.counterevidence_ids == parent.counterevidence_ids


def test_bounded_merge_is_explicit_semantic_coverage_not_verbatim(tmp_path):
    parent, events, children = ready_merge(tmp_path)
    proxy, prompt, rows, _ = compiler._analysis_merge_request(
        tmp_path, parent, {event["event_id"]: event for event in events}
    )
    payload = json.loads(prompt)
    assert payload["coverage"]["source_partition_complete"] is True
    assert payload["coverage"]["semantic_summary"] is True
    assert payload["coverage"]["verbatim_text"] is False
    assert sum(row["source_count"] for row in rows) == len(events)
    assert sum(row["counterevidence_count"] for row in rows) == 1
    assert set(proxy.evidence_ids) == {child.candidate_id for child in children}
    assert compiler.estimate_tokens(prompt) + 1200 < 16000


def test_result_schema_has_stricter_utf8_validation(tmp_path, monkeypatch):
    parent, _ = seed(tmp_path, count=2)
    schemas = []

    def run(argv, **kwargs):
        from pathlib import Path

        schema = json.loads(Path(argv[argv.index("--output-schema") + 1]).read_text())
        schemas.append(schema)
        Path(argv[argv.index("--output-last-message") + 1]).write_text('{"claim":"valid"}')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(compiler.subprocess, "run", run)
    compiler.classify_with_codex_cli(
        config(provider="codex_cli", command="/usr/bin/codex"), prompt="{}", cache_root=tmp_path
    )
    for field, byte_limit in compiler.RESULT_TEXT_BYTE_LIMITS.items():
        max_chars = schemas[0]["properties"][field]["maxLength"]
        assert max_chars == byte_limit
        value = "\U0001f600" * (byte_limit // 4)
        assert len(value.encode("utf-8")) <= byte_limit
        result = {"claim": "Valid claim", field: value}
        assert compiler.validate_provider_payload(result, candidate=parent)[0]
        result[field] += "x"
        assert compiler.validate_provider_payload(result, candidate=parent) == (
            False, f"provider_{field}_limit_exceeded"
        )
        result[field] = "x" * max_chars
        assert compiler.validate_provider_payload(result, candidate=parent)[0]


def test_partial_provider_result_does_not_limit_omitted_seed_fields(tmp_path):
    parent, _ = seed(tmp_path, count=2)
    parent = replace(parent, context="x" * 9000, uncertainty="y" * 9000)
    assert compiler.validate_provider_payload({"claim": "Valid claim"}, candidate=parent) == (
        True, ""
    )
