"""Automatic source harvesting and memory-governance snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from lwm.analysis import analyze_wiki, write_analysis_report
from lwm.compile import compile_raw_sources
from lwm.dashboard import write_dashboard_html
from lwm.export import write_ai_exports
from lwm.raw_tracker import run_raw_sync


@dataclass(frozen=True)
class SourceFileSpec:
    path: Path
    label: str
    required: bool = False


@dataclass(frozen=True)
class SourceGroupSpec:
    key: str
    title: str
    target_page: str
    tags: tuple[str, ...]
    sources: tuple[SourceFileSpec, ...]


@dataclass(frozen=True)
class HarvestOutcome:
    root: Path
    captured: tuple[tuple[str, str, str], ...]
    missing: tuple[tuple[str, str], ...]
    snapshot_page: Path
    governance_page: Path
    dashboard_page: Path
    sync_code: int
    sync_message: str
    analysis_report_path: Path
    compiled_count: int


@dataclass(frozen=True)
class ScheduleOutcome:
    root: Path
    label: str
    interval_seconds: int
    runtime_root: Path
    script_path: Path
    runner_path: Path
    launch_runner_path: Path
    plist_path: Path
    launch_agents_plist_path: Path


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser()


def _downloads_root() -> Path:
    return _home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Downloads"


def _runtime_root(root: Path) -> Path:
    return _home() / "Library" / "Application Support" / "llm-workmem-runtime" / _slugify(root.name)


def _ensure_runtime_target(path: Path, *, is_dir: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if is_dir:
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.touch()


def _replace_with_symlink(source: Path, target: Path) -> None:
    if source.is_symlink() and source.resolve() == target.resolve():
        return

    if source.exists() or source.is_symlink():
        if source.is_dir() and not source.is_symlink():
            if target.exists():
                shutil.copytree(source, target, dirs_exist_ok=True)
                shutil.rmtree(source)
            else:
                shutil.move(str(source), str(target))
        elif source.is_file() and not source.is_symlink():
            if target.exists():
                if source.read_bytes() != target.read_bytes():
                    target.write_bytes(source.read_bytes())
                source.unlink()
            else:
                shutil.move(str(source), str(target))
        else:
            source.unlink()

    source.parent.mkdir(parents=True, exist_ok=True)
    source.symlink_to(target, target_is_directory=target.is_dir())


def materialize_runtime_layout(root: Path) -> Path:
    root = root.resolve()
    runtime_root = _runtime_root(root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    package_source = root / "lwm"
    package_target = runtime_root / "lwm"

    mutable_paths = (
        ("raw", True),
        ("wiki", True),
        ("automation", True),
        ("knowledge-digest.pages", True),
        ("knowledge-digest.html", False),
        ("llms.txt", False),
        ("llms-full.txt", False),
        ("llms.json", False),
    )
    for rel_path, is_dir in mutable_paths:
        source = root / rel_path
        target = runtime_root / rel_path
        _ensure_runtime_target(target, is_dir=is_dir)
        _replace_with_symlink(source, target)
    source_config = root / "lwm-sources.json"
    runtime_config = runtime_root / "lwm-sources.json"
    if source_config.is_file() and source_config.resolve() != runtime_config.resolve():
        runtime_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_config, runtime_config)
    source_state = root / "state"
    runtime_state = runtime_root / "state"
    source_state.mkdir(parents=True, exist_ok=True)
    _replace_with_symlink(runtime_state, source_state)
    if package_source.is_dir():
        shutil.copytree(package_source, package_target, dirs_exist_ok=True)
    adapters_source = root / "adapters"
    if adapters_source.is_dir():
        shutil.copytree(adapters_source, runtime_root / "adapters", dirs_exist_ok=True)
    return runtime_root


def default_source_groups() -> tuple[SourceGroupSpec, ...]:
    home = _home()
    app_support = home / "Library" / "Application Support"
    documents = home / "Documents"
    desktop = home / "Desktop"
    return (
        SourceGroupSpec(
            key="codex",
            title="Codex",
            target_page="wiki/entities/codex.md",
            tags=("entity", "tool", "codex", "cli"),
            sources=(
                SourceFileSpec(home / ".codex" / "AGENTS.md", "AGENTS.md"),
                SourceFileSpec(home / ".codex" / "memories" / "MEMORY.md", "MEMORY.md"),
                SourceFileSpec(home / ".codex" / "memories" / "memory_summary.md", "memory_summary.md"),
                SourceFileSpec(
                    home / ".codex" / "memories" / "extensions" / "ad_hoc" / "notes",
                    "ad_hoc_notes",
                ),
            ),
        ),
        SourceGroupSpec(
            key="claude-code",
            title="Claude Code",
            target_page="wiki/entities/claude-code.md",
            tags=("entity", "tool", "claude-code", "cli"),
            sources=(
                SourceFileSpec(home / ".claude" / "CLAUDE.md", "global-CLAUDE.md"),
                SourceFileSpec(home / ".claude" / "settings.json", "settings.json"),
                SourceFileSpec(home / ".claude" / "history.jsonl", "history.jsonl"),
                SourceFileSpec(home / ".claude" / "projects", "session-projects"),
                SourceFileSpec(documents / "claude-code-config" / "memory" / "MEMORY.md", "MEMORY.md"),
                SourceFileSpec(documents / "claude-code-config" / "memory", "claude-memory-folder"),
            ),
        ),
        SourceGroupSpec(
            key="cursor",
            title="Cursor",
            target_page="wiki/entities/cursor.md",
            tags=("entity", "tool", "cursor", "ide"),
            sources=(
                SourceFileSpec(home / ".cursor" / "memory" / "MEMORY.md", "MEMORY.md"),
                SourceFileSpec(home / ".cursor" / "memory-hook.json", "memory-hook.json"),
                SourceFileSpec(home / ".cursor" / "ide_state.json", "ide_state.json"),
            ),
        ),
        SourceGroupSpec(
            key="opencode",
            title="OpenCode",
            target_page="wiki/entities/opencode.md",
            tags=("entity", "tool", "opencode", "cli"),
            sources=(
                SourceFileSpec(home / ".config" / "opencode" / "AGENTS.md", "AGENTS.md"),
                SourceFileSpec(home / ".config" / "opencode" / "commands", "commands"),
                SourceFileSpec(home / ".config" / "opencode" / "README.md", "README.md"),
                SourceFileSpec(home / ".config" / "opencode" / "VALIDATION_REPORT.md", "VALIDATION_REPORT.md"),
            ),
        ),
        SourceGroupSpec(
            key="trae-solo",
            title="Trae Solo",
            target_page="wiki/entities/trae-solo.md",
            tags=("entity", "tool", "trae", "ide"),
            sources=(
                SourceFileSpec(home / ".traerules", ".traerules"),
                SourceFileSpec(app_support / "Trae" / "User" / "settings.json", "settings.json"),
                SourceFileSpec(app_support / "Trae" / "User" / "mcp.json", "mcp.json"),
            ),
        ),
        SourceGroupSpec(
            key="github-copilot",
            title="GitHub Copilot",
            target_page="wiki/entities/github-copilot.md",
            tags=("entity", "tool", "copilot", "github", "vscode"),
            sources=(
                SourceFileSpec(desktop / "Mac旧文件" / "Ethan-GitHub-Copilot-Workflow.md", "Ethan-GitHub-Copilot-Workflow.md"),
                SourceFileSpec(
                    app_support / "Code" / "User" / "globalStorage" / "emptyWindowChatSessions",
                    "vscode-copilot-chat-sessions",
                ),
            ),
        ),
        SourceGroupSpec(
            key="vscode",
            title="VSCode",
            target_page="wiki/entities/vscode.md",
            tags=("entity", "tool", "vscode", "ide"),
            sources=(
                SourceFileSpec(home / ".vscode" / "memory" / "MEMORY.md", "MEMORY.md"),
                SourceFileSpec(home / ".vscode" / "memory" / "WORKFLOW.md", "WORKFLOW.md"),
                SourceFileSpec(home / ".vscode" / "memory" / "HIERARCHICAL_MEMORY_SYSTEM.md", "HIERARCHICAL_MEMORY_SYSTEM.md"),
                SourceFileSpec(app_support / "Code" / "User" / "settings.json", "settings.json"),
            ),
        ),
        SourceGroupSpec(
            key="kiro",
            title="Kiro",
            target_page="wiki/entities/kiro.md",
            tags=("entity", "tool", "kiro", "ide"),
            sources=(
                SourceFileSpec(home / ".kiro" / "steering", "global-steering"),
                SourceFileSpec(home / ".kiro" / "specs", "global-specs"),
                SourceFileSpec(app_support / "Kiro" / "User" / "settings.json", "settings.json"),
                SourceFileSpec(app_support / "Kiro" / "User" / "mcp.json", "mcp.json"),
            ),
        ),
        SourceGroupSpec(
            key="antigravity",
            title="Antigravity",
            target_page="wiki/entities/antigravity.md",
            tags=("entity", "tool", "antigravity", "ide"),
            sources=(
                SourceFileSpec(home / "Documents" / "antigravity" / ".agents" / "AGENTS.md", "AGENTS.md"),
                SourceFileSpec(home / "Documents" / "antigravity" / ".agents" / "GLOBAL.md", "GLOBAL.md"),
                SourceFileSpec(
                    home / "Documents" / "antigravity" / ".agents" / "ai-product-code-iteration-memory.md",
                    "ai-product-code-iteration-memory.md",
                ),
                SourceFileSpec(home / "Documents" / "antigravity" / ".memory", ".memory"),
                SourceFileSpec(home / ".agents" / "AGENTS.md", "home-AGENTS.md"),
                SourceFileSpec(home / ".agents" / "GLOBAL.md", "home-GLOBAL.md"),
            ),
        ),
        SourceGroupSpec(
            key="minimax",
            title="MiniMax",
            target_page="wiki/entities/minimax.md",
            tags=("entity", "tool", "minimax", "agent"),
            sources=(
                SourceFileSpec(home / ".minimax" / "config.yaml", "config.yaml"),
                SourceFileSpec(home / ".minimax" / "agents", "agents"),
                SourceFileSpec(home / ".minimax" / "skills", "skills"),
                SourceFileSpec(home / ".minimax" / "mcp" / "mcp.json", "mcp.json"),
                SourceFileSpec(home / ".minimax" / "recovery.json", "recovery.json"),
            ),
        ),
        SourceGroupSpec(
            key="shell",
            title="Shell",
            target_page="wiki/entities/shell.md",
            tags=("entity", "tool", "shell", "zsh"),
            sources=(
                SourceFileSpec(home / ".zshrc", ".zshrc"),
                SourceFileSpec(home / ".zprofile", ".zprofile"),
                SourceFileSpec(home / ".zshenv", ".zshenv"),
                SourceFileSpec(home / ".config" / "shell", "shell-config"),
                SourceFileSpec(home / ".config" / "zsh", "zsh-config"),
                SourceFileSpec(home / ".shell-memory.md", "shell-memory.md"),
            ),
        ),
    )



def _configured_source_groups_path(root: Path) -> Path:
    return root / "lwm-sources.json"


def _read_configured_groups(root: Path) -> tuple[SourceGroupSpec, ...]:
    path = _configured_source_groups_path(root)
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        return ()
    parsed: list[SourceGroupSpec] = []
    for item in groups:
        if not isinstance(item, dict):
            continue
        sources_payload = item.get("sources", [])
        if not isinstance(sources_payload, list):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        sources: list[SourceFileSpec] = []
        for source in sources_payload:
            if not isinstance(source, dict):
                continue
            source_path = str(source.get("path", "")).strip()
            if not source_path:
                continue
            sources.append(
                SourceFileSpec(
                    Path(source_path).expanduser(),
                    str(source.get("label") or Path(source_path).name or "source"),
                    bool(source.get("required", False)),
                )
            )
        parsed.append(
            SourceGroupSpec(
                key=key,
                title=str(item.get("title") or key),
                target_page=str(item.get("target_page") or f"wiki/entities/{key}.md"),
                tags=tuple(str(tag) for tag in item.get("tags", ["entity", "tool"])),
                sources=tuple(sources),
            )
        )
    return tuple(parsed)


def configured_source_groups(root: Path | None = None) -> tuple[SourceGroupSpec, ...]:
    groups = list(default_source_groups())
    if root is not None:
        groups.extend(_read_configured_groups(root.resolve()))
    return tuple(groups)


def render_source_groups(root: Path | None = None) -> str:
    groups = configured_source_groups(root)
    lines = ["# Source Groups", ""]
    for group in groups:
        lines.append(f"## {group.title} (`{group.key}`)")
        lines.append(f"- Target page: `{group.target_page}`")
        lines.append("- Sources:")
        for source in group.sources:
            status = "found" if _path_exists(source.path) else "missing"
            lines.append(f"  - `{source.label}` -> `{source.path}` ({status})")
        lines.append("")
    if root is not None:
        lines.append(f"Config file: `{_configured_source_groups_path(root.resolve())}`")
    return "\n".join(lines)


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _path_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _iter_files(path: Path) -> Iterable[Path]:
    try:
        for item in sorted(path.rglob("*")):
            if _path_is_file(item):
                yield item
    except OSError:
        return


def _read_text(path: Path) -> str:
    if not _path_is_file(path):
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
        if match:
            return text[match.end() :]
    return text


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip().lower())
    slug = slug.strip("-._")
    return slug or "item"


def _leading_excerpt(text: str, limit: int = 14) -> list[str]:
    body = _strip_frontmatter(text)
    lines: list[str] = []
    for line_no, raw_line in enumerate(body.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            lines.append(f"[L{line_no}] {line}")
            continue
        if line.startswith("## "):
            lines.append(f"[L{line_no}] {line}")
            continue
        if line.startswith("- ") or line.startswith("* "):
            lines.append(f"[L{line_no}] {line}")
            continue
        if line.startswith("> "):
            lines.append(f"[L{line_no}] {line}")
            continue
        if len(line) > 140:
            line = line[:140].rstrip() + "..."
        lines.append(f"[L{line_no}] {line}")
        if len(lines) >= limit:
            break
    return lines


def _snapshot_path(root: Path, group: SourceGroupSpec, source: SourceFileSpec, stamp: str) -> Path:
    target = root / "raw" / "tool-snapshots" / group.key / stamp
    if source.path.is_dir():
        return target / source.label
    return target / source.label


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render_governance_page(root: Path, stamp: str, groups: tuple[SourceGroupSpec, ...]) -> str:
    return f"""---
title: Memory Governance
type: concept
tags: [concept, memory, governance, workflow]
sources: []
updated: {stamp}
---

# Memory Governance

This page defines the working memory lifecycle for the llm-workmem-first setup.

## Memory Layers

- **Working**: the current task and the active thread.
- **Session**: decisions and context that should survive the current conversation.
- **Project**: reusable project-level facts, constraints, and playbooks.
- **Global**: stable operating rules, preferences, and cross-project principles.

## Promotion Rules

- Promote only durable working style and workflow rules.
- Keep project facts and ephemeral fixes out of the global layer.
- Prefer explicit links and dated snapshots over implicit memory.
- Re-run harvest before promoting anything into durable pages.

## Tool Sources

{chr(10).join(f'- [[{group.key}]]' for group in groups)}

## See Also

- [[purpose]]
- [[overview]]
- [[workflow-policy]]
- [[memory-policy]]
"""


def _render_harvest_page(
    root: Path,
    stamp: str,
    groups: tuple[SourceGroupSpec, ...],
    captured: tuple[tuple[str, str, str], ...],
    missing: tuple[tuple[str, str], ...],
) -> str:
    rows = []
    for tool, rel, path in captured:
        rows.append(f"| {tool} | {rel} | {path} |")
    if not rows:
        rows.append("| _none_ | _none_ | _none_ |")

    missing_rows = []
    for tool, rel in missing:
        missing_rows.append(f"- {tool}: {rel}")
    if not missing_rows:
        missing_rows.append("- None")

    section_blocks: list[str] = []
    for group in groups:
        section_blocks.append(f"## {group.title}")
        source_block_found = False
        for source in group.sources:
            text = _read_text(source.path)
            if not text:
                continue
            source_block_found = True
            excerpt = _leading_excerpt(text)
            section_blocks.append(f"### {source.label}")
            section_blocks.append(f"- Source: `{source.path}`")
            if excerpt:
                safe_excerpt = [
                    line.replace("[[", "⟦⟦").replace("]]", "⟧⟧")
                    for line in excerpt[:8]
                ]
                section_blocks.append("```text")
                section_blocks.extend(safe_excerpt)
                section_blocks.append("```")
            else:
                section_blocks.append("  - _No textual excerpt available._")
        if not source_block_found:
            section_blocks.append("_No available source files were found for this tool._")
        section_blocks.append("")

    return f"""---
title: Tool Harvest
type: insight
tags: [insight, harvest, automation, memory]
sources: []
updated: {stamp}
---

# Tool Harvest

This snapshot is generated automatically from the active tool memory sources and working docs.

## Captured Sources

| Tool | Source | Snapshot |
|------|--------|----------|
{chr(10).join(rows)}

## Missing Sources

{chr(10).join(missing_rows)}

## Current Snapshot

{chr(10).join(section_blocks)}

## Memory Governance

- See [[memory-governance]] for the current layer model and promotion rules.
- Harvest before promotion, not after.
- Keep durable rules separated from temporary work threads.

## See Also

- [[overview]]
- [[purpose]]
- [[memory-governance]]
"""


def _render_group_page(
    group: SourceGroupSpec,
    stamp: str,
    source_files: tuple[SourceFileSpec, ...],
    captured_entries: tuple[tuple[str, str, str], ...],
) -> str:
    source_paths = sorted(
        {
            path
            for tool, _label, path in captured_entries
            if tool == group.key
        }
    )
    source_lines = [f"- `{path}`" for path in source_paths]
    if not source_lines:
        source_lines = [f"- `{source.path}`" for source in source_files if source.path.exists()]
    return f"""---
title: {group.title}
type: {group.tags[0] if group.tags else "entity"}
tags: [{", ".join(group.tags)}]
sources: [{", ".join(source_paths)}]
updated: {stamp}
---

# {group.title}

This page is kept fresh by `lwm harvest`.

## Source Set

{chr(10).join(source_lines)}

## Notes

- Auto-generated from the latest source snapshot.
- Use the linked harvest snapshot for the fuller reading of current working memory.

## See Also

- [[tool-harvest]]
- [[memory-governance]]
"""


def _launch_runner_path(label: str, root: Path) -> Path:
    return root / "automation" / "launchd" / label / "run-harvest.py"


def _installed_lwm_path() -> Path:
    """Return the one runtime used by launchd and all generated schedules."""
    global_launcher = Path.home() / ".local" / "bin" / "lwm"
    if global_launcher.is_file():
        return global_launcher
    return Path.home() / "Library" / "Application Support" / "llm-workmem-runtime" / "app" / "venv" / "bin" / "lwm"


def _render_launchd_plist(
    label: str,
    root: Path,
    interval_seconds: int,
    *,
    launch_runner_path: Path,
) -> str:
    stdout_path = (root / "automation" / "logs" / "harvest.out.log").resolve()
    stderr_path = (root / "automation" / "logs" / "harvest.err.log").resolve()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{_installed_lwm_path()}</string>
    <string>hub</string>
    <string>run-supervisor</string>
    <string>{root.resolve()}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>{interval_seconds}</integer>
  <key>FullCycleInterval</key>
  <integer>43200</integer>
  <key>StandardOutPath</key>
  <string>{stdout_path}</string>
  <key>StandardErrorPath</key>
  <string>{stderr_path}</string>
</dict>
</plist>
"""


def _render_schedule_runner(runtime_root: Path, *, label: str, source_root: Path) -> str:
    launch_base = _launch_runner_path(label, runtime_root).parent
    return f'''"""15-minute supervisor for the 12-hour llm-workmem full cycle.

Generated by `lwm schedule`. This script deliberately avoids `uv run` so
launchd can keep working when network access or dependency downloads are unavailable.
"""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path({str(runtime_root)!r})
LAUNCH_BASE = Path({str(launch_base)!r})
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LAUNCH_BASE))

from lwm.supervisor import run_supervisor
# The full cycle still includes run_watch and render_watch_report via lwm.runner.


def main() -> int:
    return run_supervisor(ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_schedule_bundle(
    root: Path, *, label: str, interval_seconds: int = 900
) -> ScheduleOutcome:
    root = root.resolve()
    runtime_root = materialize_runtime_layout(root)
    script_path = root / "automation" / "bin" / "run-harvest.sh"
    runner_path = root / "automation" / "bin" / "run-harvest.py"
    launch_runner_path = _launch_runner_path(label, runtime_root)
    launch_base = launch_runner_path.resolve().parent
    plist_path = root / "automation" / "launchd" / f"{label}.plist"
    launch_agents_plist_path = _home() / "Library" / "LaunchAgents" / f"{label}.plist"

    script_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    launch_base.mkdir(parents=True, exist_ok=True)
    launch_agents_plist_path.parent.mkdir(parents=True, exist_ok=True)
    (root / "automation" / "logs").mkdir(parents=True, exist_ok=True)

    script_path.write_text(
        f"""#!/bin/zsh
set -euo pipefail
# Full cycles remain available as `hub run-cycle`; launchd uses the supervisor.
{shlex.quote(str(_installed_lwm_path()))} hub run-supervisor {shlex.quote(str(runtime_root))}
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    runner_text = _render_schedule_runner(runtime_root, label=label, source_root=root)
    runner_path.write_text(runner_text, encoding="utf-8")
    runner_path.chmod(0o755)
    launch_runner_path.write_text(runner_text, encoding="utf-8")
    launch_runner_path.chmod(0o755)
    plist_path.write_text(
        _render_launchd_plist(
            label,
            runtime_root,
            interval_seconds,
            launch_runner_path=launch_runner_path,
        ),
        encoding="utf-8",
    )
    launch_agents_plist_path.write_text(plist_path.read_text(encoding="utf-8"), encoding="utf-8")
    return ScheduleOutcome(
        root=root,
        label=label,
        interval_seconds=interval_seconds,
        runtime_root=runtime_root,
        script_path=script_path,
        runner_path=runner_path,
        launch_runner_path=launch_runner_path,
        plist_path=plist_path,
        launch_agents_plist_path=launch_agents_plist_path,
    )


def load_schedule_bundle(bundle: ScheduleOutcome) -> None:
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["launchctl", "bootout", domain, str(bundle.launch_agents_plist_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["launchctl", "bootstrap", domain, str(bundle.launch_agents_plist_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"{domain}/{bundle.label}"],
        check=True,
        capture_output=True,
        text=True,
    )


def harvest_sources(root: Path, *, compile_after_sync: bool = True) -> HarvestOutcome:
    root = root.resolve()
    stamp = date.today().isoformat()
    groups = configured_source_groups(root)
    raw_root = root / "raw" / "tool-snapshots"
    captured: list[tuple[str, str, str]] = []
    missing: list[tuple[str, str]] = []

    for group in groups:
        for source in group.sources:
            if _path_is_dir(source.path):
                files = list(_iter_files(source.path))
                if not files:
                    missing.append((group.key, source.label))
                    continue
                for item in files:
                    text = _read_text(item)
                    if not text.strip():
                        missing.append((group.key, f"{source.label}/{item.name}"))
                        continue
                    rel = item.relative_to(source.path)
                    snapshot_path = raw_root / group.key / stamp / source.label / rel
                    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                    snapshot_path.write_text(text, encoding="utf-8")
                    captured.append((group.key, source.label, str(snapshot_path.relative_to(root))))
                continue

            if not _path_exists(source.path):
                missing.append((group.key, source.label))
                continue
            text = _read_text(source.path)
            if not text.strip():
                missing.append((group.key, source.label))
                continue
            snapshot_path = raw_root / group.key / stamp / _slugify(source.label)
            snapshot_path = snapshot_path.with_suffix(source.path.suffix or ".md")
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(text, encoding="utf-8")
            captured.append((group.key, source.label, str(snapshot_path.relative_to(root))))

    governance_page = root / "wiki" / "concepts" / "memory-governance.md"
    governance_page.parent.mkdir(parents=True, exist_ok=True)
    governance_page.write_text(_render_governance_page(root, stamp, groups), encoding="utf-8")

    harvest_page = root / "wiki" / "insights" / f"tool-harvest-{stamp}.md"
    harvest_page.parent.mkdir(parents=True, exist_ok=True)
    harvest_page.write_text(
        _render_harvest_page(root, stamp, groups, tuple(captured), tuple(missing)),
        encoding="utf-8",
    )

    for group in groups:
        target = root / group.target_page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            _render_group_page(
                group,
                stamp,
                group.sources,
                tuple(captured),
            ),
            encoding="utf-8",
        )

    overview = root / "wiki" / "overview.md"
    if overview.exists():
        current = overview.read_text(encoding="utf-8")
        if "## Automation Status" not in current:
            current = current.rstrip() + f"""

## Automation Status

- Latest harvest: {stamp}
- Sources captured: {len(captured)}
- Missing source slots: {len(missing)}
- Workflow memory is now maintained by `lwm harvest`.

## See Also

- [[tool-harvest]]
- [[memory-governance]]
"""
        else:
            current = re.sub(
                r"## Automation Status\n\n.*?\n## See Also\n",
                (
                    "## Automation Status\n\n"
                    f"- Latest harvest: {stamp}\n"
                    f"- Sources captured: {len(captured)}\n"
                    f"- Missing source slots: {len(missing)}\n"
                    "- Workflow memory is now maintained by `lwm harvest`.\n\n"
                    "## See Also\n"
                ),
                current,
                flags=re.DOTALL,
            )
        overview.write_text(current, encoding="utf-8")

    sync_code, sync_message = run_raw_sync(root / "raw")
    compiled_count = 0
    if compile_after_sync:
        compile_report = compile_raw_sources(root)
        compiled_count = len([item for item in compile_report.compiled if item.changed])
    analysis = analyze_wiki(root)
    analysis_report_path = write_analysis_report(root, analysis)
    dashboard_page = write_dashboard_html(root, root / "knowledge-digest.html")
    write_ai_exports(root)

    return HarvestOutcome(
        root=root,
        captured=tuple(captured),
        missing=tuple(missing),
        snapshot_page=harvest_page,
        governance_page=governance_page,
        dashboard_page=dashboard_page,
        sync_code=sync_code,
        sync_message=sync_message,
        analysis_report_path=analysis_report_path,
        compiled_count=compiled_count,
    )
