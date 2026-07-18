from __future__ import annotations

from pathlib import Path

from lwm import capabilities, context


def test_receipt_write_failure_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    def fail_write(*args, **kwargs):
        raise PermissionError("receipt path unavailable")

    monkeypatch.setattr(Path, "write_text", fail_write)
    result = capabilities.record(tmp_path, tool="codex", direction="read", source="test")
    assert result["status"] == "unavailable"
    assert "receipt path unavailable" in result["error"]


def test_context_build_does_not_depend_on_receipt_writes(tmp_path: Path) -> None:
    report = context.build(tmp_path, tool="codex", project_path=None, format="markdown")
    assert report.ok
    assert "Scope: global-only" in report.markdown
