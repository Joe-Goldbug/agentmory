"""Memory Compiler contract tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 5. Memory Compiler
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import lwm.memory_compiler as compiler
from lwm import lockfile
from lwm.memory_compiler import (
    CACHE_DIR,
    Candidate,
    AnalysisConfig,
    cache_key_for,
    classify_with_provider,
    load_candidate,
    record_transition,
    reconcile_daily_budget,
    save_candidate,
    seed_candidate,
    review_analysis_candidate,
    load_accepted_analysis_candidates,
    validate_candidate,
    sanitize_evidence,
    reserve_daily_budget,
    validate_provider_payload,
)


def _candidate(**overrides: object) -> Candidate:
    payload = {
        "candidate_id": "c-1",
        "kind": "workflow",
        "claim": "Reuse the same daily memory refresh loop across two projects",
        "scope": ("p1", "p2"),
        "evidence_ids": ("e1", "e2"),
        "counterevidence_ids": ("e3",),
        "context": "Both projects emit a daily review event.",
        "uncertainty": "low",
        "validity": "current",
    }
    payload.update(overrides)
    return Candidate.from_dict(payload)


def test_seed_candidate_does_not_reset_existing_analysis_state(tmp_path: Path) -> None:
    candidate = _candidate(state="accepted")
    save_candidate(tmp_path, candidate)

    replacement = _candidate(state="pending_analysis", claim="new wording")
    path = seed_candidate(tmp_path, replacement)

    assert load_candidate(tmp_path, candidate.candidate_id) == candidate
    assert path.is_file()


def test_analysis_review_and_recall_require_human_acceptance(tmp_path: Path) -> None:
    candidate = _candidate(state="analyzed")
    save_candidate(tmp_path, candidate)

    review_analysis_candidate(tmp_path, candidate.candidate_id, decision="accept")

    assert load_accepted_analysis_candidates(tmp_path)[0]["candidate_id"] == "c-1"


# Configuration


def test_disabled_config_is_not_usable() -> None:
    cfg = AnalysisConfig.from_env({})
    usable, reason = cfg.is_usable()
    assert not usable
    assert reason in {"analysis_disabled", "missing_base_url", "missing_model"}


def test_explicit_empty_config_does_not_read_process_environment(monkeypatch) -> None:
    monkeypatch.setenv("LWM_ANALYSIS_ENABLED", "1")
    monkeypatch.setenv("LWM_ANALYSIS_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LWM_ANALYSIS_MODEL", "unexpected-process-model")

    config = AnalysisConfig.from_env({})

    assert config.enabled is False
    assert config.base_url == ""
    assert config.model == ""


def test_localhost_endpoint_runs_without_key() -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "http://localhost:11434/v1",
            "LWM_ANALYSIS_MODEL": "qwen2.5",
        }
    )
    usable, reason = cfg.is_usable()
    assert usable, reason


def test_remote_endpoint_requires_key() -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "https://api.openai.com/v1",
            "LWM_ANALYSIS_MODEL": "gpt-5",
        }
    )
    usable, reason = cfg.is_usable()
    assert not usable and reason == "remote_endpoint_requires_api_key"


def test_remote_endpoint_with_key_is_usable() -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "https://api.example.com/v1",
            "LWM_ANALYSIS_MODEL": "gpt-5",
            "LWM_ANALYSIS_API_KEY": "sk-" + "A" * 32,
        }
    )
    usable, _ = cfg.is_usable()
    assert usable


# Validator


@pytest.mark.parametrize("kind", ["workflow", "relationship", "conflict", "summary"])
def test_valid_candidate_passes(kind: str) -> None:
    ok, reason = validate_candidate(
        _candidate(kind=kind, evidence_ids=("e1", "e2")),
        known_event_ids={"e1", "e2", "e3"},
    )
    assert ok, reason


def test_fabricated_evidence_is_rejected() -> None:
    ok, reason = validate_candidate(
        _candidate(evidence_ids=("e1", "ghost")),
        known_event_ids={"e1"},
    )
    assert not ok and "fabricated_evidence" in reason


def test_overlap_between_claim_and_counter_is_rejected() -> None:
    ok, reason = validate_candidate(
        _candidate(evidence_ids=("e1", "e2"), counterevidence_ids=("e1",)),
        known_event_ids={"e1", "e2"},
    )
    assert not ok and "id_both_claim_and_counter" in reason


@pytest.mark.parametrize(
    "claim",
    [
        "This causes latency in ingest",
        "It happens because of the shell hook",
        "Tool X never reports back",
    ],
)
def test_forbidden_patterns_reject_claims(claim: str) -> None:
    ok, reason = validate_candidate(_candidate(claim=claim), known_event_ids={"e1", "e2", "e3"})
    assert not ok and "forbidden_pattern" in reason


def test_empty_claim_rejected() -> None:
    ok, reason = validate_candidate(_candidate(claim="   "), known_event_ids={"e1", "e2"})
    assert not ok and reason == "empty_claim"


def test_unknown_kind_rejected() -> None:
    ok, _ = validate_candidate(_candidate(kind="opinion"), known_event_ids={"e1", "e2"})
    assert not ok


def test_provider_payload_rejects_unknown_fields_and_evidence_drift() -> None:
    candidate = _candidate()
    ok, reason = validate_provider_payload({"claim": "ok", "unexpected": True}, candidate=candidate)
    assert not ok and reason.startswith("unsupported_provider_fields")

    ok, reason = validate_provider_payload(
        {"claim": "ok", "evidence_ids": ["ghost"]}, candidate=candidate
    )
    assert not ok and reason == "provider_evidence_ids_drift"


def test_provider_payload_accepts_only_existing_evidence() -> None:
    candidate = _candidate()
    ok, reason = validate_provider_payload(
        {
            "kind": "workflow",
            "claim": "supported claim",
            "scope": ["p1", "p2"],
            "evidence_ids": ["e1", "e2"],
            "counterevidence_ids": ["e3"],
            "validity": "current",
        },
        candidate=candidate,
    )
    assert ok, reason


# Provider (no real network)


def test_provider_unavailable_when_httpx_missing(monkeypatch, tmp_path: Path) -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "http://localhost:11434/v1",
            "LWM_ANALYSIS_MODEL": "qwen2.5",
        }
    )

    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result, reason = classify_with_provider(
        cfg, prompt="x", evidence=[{"id": "e1"}], cache_root=tmp_path
    )
    assert result is None
    assert reason == "provider_unavailable"


def test_provider_uses_cache_when_present(tmp_path: Path) -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "http://localhost:11434/v1",
            "LWM_ANALYSIS_MODEL": "qwen2.5",
        }
    )
    evidence = [{"event_id": "e1", "task": "x"}]
    key = cache_key_for(
        cfg,
        prompt_hash=hashlib.sha256(b"x").hexdigest(),
        evidence_hash=hashlib.sha256(
            json.dumps(evidence, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    )
    cache_dir = tmp_path / CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()[:24]}.json").write_text(
        json.dumps({"kind": "workflow", "claim": "cached claim"}),
        encoding="utf-8",
    )
    result, reason = classify_with_provider(cfg, prompt="x", evidence=evidence, cache_root=tmp_path)
    assert reason == "cache_hit"
    assert result and result["claim"] == "cached claim"


def test_provider_does_not_persist_api_key(tmp_path: Path) -> None:
    cfg = AnalysisConfig.from_env(
        {
            "LWM_ANALYSIS_ENABLED": "1",
            "LWM_ANALYSIS_BASE_URL": "http://localhost:11434/v1",
            "LWM_ANALYSIS_MODEL": "qwen2.5",
            "LWM_ANALYSIS_API_KEY": "sk-" + "X" * 32,
        }
    )

    class FakeResponse:
        status_code = 200

        def json(self_inner):  # noqa: N805
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "kind": "summary",
                                    "claim": "ok",
                                    "evidence_ids": ["e1"],
                                }
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        def post(self, *args, **kwargs):
            return FakeResponse()

    fake_module = type("M", (), {"post": FakeClient().post, "HTTPError": Exception})()
    with patch.dict("sys.modules", {"httpx": fake_module}):
        result, _ = classify_with_provider(
            cfg, prompt="x", evidence=[{"id": "e1"}], cache_root=tmp_path
        )
    assert result is not None
    for path in (tmp_path / CACHE_DIR).rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text


def test_sanitize_evidence_keeps_contract_fields_and_redacts_secrets() -> None:
    sanitized = sanitize_evidence(
        [
            {
                "event_id": "e1",
                "tool": "codex",
                "project_id": "p1",
                "task": "Ship the change",
                "decisions": ["keep the source-backed path"],
                "raw_transcript": "do not send this",
                "api_key": "sk-" + "A" * 32,
            }
        ]
    )
    assert sanitized == [
        {
            "event_id": "e1",
            "tool": "codex",
            "project_id": "p1",
            "task": "Ship the change",
            "decisions": ["keep the source-backed path"],
        }
    ]


def test_daily_budget_is_persisted_and_rejects_over_budget(tmp_path: Path) -> None:
    assert reserve_daily_budget(tmp_path, token_count=8, budget=10) is True
    assert reserve_daily_budget(tmp_path, token_count=3, budget=10) is False
    payload = json.loads(
        (tmp_path / "state" / "analysis" / "usage.json").read_text(encoding="utf-8")
    )
    assert payload["used_tokens"] == 8


def test_daily_budget_reconciles_provider_usage(tmp_path: Path) -> None:
    assert reserve_daily_budget(tmp_path, token_count=20, budget=100) is True

    usage = json.loads((tmp_path / "state" / "analysis" / "usage.json").read_text(encoding="utf-8"))
    reconcile_daily_budget(tmp_path, reserved_tokens=20, actual_tokens=7)
    usage = json.loads((tmp_path / "state" / "analysis" / "usage.json").read_text(encoding="utf-8"))

    assert usage["used_tokens"] == 7
    assert usage["last_actual_tokens"] == 7


def test_analyze_pending_uses_retry_wait_until_retry_window(tmp_path: Path, monkeypatch) -> None:
    event_path = tmp_path / "raw" / "events" / "processed" / "event.json"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    event_path.write_text(
        json.dumps(
            {
                "event_id": "e1",
                "event_type": "decision",
                "tool": "codex",
                "project_id": "p1",
                "task": "keep the evidence path",
                "decisions": ["keep the evidence path"],
            }
        ),
        encoding="utf-8",
    )
    candidate = _candidate(evidence_ids=("e1",), counterevidence_ids=(), scope=("p1",))
    save_candidate(tmp_path, candidate)
    config = AnalysisConfig(
        enabled=True,
        base_url="http://localhost:11434/v1",
        api_key="",
        model="local",
        timeout_seconds=1,
        daily_token_budget=100_000,
        max_attempts=3,
    )
    calls: list[int] = []

    def fail_once(*_args, **_kwargs):
        calls.append(1)
        return None, "temporary_failure"

    monkeypatch.setattr(compiler, "classify_with_provider", fail_once)
    first = compiler.analyze_pending(
        tmp_path,
        config=config,
        now=datetime.fromisoformat("2026-08-01T00:00:00+00:00"),
    )
    assert first["deferred"] == [candidate.candidate_id]
    assert load_candidate(tmp_path, candidate.candidate_id).state == "retry_wait"

    before_retry = compiler.analyze_pending(
        tmp_path,
        config=config,
        now=datetime.fromisoformat("2026-08-01T00:00:30+00:00"),
    )
    assert before_retry["deferred"] == [candidate.candidate_id]
    assert len(calls) == 1

    monkeypatch.setattr(
        compiler,
        "classify_with_provider",
        lambda *_args, **_kwargs: (
            {"kind": "workflow", "claim": "keep the evidence path"},
            "",
        ),
    )
    completed = compiler.analyze_pending(
        tmp_path,
        config=config,
        now=datetime.fromisoformat("2026-08-01T00:02:00+00:00"),
    )
    assert completed["analyzed"] == [candidate.candidate_id]
    assert load_candidate(tmp_path, candidate.candidate_id).state == "analyzed"


def test_analyze_pending_skips_when_cycle_writer_is_busy(tmp_path: Path, monkeypatch) -> None:
    held = lockfile.try_acquire_cycle(tmp_path)
    assert held.acquired is True
    monkeypatch.setattr(
        compiler,
        "_analyze_pending_unlocked",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("analysis must not enter while cycle is owned")
        ),
    )

    report = compiler.analyze_pending(tmp_path)

    assert report["status"] == "analysis_pending"
    assert report["errors"] == ["cycle_lock_busy"]
    assert lockfile.release_cycle(tmp_path) is True


def test_disabled_compiler_does_not_change_pending_candidates(tmp_path: Path) -> None:
    candidate = _candidate(evidence_ids=("missing",), scope=("p1",))
    path = save_candidate(tmp_path, candidate)
    original = path.read_bytes()
    config = AnalysisConfig(
        enabled=False,
        base_url="",
        api_key="",
        model="",
        timeout_seconds=1,
        daily_token_budget=100_000,
        max_attempts=3,
    )

    report = compiler.analyze_pending(tmp_path, config=config)

    assert report == {
        "status": "disabled",
        "analyzed": [],
        "deferred": [],
        "dead_letter": [],
        "errors": [],
    }
    assert path.read_bytes() == original
    assert not (tmp_path / "state" / "analysis" / "dead-letter").exists()


def test_analyze_pending_reports_lock_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        lockfile,
        "try_acquire_cycle",
        lambda _root, **_kwargs: lockfile.LockResult(
            acquired=False,
            info=None,
            existing=None,
            error="cycle lock open failed: Operation not permitted",
        ),
    )

    report = compiler.analyze_pending(tmp_path)

    assert report["status"] == "analysis_pending"
    assert report["errors"] == ["cycle_lock_unavailable"]


# Persistence


def test_save_load_round_trip(tmp_path: Path) -> None:
    candidate = _candidate()
    save_candidate(tmp_path, candidate)
    restored = load_candidate(tmp_path, candidate.candidate_id)
    assert restored == candidate


def test_record_transition_appends_jsonl(tmp_path: Path) -> None:
    record_transition(
        tmp_path,
        "c-1",
        from_state="pending_analysis",
        to_state="analyzing",
        note="dispatched",
        evidence_hash="evidence-hash",
        actor="test",
    )
    record_transition(
        tmp_path,
        "c-1",
        from_state="analyzing",
        to_state="analyzed",
        note="response received",
    )
    target = tmp_path / "state" / "analysis" / "transitions" / "c-1.jsonl"
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    payload = json.loads(lines[0])
    assert payload["from"] == "pending_analysis" and payload["to"] == "analyzing"
    assert payload["candidate_id"] == "c-1"
    assert payload["evidence_hash"] == "evidence-hash"
    assert payload["actor"] == "test"


def test_record_transition_rejects_invalid_state_change(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid candidate transition"):
        record_transition(
            tmp_path,
            "c-1",
            from_state="pending_analysis",
            to_state="promoted",
        )
