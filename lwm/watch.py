"""Source auto-watch helpers for the wiki workflow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lwm.audit import AuditReport, render_audit_report, run_audit
from lwm.harvest import SNAPSHOT_SKIP_DIR_NAMES, configured_source_groups, harvest_sources
_MAX_FINGERPRINT_FILES = 5000
_MAX_FINGERPRINT_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class WatchState:
    generated_at: str
    sources: dict[str, str]


@dataclass(frozen=True)
class WatchReport:
    root: Path
    changed_sources: tuple[str, ...]
    harvested: bool
    audit: AuditReport
    state_path: Path

    @property
    def changed(self) -> bool:
        return bool(self.changed_sources)


def _state_path(root: Path) -> Path:
    return root / "automation" / "watch-state.json"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_fingerprint(path: Path) -> str:
    try:
        if not path.exists():
            return "missing"
        if path.is_file():
            return f"file:{_sha256_text(path.read_text(encoding='utf-8', errors='ignore'))}"
        if path.is_dir():
            entries: list[str] = []
            total_bytes = 0
            for item in sorted(path.rglob("*")):
                if not item.is_file():
                    continue
                if any(
                    part in SNAPSHOT_SKIP_DIR_NAMES
                    for part in item.relative_to(path).parts
                ):
                    continue
                try:
                    rel = item.relative_to(path).as_posix()
                    stat = item.stat()
                    total_bytes += stat.st_size
                    digest = f"{stat.st_size}:{stat.st_mtime_ns}"
                except OSError:
                    continue
                entries.append(f"{rel}:{digest}")
                if len(entries) >= _MAX_FINGERPRINT_FILES or total_bytes >= _MAX_FINGERPRINT_BYTES:
                    entries.append("<fingerprint-truncated>")
                    break
            return "dir:" + _sha256_text("\n".join(entries))
        return "unknown"
    except OSError:
        return "unreadable"


def _collect_current_state(root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for group in configured_source_groups(root):
        for source in group.sources:
            key = f"{group.key}|{source.label}|{source.path}"
            fingerprints[key] = _file_fingerprint(source.path)
    return fingerprints


def _load_state(path: Path) -> WatchState | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        return None
    return WatchState(
        generated_at=str(payload.get("generated_at", "")),
        sources={str(k): str(v) for k, v in sources.items()},
    )


def _save_state(path: Path, current: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": date.today().isoformat(),
        "sources": current,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_watch(root: Path, *, eval_suite: Path | None = None, eval_mode: str = "standard") -> WatchReport:
    root = root.resolve()
    state_path = _state_path(root)
    current = _collect_current_state(root)
    previous = _load_state(state_path)
    changed_sources = tuple(
        sorted(
            key
            for key, fingerprint in current.items()
            if previous is None or previous.sources.get(key) != fingerprint
        )
    )
    removed_sources = tuple(
        sorted(
            key for key in (previous.sources.keys() if previous else ()) if key not in current
        )
    )
    changed_sources = tuple(sorted(set(changed_sources).union(removed_sources)))

    harvested = False
    if changed_sources or previous is None:
        harvest_sources(root)
        harvested = True

    # cbmem harvest runs after the file-based sources so it never blocks them.
    # ``harvest_cbmem`` swallows all exceptions internally and returns
    # ``list[CbmemSnapshotOutcome]``; we intentionally ignore the return
    # value here — the audit step is what surfaces failures to the user.
    from lwm.cbmem_source import harvest_cbmem
    harvest_cbmem(root)

    audit = run_audit(root, eval_suite=eval_suite, eval_mode=eval_mode)
    _save_state(state_path, current)
    return WatchReport(
        root=root,
        changed_sources=changed_sources,
        harvested=harvested,
        audit=audit,
        state_path=state_path,
    )


def render_watch_report(report: WatchReport) -> str:
    lines = [
        f"# Watch Report — {report.root.name}",
        "",
        f"- Changed sources: {len(report.changed_sources)}",
        f"- Harvested: {'yes' if report.harvested else 'no'}",
        f"- State file: {report.state_path}",
        "",
    ]
    if report.changed_sources:
        lines.append("## Changed Sources")
        for item in report.changed_sources:
            lines.append(f"- {item}")
        lines.append("")
    lines.append(render_audit_report(report.audit))
    return "\n".join(lines)
