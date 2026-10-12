"""F06/F07: native evidence survives federation without gaining authority."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lwm import context
from lwm.memory_compiler import Candidate, save_candidate
from lwm.memory_federation import (
    CLAIMS_PATH,
    _extract_claims,
    compile_federated_memory,
    load_published_memory,
)


def test_native_wikilinks_in_copied_evidence_are_not_local_graph_edges():
    from lwm.memory_federation import _native_excerpt

    assert _native_excerpt("Read [[user-profile]] and [[memory|Memory]]") == "Read `user-profile` and `memory|Memory`"


def test_generated_memory_delivery_cannot_feed_back_as_native_truth(tmp_path):
    snapshot(tmp_path, "codex", "AGENTS.md", "# Workflow\n- Preserve user changes.\n<!-- LLM-WIKI:START -->\n- Fabricated generated instruction.\n<!-- LLM-WIKI:END -->\n- Verify real results.\n")
    snapshot(tmp_path, "codex", "mirror.md", "<!-- LWM-COMPANION:OWNED -->\n- Copied generated memory.\n")
    claims = _extract_claims(tmp_path, "codex")
    assert any("Preserve user changes" in item["statement"] for item in claims)
    assert any("Verify real results" in item["statement"] for item in claims)
    assert not any("generated" in item["statement"] for item in claims)


def snapshot(root: Path, tool: str, name: str, body: str) -> Path:
    path = root / "raw/tool-snapshots" / tool / "current" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def register(root: Path, **projects: str) -> dict[str, str]:
    paths = {name: str(root / name) for name in projects}
    state = root / "state"
    state.mkdir(exist_ok=True)
    (state / "project-map.json").write_text(
        json.dumps({paths[name]: pid for name, pid in projects.items()}), encoding="utf-8"
    )
    return paths


def records(root: Path) -> list[dict]:
    return json.loads((root / CLAIMS_PATH).read_text(encoding="utf-8"))["claims"]


def test_federation_repair_project_scope_survives_publish_and_recall(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-ather", Eva="p-eva")
    snapshot(tmp_path, "codex", "memory.md", f"""# Task Group: Ather release
scope: Release facts only
applies_to: cwd={paths['Ather']}; reuse_rule=verify the target
## Reusable knowledge
- Ather release requires consent evidence.
# Task Group: Eva release
applies_to: cwd={paths['Eva']}
## Reusable knowledge
- Eva release requires wallet evidence.
# Task Group: Unknown release
applies_to: cwd=/not-a-known-project
- Unknown release requires private evidence.
""")
    snapshot(tmp_path, "opencode", "user-profile.md", "## User preferences\nAlways verify before editing files.\n")
    compile_federated_memory(tmp_path)
    for name, foreign in (("Ather", "Eva"), ("Eva", "Ather")):
        report = context.build(tmp_path, tool="opencode", project_path=paths[name])
        claims = report.data["unified_memory"]["claims"]
        assert any(name in row["statement"] for row in claims)
        assert any(row["scope"] == "global" for row in claims)
        assert not any(foreign in row["statement"] or "Unknown release" in row["statement"] for row in claims)
    own = next(row for row in records(tmp_path) if row["statement"].startswith("Ather"))
    assert own["scope"] == ["p-ather"]
    assert own["project_path"] == paths["Ather"]
    assert own["section"] == ["Task Group: Ather release", "Reusable knowledge"]


def test_federation_repair_scope_unknown_is_not_agents_global(tmp_path: Path) -> None:
    snapshot(tmp_path, "codex", "agents.md", "## Project: Unregistered\n- Private project uses a secret staging endpoint.\n")
    compile_federated_memory(tmp_path)
    report = context.build(tmp_path, tool="codex", project_path=None)
    assert report.data["unified_memory"]["claims"] == []
    assert records(tmp_path)[0]["scope"] == "unknown"


def test_federation_repair_identical_text_has_distinct_project_identity(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a", Eva="p-e")
    for name, tool in (("Ather", "codex"), ("Eva", "opencode")):
        snapshot(tmp_path, tool, "memory.md", f"# Project: {name}\napplies_to: cwd={paths[name]}\n- Release needs a signed approval record.\n")
    compile_federated_memory(tmp_path)
    claims = load_published_memory(tmp_path)["claims"]
    assert len(claims) == 2
    assert len({row["claim_id"] for row in claims}) == 2


def test_federation_repair_heading_path_and_name_resolve_same_project(tmp_path: Path) -> None:
    paths = register(tmp_path, **{"BCM🛵": "p-bcm", "Ather": "p-a"})
    snapshot(tmp_path, "codex", "memory_summary.md", f"### {paths['BCM🛵']}\n- Public release requires holder consent.\n")
    snapshot(tmp_path, "opencode", "memory.md", "# Task Group: BCM release\n- BCM release has one daily allocation.\n")
    compile_federated_memory(tmp_path)
    claims = load_published_memory(tmp_path)["claims"]
    assert {tuple(row["scope"]) for row in claims} == {("p-bcm",)}
    assert len(context.build(tmp_path, tool="codex", project_path=paths["BCM🛵"]).data["unified_memory"]["claims"]) == 2


def test_federation_repair_paragraph_numbered_list_table_and_code(tmp_path: Path) -> None:
    snapshot(tmp_path, "opencode", "patterns.md", """---
updated: 2026-08-16
---
# Workflow
## Preferences
Check the actual target first,
then verify the evidence.

1. Ask only questions that change the decision.
   Keep the answer bounded and actionable.
2) Preserve all unrelated dirty changes.

| Trigger | Action | Verification |
| --- | --- | --- |
| Bug repair | Read the code before editing | Run focused tests |

```text
- This example must never become a fact.
```
---
Keep native instructions authoritative.
""")
    claims = _extract_claims(tmp_path, "opencode")
    assert len(claims) == 5
    assert claims[0]["statement"] == "Check the actual target first, then verify the evidence."
    assert claims[0]["format"] == "paragraph"
    assert claims[1]["statement"].endswith("Keep the answer bounded and actionable.")
    table = next(row for row in claims if row["format"] == "table")
    assert table["table"] == {"Trigger": "Bug repair", "Action": "Read the code before editing", "Verification": "Run focused tests"}
    assert table["section"] == ["Workflow", "Preferences"]
    assert all(row["scope"] == "global" for row in claims)


def test_federation_repair_dates_do_not_relabel_copied_report(tmp_path: Path) -> None:
    path = snapshot(tmp_path, "opencode", "validation_report.md", "# Validation Report\nDate: 2026-07-03\n\n- Runtime integration passed the inventory check.\n")
    now = datetime.now(timezone.utc).timestamp()
    os.utime(path, (now, now))
    claim = _extract_claims(tmp_path, "opencode")[0]
    assert claim["document_at"].startswith("2026-07-03")
    assert claim["observed_at"].startswith("2026-07-03")
    assert claim["captured_at"] != claim["observed_at"]
    assert claim["verified_at"] is None
    compile_federated_memory(tmp_path)
    assert load_published_memory(tmp_path)["claims"] == []
    assert records(tmp_path)[0]["status"] == "stale"


def test_federation_repair_asserted_verified_and_rollout_dates_are_separate(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a")
    today = datetime.now(timezone.utc).date().isoformat()
    snapshot(tmp_path, "codex", "memory.md", f"""# Task Group: Ather consent
applies_to: cwd={paths['Ather']}
## Task 1: Verify consent
### rollout_summary_files
- rollout_summaries/2026-07-03T06-04-03-report.md (cwd={paths['Ather']}, updated_at=2026-10-10, rollout_path=/native/session)
### Reusable knowledge
- Consent evidence was recorded in the audit.
- Current consent policy requires explicit approval [asserted: 2026-09-23] [verified: {today}]
""")
    claims = _extract_claims(tmp_path, "codex")
    assert len(claims) == 2
    assert claims[0]["asserted_at"].startswith("2026-07-03")
    assert claims[0]["verified_at"] is None
    assert claims[0]["source_events"][0]["updated_at"].startswith("2026-10-10")
    assert claims[1]["asserted_at"].startswith("2026-09-23")
    assert claims[1]["verified_at"].startswith(today)


@pytest.mark.parametrize("name,old,new", [
    ("BCM", "BCM uses one daily auction for public release.", "The active BCM direction is daily free mint. The prior daily-auction note is superseded for the current release model."),
    ("Catalog", "Catalog uses one daily auction for public release.", "The active Catalog direction is daily free mint. The prior daily-auction note is superseded for the current release model."),
    ("Registry", "Registry uses password login for user access.", "Registry uses passkeys now. Password login is superseded for user access."),
])
def test_federation_repair_explicit_supersession_is_generic(tmp_path: Path, name: str, old: str, new: str) -> None:
    paths = register(tmp_path, **{name: "p1", "Other": "p2"})
    snapshot(tmp_path, "opencode", "old.md", f"# Project: {name}\napplies_to: cwd={paths[name]}\n- {old}\n")
    snapshot(tmp_path, "codex", "new.md", f"# Project: {name}\napplies_to: cwd={paths[name]}\n- {new}\n")
    snapshot(tmp_path, "codex", "other.md", f"# Project: Other\napplies_to: cwd={paths['Other']}\n- {old}\n")
    compile_federated_memory(tmp_path)
    own = [row for row in records(tmp_path) if row.get("scope") == ["p1"]]
    retired = next(row for row in own if row["statement"] == old)
    assert retired["status"] == "superseded"
    assert retired["superseded_by"] == next(row["claim_id"] for row in own if row["statement"] == new)
    assert next(row for row in records(tmp_path) if row.get("scope") == ["p2"])["status"] == "active"


def test_federation_repair_explicit_source_supersession(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "old-policy.md", "# Project: Registry\n- Public login requires a password challenge.\n- Account recovery requires a support ticket.\n")
    snapshot(tmp_path, "codex", "new-policy.md", "---\nproject_id: p1\nsupersedes: old-policy.md\n---\n- Public login and recovery both use signed passkeys.\n")
    compile_federated_memory(tmp_path)
    assert {row["status"] for row in records(tmp_path) if row["source_label"] == "old-policy"} == {"superseded"}


def test_federation_repair_negation_is_reviewed_not_published_together(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "memory.md", "# Project: Registry\n- Registry stores raw user photos on chain.\n")
    snapshot(tmp_path, "codex", "memory.md", "# Project: Registry\n- Registry does not store raw user photos on chain.\n")
    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)
    assert published["claims"] == []
    assert len(published["conflicts"]) == 2
    assert all(row["conflict_with"] for row in published["conflicts"])


def test_federation_repair_latest_verified_user_directive_beats_tool(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    snapshot(tmp_path, "opencode", "memory.md", f"# Project: Registry\n## User directives\n- Login: use passwords [verified: {yesterday}]\n")
    snapshot(tmp_path, "codex", "memory.md", f"# Project: Registry\n## User directives\n- Login: use passkeys [verified: {today}]\n")
    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)
    assert len(published["claims"]) == 1
    assert published["claims"][0]["tool"] == "codex"
    assert "passkeys" in published["claims"][0]["statement"]


def test_federation_repair_project_claims_not_starved_by_global_limit(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a")
    snapshot(tmp_path, "opencode", "agents.md", "".join(f"- Global workflow rule {i}: retain user control.\n" for i in range(10)))
    snapshot(tmp_path, "codex", "memory.md", "# Project: Ather\n- Ather release requires explicit user consent.\n")
    compile_federated_memory(tmp_path)
    report = context.build(tmp_path, tool="codex", project_path=paths["Ather"], limit=6)
    assert any(row["scope"] == ["p-a"] for row in report.data["unified_memory"]["claims"])
    assert "auxiliary evidence" in report.markdown.lower()
    assert "native" in (tmp_path / "wiki/unified/workflow-memory.md").read_text().lower()


def test_federation_repair_project_fact_in_global_preferences_does_not_leak(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a", Eva="p-e")
    snapshot(tmp_path, "codex", "memory_summary.md", "## User preferences\n- Always check evidence before editing files.\n- Ather releases require profile consent records.\n")
    compile_federated_memory(tmp_path)
    report = context.build(tmp_path, tool="codex", project_path=paths["Eva"])
    assert any("Always check" in row["statement"] for row in report.data["unified_memory"]["claims"])
    assert not any("Ather" in row["statement"] for row in report.data["unified_memory"]["claims"])


def test_federation_repair_codex_task_references_retain_event_dates(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a")
    snapshot(tmp_path, "codex", "memory.md", f"""# Task Group: Ather release
applies_to: cwd={paths['Ather']}
## Task 1: Audit release
### rollout_summary_files
- rollout_summaries/2026-07-03T06-04-03-audit.md (updated_at=2026-10-10)
## Task 2: Verify release
### rollout_summary_files
- rollout_summaries/2026-09-23T14-23-25-proof.md (updated_at=2026-10-10)
## Reusable knowledge
- The release gate was audited without deployment. [Task 1]
- The release gate was verified in isolation. [Task 2]
""")
    claims = _extract_claims(tmp_path, "codex")
    assert claims[0]["asserted_at"].startswith("2026-07-03")
    assert claims[1]["asserted_at"].startswith("2026-09-23")
    assert len(claims[0]["source_events"]) == 1


def test_federation_repair_actual_legacy_note_shape_preserves_safeguards(tmp_path: Path) -> None:
    paths = register(tmp_path, **{"BCM🛵": "p-bcm", "Ather": "p-a"})
    snapshot(tmp_path, "codex", "ad_hoc_notes/20260905-142546-bcm-auction.md", """# BCM rarity and daily auction requirements
- The founder likes the model of auctioning one BCM every day while operating one daily story.
- Current recommended failed-auction policy: move the asset into a retry pool, then a community reserve.
- Future valuable-asset allocation needs MEV and Sybil defenses; bind every request ID to the auction and committed pool; never permit admin rerolls.
""")
    snapshot(tmp_path, "codex", "memory.md", f"""# Task Group: BCM release
applies_to: cwd={paths['BCM🛵']}
## Reusable knowledge
- The active BCM direction is one public free-mint slot per day. Auction language is historical/superseded.
- The prior daily-auction note is superseded for the current V2 release model.
""")
    compile_federated_memory(tmp_path)
    rows = records(tmp_path)
    old = [row for row in rows if "auction" in row["source_label"]]
    assert all(row["scope"] == ["p-bcm"] for row in old)
    assert all(row["document_at"].startswith("2026-09-05") for row in old)
    assert {row["status"] for row in old if "founder" in row["statement"] or "recommended" in row["statement"]} == {"superseded"}
    assert next(row for row in old if "defenses" in row["statement"])["status"] == "active"
    assert next(row for row in rows if "active BCM" in row["statement"])["status"] == "active"


def test_federation_repair_explicit_unknown_scope_overrides_agents_default(tmp_path: Path) -> None:
    snapshot(tmp_path, "codex", "agents.md", "---\nscope: unknown\n---\n- Private work has an unresolved repository identity.\n")
    compile_federated_memory(tmp_path)
    assert records(tmp_path)[0]["scope"] == "unknown"
    assert context.build(tmp_path, tool="codex", project_path=None).data["unified_memory"]["claims"] == []


def test_federation_repair_unverified_different_wording_enters_review(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "memory.md", "# Project: Registry\n- Public login uses passwords for account access.\n")
    snapshot(tmp_path, "codex", "memory.md", "# Project: Registry\n- Public login uses passkeys for account access.\n")
    compile_federated_memory(tmp_path)
    assert len(load_published_memory(tmp_path)["conflicts"]) == 2


def test_federation_repair_context_json_budget_keeps_valid_scoped_json(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a", Eva="p-e")
    for tool in ("codex", "opencode"):
        snapshot(tmp_path, tool, "memory.md", "# Project: Ather\n" + "".join(
            f"- Consent gate {i}: " + "retain explicit approval evidence " * 25 + ".\n" for i in range(6)
        ))
    compile_federated_memory(tmp_path)
    report = context.build(tmp_path, tool="codex", project_path=paths["Ather"], format="json")
    parsed = json.loads(report.markdown)
    assert len(report.markdown) <= context.MAX_CONTEXT_CHARS
    assert parsed == report.data
    assert parsed["unified_memory"]["claims"]
    assert all(row["scope"] == ["p-a"] for row in parsed["unified_memory"]["claims"])


def test_federation_repair_prose_source_supersession_keeps_own_scope(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "old-policy.md", "# Project: Registry\n- Public login requires password approval.\n")
    snapshot(tmp_path, "codex", "new-policy.md", "# Project: Registry\n- User directive: new-policy.md supersedes old-policy.md. Use signed passkeys for login.\n")
    compile_federated_memory(tmp_path)
    assert next(row for row in records(tmp_path) if row["source_label"] == "old-policy")["status"] == "superseded"


def test_federation_repair_inline_supersession_not_lost_after_long_statement(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "old-policy.md", "# Project: Registry\n- Public login requires password approval.\n")
    snapshot(tmp_path, "codex", "new-policy.md", "# Project: Registry\n- Public login requires signed passkeys. " + "Keep evidence. " * 50 + "[supersedes: old-policy.md]\n")
    compile_federated_memory(tmp_path)
    assert next(row for row in records(tmp_path) if row["source_label"] == "old-policy")["status"] == "superseded"
    assert len(next(row for row in records(tmp_path) if row["source_label"] == "new-policy")["statement"]) > 600


def test_federation_repair_explicit_project_ids_schema_routes_cross_project(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a", Eva="p-e", Other="p-o")
    snapshot(tmp_path, "codex", "memory.md", "---\nproject_ids: [p-a, p-e]\n---\n- Shared consent review needs independent evidence.\n")
    compile_federated_memory(tmp_path)
    for name in ("Ather", "Eva"):
        report = context.build(tmp_path, tool="codex", project_path=paths[name])
        assert report.data["unified_memory"]["claims"][0]["cross_project"] is True
    assert context.build(tmp_path, tool="codex", project_path=paths["Other"]).data["unified_memory"]["claims"] == []


def test_federation_repair_mutual_explicit_retirement_requires_review(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "a.md", "---\nproject_id: p1\nsupersedes: b.md\n---\n- Public login requires password approval.\n")
    snapshot(tmp_path, "codex", "b.md", "---\nproject_id: p1\nsupersedes: a.md\n---\n- Public login requires passkey approval.\n")
    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)
    assert published["claims"] == []
    assert len(published["conflicts"]) == 2


def test_federation_repair_retired_copy_cannot_retire_live_new_source(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    snapshot(tmp_path, "opencode", "old-policy.md", f"---\nproject_id: p1\nverified: {yesterday}\nsupersedes: new-policy.md\n---\n- Public login requires password approval.\n")
    snapshot(tmp_path, "codex", "new-policy.md", f"---\nproject_id: p1\nverified: {today}\nsupersedes: old-policy.md\n---\n- Public login requires passkey approval.\n")
    compile_federated_memory(tmp_path)
    assert len(load_published_memory(tmp_path)["claims"]) == 1
    assert load_published_memory(tmp_path)["claims"][0]["source_label"] == "new-policy"


def test_federation_repair_duplicate_keeps_all_supporting_provenance(tmp_path: Path) -> None:
    for tool in ("opencode", "codex"):
        snapshot(tmp_path, tool, "agents.md", "- Verify the actual target before editing files.\n")
    compile_federated_memory(tmp_path)
    claim = load_published_memory(tmp_path)["claims"][0]
    assert {entry["tool"] for entry in claim["provenance"]} == {"opencode", "codex"}
    assert all(entry["statement"] == claim["statement"] for entry in claim["provenance"])


def test_federation_repair_chinese_explicit_replacement_is_generic(tmp_path: Path) -> None:
    register(tmp_path, Registry="p1")
    snapshot(tmp_path, "opencode", "memory.md", "# Project: Registry\n- Registry 登录使用密码验证并保存审核记录。\n")
    snapshot(tmp_path, "codex", "memory.md", "# Project: Registry\n- 用户要求不再使用密码验证，改为通行密钥并保存审核记录。\n")
    compile_federated_memory(tmp_path)
    assert next(row for row in records(tmp_path) if row["tool"] == "opencode")["status"] == "superseded"


def test_federation_repair_analysis_suggestions_are_scoped_unapproved_evidence(tmp_path: Path) -> None:
    paths = register(tmp_path, Ather="p-a", Eva="p-e", Other="p-o")
    processed = tmp_path / "raw/events/processed"
    processed.mkdir(parents=True)
    for eid, pid in (("e1", "p-a"), ("e2", "p-e"), ("counter", "p-a")):
        (processed / f"{eid}.json").write_text(json.dumps({
            "event_id": eid, "project_id": pid, "tool": "codex", "event_type": "decision",
            "task": "Review signed consent evidence", "decisions": ["Review signed consent evidence"],
        }), encoding="utf-8")
    save_candidate(tmp_path, Candidate(
        candidate_id="suggestion", kind="workflow", claim="Review signed consent evidence",
        scope=("p-a", "p-e"), evidence_ids=("e1", "e2"), counterevidence_ids=("counter",),
        uncertainty="Requires a human review", state="analyzed",
    ))
    for name in ("Ather", "Eva"):
        report = context.build(tmp_path, tool="codex", project_path=paths[name])
        row = report.data["analysis_suggestions"][0]
        assert row["candidate_id"] == "suggestion"
        assert row["cross_project"] is True
        assert row["status"] == "inferred" and row["approval"] == "unapproved"
        assert row["native_rule_authority"] is False
        assert row["counterevidence_ids"] == ["counter"]
        assert row["evidence"]
        assert report.data["accepted_analysis_candidates"] == []
        assert "Analysis Suggestions (Unapproved)" in report.markdown
        assert "counter" in report.markdown and "Requires a human review" in report.markdown
    for path in (paths["Other"], None):
        assert context.build(tmp_path, tool="codex", project_path=path).data["analysis_suggestions"] == []
    (processed / "e2.json").unlink()
    assert context.build(tmp_path, tool="codex", project_path=paths["Ather"]).data["analysis_suggestions"] == []


def test_federation_repair_analysis_suggestions_respect_json_budget(tmp_path: Path, monkeypatch) -> None:
    paths = register(tmp_path, Ather="p-a")
    import lwm.memory_compiler as compiler

    monkeypatch.setattr(compiler, "load_analysis_suggestions", lambda *a, **k: [{
        "candidate_id": f"suggestion-{i}", "scope": ["p-a"], "claim": "Review consent " * 100,
        "evidence": [{"event_id": f"e{i}", "decisions": ["Review consent " * 100]}],
        "status": "inferred", "approval": "unapproved", "human_review_required": True,
    } for i in range(20)])
    # Also patch the imported callable once the Context integration exists.
    if hasattr(context, "load_analysis_suggestions"):
        monkeypatch.setattr(context, "load_analysis_suggestions", compiler.load_analysis_suggestions)
    report = context.build(tmp_path, tool="codex", project_path=paths["Ather"], format="json")
    assert "analysis_suggestions" in report.data
    assert json.loads(report.markdown) == report.data
    assert len(report.markdown) <= context.MAX_CONTEXT_CHARS
