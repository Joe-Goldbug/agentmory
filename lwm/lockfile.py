"""Process-level locks for ingest and scheduled cycle writes.

The LaunchAgent runs at boot and every 12 hours; file-wake/manual invocations
may also arrive. Without a lock those triggers could overlap and write the
same wiki pages twice. The
lockfile lives at ``<root>/state/locks/ingest.lock`` and stores the
process pid + acquisition timestamp.

The supervisor lock covers the whole scheduled cycle, not only ingest. This
keeps project rebuilds, candidate writes, exports and cycle receipts under a
single writer boundary when two scheduler invocations race.
"""

from __future__ import annotations

import json
import os
import time
from contextvars import ContextVar
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
    existing: LockInfo | None
    error: str | None = None


_cycle_lock_depth: ContextVar[int] = ContextVar("lwm_cycle_lock_depth", default=0)


def _lock_dir(root: Path) -> Path:
    return (root / "state" / "locks").resolve()


def lock_path(root: Path) -> Path:
    return _lock_dir(root) / "ingest.lock"


def cycle_lock_path(root: Path) -> Path:
    return _lock_dir(root) / "cycle.lock"


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
    """Atomically try to acquire the ingest lock."""

    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for _ in range(2):
        info = LockInfo(pid=os.getpid(), acquired_at=now, stale_after=stale_after)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            data = _read_lock(path)
            if data is None:
                return LockResult(acquired=False, info=None, existing=None)
            pid = int(data.get("pid", 0))
            existing = LockInfo(
                pid=pid,
                acquired_at=float(data.get("acquired_at", now)),
                stale_after=int(data.get("stale_after", stale_after)),
            )
            # Preserve the historical stale-window recovery contract, but only
            # after a complete metadata record exists. The atomic create above
            # still prevents two fresh owners from winning simultaneously.
            if _pid_alive(pid) and not _is_stale(data, now=now):
                return LockResult(acquired=False, info=None, existing=existing)
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        except OSError:
            return LockResult(acquired=False, info=None, existing=None)

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": info.pid,
                        "acquired_at": info.acquired_at,
                        "stale_after": info.stale_after,
                        "kind": "ingest",
                    },
                    handle,
                    ensure_ascii=False,
                )
        except OSError:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            return LockResult(acquired=False, info=None, existing=None)
        return LockResult(acquired=True, info=info, existing=None)
    return LockResult(acquired=False, info=None, existing=None)


def try_acquire_cycle(root: Path, *, stale_after: int = 86400) -> LockResult:
    """Atomically acquire the lock for one complete scheduled cycle.

    ``ingest`` uses its historical JSON lock. The cycle lock must also guard
    the stages around ingest, so it uses ``O_EXCL`` to prevent the read-then-
    write race that two supervisor processes could otherwise both win.
    """

    path = cycle_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for _ in range(2):
        info = LockInfo(pid=os.getpid(), acquired_at=now, stale_after=stale_after)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            data = _read_lock(path)
            if data is None:
                # The owner may have won O_EXCL but not finished writing its
                # metadata yet. Treat a recent or unreadable marker as busy;
                # deleting it here would reopen the create/write race.
                return LockResult(acquired=False, info=None, existing=None)
            if _pid_alive(int(data.get("pid", 0))):
                return LockResult(
                    acquired=False,
                    info=None,
                    existing=LockInfo(
                        pid=int(data.get("pid", 0)),
                        acquired_at=float(data.get("acquired_at", now)),
                        stale_after=int(data.get("stale_after", stale_after)),
                    ),
                )
            # A crashed process can leave the marker behind. Reclaim only
            # when its owner is no longer alive, then retry the atomic create.
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        except OSError as exc:
            return LockResult(
                acquired=False,
                info=None,
                existing=None,
                error=f"cycle lock open failed: {exc}",
            )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "pid": info.pid,
                        "acquired_at": info.acquired_at,
                        "stale_after": info.stale_after,
                        "kind": "cycle",
                    },
                    handle,
                    ensure_ascii=False,
                )
        except OSError as exc:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            return LockResult(
                acquired=False,
                info=None,
                existing=None,
                error=f"cycle lock write failed: {exc}",
            )
        return LockResult(acquired=True, info=info, existing=None)
    return LockResult(
        acquired=False,
        info=None,
        existing=None,
        error="cycle lock unavailable after stale-marker recovery",
    )


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


def release_cycle(root: Path) -> bool:
    """Release the cycle marker only when it belongs to this process."""

    path = cycle_lock_path(root)
    data = _read_lock(path)
    if data is None or int(data.get("pid", 0)) != os.getpid():
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


class CycleLockBusyError(RuntimeError):
    def __init__(self, info: LockInfo | None, error: str | None = None):
        super().__init__(error or f"cycle lock held by pid={info.pid if info else '?'}")
        self.info = info
        self.error = error


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


@contextmanager
def cycle_lock(root: Path, *, stale_after: int = 86400):
    """Guard all writes performed by one supervisor cycle."""

    depth = _cycle_lock_depth.get()
    if depth:
        token = _cycle_lock_depth.set(depth + 1)
        try:
            yield None
        finally:
            _cycle_lock_depth.reset(token)
        return

    result = try_acquire_cycle(root, stale_after=stale_after)
    if not result.acquired:
        raise CycleLockBusyError(result.existing, result.error)
    token = _cycle_lock_depth.set(1)
    try:
        yield result.info
    finally:
        _cycle_lock_depth.reset(token)
        release_cycle(root)


__all__ = [
    "LockBusyError",
    "CycleLockBusyError",
    "LockInfo",
    "LockResult",
    "cycle_lock",
    "cycle_lock_path",
    "ingest_lock",
    "lock_path",
    "release_cycle",
    "release",
    "try_acquire_cycle",
    "try_acquire",
]
