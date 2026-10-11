"""Offline regressions for audit F08/F09/F10/F12; never invoke a model."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from lwm import memory_compiler as compiler
from lwm import stable_promotion as promotion
from lwm import structured_candidates as structured


CLAIM = "Reuse the verified refresh loop"


def test_large_evidence_is_explicitly_compressed_without_losing_any_id(tmp_path, monkeypatch):
    original = candidate()
    compiler.save_candidate(tmp_path, original)
    sources(tmp_path, [event(decisions=["A"*1200]*12), event("e2", "p2", decisions=["B"*1200]*12)])
    delivered = []
    def provider(cfg, **kwargs):
        delivered.append(json.loads(kwargs["prompt"]))
        return {"claim": CLAIM}, ""
    monkeypatch.setattr(compiler, "classify_with_provider", provider)
    report = compiler.analyze_pending(tmp_path, config=config(request_token_budget=7000))
    assert report["analyzed"] == [original.candidate_id]
    assert {row["event_id"] for row in delivered[0]["evidence"]} == {"e1", "e2"}
    assert report["coverage"][original.candidate_id]["complete"] is True
    assert report["coverage"][original.candidate_id]["compressed_ids"] == ["e1", "e2"]


def config(**overrides):
    return replace(
        compiler.AnalysisConfig(
            enabled=True,
            base_url="http://localhost:11434/v1",
            api_key="",
            model="test-model-only",
            timeout_seconds=1,
            daily_token_budget=100_000,
            max_attempts=1,
        ),
        **overrides,
    )


def event(eid="e1", project="p1", **overrides):
    return {
        "event_id": eid,
        "project_id": project,
        "tool": "codex",
        "event_type": "decision",
        "task": CLAIM,
        "decisions": [CLAIM],
        "verification": [f"PASS: {CLAIM}"],
        "tags": ["design", "security"],
        **overrides,
    }


def candidate(**overrides):
    return compiler.Candidate.from_dict(
        {
            "candidate_id": "repair-candidate",
            "kind": "workflow",
            "claim": CLAIM,
            "scope": ["p1", "p2"],
            "evidence_ids": ["e1", "e2"],
            **overrides,
        }
    )


def sources(root, events):
    base = root / "raw/events/processed/2026-10-11"
    base.mkdir(parents=True, exist_ok=True)
    for item in events:
        (base / f"{item['event_id']}.json").write_text(json.dumps(item), encoding="utf-8")


@pytest.mark.parametrize("kwargs", [{"base_url": ""}, {"model": ""}])
def test_missing_config_does_not_consume_attempts_or_budget(tmp_path, monkeypatch, kwargs):
    compiler.save_candidate(tmp_path, candidate())
    sources(tmp_path, [event(), event("e2", "p2")])
    monkeypatch.setattr(compiler, "classify_with_provider", lambda *a, **k: pytest.fail("dispatch"))
    report = compiler.analyze_pending(tmp_path, config=config(**kwargs))
    assert report["status"] == "analysis_pending"
    assert report["deferred"] == ["repair-candidate"]
    assert compiler.load_candidate(tmp_path, "repair-candidate").state == "pending_analysis"
    assert not (tmp_path / compiler.USAGE_PATH).exists()
    assert not (tmp_path / compiler.RETRY_DIR).exists()


def test_recovery_is_explicit_configuration_only_and_audited(tmp_path):
    for cid, reason in [("config", "analysis_disabled"), ("bad", "fabricated_evidence:x")]:
        dead = candidate(candidate_id=cid, state="dead_letter")
        compiler.save_candidate(tmp_path, dead)
        compiler._dead_letter(tmp_path, dead, reason=reason)
        compiler._save_retry_state(tmp_path, cid, {"attempts": 3, "retry_at": "2099-01-01"})
    assert hasattr(compiler, "recover_configuration_failures")
    report = compiler.recover_configuration_failures(tmp_path, actor="human-deployment")
    assert report["recovered"] == ["config"]
    assert compiler.load_candidate(tmp_path, "config").state == "pending_analysis"
    assert compiler.load_candidate(tmp_path, "bad").state == "dead_letter"
    assert compiler._retry_state(tmp_path, "config")["attempts"] == 0
    trail = (tmp_path / compiler.TRANSITIONS_DIR / "config.jsonl").read_text()
    assert "analysis_disabled" in trail and "human-deployment" in trail
    assert (tmp_path / compiler.DEAD_LETTER_DIR / "config.json").is_file()
    assert compiler.recover_configuration_failures(tmp_path, actor="human")["recovered"] == []


def test_file_opt_in_config_and_env_precedence_without_secrets(tmp_path):
    path = tmp_path / "state/analysis/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "provider": "codex_cli",
                "command": "/usr/bin/codex",
                "model": "test-model-only",
                "daily_token_budget": 8000,
                "timeout_seconds": 60,
                "request_token_budget": 6000,
            }
        )
    )
    assert hasattr(compiler, "load_analysis_config")
    loaded = compiler.load_analysis_config(tmp_path, env={})
    assert loaded.enabled and loaded.provider == "codex_cli"
    assert loaded.model == "test-model-only" and loaded.daily_token_budget == 8000
    assert not compiler.load_analysis_config(tmp_path, env={"LWM_ANALYSIS_ENABLED": "0"}).enabled
    assert (
        compiler.load_analysis_config(
            tmp_path,
            env={
                "LWM_ANALYSIS_MODEL": "env-test-model-only",
            },
        ).model
        == "env-test-model-only"
    )
    path.write_text(json.dumps({"enabled": True, "api_key": "do-not-load"}))
    blocked = compiler.load_analysis_config(tmp_path, env={})
    assert not blocked.is_usable()[0]
    assert "do-not-load" not in repr(blocked)


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.example/v1",
        "https://user:secret@remote.example/v1",
        "https://remote.example/v1?token=secret",
        "file:///tmp/model",
    ],
)
def test_unsafe_api_urls_are_not_usable(url):
    assert not config(base_url=url, api_key="secret").is_usable()[0]
    assert "secret" not in repr(config(api_key="secret"))


def test_complete_bounded_json_includes_claim_scope_and_counterevidence(tmp_path, monkeypatch):
    items = [event(f"e{i}", f"p{i % 2 + 1}", changes=["x" * 900] * 4) for i in range(12)]
    items.append(event("counter", "p2", risks=["counterexample"]))
    sources(tmp_path, items)
    original = candidate(evidence_ids=[f"e{i}" for i in range(12)], counterevidence_ids=["counter"])
    compiler.save_candidate(tmp_path, original)
    captured = {}

    def classify(cfg, **kwargs):
        captured.update(kwargs)
        return {"claim": CLAIM}, ""

    monkeypatch.setattr(compiler, "classify_with_provider", classify)
    report = compiler.analyze_pending(tmp_path, config=config(request_token_budget=100_000))
    request = json.loads(captured["prompt"])
    assert request["candidate"]["claim"] == CLAIM
    assert request["candidate"]["scope"] == ["p1", "p2"]
    assert request["candidate"]["counterevidence_ids"] == ["counter"]
    assert {e["event_id"] for e in request["evidence"]} == {e["event_id"] for e in items}
    assert len(captured["prompt"]) > 4000
    assert report["coverage"][original.candidate_id]["complete"] is True
    assert report["analyzed"] == [original.candidate_id]
    assert compiler.load_candidate(tmp_path, original.candidate_id).state == "analyzed"
    assert compiler.load_accepted_analysis_candidates(tmp_path) == []


@pytest.mark.parametrize("mode", ["missing", "over_budget", "operational"])
def test_coverage_gaps_defer_without_partial_analysis(tmp_path, monkeypatch, mode):
    items = [event(), event("e2", "p2")]
    if mode == "missing":
        items.pop()
    elif mode == "operational":
        items[1] = event("e2", "p2", event_type="session_start")
    compiler.save_candidate(tmp_path, candidate())
    sources(tmp_path, items)
    monkeypatch.setattr(
        compiler, "classify_with_provider", lambda *a, **k: pytest.fail("partial dispatch")
    )
    cfg = config(request_token_budget=1300 if mode == "over_budget" else 16_000)
    report = compiler.analyze_pending(tmp_path, config=cfg)
    assert report["deferred"] == ["repair-candidate"]
    assert report["coverage"]["repair-candidate"]["complete"] is False
    assert not (tmp_path / compiler.USAGE_PATH).exists()


def test_api_dispatch_does_not_truncate_and_cache_is_claim_specific(tmp_path, monkeypatch):
    sent = []
    fake = SimpleNamespace(HTTPError=OSError)

    def post(url, **kwargs):
        sent.append(kwargs)
        return SimpleNamespace(
            status_code=200,
            content=b"",
            json=lambda: {
                "choices": [{"message": {"content": json.dumps({"claim": "supported"})}}],
            },
        )

    fake.post = post
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake)
    evidence = [event()]
    first = json.dumps(
        {"candidate": {"claim": "topic-one"}, "evidence": evidence, "padding": "x" * 5000}
    )
    second = first.replace("topic-one", "topic-two")
    compiler.classify_with_provider(config(), prompt=first, evidence=evidence, cache_root=tmp_path)
    compiler.classify_with_provider(config(), prompt=second, evidence=evidence, cache_root=tmp_path)
    assert len(sent) == 2
    assert sent[0]["json"]["messages"][1]["content"] == first
    assert sent[0]["follow_redirects"] is False and sent[0]["trust_env"] is False


def test_codex_cli_is_fixed_no_shell_isolated_bounded_and_uses_local_auth(tmp_path, monkeypatch):
    assert hasattr(compiler, "classify_with_codex_cli")
    seen = {}

    def run(argv, **kwargs):
        seen.update(argv=argv, **kwargs)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "claim": CLAIM,
                    "kind": "workflow",
                    "scope": ["p1", "p2"],
                    "evidence_ids": ["e1", "e2"],
                    "counterevidence_ids": [],
                    "context": "",
                    "uncertainty": "limited",
                    "validity": "unknown",
                }
            )
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(compiler.subprocess, "run", run)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-forward")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "local-auth"))
    cfg = config(provider="codex_cli", command="/usr/bin/codex")
    result, reason = compiler.classify_with_provider(
        cfg, prompt="{}", evidence=[], cache_root=tmp_path
    )
    assert result and reason == ""
    assert seen["argv"][0:2] == ["/usr/bin/codex", "exec"]
    assert "--ephemeral" in seen["argv"] and "--output-schema" in seen["argv"]
    assert "read-only" in seen["argv"] and "features.hooks=false" in seen["argv"]
    assert "--ignore-user-config" in seen["argv"] and "--ignore-rules" in seen["argv"]
    assert seen["env"]["LWM_ANALYSIS_JOB"] == "1"
    assert seen["env"]["CODEX_HOME"] == str(tmp_path / "local-auth")
    assert "OPENAI_API_KEY" not in seen["env"]
    assert seen["cwd"] != str(tmp_path)
    assert seen["timeout"] == 1 and seen.get("shell", False) is False
    assert "must-not-forward" not in str(seen)


def test_semantic_identity_no_tag_collision_or_evidence_growth():
    items = [event(), event("e2", "p2"), event("e3", "p1")]
    relationships = structured.build_relationship_candidates(items)
    assert len({c.candidate_id for c in relationships}) == 2
    more = structured.build_relationship_candidates(items + [event("e4", "p2")])
    assert {c.candidate_id for c in relationships} == {c.candidate_id for c in more}
    workflows = structured.build_workflow_candidates(items)
    grown = structured.build_workflow_candidates(items + [event("e4", "p2")])
    assert workflows[0].candidate_id == grown[0].candidate_id


@pytest.mark.parametrize("decision", ["accept", "reject", "correct"])
def test_growth_preserves_human_decision_but_updates_support(tmp_path, decision):
    items = [event(), event("e2", "p2"), event("e3", "p1")]
    sources(tmp_path, items)
    original = structured.build_workflow_candidates(items)[0]
    path = structured.save_candidate(tmp_path, original)
    structured.review_candidate(
        tmp_path, original.candidate_id, decision=decision, correction="human wording"
    )
    structured.generate_candidates(tmp_path, items + [event("e4", "p2")])
    saved = json.loads(path.read_text())
    assert (
        saved["state"]
        == {"accept": "accepted", "reject": "rejected", "correct": "corrected"}[decision]
    )
    assert saved["correction"] == "human wording"
    assert "e4" in saved["evidence_ids"] and saved["evidence_revision"] == 2


@pytest.mark.parametrize(
    "verification",
    [
        ["FAIL: unrelated test failed"],
        ["unknown"],
        ["v1"],
        ["PASS: unrelated test"],
        [{"status": "passed", "claim": "another claim"}],
        [{"status": "failed", "claim": CLAIM}],
    ],
)
def test_only_positive_relevant_verification_supports_promotion(tmp_path, verification):
    result = promotion.evaluate_promotion(
        tmp_path,
        claim=CLAIM,
        events=[
            event(verification=verification),
            event("e2", "p2", verification=verification),
        ],
    )
    assert not result.promoted and result.verification_count == 0


@pytest.mark.parametrize("cause", ["missing", "retired", "counterevidence"])
def test_derived_approved_page_retracts_with_backup_audit_and_no_auto_reapproval(tmp_path, cause):
    items = [event(), event("e2", "p2")]
    first = promotion.evaluate_promotion(
        tmp_path, claim=CLAIM, events=items, evidence_ids=["e1", "e2"]
    )
    path = promotion.persist_promotion(first, page_type="pattern")
    assert path
    assert "status: approved" in path.read_text()
    kwargs = {}
    if cause == "missing":
        items.pop()
    elif cause == "retired":
        items[1]["status"] = "retired"
    else:
        items.append(event("counter", "p1", decisions=["counterexample"]))
        kwargs["counterevidence_ids"] = ["counter"]
    reevaluated = promotion.evaluate_promotion(
        tmp_path, claim=CLAIM, events=items, evidence_ids=["e1", "e2"], **kwargs
    )
    assert not reevaluated.promoted
    promotion.persist_promotion(reevaluated)
    assert "status: retracted" in path.read_text()
    audit = [
        json.loads(line)
        for line in (tmp_path / "wiki/promotion-audit.jsonl").read_text().splitlines()
    ]
    assert [row["action"] for row in audit] == ["promoted", "retracted"]
    assert Path(audit[-1]["rollback"]["backup_path"]).is_file()
    promotion.persist_promotion(reevaluated)
    assert len((tmp_path / "wiki/promotion-audit.jsonl").read_text().splitlines()) == 2


def test_lifecycle_helper_only_revalidates_derived_pages(tmp_path):
    sources(tmp_path, [event(), event("e2", "p2")])
    approved = promotion.evaluate_promotion(
        tmp_path, claim=CLAIM, events=[event(), event("e2", "p2")]
    )
    page = promotion.persist_promotion(approved)
    manual = tmp_path / "wiki/global/manual.md"
    manual.write_text("---\nstatus: approved\ntags: [principle]\n---\nHuman rule\n")
    sources(tmp_path, [event("e2", "p2", status="withdrawn")])
    assert hasattr(promotion, "revalidate_promotions")
    report = promotion.revalidate_promotions(tmp_path, actor="supervisor")
    assert report["retracted"] == [page.name]
    assert manual.read_text().endswith("Human rule\n")
    assert promotion.revalidate_promotions(tmp_path, actor="supervisor")["retracted"] == []


def test_seed_refreshes_unreviewed_evidence_without_resetting_human_decision(tmp_path):
    original = candidate()
    compiler.seed_candidate(tmp_path, original)
    grown = candidate(evidence_ids=["e1", "e2", "e3"])
    compiler.seed_candidate(tmp_path, grown)
    assert (
        compiler.load_candidate(tmp_path, original.candidate_id).evidence_ids == grown.evidence_ids
    )
    compiler.save_candidate(tmp_path, candidate(state="rejected"))
    compiler.seed_candidate(tmp_path, grown)
    assert compiler.load_candidate(tmp_path, original.candidate_id).state == "rejected"


def test_legacy_rejection_is_reused_by_topic_not_shared_evidence(tmp_path):
    items = [event(), event("e2", "p2"), event("e3", "p1")]
    design = next(
        c for c in structured.build_relationship_candidates(items) if "design" in c.relationship
    )
    old = design.to_dict()
    for field in ("semantic_topic", "identity_scope", "evidence_revision"):
        old.pop(field)
    old.update(candidate_id="legacy", state="rejected")
    path = tmp_path / "state/candidates/legacy.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(old))
    grown = items + [event("e4", "p2")]
    paths = structured.generate_candidates(tmp_path, grown)
    assert path in paths
    assert json.loads(path.read_text())["state"] == "rejected"
    assert any("security" in p.read_text() for p in paths)
    assert "legacy" not in {p.stem for p in structured.seed_analysis_candidates(tmp_path, grown)}


@pytest.mark.parametrize("payload", [{}, {"kind": "summary", "claim": CLAIM}])
def test_analysis_output_requires_claim_and_cannot_change_semantic_kind(payload):
    assert not compiler.validate_provider_payload(payload, candidate=candidate())[0]


def test_provider_output_cannot_persist_secret_or_unknown_fields(tmp_path, monkeypatch):
    fake = SimpleNamespace(
        HTTPError=OSError,
        post=lambda *a, **k: SimpleNamespace(
            status_code=200,
            content=b"",
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"claim": CLAIM, "password": "private-value"})
                        }
                    }
                ]
            },
        ),
    )
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake)
    result, _ = compiler.classify_with_provider(
        config(), prompt="{}", evidence=[], cache_root=tmp_path
    )
    assert result is None
    assert not list((tmp_path / compiler.CACHE_DIR).glob("*.json"))


def test_recursive_analysis_job_is_noop_even_with_enabled_config(tmp_path, monkeypatch):
    compiler.save_candidate(tmp_path, candidate())
    monkeypatch.setenv("LWM_ANALYSIS_JOB", "1")
    monkeypatch.setattr(
        compiler, "classify_with_provider", lambda *a, **k: pytest.fail("recursive job")
    )
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["status"] == "internal_job_skipped"


def test_scheduler_revalidates_derived_approvals_even_when_analysis_disabled(tmp_path):
    items = [event(), event("e2", "p2")]
    sources(tmp_path, items)
    page = promotion.persist_promotion(
        promotion.evaluate_promotion(tmp_path, claim=CLAIM, events=items)
    )
    sources(tmp_path, [event("e2", "p2", status="retired")])
    compiler.analyze_pending(tmp_path, config=config(enabled=False))
    assert "status: retracted" in page.read_text()


def test_explicit_retraction_and_rejected_approval_retract_derived_page(tmp_path):
    items = [event(), event("e2", "p2")]
    sources(tmp_path, items)
    page = promotion.persist_promotion(
        promotion.evaluate_promotion(tmp_path, claim=CLAIM, events=items)
    )
    compiler.save_candidate(tmp_path, candidate(state="rejected"))
    assert promotion.revalidate_promotions(tmp_path)["retracted"] == [page.name]


def test_structured_pass_verification_is_relevant_and_duplicate_ids_cannot_add_projects(tmp_path):
    items = [
        event(verification=[], verification_results=[{"status": "passed", "claim": CLAIM}]),
        event(
            "e2", "p2", verification=[], verification_results=[{"status": "passed", "claim": CLAIM}]
        ),
    ]
    assert promotion.evaluate_promotion(tmp_path, claim=CLAIM, events=items).promoted
    items[1]["event_id"] = "e1"
    assert not promotion.evaluate_promotion(tmp_path, claim=CLAIM, events=items).promoted


def test_cli_timeout_is_bounded_and_no_stderr_is_exposed(tmp_path, monkeypatch):
    def fail(*a, **k):
        raise compiler.subprocess.TimeoutExpired(a[0], 1, stderr=b"private output")

    monkeypatch.setattr(compiler.subprocess, "run", fail)
    result, reason = compiler.classify_with_provider(
        config(provider="codex_cli", command="/usr/bin/codex"),
        prompt="{}",
        evidence=[],
        cache_root=tmp_path,
    )
    assert result is None and reason == "cli_timeout"
    assert not list((tmp_path / compiler.CACHE_DIR).glob("*.json"))


def test_failed_verification_cannot_be_hidden_after_a_positive_entry(tmp_path):
    verification = [{"status": "passed", "claim": CLAIM}, {"status": "failed", "claim": CLAIM}]
    result = promotion.evaluate_promotion(
        tmp_path,
        claim=CLAIM,
        events=[
            event(verification=verification),
            event("e2", "p2", verification=verification),
        ],
    )
    assert not result.promoted


def test_verification_success_does_not_override_explicit_source_retraction(tmp_path):
    result = promotion.evaluate_promotion(
        tmp_path,
        claim=CLAIM,
        events=[
            event(),
            event("e2", "p2"),
            event("withdrawal", "p1", retracts_event_ids=["e1"]),
        ],
        evidence_ids=["e1", "e2"],
    )
    assert not result.promoted and "source_retraction" in result.reasons


def test_provider_unavailable_is_configuration_pause_not_dead_letter(tmp_path, monkeypatch):
    compiler.save_candidate(tmp_path, candidate())
    sources(tmp_path, [event(), event("e2", "p2")])
    monkeypatch.setattr(
        compiler, "classify_with_provider", lambda *a, **k: (None, "provider_unavailable")
    )
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["dead_letter"] == [] and report["deferred"] == ["repair-candidate"]
    assert compiler.load_candidate(tmp_path, "repair-candidate").state == "pending_analysis"
    assert compiler._retry_state(tmp_path, "repair-candidate")["attempts"] == 0
    assert json.loads((tmp_path / compiler.USAGE_PATH).read_text())["used_tokens"] == 0


def test_cli_usage_reconciles_daily_reservation(tmp_path, monkeypatch):
    compiler.reserve_daily_budget(tmp_path, token_count=16_000, budget=20_000)

    def run(argv, **kwargs):
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(json.dumps({"claim": CLAIM}))
        kwargs["stdout"].write(
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 150,
                        "output_tokens": 100,
                    },
                }
            ).encode()
            + b"\n"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(compiler.subprocess, "run", run)
    compiler.classify_with_provider(
        config(provider="codex_cli", command="/usr/bin/codex"),
        prompt="{}",
        evidence=[],
        cache_root=tmp_path,
        reserved_tokens=16_000,
    )
    assert json.loads((tmp_path / compiler.USAGE_PATH).read_text())["used_tokens"] == 250


def test_hub_promotion_contract_with_real_positive_evidence(tmp_path):
    from lwm import hub_service

    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(tmp_path, candidate(state="promotion_pending"))
    result = hub_service.promote_analysis(tmp_path, "repair-candidate")
    assert result["status"] == "promoted"


def test_unsafe_file_configuration_never_enables_analysis(tmp_path):
    path = tmp_path / "state/analysis/config.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"enabled":true}')
    path.chmod(0o666)
    assert not compiler.load_analysis_config(tmp_path, env={}).is_usable()[0]


def test_candidate_long_topics_do_not_share_truncated_identity():
    task = "long-task-" * 30
    events_a = [event(f"a{i}", f"p{i % 2}", task=task + "one") for i in range(3)]
    events_b = [event(f"b{i}", f"p{i % 2}", task=task + "two") for i in range(3)]
    candidates = structured.build_workflow_candidates(events_a + events_b)
    assert len(candidates) == 2 and len({c.candidate_id for c in candidates}) == 2


def test_analysis_suggestions_are_scoped_source_backed_and_unapproved(tmp_path):
    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(
        tmp_path, candidate(state="analyzed", context="Check the loop before reuse")
    )
    compiler.save_candidate(tmp_path, candidate(candidate_id="pending", state="pending_analysis"))
    compiler.save_candidate(tmp_path, candidate(candidate_id="rejected", state="rejected"))
    assert hasattr(compiler, "load_analysis_suggestions")
    suggestions = compiler.load_analysis_suggestions(tmp_path, project_id="p1")
    assert len(suggestions) == 1
    assert suggestions[0]["scope"] == ["p1", "p2"]
    assert suggestions[0]["status"] == "inferred"
    assert suggestions[0]["approval"] == "unapproved"
    assert suggestions[0]["native_rule_authority"] is False
    assert suggestions[0]["evidence_ids"] == ["e1", "e2"]
    assert compiler.load_analysis_suggestions(tmp_path, project_id="unrelated") == []
    sources(tmp_path, [event("e2", "p2", status="withdrawn")])
    assert compiler.load_analysis_suggestions(tmp_path) == []


def test_suggestions_reject_invalid_scope_or_counterevidence(tmp_path):
    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(tmp_path, candidate(state="analyzed", scope=["unrelated"]))
    assert hasattr(compiler, "load_analysis_suggestions")
    assert compiler.load_analysis_suggestions(tmp_path) == []
    compiler.save_candidate(tmp_path, candidate(state="analyzed", counterevidence_ids=["missing"]))
    assert compiler.load_analysis_suggestions(tmp_path) == []


def test_analysis_creates_project_drafts_and_retires_them_without_touching_native_rules(
    tmp_path, monkeypatch
):
    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(tmp_path, candidate())
    monkeypatch.setattr(compiler, "classify_with_provider", lambda *a, **k: ({"claim": CLAIM}, ""))
    report = compiler.analyze_pending(tmp_path, config=config())
    assert "project_drafts" in report
    assert len(report["project_drafts"]["updated"]) == 2
    base = tmp_path / "state/analysis/projects"
    artifacts = sorted(base.glob("*.json"))
    assert len(artifacts) == 2
    contents = [json.loads(path.read_text()) for path in artifacts]
    assert {doc["project_id"] for doc in contents} == {"p1", "p2"}
    assert all(
        doc["status"] == "analysis_draft" and doc["approval"] == "unapproved" for doc in contents
    )
    assert all(doc["suggestions"][0]["evidence_ids"] == ["e1", "e2"] for doc in contents)
    assert not (tmp_path / "wiki/global").exists()
    sources(tmp_path, [event("e2", "p2", status="retired")])
    compiler.analyze_pending(tmp_path, config=config(enabled=False))
    assert all(json.loads(path.read_text())["status"] == "inactive" for path in artifacts)


def test_changed_evidence_requires_reanalysis_before_tool_suggestions(tmp_path, monkeypatch):
    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(tmp_path, candidate())
    monkeypatch.setattr(compiler, "classify_with_provider", lambda *a, **k: ({"claim": CLAIM}, ""))
    compiler.analyze_pending(tmp_path, config=config())
    assert hasattr(compiler, "load_analysis_suggestions")
    assert compiler.load_analysis_suggestions(tmp_path)
    sources(tmp_path, [event("e2", "p2", decisions=["a changed decision"])])
    assert compiler.load_analysis_suggestions(tmp_path) == []


def test_growing_unapproved_analysis_returns_to_pending_with_audit(tmp_path):
    compiler.save_candidate(tmp_path, candidate(state="analyzed"))
    compiler.seed_candidate(tmp_path, candidate(evidence_ids=["e1", "e2", "e3"]))
    assert compiler.load_candidate(tmp_path, "repair-candidate").state == "pending_analysis"
    trail = (tmp_path / compiler.TRANSITIONS_DIR / "repair-candidate.jsonl").read_text()
    assert "evidence revision" in trail


def test_global_manual_page_is_not_modified_by_failed_promotion(tmp_path):
    assessed = promotion.evaluate_promotion(tmp_path, claim=CLAIM, events=[])
    assessed.target_path.parent.mkdir(parents=True)
    assessed.target_path.write_text(
        "---\nstatus: approved\ntype: principle\n---\nHuman instructions\n"
    )
    before = assessed.target_path.read_bytes()
    assert promotion.persist_promotion(assessed) is None
    assert assessed.target_path.read_bytes() == before


def test_redaction_preserves_json_and_coverage_when_strings_compress():
    request, coverage = compiler.build_analysis_request(
        candidate(),
        [
            event(task="password=privatevalue " + "long " * 200),
            event("e2", "p2"),
        ],
    )
    assert json.loads(request)["candidate"]["claim"] == CLAIM
    assert "privatevalue" not in request
    assert coverage["compressed_ids"] == ["e1"]


def test_codex_budget_limit_is_reported_as_reservation_not_hard_token_cap(tmp_path):
    report = compiler.analysis_usability(
        tmp_path, config=config(provider="codex_cli", command="/usr/bin/codex")
    )
    assert report["hard_provider_token_cap"] is False


def test_budget_projection_keeps_counterexamples_and_identity():
    evidence = event(verification=["PASS " + "x" * 100] * 15 + ["FAIL regression reproduced"])
    safe = compiler.sanitize_evidence([evidence], max_chars=80)[0]
    assert safe["event_id"] == evidence["event_id"]
    assert any("FAIL" in value for value in safe["verification"])
    assert len(safe["verification"]) == 4
    assert "verification" in safe["compressed_fields"]


def test_from_root_reads_deliberate_nonsecret_opt_in(tmp_path):
    path = tmp_path / "state/analysis/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "enabled": True,
                "provider": "codex_cli",
                "command": "/usr/bin/codex",
                "model": "test-model-only",
                "daily_token_budget": 20_000,
            }
        )
    )
    assert hasattr(compiler.AnalysisConfig, "from_root")
    loaded = compiler.AnalysisConfig.from_root(tmp_path, env={})
    assert loaded.provider == "codex_cli" and loaded.daily_token_budget == 20_000


def test_workflow_seed_does_not_require_identical_task_wording():
    items = [
        event(
            f"e{i}",
            f"p{i % 2 + 1}",
            task=f"Repair refresh issue {i}",
            changes=[f"Source change {i}"],
            tags=["refresh-verification"],
        )
        for i in range(3)
    ]
    workflows = structured.build_workflow_candidates(items)
    assert len(workflows) == 1
    assert set(workflows[0].evidence_ids) == {"e0", "e1", "e2"}
    assert "refresh-verification" in workflows[0].trigger
    grown = structured.build_workflow_candidates(
        items
        + [
            event(
                "e4",
                "p2",
                task="Another refresh repair",
                changes=["Another source change"],
                tags=["refresh-verification"],
            )
        ]
    )
    assert grown[0].candidate_id == workflows[0].candidate_id


def test_workflow_theme_namespace_does_not_collide_with_literal_task():
    literal = [event(f"literal{i}", "p1", task="topic:design", tags=[]) for i in range(3)]
    theme = [
        event(f"theme{i}", "p2", task=f"Different action {i}", tags=["design"]) for i in range(3)
    ]
    workflows = structured.build_workflow_candidates(literal + theme)
    assert len(workflows) == 2 and len({c.candidate_id for c in workflows}) == 2


def test_semantic_model_can_identify_counterevidence_only_among_delivered_ids(
    tmp_path, monkeypatch
):
    sources(tmp_path, [event(), event("e2", "p2")])
    compiler.save_candidate(tmp_path, candidate())
    monkeypatch.setattr(
        compiler,
        "classify_with_provider",
        lambda *a, **k: (
            {
                "claim": CLAIM,
                "evidence_ids": ["e1"],
                "counterevidence_ids": ["e2"],
                "uncertainty": "The second project is a counterexample",
            },
            "",
        ),
    )
    report = compiler.analyze_pending(tmp_path, config=config())
    assert report["analyzed"] == ["repair-candidate"]
    analyzed = compiler.load_candidate(tmp_path, "repair-candidate")
    assert analyzed.evidence_ids == ("e1",) and analyzed.counterevidence_ids == ("e2",)
    assert compiler.load_analysis_suggestions(tmp_path)[0]["counterevidence_ids"] == ["e2"]
    assert not compiler.validate_provider_payload(
        {
            "claim": CLAIM,
            "evidence_ids": ["e1"],
            "counterevidence_ids": ["ghost"],
        },
        candidate=candidate(),
    )[0]
