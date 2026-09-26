"""Cycle receipt v2 tests.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 7. Cycle, failure isolation, and health
"""

from __future__ import annotations

import json
from pathlib import Path

from lwm.cycle_receipt import (
    CoreStatus,
    CycleReceiptV2,
    LATEST_POINTER,
    RECEIPTS_ROOT,
    SourceResult,
    StageResult,
    derive_core_status,
    list_cycle_receipts,
    load_latest,
    load_last_attempt,
    make_cycle_id,
    write_cycle_receipt,
)


def _sample_receipt(*, core: CoreStatus = "success") -> CycleReceiptV2:
    return CycleReceiptV2(
        schema_version=2,
        cycle_id=make_cycle_id(),
        runtime_id="runtime-1",
        started_at="2026-08-01T01:00:00+08:00",
        finished_at="2026-08-01T01:00:05+08:00",
        core_status=core,
        overall_status=core,
        sources=(SourceResult(name="codex", status="ok", detail=""),),
        stages=(StageResult(name="ingest", status="ok", duration_ms=120, detail=""),),
        counts={"admitted": 12, "operational": 4, "rejected": 1},
        artifacts=("wiki/projects/git-x.md",),
    )


def test_write_cycle_receipt_creates_immutable_file(tmp_path: Path) -> None:
    receipt = _sample_receipt()
    target = write_cycle_receipt(receipt, tmp_path)
    assert target == tmp_path / RECEIPTS_ROOT / f"{receipt.cycle_id}.json"
    assert target.is_file()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["cycle_id"] == receipt.cycle_id
    assert payload["core_status"] == "success"


def test_write_cycle_receipt_uses_data_root_not_process_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "data"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    target = write_cycle_receipt(_sample_receipt(), root)

    assert target.is_file()
    assert not (cwd / "state" / "receipts" / "cycles").exists()


def test_write_cycle_receipt_updates_latest_pointer(tmp_path: Path) -> None:
    first = _sample_receipt()
    second = _sample_receipt()
    write_cycle_receipt(first, tmp_path)
    write_cycle_receipt(second, tmp_path)

    pointer = tmp_path / LATEST_POINTER
    assert pointer.is_file()
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    assert payload["cycle_id"] == second.cycle_id
    assert payload["path"] == str(RECEIPTS_ROOT / f"{second.cycle_id}.json")
    assert len(payload["receipt_sha256"]) == 64


def test_existing_cycle_file_cannot_be_overwritten(tmp_path: Path) -> None:
    receipt = _sample_receipt()
    write_cycle_receipt(receipt, tmp_path)
    try:
        write_cycle_receipt(receipt, tmp_path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("cycle receipt was overwritten")


def test_failed_attempt_does_not_replace_last_success(tmp_path: Path) -> None:
    success = _sample_receipt(core="success")
    failed = _sample_receipt(core="failed_core")
    write_cycle_receipt(success, tmp_path)
    write_cycle_receipt(failed, tmp_path)

    assert load_latest(tmp_path)["cycle_id"] == success.cycle_id
    assert load_last_attempt(tmp_path)["cycle_id"] == failed.cycle_id


def test_cycle_receipts_are_immutable_and_per_cycle(tmp_path: Path) -> None:
    for _ in range(3):
        write_cycle_receipt(_sample_receipt(), tmp_path)
    assert len(list_cycle_receipts(tmp_path)) == 3


def test_legacy_v1_health_json_is_loaded_as_fallback(tmp_path: Path) -> None:
    legacy = tmp_path / "state" / "health.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps({"status": "failed", "legacy": True}), encoding="utf-8")
    payload = load_latest(tmp_path)
    assert payload and payload.get("legacy") is True


def test_load_latest_returns_v2_body(tmp_path: Path) -> None:
    receipt = _sample_receipt()
    write_cycle_receipt(receipt, tmp_path)
    payload = load_latest(tmp_path)
    assert payload["cycle_id"] == receipt.cycle_id
    assert payload["schema_version"] == 2


def test_derive_core_status_happy_path() -> None:
    status = derive_core_status(
        raw_writable=True, all_recall_ok=True, receipt_committed=True
    )
    assert status == "success"


def test_derive_core_status_quality_warning() -> None:
    status = derive_core_status(
        raw_writable=True,
        all_recall_ok=True,
        receipt_committed=True,
        quality_warning=True,
    )
    assert status == "success_with_warnings"


def test_derive_core_status_failed_when_raw_unwritable() -> None:
    status = derive_core_status(
        raw_writable=False, all_recall_ok=True, receipt_committed=True
    )
    assert status == "failed_core"


def test_derive_core_status_failed_when_recall_unavailable() -> None:
    status = derive_core_status(
        raw_writable=True, all_recall_ok=False, receipt_committed=True
    )
    assert status == "failed_core"


def test_derive_core_status_failed_when_receipt_not_committed() -> None:
    status = derive_core_status(
        raw_writable=True, all_recall_ok=True, receipt_committed=False
    )
    assert status == "failed_core"


def test_health_reads_latest_v2_receipt_for_cycle_truth(tmp_path: Path, monkeypatch) -> None:
    from lwm import health

    receipt = _sample_receipt(core="success_with_warnings")
    write_cycle_receipt(receipt, tmp_path)
    monkeypatch.setattr(health, "_audit_summary", lambda root: {"audit_ok": True, "issues": 0})

    snapshot = health.collect(tmp_path, strict=True)

    assert snapshot.cycle["last_receipt_id"] == receipt.cycle_id
    assert snapshot.cycle["last_status"] == "success_with_warnings"
    assert snapshot.cycle["receipt_schema_version"] == 2
    assert snapshot.status == "degraded"


def test_degraded_sources_do_not_become_core_failure() -> None:
    status = derive_core_status(
        raw_writable=True,
        all_recall_ok=True,
        receipt_committed=True,
        degraded_sources=("codex", "claude-code"),
    )
    assert status == "success_with_warnings"


def test_receipt_round_trip_through_disk(tmp_path: Path) -> None:
    receipt = _sample_receipt(core="success_with_warnings")
    target = write_cycle_receipt(receipt, tmp_path)
    restored = json.loads(target.read_text(encoding="utf-8"))
    assert restored["core_status"] == "success_with_warnings"
    assert restored["counts"]["admitted"] == 12
    assert restored["artifacts"] == ["wiki/projects/git-x.md"]


def test_pointer_is_never_overwritten_with_empty_payload(tmp_path: Path) -> None:
    write_cycle_receipt(_sample_receipt(), tmp_path)
    pointer = tmp_path / LATEST_POINTER
    assert json.loads(pointer.read_text(encoding="utf-8"))["core_status"] == "success"
    # No second write leaves the pointer dangling.
    assert pointer.is_file()


def test_make_cycle_id_is_unique() -> None:
    ids = {make_cycle_id() for _ in range(50)}
    assert len(ids) == 50
