"""Shared pytest fixtures for cbmem tests."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest


@pytest.fixture
def stub_cbmem_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Drop a fake ``codebase-memory-mcp`` binary in tmp_path and point
    ``LBM_CBMEM_BIN`` at it. The fake is a +x empty file — tests mock
    ``subprocess.run`` so the binary is never actually executed; we only
    need it to be discoverable by ``cbmem.resolve_binary``.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codebase-memory-mcp"
    fake.write_text("#!/bin/sh\necho stub\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("LBM_CBMEM_BIN", str(fake))
    return fake
