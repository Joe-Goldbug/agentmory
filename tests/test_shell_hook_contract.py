from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def test_shell_hook_uses_runtime_data_root_and_compatible_opt_out() -> None:
    hook = Path(__file__).parents[1] / "lwm" / "lwm_shell_hook.zsh"
    text = hook.read_text(encoding="utf-8")
    assert "Application Support/llm-workmem-runtime/llm-workmem" in text
    assert "LWM_SHELL_HOOK" in text
    assert "LBM_SHELL_HOOK" in text
    assert ".local/share/llm-workmem" not in text


def test_interactive_shell_records_real_exit_code_and_escaped_pwd(tmp_path: Path) -> None:
    """Exercise zsh's real preexec/precmd boundary, not only static text."""

    hook = Path(__file__).parents[1] / "lwm" / "lwm_shell_hook.zsh"
    quoted_dir = tmp_path / 'dir"with'
    quoted_dir.mkdir()
    commands = "\n".join(
        (
            f"source {shlex.quote(str(hook))}",
            f"cd {shlex.quote(str(quoted_dir))}",
            "false",
            "true",
            "exit",
        )
    )
    env = {**os.environ, "LWM_ROOT": str(tmp_path)}
    result = subprocess.run(
        ["zsh", "-f", "-i"],
        input=commands + "\n",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    rows = [
        json.loads(line)
        for path in (tmp_path / "raw" / "shell").glob("*.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    false_rows = [row for row in rows if row.get("command") == "false"]
    assert false_rows
    assert false_rows[-1]["exit_code"] == 1
    assert 'dir"with' in false_rows[-1]["pwd"]


def test_interactive_shell_emits_verified_lifecycle_receipts_without_commands(
    tmp_path: Path,
) -> None:
    """A real zsh process must prove read/write lifecycle, not just observe commands."""

    hook = Path(__file__).parents[1] / "lwm" / "lwm_shell_hook.zsh"
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    wrapper = tmp_path / "bin" / "lwm"
    wrapper.parent.mkdir()
    wrapper.write_text(
        "#!/bin/sh\n"
        f"exec {shlex.quote(sys.executable)} -m lwm.cli \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    commands = "\n".join(
        (
            f"cd {shlex.quote(str(project))}",
            f"source {shlex.quote(str(hook))}",
            f"source {shlex.quote(str(hook))}",
            "printf '%s\\n' shell-proof-test",
            "exit",
        )
    )
    env = {
        **os.environ,
        "LWM_ROOT": str(tmp_path),
        "LWM_BIN": str(wrapper),
        "LWM_SHELL_HOOK": "1",
    }
    result = subprocess.run(
        ["zsh", "-f", "-i"],
        input=commands + "\n",
        text=True,
        capture_output=True,
        env=env,
        cwd=project,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    events = []
    for path in (tmp_path / "raw" / "events").rglob("*.json"):
        events.append(json.loads(path.read_text(encoding="utf-8")))
    lifecycle = [
        event
        for event in events
        if event.get("tool") == "shell"
        and event.get("source", {}).get("kind") == "native-hook"
    ]
    assert len([event for event in lifecycle if event["event_type"] == "session_start"]) == 1
    assert len([event for event in lifecycle if event["event_type"] == "session_summary"]) == 1
    assert {event["event_type"] for event in lifecycle} >= {
        "session_start",
        "session_summary",
    }
    assert {
        event["source"]["host_proof"]["integration"] for event in lifecycle
    } == {"shell-hook"}
    assert {
        event["source"]["host_proof"]["event"] for event in lifecycle
    } == {"shell_session_start", "shell_session_end"}
    assert all("command" not in event for event in lifecycle)

    receipts = json.loads(
        (tmp_path / "state" / "capability-receipts.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipts["shell"]["status"] == "verified"
    assert receipts["shell"]["direction"] == "write"
