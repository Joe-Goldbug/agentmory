"""Install/uninstall the lwm zsh shell-history hook.

The hook file at ``lwm/lwm_shell_hook.zsh`` is a pure-zsh preexec+precmd
pair that drops a sanitized JSONL record of each non-trivial command into
``$LWM_ROOT/raw/shell/<date>.jsonl``.  It is opt-out via
``LBM_SHELL_HOOK=0`` and never persists secrets.

This module handles the **installation step only** — it appends a
guarded block to ``~/.zshrc`` so the hook is sourced on every interactive
shell. Removal is symmetric and idempotent.

Design notes:

* The block is wrapped in two markers so uninstall is precise:
  ``# LBM-WIKI:SHELL-HOOK-START`` and ``# LBM-WIKI:SHELL-HOOK-END``.
* The hook script is referenced by absolute path so users moving their
  wiki root around do not silently disable capture.
* The block also embeds a short sha256 of the hook file inside a
  ``# LBM-WIKI:SHELL-HOOK-FP: <hex>`` header line so we can detect when
  the on-disk hook bytes have changed and need to be re-applied.
* We never rewrite user-owned lines outside the marker band.
* We do not touch ``raw/shell/*.jsonl`` on uninstall — history is the
  user's record.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


MARKER_START = "# LBM-WIKI:SHELL-HOOK-START"
MARKER_END = "# LBM-WIKI:SHELL-HOOK-END"
_FP_HEADER_RE = re.compile(r"^# LBM-WIKI:SHELL-HOOK-FP:\s*([0-9a-f]+)\s*$", re.MULTILINE)

DEFAULT_RC_PATHS: tuple[Path, ...] = (
    Path.home() / ".zshrc",
)


@dataclass(frozen=True)
class InstallResult:
    """Outcome of an install/uninstall attempt."""

    rc_path: Path
    changed: bool
    already_installed: bool
    hook_path: Path | None


def _resolve_rc(rc_path: Path | None) -> Path:
    if rc_path is not None:
        return rc_path.expanduser().resolve()
    for candidate in DEFAULT_RC_PATHS:
        if candidate.exists():
            return candidate.resolve()
    return DEFAULT_RC_PATHS[0].expanduser().resolve()


def _hook_path(lwm_root: Path) -> Path:
    return (lwm_root / "lwm" / "lwm_shell_hook.zsh").resolve()


def _hook_fingerprint(hook: Path) -> str:
    """Short fingerprint of the hook bytes; refreshes trigger rewriting the block."""

    return hashlib.sha256(hook.read_bytes()).hexdigest()[:12]


def _block(hook: Path, *, fingerprint: str) -> str:
    """The block we write between the markers.

    The fingerprint line lets us detect when the on-disk hook script has
    been updated and refresh the block accordingly.
    """

    return (
        f"{MARKER_START}\n"
        f"# Auto-installed by `lwm install-shell-hook`. Do not edit by hand.\n"
        f"# Remove with `lwm uninstall-shell-hook`.\n"
        f"# LBM-WIKI:SHELL-HOOK-FP: {fingerprint}\n"
        f"if [[ -f {str(hook)!r} ]]; then\n"
        f"  source {str(hook)!r}\n"
        f"fi\n"
        f"{MARKER_END}\n"
    )


def _existing_fingerprint(text: str) -> str | None:
    match = _FP_HEADER_RE.search(text)
    return match.group(1) if match else None


_BLOCK_RE = re.compile(
    rf"^{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\s*\n?",
    re.MULTILINE | re.DOTALL,
)


def _has_block(text: str) -> bool:
    return MARKER_START in text and MARKER_END in text


def install(
    *,
    lwm_root: Path,
    rc_path: Path | None = None,
) -> InstallResult:
    """Install (or refresh) the shell-hook marker block in the rcfile.

    * Idempotent: re-running with the same hook bytes writes nothing.
    * Refreshable: if the hook script changed, the block is rewritten in
      place so users get the new bytes after the next shell start.
    * Creates the rcfile (and parent dir) when missing.
    """

    rc = _resolve_rc(rc_path)
    hook = _hook_path(lwm_root)
    if not hook.is_file():
        raise FileNotFoundError(
            f"shell hook script not found at {hook}; reinstall LLM-WorkMem"
        )
    rc.parent.mkdir(parents=True, exist_ok=True)
    existing = rc.read_text(encoding="utf-8") if rc.is_file() else ""
    fingerprint = _hook_fingerprint(hook)
    block = _block(hook, fingerprint=fingerprint)

    existing_block = _BLOCK_RE.search(existing)
    if existing_block:
        current_fp = _existing_fingerprint(existing_block.group(0))
        new_text = _BLOCK_RE.sub(lambda _m: block, existing)
        if new_text == existing and current_fp == fingerprint:
            return InstallResult(
                rc_path=rc, changed=False, already_installed=True, hook_path=hook
            )
        rc.write_text(new_text, encoding="utf-8")
        return InstallResult(
            rc_path=rc, changed=True, already_installed=True, hook_path=hook
        )

    if existing and not existing.endswith("\n"):
        existing = existing + "\n"
    new_text = f"{existing}\n{block}" if existing else block
    rc.write_text(new_text, encoding="utf-8")
    return InstallResult(
        rc_path=rc, changed=True, already_installed=False, hook_path=hook
    )


def uninstall(*, rc_path: Path | None = None) -> InstallResult:
    """Remove the marker block (if present) and leave the rest of the rcfile alone."""

    rc = _resolve_rc(rc_path)
    if not rc.is_file():
        return InstallResult(
            rc_path=rc, changed=False, already_installed=False, hook_path=None
        )
    existing = rc.read_text(encoding="utf-8")
    if not _has_block(existing):
        return InstallResult(
            rc_path=rc, changed=False, already_installed=False, hook_path=None
        )
    new_text = _BLOCK_RE.sub("", existing).lstrip("\n")
    rc.write_text(new_text, encoding="utf-8")
    return InstallResult(
        rc_path=rc, changed=True, already_installed=True, hook_path=None
    )


def is_installed(*, rc_path: Path | None = None) -> bool:
    """True if the rcfile currently contains our marker block."""

    rc = _resolve_rc(rc_path)
    if not rc.is_file():
        return False
    return _has_block(rc.read_text(encoding="utf-8"))


__all__ = [
    "DEFAULT_RC_PATHS",
    "InstallResult",
    "MARKER_END",
    "MARKER_START",
    "install",
    "is_installed",
    "uninstall",
]

