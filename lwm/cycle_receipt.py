"""Cycle receipts (v1 backwards-compatible + v2 immutable).

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Implementation Changes / 7. Cycle, failure isolation, and health

* ``CycleReceiptV2`` is written once per cycle as an immutable file under
  ``state/receipts/cycles/<cycle_id>.json``.
* ``state/receipts/latest-cycle.json`` is the atomic pointer; it always
  references one of the immutable cycle files.
* v1 receipts are still read so legacy code can consume them; nothing writes
  the v1 format any more.
"""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


RECEIPTS_ROOT = Path("state/receipts/cycles")
LATEST_POINTER = Path("state/receipts/latest-cycle.json")
LAST_ATTEMPT_POINTER = Path("state/receipts/last-attempt.json")

CoreStatus = Literal["success", "success_with_warnings", "failed_core"]


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class SourceResult:
    name: str
    status: str
    detail: str = ""
    error: str = ""


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    duration_ms: int = 0
    detail: str = ""
    error: str = ""


@dataclass(frozen=True)
class CycleReceiptV2:
    schema_version: Literal[2]
    cycle_id: str
    runtime_id: str
    started_at: str
    finished_at: str
    core_status: CoreStatus
    overall_status: str
    sources: tuple[SourceResult, ...] = ()
    stages: tuple[StageResult, ...] = ()
    quality: dict[str, Any] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    artifacts: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    receipt_id: str = ""
    source_revision: str = ""
    runtime_manifest_path: str = ""
    runtime_manifest_sha256: str = ""
    runtime_module_path: str = ""
    runtime_sys_path: tuple[str, ...] = ()
    runtime_import_independent: bool = False
    eval_suite_sha256: str = ""
    context_sha256: str = ""
    health_sha256: str = ""
    health_snapshot_path: str = ""
    evidence_hashes: dict[str, str] = field(default_factory=dict)
    exit_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cycle_id": self.cycle_id,
            "runtime_id": self.runtime_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "core_status": self.core_status,
            "overall_status": self.overall_status,
            "sources": [asdict(s) for s in self.sources],
            "stages": [asdict(s) for s in self.stages],
            "quality": self.quality,
            "analysis": self.analysis,
            "counts": self.counts,
            "artifacts": list(self.artifacts),
            "errors": list(self.errors),
            "receipt_id": self.receipt_id,
            "source_revision": self.source_revision,
            "runtime_manifest_path": self.runtime_manifest_path,
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
            "runtime_module_path": self.runtime_module_path,
            "runtime_sys_path": list(self.runtime_sys_path),
            "runtime_import_independent": self.runtime_import_independent,
            "eval_suite_sha256": self.eval_suite_sha256,
            "context_sha256": self.context_sha256,
            "health_sha256": self.health_sha256,
            "health_snapshot_path": self.health_snapshot_path,
            "evidence_hashes": self.evidence_hashes,
            "exit_code": self.exit_code,
        }


def _path_for(receipt: CycleReceiptV2) -> Path:
    return RECEIPTS_ROOT / f"{receipt.cycle_id}.json"


def write_cycle_receipt(receipt: CycleReceiptV2, root: Path) -> Path:
    """Persist a cycle receipt as an immutable file and update the pointer.

    The per-cycle file is written atomically; the latest-cycle pointer is then
    replaced in-place. Existing receipts are never overwritten.
    """

    target_root = root.resolve()
    (target_root / RECEIPTS_ROOT).mkdir(parents=True, exist_ok=True)
    target = target_root / _path_for(receipt)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = receipt.to_dict()
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    receipt_sha256 = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    fd, tmp = tempfile.mkstemp(
        prefix=f".{receipt.cycle_id}.", suffix=".json", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload_text)
        # Link the completed temporary file into place instead of replacing
        # an existing cycle file. This makes the per-cycle record immutable.
        os.link(tmp, target)
        os.unlink(tmp)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    pointer_relative = LATEST_POINTER if receipt.core_status == "success" else LAST_ATTEMPT_POINTER
    pointer = target_root / pointer_relative
    pointer.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".latest-cycle.", suffix=".json", dir=str(pointer.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "cycle_id": receipt.cycle_id,
                        "core_status": receipt.core_status,
                        "finished_at": receipt.finished_at,
                        "path": str(_path_for(receipt)),
                        "receipt_sha256": receipt_sha256,
                        "pointer_kind": "last_success" if receipt.core_status == "success" else "last_attempt",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        os.replace(tmp, pointer)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target


def load_latest(root: Path) -> dict[str, Any] | None:
    pointer = root / LATEST_POINTER
    if not pointer.is_file():
        return _read_legacy_latest(root)
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _read_legacy_latest(root)
    if not isinstance(payload, dict):
        return None
    if "path" in payload:
        path = root / payload["path"]
        if path.is_file():
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                body = None
            if isinstance(body, dict):
                return body
    return payload


def load_last_attempt(root: Path) -> dict[str, Any] | None:
    """Load the most recent failed or warning cycle without replacing success."""

    pointer = root / LAST_ATTEMPT_POINTER
    if not pointer.is_file():
        return None
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    path_value = payload.get("path")
    if not isinstance(path_value, str):
        return payload
    path = root / path_value
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return payload
    return body if isinstance(body, dict) else payload


def _read_legacy_latest(root: Path) -> dict[str, Any] | None:
    """Read the legacy v1 latest-receipt from ``state/health.json``."""

    legacy = root / "state" / "health.json"
    if not legacy.is_file():
        return None
    try:
        return json.loads(legacy.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_cycle_receipts(root: Path) -> tuple[Path, ...]:
    base = root / RECEIPTS_ROOT
    if not base.is_dir():
        return ()
    return tuple(sorted(base.glob("*.json")))


def make_cycle_id(*, prefix: str = "cycle") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def derive_core_status(
    *,
    raw_writable: bool,
    all_recall_ok: bool,
    receipt_committed: bool,
    quality_warning: bool = False,
    degraded_sources: tuple[str, ...] = (),
) -> CoreStatus:
    """Compute the truthful core status from invariant predicates.

    A single adapter/CBMEM/LLM/Markdown/audit/eval failure is *not* a core
    failure — it lands as ``success_with_warnings`` and contributes to
    ``degraded_sources`` for the cycle report. A real core failure is reserved
    for the three truly fatal conditions spelled out in the spec.
    """

    if not raw_writable:
        return "failed_core"
    if not all_recall_ok:
        return "failed_core"
    if not receipt_committed:
        return "failed_core"
    if quality_warning or degraded_sources:
        return "success_with_warnings"
    return "success"


__all__ = [
    "CoreStatus",
    "CycleReceiptV2",
    "LATEST_POINTER",
    "LAST_ATTEMPT_POINTER",
    "RECEIPTS_ROOT",
    "SourceResult",
    "StageResult",
    "derive_core_status",
    "list_cycle_receipts",
    "load_latest",
    "load_last_attempt",
    "make_cycle_id",
    "write_cycle_receipt",
]
