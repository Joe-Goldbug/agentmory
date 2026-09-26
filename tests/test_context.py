"""`lwm context` tests (acceptance: markdown + json output, all priority sections)."""

from __future__ import annotations

import json
from pathlib import Path

from lwm import context as lwm_context
from lwm import ingest
from lwm.events import make_event


def _seed_event(root: Path, project_path: Path, **overrides):
    event = make_event(
        tool="claude-code",
        project_path=str(project_path),
        project_id="git-demo",
        event_type="decision",
        task="bootstrap",
        verification=["smoke-ok"],
        decisions=["ship-it"],
    )
    event.update(overrides)
    inbox_dir = root / "raw" / "events" / "inbox" / "2026-07-11"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{event['event_id']}.json").write_text(
        json.dumps(event, ensure_ascii=False), encoding="utf-8"
    )


def test_context_markdown_sections(tmp_path: Path) -> None:
    project_path = tmp_path / "proj"
    project_path.mkdir()
    _seed_event(tmp_path, project_path)
    ingest.run(tmp_path, with_lock=False)

    report = lwm_context.build(
        tmp_path,
        tool="claude-code",
        project_path=str(project_path),
        format="markdown",
        limit=4,
    )
    assert "Global Memory" in report.markdown
    assert "Project Memory" in report.markdown
    assert "Scope: project" in report.markdown
    assert "ship-it" in report.markdown


def test_context_json_mode(tmp_path: Path) -> None:
    project_path = tmp_path / "proj"
    project_path.mkdir()
    report = lwm_context.build(
        tmp_path,
        tool="codex",
        project_path=str(project_path),
        format="json",
    )
    data = json.loads(report.markdown)
    assert data["tool"] == "codex"
    assert "global_rules" in data
    assert "recent_activity" in data


def test_context_contains_canonical_behavior_contract(tmp_path: Path) -> None:
    (tmp_path / "GLOBAL.md").write_text(
        "<!-- contract-version: 7 -->\n# Contract\n\nDo the verified thing.\n",
        encoding="utf-8",
    )

    report = lwm_context.build(
        tmp_path,
        tool="codex",
        project_path=None,
        format="json",
    )
    data = json.loads(report.markdown)

    assert data["behavior_contract"]["version"] == "7"
    assert len(data["behavior_contract"]["sha256"]) == 64
    assert "behavior_contract" in report.markdown


def test_context_recalls_only_accepted_structured_candidates(tmp_path: Path) -> None:
    from lwm.structured_candidates import build_workflow_candidates, review_candidate, save_candidate

    candidate = build_workflow_candidates(
        [
            {
                "event_id": f"e-{i}",
                "event_type": "verification",
                "tool": "codex",
                "project_id": "p1",
                "task": "run checks",
                "verification": ["checks passed"],
            }
            for i in range(3)
        ]
    )[0]
    save_candidate(tmp_path, candidate)
    processed = tmp_path / "raw" / "events" / "processed" / "2026-07-11"
    processed.mkdir(parents=True)
    for event_id in candidate.evidence_ids:
        (processed / f"{event_id}.json").write_text(
            json.dumps({"event_id": event_id}), encoding="utf-8"
        )
    assert "Accepted Workflows" not in lwm_context.build(
        tmp_path, tool="codex", project_path=None
    ).markdown
    review_candidate(tmp_path, candidate.candidate_id, decision="accept")
    assert "Accepted Workflows" not in lwm_context.build(
        tmp_path, tool="codex", project_path=None
    ).markdown


def test_context_recalls_only_accepted_compiler_candidates(tmp_path: Path) -> None:
    from lwm.memory_compiler import Candidate, review_analysis_candidate, save_candidate

    candidate = Candidate(
        candidate_id="compiler-1",
        kind="workflow",
        claim="The verified release loop recurs across two projects.",
        scope=("p1", "p2"),
        evidence_ids=("e1", "e2"),
        state="analyzed",
    )
    save_candidate(tmp_path, candidate)
    assert "Accepted Compiler Findings" not in lwm_context.build(
        tmp_path, tool="codex", project_path=None
    ).markdown

    review_analysis_candidate(tmp_path, candidate.candidate_id, decision="accept")
    report = lwm_context.build(tmp_path, tool="codex", project_path=None)
    assert "Accepted Compiler Findings" not in report.markdown
    assert report.data["accepted_analysis_candidates"] == []


def test_context_only_includes_approved_global_principles(tmp_path: Path) -> None:
    global_dir = tmp_path / "wiki" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "approved.md").write_text(
        "---\ntitle: Approved\ntype: principle\nstatus: approved\ntags: [principle]\n---\n# Approved\n",
        encoding="utf-8",
    )
    (global_dir / "pattern.md").write_text(
        "---\ntitle: Pattern\ntype: pattern\nstatus: approved\ntags: [pattern]\n---\n# Pattern\n",
        encoding="utf-8",
    )
    (global_dir / "draft.md").write_text(
        "---\ntitle: Draft\ntype: principle\nstatus: review\ntags: [principle]\n---\n# Draft\n",
        encoding="utf-8",
    )
    (global_dir / "recurring-tag-lifecycle-39-projects.md").write_text(
        "---\ntitle: Noise\ntype: principle\nstatus: approved\ntags: [lifecycle]\n---\n# Noise\n",
        encoding="utf-8",
    )

    report = lwm_context.build(tmp_path, tool="codex", project_path=None, format="json")
    data = json.loads(report.markdown)
    titles = {item["title"] for item in data["global_rules"]}
    assert titles == {"Approved", "Pattern"}
