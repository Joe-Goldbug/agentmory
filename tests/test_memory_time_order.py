"""New UTC evidence must outrank older local-offset evidence."""
from lwm import context, dedup, project_memory
import json


def test_project_page_orders_by_instant_not_iso_spelling():
    older = project_memory.ProjectMemoryEntry(timestamp="2026-10-11T08:20:14+08:00", text="old truncated", event_id="older", tool="opencode", evidence_path="old.json", section="verifications")
    newer = project_memory.ProjectMemoryEntry(timestamp="2026-10-11T03:16:23Z", text="new complete", event_id="newer", tool="opencode", evidence_path="new.json", section="verifications")
    page = project_memory.render_project_page("p-test", {"verifications": [older, newer]}, {})
    assert page.index("new complete") < page.index("old truncated")


def test_verification_summary_preserves_values_after_short_handoff_boundary():
    text = project_memory._durable_text({"verification": ["Observed tool output: " + "x" * 280 + " interval_seconds=21600 run_on_boot=true"]}, "verifications")
    assert "interval_seconds=21600" in text
    assert "run_on_boot=true" in text


def test_verification_field_is_evidence_not_automatic_success():
    text = project_memory._durable_text({"verification": ["Observed output (status unknown): FAIL actual check"]}, "verifications")
    assert text.startswith("verification evidence:")
    assert "FAIL actual check" in text
    assert "verified:" not in text


def test_context_separates_current_runtime_from_dated_history(tmp_path):
    from datetime import datetime, timezone
    path = tmp_path / "state/health.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"status": "healthy", "checked_at": datetime.now(timezone.utc).isoformat(), "cycle": {"core_status": "success"}, "quality": {"audit_ok": True, "issues": 0}}))
    report = context.build(tmp_path, tool="codex", project_path=None)
    assert report.data["runtime_snapshot"]["status"] == "healthy"
    assert report.data["runtime_snapshot"]["fresh"] is True
    assert "Current Runtime Snapshot" in report.markdown
    assert "not proof of every client" in report.markdown


def test_project_aggregation_selects_newest_instant(tmp_path):
    rows = []
    for eid, ts in (("newer", "2026-10-11T03:16:23Z"), ("older", "2026-10-11T08:20:14+08:00")):
        event = {"event_id": eid, "timestamp": ts, "project_id": "p-test", "tool": "opencode", "event_type": "verification", "task": "Read actual policy", "verification": [eid], "tags": ["structured-summary"]}
        rows.append((tmp_path / (eid + ".json"), event, project_memory.classify_event(event)))
    pages = project_memory.aggregate_project_pages(tmp_path, rows)
    assert pages["p-test"][1]["event_id"] == "newer"


def test_recent_activity_orders_by_instant(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 11, 4, tzinfo=timezone.utc)
    monkeypatch.setattr(context, "datetime", FixedDateTime)
    monkeypatch.setattr(dedup, "load_event_index", lambda root: {"older": {"timestamp": "2026-10-11T08:20:14+08:00"}, "newer": {"timestamp": "2026-10-11T03:16:23Z"}})
    assert context._recent_tool_activity(tmp_path)[0]["timestamp"] == "2026-10-11T03:16:23Z"


def test_cross_tool_context_is_not_monopolized_by_high_volume_host(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    entries = []
    for tool, eid in [("codex", f"c{i}") for i in range(12)] + [("opencode", "o1"), ("antigravity", "a1")]:
        entries += [f"- {timestamp} — verification evidence: {tool} observed policy 21600 true",
                    f"  ↳ {tool} · {eid} · raw/{eid}.json"]
    page = tmp_path / "wiki/projects/p-test.md"
    page.parent.mkdir(parents=True)
    page.write_text("## Verifications\n\n" + "\n".join(entries), encoding="utf-8")
    monkeypatch.setattr(context, "_resolve_id_for_context", lambda *args: "p-test")
    selection = context._unique_lines
    with monkeypatch.context() as baseline:
        baseline.setattr(context, "_unique_lines", lambda lines, limit, **kwargs: selection(lines, limit))
        old = context.build(tmp_path, tool="codex", project_path=str(tmp_path))
        assert "↳ antigravity · a1" not in old.markdown
    report = context.build(tmp_path, tool="codex", project_path=str(tmp_path))
    selected = report.data["project"]["verifications"]
    assert len(selected) <= context.CONTEXT_LIMITS["verifications"]
    assert "↳ codex · c0" in report.markdown
    assert "↳ opencode · o1" in report.markdown
    assert "↳ antigravity · a1" in report.markdown
    assert "raw/a1.json" in report.markdown


def test_stale_tool_cannot_displace_recent_project_evidence():
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [f"- {timestamp} — latest\n  ↳ codex · c1 · raw/c1.json",
             f"- {timestamp} — newer check\n  ↳ codex · c2 · raw/c2.json",
             "- 2000-01-01T00:00:00Z — stale gap\n  ↳ antigravity · a1 · raw/a1.json"]
    result = context._unique_lines(lines, 2, diverse_tools=True)
    assert "c1" in result[0] and "c2" in result[1]


def test_markdown_budget_preserves_shared_workflow_and_complete_provenance(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(context, "_resolve_id_for_context", lambda *args: "p-test")
    monkeypatch.setattr(context, "load_published_memory", lambda *args, **kwargs: {
        "release_id": "release-test", "claims": [{"statement": "Inspect real evidence before editing.",
            "scope": "global", "tool": "opencode", "source_label": "agents"}], "conflicts": []})
    page = tmp_path / "wiki/projects/p-test.md"
    page.parent.mkdir(parents=True)
    rows = [f"- {timestamp} — {'long work ' * 250}\n  ↳ codex · e{i} · raw/e{i}.json" for i in range(6)]
    page.write_text("## Bugfixes\n\n" + "\n".join(rows), encoding="utf-8")
    report = context.build(tmp_path, tool="codex", project_path=str(tmp_path))
    assert "Unified Native Workflow Memory" in report.markdown
    assert "Inspect real evidence before editing." in report.markdown
    assert "source=opencode:agents" in report.markdown
    assert len(report.markdown) <= context.MAX_CONTEXT_CHARS
    for i in range(6):
        # A memory bullet and its source are one indivisible delivered record.
        if f"raw/e{i}.json" not in report.markdown:
            assert f"{'long work ' * 250}\n  ↳ codex · e{i}" not in report.markdown
    assert report.data["warnings"]
