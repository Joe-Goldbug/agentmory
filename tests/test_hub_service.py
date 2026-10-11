from __future__ import annotations

import json
from pathlib import Path

from lwm import hub_service
from lwm.memory_compiler import Candidate, save_candidate
from mcp.lwm_server import _call_tool


def _event_shape(event: dict) -> dict:
    return {
        key: event.get(key)
        for key in (
            "tool",
            "project_path",
            "event_type",
            "importance",
            "privacy",
            "task",
        )
    }


def test_cli_and_mcp_event_transports_share_canonical_defaults(tmp_path: Path) -> None:
    shared_root = tmp_path / "shared"
    cli_result = hub_service.record_event(
        shared_root,
        {"tool": "gemini-cli", "event_type": "workflow_observation", "task": "same"},
    )
    mcp_result = _call_tool(
        "record_event",
        {
            "root": str(shared_root),
            "event": {"tool": "gemini-cli", "event_type": "workflow_observation", "task": "same"},
        },
    )

    cli_event = cli_result["event"]
    mcp_files = list((shared_root / "raw" / "events" / "inbox").rglob("*.json"))
    assert len(mcp_files) == 2
    mcp_event = next(
        json.loads(path.read_text(encoding="utf-8"))
        for path in mcp_files
        if json.loads(path.read_text(encoding="utf-8"))["event_id"] != cli_result["event_id"]
    )
    assert _event_shape(cli_event) == _event_shape(mcp_event)
    assert cli_result["event_id"]
    assert mcp_result["ingested"] is True


def test_sparse_event_uses_data_root_for_project_identity(tmp_path: Path) -> None:
    root = tmp_path / "root"
    result = hub_service.record_event(root, {"tool": "shell"})
    assert result["event"]["project_path"] == str(root.resolve())
    assert result["event"]["project_id"]


def test_record_event_canonicalizes_registry_aliases(tmp_path: Path) -> None:
    result = hub_service.record_event(
        tmp_path,
        {"tool": "cc", "event_type": "workflow_observation", "task": "alias"},
    )
    assert result["event"]["tool"] == "claude-code"


def test_review_analysis_uses_one_canonical_service(tmp_path: Path) -> None:
    candidate = Candidate(
        candidate_id="compiler-1",
        kind="workflow",
        claim="A verified loop repeats.",
        scope=("p1", "p2"),
        evidence_ids=("e1", "e2"),
        state="analyzed",
    )
    save_candidate(tmp_path, candidate)

    payload = hub_service.review_analysis(
        tmp_path, candidate.candidate_id, decision="accept"
    )

    assert payload["state"] == "accepted"


def test_promote_analysis_uses_stable_evidence_and_updates_state(tmp_path: Path) -> None:
    events_dir = tmp_path / "raw" / "events" / "processed" / "2026-08-01"
    events_dir.mkdir(parents=True)
    events = [
        {
            "event_id": "e1",
            "event_type": "decision",
            "project_id": "p1",
            "task": "Reuse the same daily memory refresh loop",
            "decisions": ["Reuse the same daily memory refresh loop"],
            "verification": ["PASS: daily refresh replay retained source event IDs in project p1"],
            "verification_results": [{
                "status": "passed",
                "claim": "The daily refresh loop is reused across projects",
                "check": "Source-backed daily refresh replay in p1",
            }],
        },
        {
            "event_id": "e2",
            "event_type": "decision",
            "project_id": "p2",
            "task": "Reuse the same daily memory refresh loop",
            "decisions": ["Reuse the same daily memory refresh loop"],
            "verification": ["PASS: daily refresh replay retained source event IDs in project p2"],
            "verification_results": [{
                "status": "passed",
                "claim": "The daily refresh loop is reused across projects",
                "check": "Source-backed daily refresh replay in p2",
            }],
        },
    ]
    for event in events:
        (events_dir / f"{event['event_id']}.json").write_text(
            json.dumps(event), encoding="utf-8"
        )
    candidate = Candidate(
        candidate_id="compiler-1",
        kind="workflow",
        claim="The daily refresh loop is reused across projects",
        scope=("p1", "p2"),
        evidence_ids=("e1", "e2"),
        state="promotion_pending",
    )
    save_candidate(tmp_path, candidate)

    result = hub_service.promote_analysis(tmp_path, candidate.candidate_id)

    assert result["status"] == "promoted"
    assert result["candidate"]["state"] == "promoted"
    assert "type: pattern" in Path(result["target"]).read_text(encoding="utf-8")
