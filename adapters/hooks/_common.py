"""Helper utilities shared by all IDE adapters."""

from __future__ import annotations

import json
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

_SENSITIVE_PATH_RE = re.compile(
    r"(^|/)(?:\.env(?:\.[^/]+)?|credentials|id_rsa|id_ed25519|secrets?(?:/|$)|tokens?(?:/|$))",
    re.IGNORECASE,
)


def redact_paths(paths: Iterable[str]) -> list[str]:
    """Return ``paths`` with any sensitive entry replaced by ``<REDACTED:path>``."""

    out: list[str] = []
    for raw in paths:
        p = str(raw)
        if _SENSITIVE_PATH_RE.search(p):
            out.append("<REDACTED:path>")
        else:
            out.append(p)
    return out


def structured_handoff(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return only an explicit structured handoff object from host input.

    Ordinary task, prompt, and transcript fields are intentionally ignored;
    lifecycle hooks may forward a handoff only when the host names one of the
    supported structured fields.
    """

    for key in ("handoff", "handoff_summary", "task_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return None


def analysis_job() -> bool:
    return os.environ.get("LWM_ANALYSIS_JOB") == "1"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(_text(v.get("text", "")) for v in value
                         if isinstance(v, dict) and v.get("type") in {"text", "output_text", "input_text"})
    return ""


def _assistant_report(value: str) -> str:
    value = re.sub(r"(?is)<think>.*?</think>", "", value)
    return value.split("<think>", 1)[0].strip()


def host_results(payload: Mapping[str, Any], *, host: str) -> dict[str, Any] | None:
    """Extract bounded observed outputs, not user requests or inferred success.

    Transcript paths must come from native hook input. Unsupported records
    are ignored; only the tail and the latest user/turn boundary are considered.
    """
    explicit = structured_handoff(payload)
    if explicit is not None:
        return explicit
    if analysis_job():
        return None
    rows = payload.get("transcript") or payload.get("messages") or []
    path = payload.get("transcript_path") or payload.get("transcriptPath")
    if isinstance(path, str) and path and not _SENSITIVE_PATH_RE.search(path):
        try:
            with Path(path).expanduser().open("rb") as stream:
                size = stream.seek(0, 2)
                stream.seek(max(0, size - 131072))
                data = stream.read(131072)
            lines = data.splitlines()
            if size > 131072:
                lines = lines[1:]
            rows = []
            for line in lines[-160:]:
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        except OSError:
            rows = []
    if not isinstance(rows, list):
        rows = []
    calls: dict[str, str] = {}
    results: list[str] = []
    assistant = ""
    boundary = ""
    for row in rows[-160:]:
        if not isinstance(row, dict):
            continue
        msg = row.get("message") or row.get("payload") or row
        if not isinstance(msg, dict):
            continue
        kind = msg.get("type", row.get("type"))
        role = msg.get("role", row.get("type"))
        content = msg.get("content")
        blocks = content if isinstance(content, list) else []
        is_result = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks)
        if (role in {"user", "human"} and not is_result) or kind in {"user_message", "turn_started"}:
            calls, results, assistant = {}, [], ""
            boundary = str(row.get("uuid") or msg.get("turn_id") or row.get("timestamp") or "")
        if role == "assistant" or kind == "agent_message":
            assistant = _text(content) or _text(msg.get("message")) or assistant
        if kind in {"function_call", "custom_tool_call"}:
            calls[str(msg.get("call_id"))] = str(msg.get("name") or "tool")
        if kind in {"function_call_output", "custom_tool_call_output"}:
            name = calls.get(str(msg.get("call_id")), "tool")
            raw_output = msg.get("output")
            output = _text(raw_output) if isinstance(raw_output, list) else str(raw_output or "")
            if output:
                results.append(f"Observed {name} output (status unknown): {output}"[:1000])
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls[str(block.get("id"))] = str(block.get("name") or "tool")
            if block.get("type") == "tool_result":
                name = calls.get(str(block.get("tool_use_id")), "tool")
                output = _text(block.get("content"))
                if output:
                    status = "FAIL" if block.get("is_error") else "status unknown"
                    results.append(f"Observed {name} output ({status}): {output}"[:1000])
    assistant = _assistant_report(_text(payload.get("last_assistant_message")) or assistant)
    if not assistant and not results:
        return None
    summary = {
        "objective": f"Observed {host} turn results",
        "current_state": (f"Assistant report (unverified): {assistant}" if assistant else "Tool outputs observed; task completion unknown")[:480],
        "verifications": results[-8:],
        "risks": [f"Assistant report (unverified): {assistant}"[:240]] if assistant else [],
        "open_questions": ["Task completion and claim support are unknown unless explicitly verified."],
    }
    turn = payload.get("turn_id") or payload.get("executionNum") or boundary
    fingerprint = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()[:24]
    summary["task_id"] = f"{host}:{turn or fingerprint}"
    return summary


def emit(
    root: Optional[Path],
    event: dict[str, Any],
    *,
    root_env: str = "LWM_ROOT",
) -> int:
    """Emit an event by invoking the central record CLI.

    Returns 0 on success, non-zero otherwise. Prints a short error to
    stderr if the recording path fails — adapters stay non-blocking.
    """

    target_root = root or Path(os.environ.get(root_env) or ".").expanduser()
    payload = json.dumps(event, ensure_ascii=False)
    cmd = [
        sys.executable,
        "-I",
        "-m",
        "lwm.cli",
        "hub",
        "record",
        payload,
        "--root",
        str(target_root.resolve()),
    ]
    try:
        import subprocess
    except ImportError:
        return 1
    env = dict(os.environ)
    # Hooks are shipped in the installed wheel. Never derive an import path
    # from this helper's source location: on the development machine that
    # location is the iCloud checkout and would break runtime independence.
    python_path = env.get("PYTHONPATH")
    if python_path:
        safe_entries = [
            entry for entry in python_path.split(os.pathsep)
            if "Mobile Documents" not in entry
        ]
        if safe_entries:
            env["PYTHONPATH"] = os.pathsep.join(safe_entries)
        else:
            env.pop("PYTHONPATH", None)
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if completed.returncode == 0:
        return 0
    sys.stderr.write(
        f"adapter record failed (rc={completed.returncode}): "
        f"{(completed.stderr or completed.stdout).strip()}\n"
    )
    return completed.returncode
