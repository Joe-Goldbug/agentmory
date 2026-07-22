from __future__ import annotations

import json
import os
import time
from pathlib import Path

from adapters.hooks import codex_export
from lwm import capabilities


def test_codex_export_uses_current_schema_and_real_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    session = tmp_path / "session.jsonl"
    rows = [
        {
            "type": "session_meta",
            "payload": {"id": "session-1", "cwd": str(project)},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Fix the real project"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Done"}],
            },
        },
    ]
    session.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    old = time.time() - 120
    os.utime(session, (old, old))

    emitted: list[dict] = []
    monkeypatch.setattr("adapters.hooks._common.emit", lambda _root, event: emitted.append(event) or 0)

    seen: set[str] = set()
    assert codex_export.emit_session(tmp_path, session, seen=seen) == 0
    assert emitted[0]["project_path"] == str(project)
    assert emitted[0]["task"] == "Fix the real project"
    receipts = capabilities.load(tmp_path)
    assert receipts["codex:read"]["project_id"] == receipts["codex:write"]["project_id"]
    assert receipts["codex:read"]["source"] == "watcher-observed"
    assert receipts["codex:write"]["source"] == "watcher-observed"

    assert codex_export.emit_session(tmp_path, session, seen=seen) == 0
    assert len(emitted) == 1
