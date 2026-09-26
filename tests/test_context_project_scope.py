"""Project context must not borrow unscoped or foreign memory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lwm import context, dedup
from lwm.memory_compiler import Candidate, save_candidate
from lwm.memory_federation import load_published_memory


def test_project_context_filters_all_recall_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(context, "_resolve_id_for_context", lambda root, path: "p1")
    (tmp_path / "GLOBAL.md").write_text("# Global rule\nAlways verify.\n", encoding="utf-8")
    global_dir = tmp_path / "wiki" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "rule.md").write_text(
        "---\ntitle: Verify\ntype: principle\nstatus: approved\n---\n# Verify\n",
        encoding="utf-8",
    )
    now = datetime.now(timezone.utc).isoformat()
    dedup.save_event_index(tmp_path, {
        "e1": {"project_id": "p1", "timestamp": now, "tool": "codex", "event_type": "decision"},
        "e2": {"project_id": "p2", "timestamp": now, "tool": "claude", "event_type": "decision"},
    })
    candidates = tmp_path / "state" / "candidates"
    candidates.mkdir(parents=True)
    for candidate_id, evidence_ids, kind in (
        ("own", ["e1"], "workflow"),
        ("foreign", ["e2"], "workflow"),
        ("unknown", ["missing"], "workflow"),
        ("partial", ["e1", "missing"], "workflow"),
        ("shared", ["e1", "e2"], "relationship"),
    ):
        (candidates / f"{candidate_id}.json").write_text(
            json.dumps({"candidate_id": candidate_id, "kind": kind,
                        "evidence_ids": evidence_ids, "state": "accepted"}),
            encoding="utf-8",
        )
    for candidate_id, scope in (
        ("own-analysis", ("p1",)),
        ("foreign-analysis", ("p2",)),
        ("shared-analysis", ("p1", "p2")),
        ("unknown-analysis", ()),
    ):
        save_candidate(tmp_path, Candidate(candidate_id=candidate_id, kind="workflow",
                                           claim=candidate_id, scope=scope,
                                           evidence_ids=("e1",), state="accepted"))
    release_id = "release-20260925T000000Z-test"
    release_dir = tmp_path / "state" / "federation" / "releases"
    claims = release_dir / f"{release_id}.json"
    claims.parent.mkdir(parents=True)
    (release_dir / f"{release_id}-workflow.md").write_text("# Workflow\n", encoding="utf-8")
    (release_dir / f"{release_id}-conflicts.md").write_text("# Conflicts\n", encoding="utf-8")
    (tmp_path / "state" / "federation" / "release.json").write_text(
        json.dumps({"release_id": release_id, "path": f"state/federation/releases/{release_id}.json"}),
        encoding="utf-8",
    )
    claims.write_text(json.dumps({"release_id": release_id, "claims": [
        {"statement": "own claim", "status": "active", "project_id": "p1", "observed_at": now},
        {"statement": "foreign claim", "status": "active", "project_id": "p2", "observed_at": now},
        {"statement": "unknown claim", "status": "active", "observed_at": now},
        {"statement": "global claim", "status": "active", "scope": "global", "observed_at": now},
        {"statement": "shared claim", "status": "active", "scope": ["p1", "p2"], "observed_at": now},
        {"statement": "foreign conflict", "status": "conflicted", "project_id": "p2"},
        {"statement": "global rule", "status": "active", "observed_at": now, "source_path":
         str(tmp_path / "raw/tool-snapshots/codex/current/agents.md")},
    ]}), encoding="utf-8")
    assert load_published_memory(tmp_path)["claims"]

    report = context.build(tmp_path, tool="codex", project_path=str(tmp_path / "project"))
    data = report.data
    assert {item["candidate_id"] for item in data["accepted_candidates"]} == {"own", "shared"}
    assert {item["candidate_id"] for item in data["accepted_analysis_candidates"]} == {
        "own-analysis", "shared-analysis"
    }
    assert {item["statement"] for item in data["unified_memory"]["claims"]} == {
        "own claim", "global claim", "global rule", "shared claim"
    }
    assert data["unified_memory"]["conflicts"] == []
    assert [item["project_id"] for item in data["recent_activity"]] == ["p1"]
    assert data["global_rules"][0]["title"] == "Verify"
    assert data["behavior_contract"]["status"] == "verified"
    assert "cross-project insight" in report.markdown


def test_project_activity_filters_before_limit(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc).isoformat()
    dedup.save_event_index(tmp_path, {
        f"other-{i}": {"project_id": "p2", "timestamp": now}
        for i in range(20)
    } | {"own": {"project_id": "p1", "timestamp": now}})
    assert [row["project_id"] for row in context._recent_tool_activity(
        tmp_path, limit=12, project_id="p1"
    )] == ["p1"]


def test_unknown_project_context_only_keeps_explicit_global_memory(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(context, "load_accepted", lambda root: [
        {"candidate_id": "project", "scope": ["p1"], "state": "accepted"},
        {"candidate_id": "global", "scope": "global", "state": "accepted"},
        {"candidate_id": "unknown", "state": "accepted"},
    ])
    monkeypatch.setattr(context, "load_accepted_analysis_candidates", lambda root: [
        {"candidate_id": "project", "scope": ["p1"]},
        {"candidate_id": "global", "scope": "global"},
    ])
    monkeypatch.setattr(context, "load_published_memory", lambda root, limit: {
        "release_id": "r1",
        "claims": [
            {"statement": "project", "project_id": "p1"},
            {"statement": "unknown"},
            {"statement": "global", "scope": "global"},
            {"statement": "snapshot rule", "source_path":
             str(tmp_path / "raw/tool-snapshots/codex/current/agents.md")},
            {"statement": "mislabelled", "project_id": "p1", "source_path":
             str(tmp_path / "raw/tool-snapshots/codex/current/agents.md")},
        ],
        "conflicts": [{"statement": "project conflict", "project_id": "p1"}],
    })
    now = datetime.now(timezone.utc).isoformat()
    dedup.save_event_index(tmp_path, {"e1": {"project_id": "p1", "timestamp": now}})

    report = context.build(tmp_path, tool="codex", project_path=None)
    assert report.data["scope"] == "global-only"
    assert [item["candidate_id"] for item in report.data["accepted_candidates"]] == ["global"]
    assert [item["candidate_id"] for item in report.data["accepted_analysis_candidates"]] == ["global"]
    assert [item["statement"] for item in report.data["unified_memory"]["claims"]] == [
        "global", "snapshot rule"
    ]
    assert report.data["unified_memory"]["conflicts"] == []
    assert report.data["recent_activity"] == []
    assert "project conflict" not in report.markdown
