"""Tests for the cbmem section of ``lwiki.audit.run_audit``."""

from __future__ import annotations

import json
from pathlib import Path

from lwiki import audit


def _make_artifact(project: Path) -> None:
    artifact = project / ".codebase-memory" / "graph.db.zst"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x00")


def test_audit_reports_cbmem_indexed_state_no_config(tmp_path: Path) -> None:
    """No lwiki-sources.json -> cbmem counts default to (0, 0)."""
    report = audit.run_audit(tmp_path, eval_suite=None, eval_mode="standard")
    assert report.cbmem_indexed == 0
    assert report.cbmem_projects_total == 0


def test_audit_reports_cbmem_indexed_state_partial(tmp_path: Path) -> None:
    """With 2 projects configured and 1 indexed, report shows 1/2."""
    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    proj_a.mkdir()
    proj_b.mkdir()
    _make_artifact(proj_a)

    (tmp_path / "lwiki-sources.json").write_text(
        json.dumps({"cbmem": {"projects": [str(proj_a), str(proj_b)]}}),
        encoding="utf-8",
    )
    report = audit.run_audit(tmp_path, eval_suite=None, eval_mode="standard")
    assert report.cbmem_indexed == 1
    assert report.cbmem_projects_total == 2
    rendered = audit.render_audit_report(report)
    assert "CBMEM: 1/2 projects indexed" in rendered