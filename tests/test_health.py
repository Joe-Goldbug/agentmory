"""Health snapshot tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from lwm import health, ingest
from lwm.events import make_event


def _seed_events(root: Path) -> None:
    for tool in ("claude-code", "codex", "shell"):
        for i in range(2):
            event = make_event(
                tool=tool,
                project_path=str(root),
                project_id=f"git-{tool}-{i}",
                event_type="workflow_observation",
                task=f"{tool}-{i}",
            )
            inbox_dir = root / "raw" / "events" / "inbox" / "2026-07-11"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            (inbox_dir / f"{event['event_id']}.json").write_text(
                json.dumps(event, ensure_ascii=False), encoding="utf-8"
            )
    ingest.run(root, with_lock=False)


def test_health_records_each_tool(tmp_path: Path) -> None:
    _seed_events(tmp_path)
    snapshot = health.collect_and_write(tmp_path)
    tools = {t.tool for t in snapshot.tools}
    assert {"claude-code", "codex", "shell"} <= tools
    payload = json.loads((tmp_path / "state" / "health.json").read_text(encoding="utf-8"))
    assert payload["status"] in {"healthy", "degraded", "failed", "unknown"}
    assert "tools" in payload
    assert payload["inbox_counts"]["processed"] >= 6


def test_health_with_empty_inbox(tmp_path: Path) -> None:
    snapshot = health.collect_and_write(tmp_path)
    assert snapshot.status in {"healthy", "degraded", "failed", "unknown"}
    assert snapshot.inbox_counts["inbox"] == 0


def test_launchd_status_uses_print_history_for_idle_job(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def _fake_run(cmd, capture_output=False, text=False, timeout=0):
        calls.append(tuple(cmd))
        result = MagicMock()
        if cmd[:2] == ["launchctl", "list"]:
            result.returncode = 0
            result.stdout = "-\t0\tcom.ethan.lwm.harvest\n"
            return result
        result.returncode = 0
        result.stdout = (
            "gui/501/com.ethan.lwm.harvest = {\n"
            "\tstate = not running\n"
            "\truns = 3\n"
            "\tlast exit code = 0\n"
            "}\n"
        )
        return result

    monkeypatch.setattr(health, "shutil_which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(health.subprocess, "run", _fake_run)

    status = health._launchd_status()

    assert status["loaded"] is True
    assert status["pid"] is None
    assert status["has_history"] is True
    assert status["last_exit_code"] == 0
    assert status["runs"] == 3
    assert ("launchctl", "print", f"gui/{health.os.getuid()}/com.ethan.lwm.harvest") in calls


def test_launchd_status_stays_false_when_print_cannot_find_job(monkeypatch) -> None:
    def _fake_run(cmd, capture_output=False, text=False, timeout=0):
        result = MagicMock()
        if cmd[:2] == ["launchctl", "list"]:
            result.returncode = 0
            result.stdout = ""
            return result
        result.returncode = 113
        result.stdout = ""
        return result

    monkeypatch.setattr(health, "shutil_which", lambda _: "/bin/launchctl")
    monkeypatch.setattr(health.subprocess, "run", _fake_run)

    status = health._launchd_status()

    assert status == {"loaded": False, "label": "com.ethan.lwm.harvest"}


def test_health_detects_test_launch_agent_residue(tmp_path: Path) -> None:
    launch_agents = tmp_path / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    stale = launch_agents / "com.ethan.lwm.local.plist"
    stale.write_text(
        "<string>/Users/ethan/Library/Application Support/"
        "llm-workmem-runtime/test_schedule_runner_uses_loca0</string>",
        encoding="utf-8",
    )
    (launch_agents / "com.ethan.lwm.harvest.plist").write_text(
        "<string>/Users/ethan/Library/Application Support/"
        "llm-workmem-runtime/llm-workmem</string>",
        encoding="utf-8",
    )

    residue = health._stale_test_launch_agents(home=tmp_path)

    assert residue == (str(stale),)
