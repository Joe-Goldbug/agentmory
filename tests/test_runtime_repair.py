from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import plistlib
import json

from lwm.audit import AuditReport
from lwm.events import make_event
from lwm.health import _classify, collect
from lwm.harvest import write_schedule_bundle
from lwm.privacy import sanitize_event


def test_core_cli_does_not_require_unpublished_optional_backup():
    import subprocess
    import sys

    code = """
import builtins
original = builtins.__import__
def without_backup(name, globals=None, locals=None, fromlist=(), level=0):
    if name == 'lwm.backup' or (name == 'lwm' and 'backup' in (fromlist or ())):
        raise ImportError('optional backup module unavailable')
    return original(name, globals, locals, fromlist, level)
builtins.__import__ = without_backup
import lwm.cli
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parents[1],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_host_conversation_id_is_not_an_authentication_secret():
    event = make_event(tool="codex", project_path="/work/project", project_id="git-project", event_type="session_start")
    event["session_id"] = "01a126a4-40f4-7fc1-bf3b-75372adf10bb"
    event["source"] = {"host_proof": {"integration": "codex-hook", "event": "SessionStart", "session_id": event["session_id"]}}
    assert sanitize_event(event)[2] is False
    event["source"]["host_proof"]["api_key"] = "sk-abcdefghijklmnopqrstuv"
    assert sanitize_event(event)[2] is True


def test_host_metadata_does_not_hide_real_secret_value():
    event = make_event(tool="codex", project_path="/work/project", project_id="git-project", event_type="session_start")
    event["session_id"] = "sk-abcdefghijklmnopqrstuv"
    event["source"] = {"host_proof": {"session_id": event["session_id"]}}
    assert sanitize_event(event)[2] is True


def _snapshot():
    return {"infrastructure": {"launchd": {"loaded": False}},
            "quality": {"audit_ok": True, "eval_verified": True, "eval_pass": 2, "eval_total": 2, "cbmem": {"status": "healthy"}},
            "data_flow": {"last_processed_at": "event", "last_cycle_failed": 0},
            "cycle": {"due": False, "last_success_at": "now", "last_status": "success", "context_smoke_ok": True, "last_cycle_exit_code": 0, "runtime_import_independent": True, "loop_exit_state": "completed_verified"},
            "inbox_counts": {"inbox": 0}}


def test_unloaded_scheduler_cannot_report_healthy():
    assert _classify(_snapshot(), strict=True) == "degraded"
    assert _classify(_snapshot(), strict=False) == "degraded"


def test_new_failed_attempt_is_not_hidden_by_previous_success(tmp_path: Path):
    now = datetime.now(timezone.utc)
    old = {"schema_version": 2, "cycle_id": "old", "finished_at": (now-timedelta(hours=1)).isoformat(), "core_status": "success"}
    new = {"schema_version": 2, "cycle_id": "new", "finished_at": now.isoformat(), "core_status": "failed_core"}
    with patch("lwm.health.load_latest", return_value=old), patch("lwm.health.load_last_attempt", return_value=new), patch("lwm.health.capabilities.summary", return_value={}):
        health = collect(tmp_path, strict=True, audit_report=AuditReport(tmp_path, 0, 0, 0, 2, 2))
    assert health.cycle["last_status"] == "failed_core"
    assert health.cycle["last_success_at"] == old["finished_at"]
    assert health.cycle["last_attempt_is_current"] is True
    assert health.status == "failed"


def test_six_hour_schedule_has_wake_coalescing_and_startup(tmp_path: Path):
    bundle = write_schedule_bundle(tmp_path, label="com.ethan.lwm.test", home=tmp_path/"home")
    plist = plistlib.loads(bundle.plist_path.read_bytes())
    assert plist["StartInterval"] == 21600
    assert plist["RunAtLoad"] is True
    assert plist["StartCalendarInterval"] == [{"Minute": minute} for minute in range(0, 60, 5)]
    assert (bundle.runtime_root/"state/schedule-policy.json").is_file()


def test_rejected_events_cannot_be_native_proof(tmp_path: Path):
    from lwm.capability_proof import _evidence_file

    rejected = tmp_path/"raw/events/rejected/2026-10-11/work.json"
    rejected.parent.mkdir(parents=True)
    rejected.write_text("{}")
    assert _evidence_file(tmp_path, str(rejected.relative_to(tmp_path))) is None


def test_relocated_proofs_share_one_event_index(tmp_path: Path, monkeypatch):
    from lwm.capability_proof import latest_proof_receipts

    now = datetime.now(timezone.utc).isoformat()
    per_tool = tmp_path/"state/receipts/tools/codex"
    per_tool.mkdir(parents=True)
    for i, direction in enumerate(("read", "write")):
        event = tmp_path/f"raw/events/processed/2026-10-11/event-{i}.json"
        event.parent.mkdir(parents=True, exist_ok=True)
        event.write_text("{}")
        (per_tool/f"proof-{i}.json").write_text(json.dumps({"tool":"codex", "direction":direction, "project_id":"p", "source":"native-hook", "status":"verified", "timestamp":now, "operation_id":str(i), "evidence_path":f"raw/events/inbox/2026-10-11/event-{i}.json"}))
    original = Path.rglob
    scans = []
    def counted(path, pattern):
        if "events" in path.parts:
            scans.append(str(path))
        return original(path, pattern)
    monkeypatch.setattr(Path, "rglob", counted)
    read, write = latest_proof_receipts(tmp_path, tool="codex")
    assert read is not None and write is not None
    assert len(scans) <= 2


def test_privacy_recovery_preserves_bytes_and_rechecks_secrets(tmp_path: Path):
    from lwm.ingest import recover_false_privacy_rejections

    event = make_event(tool="codex", project_path="/work", project_id="p", event_type="session_start")
    event.update(session_id="conversation-123456", source={"host_proof":{"integration":"codex-hook", "event":"SessionStart", "session_id":"conversation-123456"}})
    path = tmp_path/"raw/events/rejected/2026-10-11"/f"{event['event_id']}.json"
    path.parent.mkdir(parents=True)
    text = json.dumps(event)
    path.write_text(text)
    path.with_suffix(".json.reason").write_text("privacy: redacted: secret_kv\n")
    assert recover_false_privacy_rejections(tmp_path)["eligible"] == 1
    assert path.read_text() == text
    assert recover_false_privacy_rejections(tmp_path, apply=True)["requeued"] == 1
    assert (tmp_path/"raw/events/inbox/2026-10-11"/path.name).read_text() == text
    assert recover_false_privacy_rejections(tmp_path, apply=True)["requeued"] == 0


def test_new_boot_runs_even_with_fresh_success_and_marks_boot_once(tmp_path: Path, monkeypatch):
    from lwm import supervisor
    from lwm.cycle_state import begin, finish, write_receipt

    write_receipt(tmp_path, finish(begin("full", "due"), status="success"))
    policy = tmp_path / "state/schedule-policy.json"
    policy.write_text(json.dumps({"run_on_boot": True, "interval_seconds": 21600}))
    monkeypatch.setattr(supervisor, "_boot_id", lambda: "new-boot")
    calls = []
    monkeypatch.setattr("lwm.runner.run_cycle", lambda root: calls.append(root) or 0)
    assert supervisor.run_supervisor(tmp_path) == 0
    assert calls == [tmp_path.resolve()]
    assert json.loads(policy.read_text())["last_boot_id"] == "new-boot"
    assert supervisor.run_supervisor(tmp_path) == 0
    assert len(calls) == 1


def test_failed_boot_cycle_does_not_mark_it_successful(tmp_path: Path, monkeypatch):
    from lwm import supervisor

    policy = tmp_path / "state/schedule-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"run_on_boot": True}))
    monkeypatch.setattr(supervisor, "_boot_id", lambda: "new-boot")
    monkeypatch.setattr("lwm.runner.run_cycle", lambda root: 1)
    assert supervisor.run_supervisor(tmp_path) == 1
    assert "last_boot_id" not in json.loads(policy.read_text())


def test_receipts_from_different_projects_are_not_bidirectional():
    from lwm.capability_proof import capability_status

    receipt = {"source": "native-hook", "status": "verified", "timestamp": datetime.now(timezone.utc).isoformat(),
               "evidence_path": "raw/events/processed/e.json", "operation_id": "op"}
    result = capability_status(read_receipt={**receipt, "project_id": "a"},
                               write_receipt={**receipt, "project_id": "b"}, expected_project_id=None)
    assert result != "verified_bidirectional"


def test_context_limits_count_work_with_source_as_one_record():
    from lwm.context import _unique_lines

    assert _unique_lines(["- newest work", "\u21b3 tool event-new", "- older work", "\u21b3 tool event-old"], 1) == ["- newest work\n  \u21b3 tool event-new"]


def test_cheap_calendar_check_never_runs_a_full_cycle_before_six_hours(tmp_path: Path, monkeypatch):
    from lwm import supervisor
    from lwm.cycle_receipt import CycleReceiptV2, write_cycle_receipt

    now = datetime.now(timezone.utc)
    write_cycle_receipt(CycleReceiptV2(schema_version=2, cycle_id="clock", runtime_id="test",
        started_at=(now-timedelta(hours=6)).isoformat(), finished_at=(now-timedelta(hours=5, minutes=59)).isoformat(),
        core_status="success", overall_status="success"), tmp_path)
    calls = []
    monkeypatch.setattr("lwm.cycle_state.time.time", lambda: now.timestamp())
    monkeypatch.setattr("lwm.runner.run_cycle", lambda root: calls.append(root) or 0)
    assert supervisor.run_supervisor(tmp_path) == 0
    assert calls == []
    monkeypatch.setattr("lwm.cycle_state.time.time", lambda: (now+timedelta(minutes=5)).timestamp())
    assert supervisor.run_supervisor(tmp_path) == 0
    assert calls == [tmp_path.resolve()]
