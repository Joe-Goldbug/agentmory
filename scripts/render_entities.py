"""Render ``wiki/entities/*.md`` with canonical "official interface" and
"fallback path" sections so every IDE page captures the design intent of
LLM-WorkMem central hub design §17 (the seventeen previously-omitted
questions).

The script is idempotent: if a section is already present it is rewritten
in place; otherwise it is appended. Existing prose is never deleted.
The frontmatter ``updated`` line is bumped on every rewrite.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ENTITIES: dict[str, dict[str, str]] = {
    "codex": {
        "official": "Codex CLI <=0.x has no public hooks API. Use ``~/.codex/AGENTS.md`` instructions + a `watch`-style file listener pointing at the Codex memory directory (``~/.codex/memories`` or ``~/.codex/sessions``).",
        "fallback": "Level 2 file watcher: ``lwm watch`` reads Codex session export drops and feeds them through the same ``lwm hub record`` pipeline. No manual CLI invocation required.",
        "install": "`lwm hub install-global` (instruction pointer); the Codex session observer is enabled by the scheduled collector.",
        "status": "Level 2 file observation; no native Codex hook is claimed or generated without host proof.",
    },
    "claude-code": {
        "official": "``~/.claude/settings.json`` exposes a ``hooks`` object accepting ``SessionStart`` / ``PostToolUse`` / ``Stop`` event matchers.",
        "fallback": "If hooks are not installable (e.g. corporate lockdown), use ``~/.claude/CLAUDE.md`` instructions + the existing file-watcher harvester.",
        "install": "`lwm hub install-ide-hooks --tools=claude-code`",
        "status": "Level 1 native hook installed by default; CLI handles ``--project`` and ``--task`` via env injection.",
    },
    "opencode": {
        "official": "OpenCode uses the generated native plugin for session lifecycle events and the ``experimental.session.compacting`` callback for bounded Context injection.",
        "fallback": "If the plugin is unavailable, use the shell lifecycle observer and the generated ``~/.config/opencode/AGENTS.md`` instruction pointer.",
        "install": "`lwm hub install-ide-hooks --tools=opencode`",
        "status": "Native plugin path is available in the code package; proof still depends on a real OpenCode host event.",
    },
    "kiro": {
        "official": "Kiro stores steering markdown under ``~/.kiro/steering/``. The VS Code-compatible LLM-WorkMem Companion can request bounded start/stop Context through Kiro's extension host; this is separate from claiming a public native Kiro hook.",
        "fallback": "Without the companion, use the steering file as an instruction pointer plus the session/steering observers for bounded metadata. The companion must still produce a real host receipt before coverage is marked verified.",
        "install": "Install ``integrations/ide-companion`` as a local extension and set ``llmWorkmem.toolId=kiro`` plus ``llmWorkmem.integration=kiro-extension``; `lwm hub install-ide-hooks --tools=kiro` remains the instruction/observer fallback.",
        "status": "Companion native bridge is available and local Kiro start/stop proof is verified; steering and session observation remain active as fallback.",
    },
    "trae-solo": {
        "official": "Trae reads ``~/.traerules`` for global behaviour. The VS Code-compatible LLM-WorkMem Companion can request bounded start/stop Context through Trae's extension host.",
        "fallback": "Without the companion, use the Trae session adapter and ``watch`` the recent workspace for bounded task metadata; CLI fallback via `lwm hub record` after each task.",
        "install": "Install ``integrations/ide-companion`` as a local extension and set ``llmWorkmem.toolId=trae`` plus ``llmWorkmem.integration=trae-extension``; the Trae session observer remains the fallback.",
        "status": "Companion native bridge is available and local Trae start/stop proof is verified; session/file observation remains active as fallback.",
    },
    "antigravity": {
        "official": "Antigravity reads ``~/.agents/AGENTS.md`` / ``~/.agents/GLOBAL.md`` and exposes ``brain/`` task files but offers **no public hook API**.",
        "fallback": "Level 2 only: ``lwm watch`` reads ``~/.agents/brain`` whenever Antigravity writes tasks; CLI fallback via `lwm hub record`.",
        "install": "`lwm hub install-global` (writes ``~/.agents/AGENTS.md`` and ``GLOBAL.md``).",
        "status": "Level 2 file watcher only.",
    },
    "shell": {
        "official": "No hook API. ``zsh`` does have ``preexec`` + ``precmd`` which is what ``lwm/lwm_shell_hook.zsh`` wires up.",
        "fallback": "If users opt out of the shell hook, they may submit important moments via `lwm hub record --tool=shell` explicitly.",
        "install": "`lwm hub install-shell-hook` writes the marker block to ``~/.zshrc``.",
        "status": "Level 1 (zsh hook) — opt-out by setting ``LWM_SHELL_HOOK=0``.",
    },
    "vscode": {
        "official": "VSCode itself has no generic public hook API. The local VS Code-compatible LLM-WorkMem Companion requests bounded start/stop Context through the extension host; Copilot history remains outside the durable evidence path.",
        "fallback": "Without the companion, ``lwm watch`` reads bounded extension metadata and the generated User instruction pointer supplies Context. Users may also use ``lwm hub record --tool=vscode`` after manual tasks.",
        "install": "Install ``integrations/ide-companion`` as a local extension and keep ``llmWorkmem.toolId=vscode`` plus ``llmWorkmem.integration=vscode-extension``; `lwm install-global` remains the instruction-pointer fallback.",
        "status": "Companion native bridge is available and local VS Code start/stop proof is verified; bounded observation is the fallback.",
    },
    "cursor": {
        "official": "Cursor receives the generated ``.cursor/rules/llm-workmem.mdc`` instruction pointer. The VS Code-compatible LLM-WorkMem Companion can request bounded start/stop Context through the extension host.",
        "fallback": "The project companion ``.llm-workmem/events.jsonl`` is tailed by ``adapters.hooks.cursor_tasks`` and enters the same central event pipeline.",
        "install": "Install ``integrations/ide-companion`` as a local extension and set ``llmWorkmem.toolId=cursor`` plus ``llmWorkmem.integration=cursor-extension``; keep the Cursor rule and event contract.",
        "status": "Companion native bridge is available but local Cursor firing remains unverified; project companion observation remains active.",
    },
    "minimax": {
        "official": "MiniMax local sessions are observed from ``~/.minimax/v2/sqlite/runtime-state.sqlite`` and agent rules from ``~/.minimax/agents``. The local MiniMax MCP registry can also load the LLM-WorkMem server for Context, Recall, Retain and Handoff.",
        "fallback": "If the local runtime database or MCP host is unavailable, use the generated ``~/.minimax/lwm-shell.sh`` wrapper or ``lwm-shell-record``.",
        "install": "`lwm hub install-ide-hooks --tools=minimax`",
        "status": "Local MCP bridge, session/database observation and structured shell write-back are available; real MiniMax host read/write proof remains unverified.",
    },
    "gemini-cli": {
        "official": "Gemini CLI reads ``~/.gemini/GEMINI.md`` and project ``GEMINI.md``; shell lifecycle identifies a command invoking the registered ``gemini`` tool.",
        "fallback": "Use the generated GEMINI.md instruction pointer and ``lwm hub bridge`` for bounded Context and structured completion handoff.",
        "install": "`lwm hub install-global`",
        "status": "Shell lifecycle and instruction delivery are supported; no Gemini native session hook is assumed.",
    },
}


SKIP_TITLE_KEYWORDS = (
    "shell",
    "vscode",
    "antigravity",
    "codex",
    "claude-code",
    "kiro",
    "trae-solo",
    "opencode",
    "cursor",
    "minimax",
    "gemini",
)


SECTION_RE = re.compile(
    r"^##\s+(?P<title>official interface|fallback path|install command|current status)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def _today_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def _strip_managed_sections(text: str) -> str:
    """Remove any previously-managed section so we can re-append the current copy."""

    lines = text.splitlines()
    keep: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("## official interface") or stripped.startswith(
            "## fallback path"
        ) or stripped.startswith("## install command") or stripped.startswith(
            "## current status"
        ):
            skipping = True
            continue
        if skipping and line.startswith("## "):
            skipping = False
        if not skipping:
            keep.append(line)
    return "\n".join(keep).rstrip() + "\n"


def _build_section(info: dict[str, str]) -> str:
    out = ["## Official interface", "", info["official"], "", "## Fallback path", "", info["fallback"], "", "## Install command", "", f"```\n{info['install']}\n```", "", "## Current status", "", info["status"], ""]
    return "\n".join(out)


def _update_frontmatter(text: str, updated: str) -> str:
    if not text.startswith("---\n"):
        return text
    lines = text.splitlines(keepends=True)
    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.rstrip("\r\n").strip() == "---"
        ),
        None,
    )
    closing_suffix = ""
    if closing_index is None:
        # Older generated pages occasionally joined the closing delimiter to
        # the first body line (for example ``---Codex``). Preserve that body
        # suffix while normalizing the delimiter.
        closing_index = next(
            (
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.startswith("---") and line[3:].strip()
            ),
            None,
        )
        if closing_index is not None:
            closing_suffix = lines[closing_index][3:]
    if closing_index is None:
        return text
    front = "".join(lines[:closing_index])
    closing = "---\n" if closing_suffix else lines[closing_index]
    body = closing_suffix + "".join(lines[closing_index + 1:])
    front = re.sub(
        r"^type:\s*entityupdated:\s*.*$",
        "type: entity",
        front,
        flags=re.MULTILINE,
    )
    if re.search(r"^updated:\s*.*$", front, flags=re.MULTILINE):
        front = re.sub(
            r"^updated:\s*.*$",
            f"updated: {updated}",
            front,
            flags=re.MULTILINE,
        )
    else:
        if not front.endswith(("\n", "\r")):
            front += "\n"
        front += f"updated: {updated}\n"
    if not closing.endswith(("\n", "\r")):
        closing += "\n"
    return front + closing + body


def _ensure_frontmatter(
    text: str, *, key: str, title: str, updated: str
) -> str:
    """Add the canonical entity frontmatter when an older page lacks it."""

    if text.startswith("---"):
        normalized = _update_frontmatter(text, updated)
        lines = normalized.splitlines(keepends=True)
        closing_index = next(
            (
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.rstrip("\r\n").strip() == "---"
            ),
            None,
        )
        if closing_index is None:
            return normalized
        front = "".join(lines[:closing_index])
        closing = lines[closing_index]
        body = "".join(lines[closing_index + 1:])
    else:
        front = "---\n"
        closing = "---\n"
        body = text.lstrip("\n")

    defaults = (
        ("title", title),
        ("type", "entity"),
        ("tags", f"[entity, tool, {key}]"),
        ("sources", f"[raw/tool-snapshots/{key}/current]"),
    )
    for name, value in defaults:
        if not re.search(rf"^{re.escape(name)}:\s*.*$", front, flags=re.MULTILINE):
            if not front.endswith(("\n", "\r")):
                front += "\n"
            front += f"{name}: {value}\n"
    if not re.search(r"^updated:\s*.*$", front, flags=re.MULTILINE):
        front += f"updated: {updated}\n"
    return front + closing + body


def render_entity_page(root: Path, key: str, info: dict[str, str]) -> Path:
    target = root / "wiki" / "entities" / f"{key}.md"
    title_map = {
        "codex": "Codex CLI",
        "claude-code": "Claude Code",
        "kiro": "Kiro",
        "trae-solo": "Trae (solo IDE)",
        "shell": "Shell (zsh)",
        "antigravity": "Antigravity",
        "vscode": "VSCode",
        "opencode": "OpenCode",
        "cursor": "Cursor",
        "minimax": "MiniMax",
        "gemini-cli": "Gemini CLI",
    }
    if not target.is_file():
        # shells/trae-solo naming: trae-solo lives under that filename;
        # for codex etc. we create the file if missing.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "---\n"
            f"title: {title_map.get(key, key)}\n"
            "type: entity\n"
            "---\n\n"
            "# placeholder\n",
            encoding="utf-8",
        )
    text = target.read_text(encoding="utf-8")
    body = _strip_managed_sections(text)
    body = _ensure_frontmatter(
        body,
        key=key,
        title=title_map.get(key, key),
        updated=_today_iso(),
    )
    body = body.rstrip() + "\n\n" + _build_section(info) + "\n"
    target.write_text(body, encoding="utf-8")
    return target


def render_all(root: Path) -> list[Path]:
    written: list[Path] = []
    for key, info in ENTITIES.items():
        written.append(render_entity_page(root, key, info))
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Augment wiki/entities/*.md with official-interface/fallback-path sections.")
    p.add_argument("--root", required=True, help="Wiki root directory.")
    args = p.parse_args(argv)

    written = render_all(Path(args.root).resolve())
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
