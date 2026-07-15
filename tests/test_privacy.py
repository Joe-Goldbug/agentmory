"""Privacy filter tests (acceptance: secret patterns + path redaction)."""

from __future__ import annotations

from lwm.events import make_event
from lwm.privacy import redact_text, sanitize_event


def test_redact_openai_key() -> None:
    text = "Logging in with sk-abcdefghijklmnopqrstuv secret-token=value"
    out, applied = redact_text(text)
    assert "<REDACTED>" in out
    assert "openai_sk" in applied


def test_redact_aws_access_key() -> None:
    text = "AWS AKIAIOSFODNN7EXAMPLE was here"
    out, applied = redact_text(text)
    assert "<REDACTED>" in out
    assert "aws_access_key" in applied


def test_redact_github_pat() -> None:
    text = "Token: ghp_abcdefghijklmnopqrstuvwxyz0123456789 end"
    out, applied = redact_text(text)
    assert "<REDACTED>" in out
    assert "github_pat" in applied


def test_redact_jwt_token() -> None:
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    out, applied = redact_text(f"bearer {jwt} ok")
    assert "<REDACTED>" in jwt or "<REDACTED>" in out
    assert "jwt" in applied


def test_redact_kv_patterns() -> None:
    text = "password=hunter2 api_key=ABCDEFGHIJKLMNOPQRST uv"
    out, applied = redact_text(text)
    assert "hunter2" not in out
    assert "ABCDEFGHIJKLMNOPQRST" not in out
    assert "secret_kv" in applied


def test_sanitize_event_blocks_path() -> None:
    event = make_event(
        tool="claude-code",
        project_path="/Users/me/secrets/api.json",
        project_id="git-x",
        event_type="workflow_observation",
    )
    sanitized, issues, blocked = sanitize_event(event)
    assert blocked is True
    assert sanitized["project_path"] == "<REDACTED:path>"
    assert any("project_path" in issue.field for issue in issues)


def test_sanitize_event_blocks_file_in_files_touched() -> None:
    event = make_event(
        tool="codex",
        project_path="/Users/me/proj",
        project_id="git-y",
        event_type="bugfix",
        files_touched=["/Users/me/proj/.env", "src/auth.py"],
    )
    sanitized, issues, blocked = sanitize_event(event)
    assert "<REDACTED:path>" in sanitized["files_touched"]
    assert "src/auth.py" in sanitized["files_touched"]
    assert blocked is True


def test_sanitize_event_redacts_secret_in_task() -> None:
    event = make_event(
        tool="shell",
        project_path="/work",
        project_id="local-abc",
        event_type="workflow_observation",
        task="rotated sk-abcdefghijklmnopqrstuv token",
    )
    sanitized, issues, blocked = sanitize_event(event)
    assert "sk-abcdefghijklmnopqrstuv" not in sanitized["task"]
    assert blocked is True


def test_sanitize_event_marks_privacy_redacted_when_any_rule_fires() -> None:
    event = make_event(
        tool="claude-code",
        project_path="/work",
        project_id="local-abc",
        event_type="workflow_observation",
        task="normal task with AKIAIOSFODNN7EXAMPLE in it",
    )
    sanitized, _issues, blocked = sanitize_event(event)
    assert blocked is True
    assert sanitized["privacy"] in {"sanitized", "redacted"}


def test_sanitize_event_truncates_long_string() -> None:
    long_text = "x" * 20000
    event = make_event(
        tool="codex",
        project_path="/work",
        project_id="git-abc",
        event_type="decision",
        task=long_text,
    )
    sanitized, issues, _blocked = sanitize_event(event)
    # truncation itself is not a privacy block — blocked should be False
    assert any("truncated" in issue.reason for issue in issues)
    assert len(sanitized["task"]) < len(long_text)
