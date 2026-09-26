from __future__ import annotations

from pathlib import Path

from lwm import behavior_contract
from lwm.adapters import _context_block


def test_behavior_snapshot_is_explicit_and_marked_stale_when_source_is_missing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-GLOBAL.md"
    source.write_text("<!-- contract-version: 9 -->\n# Contract\n", encoding="utf-8")
    data_root = tmp_path / "data"

    snapshot = behavior_contract.write_snapshot(data_root, source)
    source.unlink()

    loaded = behavior_contract.load(data_root)

    assert snapshot == data_root / behavior_contract.SNAPSHOT_PATH
    assert loaded.status == "stale"
    assert loaded.version == "9"
    assert loaded.sha256


def test_behavior_snapshot_is_verified_when_recorded_source_still_matches(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-GLOBAL.md"
    source.write_text("<!-- contract-version: 10 -->\n# Contract\n", encoding="utf-8")
    data_root = tmp_path / "data"

    behavior_contract.write_snapshot(data_root, source)

    loaded = behavior_contract.load(data_root)

    assert loaded.status == "verified"
    assert loaded.path == str(source.resolve())
    assert loaded.version == "10"


def test_behavior_snapshot_stays_stale_when_recorded_source_changes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-GLOBAL.md"
    source.write_text("<!-- contract-version: 11 -->\n# Contract\n", encoding="utf-8")
    data_root = tmp_path / "data"

    behavior_contract.write_snapshot(data_root, source)
    source.write_text("<!-- contract-version: 12 -->\n# Changed\n", encoding="utf-8")

    loaded = behavior_contract.load(data_root)

    assert loaded.status == "stale"
    assert loaded.version == "11"


def test_adapter_points_to_the_verified_contract_source_or_snapshot(tmp_path: Path) -> None:
    (tmp_path / "GLOBAL.md").write_text(
        "<!-- contract-version: 2 -->\n# Contract\n", encoding="utf-8"
    )

    block = _context_block(tmp_path)

    assert str(tmp_path / "GLOBAL.md") in block
    assert "status=verified" in block


def test_runtime_adapters_point_to_snapshot_when_checkout_contract_is_unavailable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-GLOBAL.md"
    source.write_text("<!-- contract-version: 11 -->\n# Contract\n", encoding="utf-8")
    data_root = tmp_path / "runtime" / "llm-workmem"
    behavior_contract.write_snapshot(data_root, source)

    source.unlink()
    block = _context_block(data_root, tool="codex")

    assert str(data_root / behavior_contract.SNAPSHOT_PATH) in block
    assert "version=11" in block
    assert "status=stale" in block
    assert str(data_root / "GLOBAL.md") not in block


def test_cursor_and_gemini_adapters_expose_contract_metadata(tmp_path: Path) -> None:
    (tmp_path / "GLOBAL.md").write_text(
        "<!-- contract-version: 12 -->\n# Contract\n", encoding="utf-8"
    )

    from lwm.adapters import _cursor_rules_block, _gemini_block

    cursor = _cursor_rules_block(tmp_path)
    gemini = _gemini_block(tmp_path)

    for block in (cursor, gemini):
        assert "version=12" in block
        assert "status=verified" in block
        assert str(tmp_path / "GLOBAL.md") in block
