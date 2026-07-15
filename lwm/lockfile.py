"""Process-level lock for ``lwm ingest`` to prevent overlapping runs.

The LaunchAgent runs every 12 hours AND on file-wake; without a lock the
two triggers could overlap and write the same wiki pages twice. The
lockfile lives at ``<root>/state/locks/ingest.lock`` and stores the
process pid + acquisition timestamp.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LockInfo:
    pid: int
    acquired_at: float
    stale_after: int


@dataclass(frozen=True)
class LockResult:
    acquired: bool
    info: LockInfo | None
    existing: bool


def _lock_dir(root: Path) -> Path:
    return (root / "state" / "locks").resolve()


def lock_path(root: Path) -> Path:
    return _lock_dir(root) / "ingest.lock"


def _read_lock(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_lock(path: Path, info: LockInfo) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {
                "pid": info.pid,
                "acquired_at": info.acquired_at,
                "stale_after": info.stale_after,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tmp.replace(path)


def _is_stale(data: dict, *, now: float) -> bool:
    stale_after = int(data.get("stale_after", 1800))
    acquired_at = float(data.get("acquired_at", 0))
    return (now - acquired_at) > stale_after


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def try_acquire(root: Path, *, stale_after: int = 1800) -> LockResult:
    """Try to acquire the ingest lock. Returns ``acquired=True`` if held."""

    path = lock_path(root)
    now = time.time()
    data = _read_lock(path)
    if data is not None:
        pid = int(data.get("pid", 0))
        if _pid_alive(pid) and not _is_stale(data, now=now):
            return LockResult(
                acquired=False,
                info=None,
                existing=LockInfo(
                    pid=pid,
                    acquired_at=float(data.get("acquired_at", now)),
                    stale_after=int(data.get("stale_after", stale_after)),
                ),
            )
    info = LockInfo(pid=os.getpid(), acquired_at=now, stale_after=stale_after)
    _write_lock(path, info)
    return LockResult(acquired=True, info=info, existing=None)


def release(root: Path) -> bool:
    path = lock_path(root)
    data = _read_lock(path)
    if data is None:
        return False
    pid = int(data.get("pid", 0))
    if pid != os.getpid():
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


class LockBusyError(RuntimeError):
    def __init__(self, info: LockInfo | None):
        super().__init__(f"ingest lock held by pid={info.pid if info else '?'}")
        self.info = info


@contextmanager
def ingest_lock(root: Path, *, stale_after: int = 1800):
    """Context manager that raises :class:`LockBusyError` if not acquired."""

    result = try_acquire(root, stale_after=stale_after)
    if not result.acquired:
        raise LockBusyError(result.existing)
    try:
        yield result.info
    finally:
        release(root)


__all__ = [
    "LockBusyError",
    "LockInfo",
    "LockResult",
    "ingest_lock",
    "lock_path",
    "release",
    "try_acquire",
]
