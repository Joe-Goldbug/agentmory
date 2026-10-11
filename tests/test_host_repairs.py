"""Host repairs run only against temporary data, never providers."""
import json
import subprocess
import os
import shlex
from pathlib import Path

from adapters.hooks import _common, codex_native
from lwm import inbox, lifecycle


def test_repeated_start_after_move(tmp_path):
    first = lifecycle.start(tmp_path, tool="codex", project_path=tmp_path, session_id="s")
    moved = inbox.move_event(first.event_path, target_bucket="processed")
    second = lifecycle.start(tmp_path, tool="codex", project_path=tmp_path, session_id="s")
    assert second.event_path == moved
    assert second.context_markdown
    assert len(list((tmp_path / "raw/events").rglob("*.json"))) == 1


def test_transcript_captures_results_not_request(tmp_path):
    rows = [
        {"type": "user", "message": {"role": "user", "content": "Please pass tests"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest"}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "FAILED test_one", "is_error": True}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": "Tests still fail."}},
    ]
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    summary = _common.host_results({"transcript_path": str(path)}, host="claude-code")
    assert "FAILED" in " ".join(summary["verifications"])
    assert "Please pass" not in json.dumps(summary)
    assert summary["current_state"].startswith("Assistant report (unverified):")
    assert not summary.get("changes")


def test_prompt_only_not_result():
    assert _common.host_results({"transcript": [{"role": "assistant", "content": "Old result"},
                                                 {"role": "user", "content": "New request"}]}, host="codex") is None


def test_antigravity_actual_transcript_results_are_bounded_and_turn_scoped():
    rows = [
        {"type": "GENERIC", "step_index": 0, "status": "DONE", "content": "old output"},
        {"type": "USER_INPUT", "step_index": 1, "content": "private request"},
        {"type": "EPHEMERAL_MESSAGE", "step_index": 2, "content": "injected context"},
        {"type": "PLANNER_RESPONSE", "step_index": 3, "status": "DONE",
         "tool_calls": [{"name": "view_file", "args": {"path": "private input"}}]},
        {"type": "GENERIC", "step_index": 4, "status": "DONE", "content": "interval_seconds=21600, run_on_boot=true"},
        {"type": "PLANNER_RESPONSE", "step_index": 5, "status": "DONE",
         "content": "<think>private thought</think>Read policy; restart unverified"},
    ]
    summary = _common.host_results({"transcript": rows}, host="antigravity")
    assert summary is not None
    assert "interval_seconds=21600" in " ".join(summary["verifications"])
    assert "status unknown" in summary["verifications"][0]
    assert summary["task_id"] == "antigravity:1"
    rendered = json.dumps(summary)
    for excluded in ("private request", "private input", "private thought", "injected context", "old output"):
        assert excluded not in rendered
    assert "restart unverified" in rendered
    assert _common.host_results({"transcript": rows + [{"type": "USER_INPUT", "step_index": 6, "content": "new request"}]}, host="antigravity") is None


def test_antigravity_unknown_or_incomplete_steps_are_not_results():
    rows = [{"type": "GENERIC", "step_index": 1, "status": "RUNNING", "content": "partial output"},
            {"type": "THOUGHT", "step_index": 2, "status": "DONE", "content": "private reasoning"},
            {"type": "PLANNER_RESPONSE", "step_index": 3, "status": "RUNNING", "content": "partial report"}]
    assert _common.host_results({"transcript": rows}, host="antigravity") is None


def test_antigravity_task_ids_are_scoped_to_conversation():
    rows = [{"type": "USER_INPUT", "step_index": 0, "content": "request"},
            {"type": "PLANNER_RESPONSE", "step_index": 1, "status": "DONE", "content": "Observed report"}]
    first = _common.host_results({"transcript": rows, "conversationId": "one", "executionNum": 1}, host="antigravity")
    second = _common.host_results({"transcript": rows, "conversationId": "two", "executionNum": 1}, host="antigravity")
    assert first["task_id"] == "antigravity:one:1"
    assert first["task_id"] != second["task_id"]


def test_antigravity_file_values_survive_compact_project_summary():
    from lwm.project_memory import _durable_text
    output = ("Created At: date\nCompleted At: date\nFile Path: `file:///tmp/policy.json`\n"
              "Total Lines: 4\nTotal Bytes: 80\nShowing lines 1 to 4\n" + "formatting instruction " * 30 +
              '\n1: {\n2: "interval_seconds": 21600,\n3: "run_on_boot": true\n4: }\nfile complete')
    summary = _common.host_results({"transcript": [{"type": "GENERIC", "status": "DONE", "content": output}]}, host="antigravity")
    rendered = _durable_text({"verification": summary["verifications"]}, "verifications")
    assert '"interval_seconds": 21600' in rendered
    assert '"run_on_boot": true' in rendered
    assert "file:///tmp/policy.json" in rendered
    assert "formatting instruction" not in rendered
    legacy = {"tool": "antigravity", "verification": ["Observed AGY step output (status unknown): " + output]}
    original = json.dumps(legacy)
    legacy_rendered = _durable_text(legacy, "verifications")
    assert '"run_on_boot": true' in legacy_rendered
    assert "status unknown" in legacy_rendered
    assert json.dumps(legacy) == original


def test_internal_reasoning_is_not_a_durable_assistant_report():
    result = _common.host_results({"last_assistant_message": "<think>maybe pretend success</think>Read schedule; launchd not verified"}, host="opencode")
    assert result is not None
    assert "pretend" not in json.dumps(result)
    assert "launchd not verified" in result["current_state"]


def test_internal_analysis_no_events(tmp_path, monkeypatch):
    monkeypatch.setenv("LWM_ANALYSIS_JOB", "1")
    assert codex_native.handle_payload({"cwd": str(tmp_path), "session_id": "s"},
                                       root=tmp_path, phase="SessionStart") == {}
    lifecycle.start(tmp_path, tool="codex", project_path=tmp_path, session_id="s")
    lifecycle.stop(tmp_path, tool="codex", project_path=tmp_path, session_id="s")
    assert not list((tmp_path / "raw/events").rglob("*.json"))


def test_stop_per_turn_and_empty_metadata(tmp_path):
    summary = {"objective": "Observed host results", "current_state": "Tests failed",
               "verifications": ["FAIL: pytest exit 1"]}
    for turn in ("t1", "t1", "t2", "t2"):
        lifecycle.stop(tmp_path, tool="codex", project_path=tmp_path, session_id="s",
                       task_id=turn, handoff_summary=summary)
    events = [json.loads(p.read_text()) for p in (tmp_path / "raw/events").rglob("*.json")]
    assert len([e for e in events if "structured-summary" in e.get("tags", [])]) == 2
    empty = lifecycle.stop(tmp_path, tool="codex", project_path=tmp_path, session_id="empty")
    assert json.loads(empty.event_path.read_text())["importance"] == "scratch"


def test_codex_turn_stop(tmp_path):
    codex_native.handle_payload({"cwd": str(tmp_path), "session_id": "s", "turn_id": "t1",
                                 "last_assistant_message": "Parser updated; tests pending"},
                                root=tmp_path, phase="Stop")
    events = [json.loads(p.read_text()) for p in (tmp_path / "raw/events").rglob("*.json")]
    assert any("tests pending" in json.dumps(e) for e in events)
    assert not any("execution completed" in json.dumps(e) for e in events)


def test_opencode_behavior(tmp_path):
    script = Path(__file__).with_name("host-opencode.ts")
    result = subprocess.run(["bun", str(script), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    from lwm.events import validate_event
    events = list((tmp_path / "raw/events/inbox").glob("*/*.json"))
    assert len(events) == 1
    assert validate_event(json.loads(events[0].read_text())).ok


def test_companion_behavior(tmp_path):
    script = Path(__file__).with_name("host-companion.cjs")
    result = subprocess.run(["node", str(script), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_plugin_exact_source(tmp_path):
    from lwm.hooks_gen import _opencode_plugin
    source = Path(__file__).parents[1] / "integrations/opencode/lwm-workmem.ts"
    assert _opencode_plugin(tmp_path) == source.read_text()


def test_shell_context_reaches_agent_argv(tmp_path):
    hook = Path(__file__).parents[1] / "lwm/lwm_shell_hook.zsh"
    binary = tmp_path / "lwm"
    binary.write_text("#!/bin/sh\ncase \"$*\" in *markdown*) printf 'project context marker';; *) printf '{}';; esac\n")
    binary.chmod(0o755)
    agent = tmp_path / "codex"
    agent.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
    agent.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "LWM_ROOT": str(tmp_path), "LWM_BIN": str(binary)}
    command = f"source {shlex.quote(str(hook))}\nlwm-agent codex 'inspect only' --model native-model\n"
    result = subprocess.run(["zsh", "-f", "-i"], input=command, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "project context marker" in result.stdout
    assert "inspect only" in result.stdout
    assert "native-model" in result.stdout
    env["LWM_ANALYSIS_JOB"] = "1"
    internal = subprocess.run(["zsh", "-f", "-i"], input=command, env=env, text=True, capture_output=True)
    assert "project context marker" not in internal.stdout
    assert "inspect only" in internal.stdout


def test_delivery_source_explicit_and_bounded_transcript(tmp_path):
    result = lifecycle.start(tmp_path, tool="codex", project_path=tmp_path, session_id="s")
    delivery = json.loads(result.event_path.read_text())["source"]["delivery"]
    assert delivery["stage"] == "prepared-for-host"
    assert delivery["host_mechanism"] == "hookSpecificOutput.additionalContext"
    assert len(delivery["context_sha256"]) == 64
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"role": "assistant", "content": "x" * 200000}))
    assert _common.host_results({"transcript_path": str(transcript)}, host="codex") is None


def test_codex_shared_installer_enables_real_start_and_turn_hooks(tmp_path):
    from lwm.adapters import _write_codex_hooks
    target = tmp_path / ".codex/hooks.json"
    target.parent.mkdir()
    target.write_text(json.dumps({"hooks": {"SessionStart": [], "Stop": [{"matcher": "", "hooks": [
        {"type": "command", "command": "user-owned-stop"},
        {"type": "command", "command": "python -m adapters.hooks.codex_native --phase Stop"},
    ]}]}}))
    _write_codex_hooks(target, tmp_path / "data", home=tmp_path)
    first = target.read_text()
    _write_codex_hooks(target, tmp_path / "data", home=tmp_path)
    assert target.read_text() == first
    hooks = json.loads(first)["hooks"]
    assert set(hooks) == {"SessionStart", "SessionEnd", "UserPromptSubmit", "Stop"}
    for event, groups in hooks.items():
        generated = [h for g in groups for h in g["hooks"] if "adapters.hooks.codex_native" in h["command"]]
        assert len(generated) == 1
        assert f"--phase {event}" in generated[0]["command"]
        assert generated[0]["type"] == "command"
    assert any(h["command"] == "user-owned-stop" for g in hooks["Stop"] for h in g["hooks"])
def test_observed_work_is_durable_before_receipt_side_effects(tmp_path, monkeypatch):
    from lwm import lifecycle
    def unavailable(*args, **kwargs):
        raise RuntimeError("receipt unavailable")
    monkeypatch.setattr(lifecycle.capabilities, "record", unavailable)
    import pytest
    with pytest.raises(RuntimeError, match="receipt unavailable"):
        lifecycle.stop(tmp_path, tool="codex", project_path=tmp_path,
                       session_id="real-host-session", task_id="turn-one",
                       handoff_summary={"objective": "Observed read", "verifications": ["Observed output: " + "x" * 400 + " interval_seconds=21600, run_on_boot=true"]})
    events = [json.loads(path.read_text()) for path in (tmp_path / "raw/events/inbox").glob("*/*.json")]
    work = [event for event in events if "structured-summary" in event.get("tags", [])]
    assert len(work) == 1
    assert work[0]["session_id"] == "real-host-session"
    assert "run_on_boot=true" in work[0]["verification"][0]
    assert len(work[0]["verification"][0]) > 240
    assert work[0]["source_receipt_id"] in {event["event_id"] for event in events}


def test_codex_end_reuses_native_turn_identity():
    rows = [{"type": "event_msg", "payload": {"type": "task_started", "turn_id": "native-turn"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": "private request"}},
            {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "c", "output": "actual result"}}]
    from adapters.hooks._common import host_results
    end = host_results({"transcript": rows}, host="codex")
    stop = host_results({"transcript": rows, "turn_id": "native-turn"}, host="codex")
    assert end["task_id"] == stop["task_id"] == "codex:native-turn"

