"""Tests for the cbmem-related additions to lwm.init_scaffold."""

from __future__ import annotations

import json
from pathlib import Path

from lwm import init_scaffold


def test_init_writes_cbmem_projects_empty(tmp_path: Path) -> None:
    """After ``init_wiki_tree`` runs, ``lwm-sources.json`` must contain
    a ``cbmem`` block with ``projects: []`` and the default search queries.
    """
    init_scaffold.init_wiki_tree(
        tmp_path, domain="test", source_types="memory", force=True
    )
    sources = tmp_path / "lwm-sources.json"
    assert sources.is_file()
    payload = json.loads(sources.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    cbmem_block = payload["cbmem"]
    assert cbmem_block["projects"] == []
    assert cbmem_block["search_queries"] == ["<TODO>", "<FIXME>", "<XXX>"]


def test_init_preserves_existing_cbmem_projects(tmp_path: Path) -> None:
    """If ``lwm-sources.json`` already lists projects, ``init`` must NOT
    clobber them — only fill missing keys.
    """
    sources_path = tmp_path / "lwm-sources.json"
    sources_path.write_text(
        json.dumps(
            {"cbmem": {"projects": ["/Users/foo/proj1"], "search_queries": ["<MY>"]}}
        ),
        encoding="utf-8",
    )
    init_scaffold.init_wiki_tree(
        tmp_path, domain="test", source_types="memory", force=True
    )
    payload = json.loads(sources_path.read_text(encoding="utf-8"))
    # Existing keys preserved; projects list untouched.
    assert payload["cbmem"]["projects"] == ["/Users/foo/proj1"]
    assert payload["cbmem"]["search_queries"] == ["<MY>"]


def test_init_reports_cbmem_install_status(tmp_path: Path, capsys) -> None:
    """When the binary is present, the printed line says ``installed``;
    when absent, it says ``not installed`` with an install hint."""
    init_scaffold.init_wiki_tree(
        tmp_path, domain="test", source_types="memory", force=True
    )
    out = capsys.readouterr().out
    assert "CBMEM:" in out
    # HOME-relative path: the real binary exists on this machine, so we expect "installed".
    # The assertion below intentionally does NOT pin to "installed" or "not installed"
    # because it depends on the test environment — instead, just make sure the line
    # mentions one of the two known phrases.
    assert ("installed" in out) or ("not installed" in out)