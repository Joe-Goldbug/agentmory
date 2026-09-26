"""Safety tests for Claude Code native lifecycle hooks."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from lwm import capabilities


def _seed_root(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "llms.txt").write_text("# shared context\n", encoding="utf-8")
    (root / "llms-full.txt").write_text("# full context\n", encoding="utf-8")
    (root / "llms.json").write_text("{}\n", encoding="utf-8")
    (root / "wiki").mkdir()
    (root / "wiki" / "purpose.md").write_text("# purpose\n", encoding="utf-8")
    (root / "wiki" / "overview.md").write_text("# overview\n", encoding="utf-8")
    return root


def _payload(project: Path) -> dict[str, object]:
    return {"cwd": str(project), "session_id": "claude-session-1"}


def test_session_start_with_identity_records_native_read(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from adapters.hooks import claude_code_session_start

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(claude_code_session_start, "ROOT_HINT", root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload(project))))

    assert claude_code_session_start.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    receipt = capabilities.load(root)["claude-code"]
    assert receipt["direction"] == "read"
    assert receipt["status"] == "verified"


def test_stop_with_identity_records_native_write(tmp_path: Path, monkeypatch) -> None:
    from adapters.hooks import claude_code_stop

    root = _seed_root(tmp_path / "root")
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(claude_code_stop, "ROOT_HINT", root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload(project))))

    assert claude_code_stop.main() == 0
    receipt = capabilities.load(root)["claude-code"]
    assert receipt["direction"] == "write"
    assert receipt["status"] == "verified"


def test_session_start_missing_identity_fails_open_without_receipt(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from adapters.hooks import claude_code_session_start

    root = _seed_root(tmp_path / "root")
    monkeypatch.setattr(claude_code_session_start, "ROOT_HINT", root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"prompt": "redacted"})))

    assert claude_code_session_start.main() == 0
    assert capabilities.load(root) == {}
    assert json.loads(capsys.readouterr().out or "{}") == {}


def test_stop_missing_identity_fails_open_without_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    from adapters.hooks import claude_code_stop

    root = _seed_root(tmp_path / "root")
    monkeypatch.setattr(claude_code_stop, "ROOT_HINT", root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"messages": []})))

    assert claude_code_stop.main() == 0
    assert capabilities.load(root) == {}
    assert not list((root / "raw" / "events").rglob("*.json"))
