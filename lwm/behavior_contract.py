"""Canonical personal behavior contract metadata.

``GLOBAL.md`` remains the only human-edited source.  This module deliberately
does not copy the contract into tool-specific files; it exposes a version and
content hash so every adapter can prove which source it delivered.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("GLOBAL.md")
SNAPSHOT_PATH = Path("state/behavior/current.json")
VERSION_PATTERN = re.compile(r"contract-version\s*:\s*([A-Za-z0-9._-]+)", re.IGNORECASE)
DEFAULT_VERSION = "1"


@dataclass(frozen=True)
class BehaviorContract:
    path: str
    version: str
    sha256: str
    text: str
    status: str = "verified"

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "version": self.version,
            "sha256": self.sha256,
            "status": self.status,
        }
        if include_text:
            payload["text"] = self.text
        return payload


def _from_bytes(path: Path, raw: bytes, *, status: str = "verified") -> BehaviorContract:
    text = raw.decode("utf-8", errors="replace")
    match = VERSION_PATTERN.search(text)
    version = match.group(1) if match else DEFAULT_VERSION
    return BehaviorContract(
        path=str(path),
        version=version,
        sha256=hashlib.sha256(raw).hexdigest(),
        text=text,
        status=status,
    )


def _load_snapshot(root: Path) -> BehaviorContract | None:
    path = root / SNAPSHOT_PATH
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or not str(payload.get("text") or "").strip():
        return None
    text = str(payload["text"])
    raw = text.encode("utf-8")
    expected = str(payload.get("sha256") or "")
    actual = hashlib.sha256(raw).hexdigest()
    if expected and expected != actual:
        return None

    source_reference = str(payload.get("source_path") or "").strip()
    source_path = Path(source_reference).expanduser() if source_reference else None
    if source_path is not None and not source_path.is_absolute():
        source_path = root / source_path
    status = "stale"
    if source_path is not None:
        try:
            source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        except OSError:
            source_hash = ""
        if source_hash == actual:
            status = "verified"

    return BehaviorContract(
        path=str(source_path or CONTRACT_PATH),
        version=str(payload.get("version") or DEFAULT_VERSION),
        sha256=actual,
        text=text,
        status=status,
    )


def load(root: Path, *, contract_path: Path | None = None) -> BehaviorContract:
    root = root.resolve()
    configured = os.environ.get("LWM_GLOBAL_PATH", "").strip()
    if contract_path is not None:
        path = contract_path.expanduser().resolve()
    elif configured:
        path = Path(configured).expanduser().resolve()
    else:
        path = root / CONTRACT_PATH
    try:
        raw = path.read_bytes()
    except OSError:
        snapshot = _load_snapshot(root)
        if snapshot is not None:
            return snapshot
        return BehaviorContract(path=str(CONTRACT_PATH), version="unknown", sha256="", text="", status="missing")
    return _from_bytes(path, raw)


def write_snapshot(root: Path, source_path: Path) -> Path:
    """Write an explicit runtime snapshot without changing the source contract."""

    source_path = source_path.expanduser().resolve()
    contract = load(root, contract_path=source_path)
    if contract.status != "verified":
        raise FileNotFoundError(source_path)
    target = root / SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source_path": str(source_path),
        "version": contract.version,
        "sha256": contract.sha256,
        "text": contract.text,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    fd, temporary = tempfile.mkstemp(prefix=".behavior.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target


def verify(root: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    contract = load(root)
    valid = contract.status == "verified" and bool(contract.sha256)
    if expected_sha256 is not None:
        valid = valid and contract.sha256 == expected_sha256
    return {
        **contract.to_dict(),
        "valid": valid,
        "expected_sha256": expected_sha256,
    }


def render_json(root: Path) -> str:
    return json.dumps(load(root).to_dict(), ensure_ascii=False, indent=2)


__all__ = [
    "BehaviorContract",
    "CONTRACT_PATH",
    "SNAPSHOT_PATH",
    "load",
    "render_json",
    "verify",
    "write_snapshot",
]
