"""Executable authority and runtime-boundary contract for the goal refactor."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_lean_core_is_current_and_v2_is_historical() -> None:
    lean_core = (ROOT / "docs/superpowers/specs/2026-07-28-llm-workmem-lean-core-design.md").read_text(
        encoding="utf-8"
    )
    v2 = (ROOT / "docs/superpowers/specs/2026-07-18-llm-workmem-v2-control-plane-design.md").read_text(
        encoding="utf-8"
    )

    assert "## Design Precedence" in lean_core
    assert "current architecture boundary" in lean_core
    assert "historical rationale only" in lean_core
    assert "历史文档" in v2
    assert "supersede" in v2
    assert "projects/<id>/STATE.md" in v2


def test_global_contract_does_not_claim_portable_runtime_git_sync() -> None:
    global_contract = (ROOT / "GLOBAL.md").read_text(encoding="utf-8")

    assert "not proven Git-synchronized or portable across Macs" in global_contract
