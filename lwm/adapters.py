"""Per-tool adapters that let IDEs and shells consume llm-workmem."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from lwm import behavior_contract
from lwm.behavior_contract import load as load_behavior_contract
from lwm.harvest import canonical_data_root, runtime_paths

MARKER_START = "<!-- LLM-WIKI:START -->"
MARKER_END = "<!-- LLM-WIKI:END -->"
SHELL_MARKER_START = "# LLM-WIKI:START"
SHELL_MARKER_END = "# LLM-WIKI:END"


@dataclass(frozen=True)
class AdapterReport:
    root: Path
    target: Path
    written: tuple[Path, ...]


@dataclass(frozen=True)
class AttachReport:
    root: Path
    project: Path
    written: tuple[Path, ...]


def _bridge_context_command(
    root: Path,
    *,
    tool: str,
    project: Path | None = None,
) -> str:
    """Render one safe startup Context command for generated host rules."""

    quoted_root = shlex.quote(str(root.resolve()))
    if project is not None:
        payload = json.dumps(
            {
                "phase": "context",
                "tool": tool,
                "project_path": str(project.resolve()),
            },
            ensure_ascii=False,
        )
        return f"lwm hub bridge {shlex.quote(payload)} --output markdown --root {quoted_root}"
    python_code = (
        "import json,sys; "
        f"print(json.dumps({{'phase':'context','tool':{json.dumps(tool)},"
        "'project_path':sys.stdin.read()}))"
    )
    return (
        "printf '%s' \"$PWD\" | "
        f"python3 -c {shlex.quote(python_code)} | "
        f"lwm hub bridge --output markdown --root {quoted_root}"
    )


def _context_block(
    root: Path, *, tool: str = "shell", project: Path | None = None
) -> str:
    root = root.resolve()
    project_line = f"\nProject: `{project}`" if project else ""
    quoted_root = shlex.quote(str(root))
    context_cmd = _bridge_context_command(
        root, tool=tool, project=project
    )
    contract = load_behavior_contract(root)
    contract_reference = _contract_reference(root, contract)
    contract_line = (
        f"version={contract.version} sha256={contract.sha256 or 'missing'} "
        f"status={contract.status}"
    )
    return f"""{MARKER_START}
# LLM-WorkMem Context

Use `{contract_reference}` as the shared personal behavior contract for this tool.{project_line}
Project memory, handoffs, Recall and review candidates are auxiliary evidence; native platform safety rules, instructions, skills, memory, planning, execution and verification remain authoritative.
Canonical personal behavior contract: `{contract_reference}` ({contract_line}).
Reuse context already injected by a native hook, plugin, companion, or the current
session. Do not run a second startup fetch when equivalent context is present.

Read order:
0. When the task depends on historical decisions, cross-tool continuation, or
   missing project evidence and no equivalent context is already present, run
   `{context_cmd}` for bounded dynamic context.
1. `{root / 'llms.txt'}` for compact context (fallback if step 0 is unavailable).
2. `{root / 'wiki' / 'purpose.md'}` for scope and guardrails.
3. `{root / 'wiki' / 'overview.md'}` for the current synthesis.
4. `{root / 'llms-full.txt'}` only when deeper context is needed.
5. `{root / 'llms.json'}` for programmatic page metadata.

Write-back:
- After meaningful work that changed verified cross-tool state, emit a bounded
  event via `lwm hub record`. Skip unchanged-state write-back.
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.

Structured write-back for completed work:
- Record only bounded decisions, changes, verifications, risks, or open questions; do not paste a transcript or raw prompt.
- For cross-tool continuation, submit a bounded handoff with:
  `lwm hub bridge-stop --tool {tool} --project "$PWD" --task-id "$LWM_TASK_ID" --handoff-json '{{"task_id":"...","objective":"...","current_state":"...","changes":["..."],"verifications":["..."],"risks":[],"open_questions":[],"next_action":"..."}}' --root {quoted_root}`
- A handoff is evidence for the next tool, not a replacement for native instructions, skills, planning, execution, or verification.
{MARKER_END}
"""


def _contract_reference(root: Path, contract: object) -> Path:
    """Return the behavior-contract path that exists for this runtime.

    A runtime data root normally contains the verified snapshot rather than a
    checkout-level ``GLOBAL.md``. Generated adapters must therefore point at
    the snapshot when the source contract is unavailable.
    """

    if getattr(contract, "status", "missing") == "stale":
        return root / behavior_contract.SNAPSHOT_PATH
    raw_path = str(getattr(contract, "path", "") or "")
    path = Path(raw_path)
    return path if path.is_absolute() else root / (path or behavior_contract.CONTRACT_PATH)


def _cursor_rules_block(root: Path, *, project: Path | None = None) -> str:
    """Cursor .mdc rule body.

    Cursor reads project rules from ``.cursor/rules/*.mdc``. The same body is
    reused for the legacy single-file ``.cursorrules`` (no frontmatter needed
    there — Cursor falls back to plain markdown).
    """
    root = root.resolve()
    quoted_root = shlex.quote(str(root))
    project_line = f"\nProject: `{project}`" if project else ""
    context_cmd = _bridge_context_command(root, tool="cursor", project=project)
    contract = load_behavior_contract(root)
    contract_reference = _contract_reference(root, contract)
    contract_line = (
        f"version={contract.version} sha256={contract.sha256 or 'missing'} "
        f"status={contract.status}"
    )
    body = f"""---
description: Shared personal behavior contract plus auxiliary evidence context (always apply)
globs:
alwaysApply: true
---

# LLM-WorkMem Context

Use `{contract_reference}` as the shared personal behavior contract for this tool.{project_line}
Project memory, handoffs, Recall and review candidates are auxiliary evidence; native platform safety rules, instructions, skills, memory, planning, execution and verification remain authoritative.
Canonical personal behavior contract: `{contract_reference}` ({contract_line}).

Read order:
1. `{root / "llms.txt"}` for compact context.
2. `{root / "wiki" / "purpose.md"}` for scope and guardrails.
3. `{root / "wiki" / "overview.md"}` for the current synthesis.
4. `{root / "llms-full.txt"}` only when deeper context is needed.
5. `{root / "llms.json"}` for programmatic page metadata.

Rules:
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.

On session start, refresh bounded context with:
`{context_cmd}`

For completed work, use structured write-back rather than a transcript:
`lwm hub bridge-stop --tool cursor --project "$PWD" --task-id "$LWM_TASK_ID" --handoff-json '{{"task_id":"...","objective":"...","current_state":"...","changes":["..."],"verifications":["..."],"risks":[],"open_questions":[],"next_action":"..."}}' --root {quoted_root}`
"""
    return body


def _gemini_block(root: Path, *, project: Path | None = None) -> str:
    """Gemini CLI GEMINI.md body.

    Gemini CLI reads ``~/.gemini/GEMINI.md`` (global) and any ``GEMINI.md`` in
    the cwd / project tree. It uses plain markdown — no frontmatter needed.
    """
    root = root.resolve()
    quoted_root = shlex.quote(str(root))
    project_line = f"\nProject: `{project}`" if project else ""
    context_cmd = _bridge_context_command(root, tool="gemini-cli", project=project)
    contract = load_behavior_contract(root)
    contract_reference = _contract_reference(root, contract)
    contract_line = (
        f"version={contract.version} sha256={contract.sha256 or 'missing'} "
        f"status={contract.status}"
    )
    return f"""# LLM-WorkMem Context

Use `{contract_reference}` as the shared personal behavior contract for this tool.{project_line}
Project memory, handoffs, Recall and review candidates are auxiliary evidence; native platform safety rules, instructions, skills, memory, planning, execution and verification remain authoritative.
Canonical personal behavior contract: `{contract_reference}` ({contract_line}).

Read order:
1. `{root / "llms.txt"}` for compact context.
2. `{root / "wiki" / "purpose.md"}` for scope and guardrails.
3. `{root / "wiki" / "overview.md"}` for the current synthesis.
4. `{root / "llms-full.txt"}` only when deeper context is needed.
5. `{root / "llms.json"}` for programmatic page metadata.

Rules:
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.

On session start, refresh bounded context with:
`{context_cmd}`

For completed work, use structured write-back rather than a transcript:
`lwm hub bridge-stop --tool gemini-cli --project "$PWD" --task-id "$LWM_TASK_ID" --handoff-json '{{"task_id":"...","objective":"...","current_state":"...","changes":["..."],"verifications":["..."],"risks":[],"open_questions":[],"next_action":"..."}}' --root {quoted_root}`
"""


def _shell_context(root: Path) -> str:
    root = root.resolve()
    quoted_root = shlex.quote(str(root))
    contract = load_behavior_contract(root)
    contract_reference = _contract_reference(root, contract)
    contract_line = (
        f"version={contract.version} sha256={contract.sha256 or 'missing'} "
        f"status={contract.status}"
    )
    return """#!/bin/zsh
# Generated by `lwm adapters`. Source this file from zsh when you want
# shell commands that expose the shared llm-workmem context.

if [[ -z "${{LWM_ROOT:-}}" ]]; then
  export LWM_ROOT={quoted_root}
fi

# Canonical behavior contract: {contract_reference} ({contract_line})

lwm-root() {{
  printf '%s\\n' "$LWM_ROOT"
}}

lwm-open() {{
  open "$LWM_ROOT/knowledge-digest.html"
}}

lwm-status() {{
  local lwm_bin="${{LWM_BIN:-lwm}}"
  "$lwm_bin" audit "$LWM_ROOT"
}}

lwm-refresh() {{
  local lwm_bin="${{LWM_BIN:-lwm}}"
  "$lwm_bin" watch "$LWM_ROOT"
}}

lwm-context() {{
  local project="${{PWD}}"
  local lwm_bin="${{LWM_BIN:-lwm}}"
  printf '%s' "$project" \\
    | python3 -c 'import json,sys; print(json.dumps({{"phase":"context","tool":"shell","project_path":sys.stdin.read()}}))' \\
    | "$lwm_bin" hub bridge --output markdown --root "$LWM_ROOT"
}}
""".format(
        quoted_root=quoted_root,
        contract_reference=str(contract_reference),
        contract_line=contract_line,
    )


def _global_lwm_launcher(root: Path, *, home: Path | None = None) -> str:
    """Stable ``lwm`` command for IDE terminals outside the iCloud source tree."""
    paths = runtime_paths(root, home=home)
    runtime_python = paths.app_venv / "bin" / "python"
    fallback_python = root / ".venv" / "bin" / "python"
    return f'''#!/bin/zsh
# Generated by `lwm install-global`. Keep IDE terminals on the stable runtime
# copy. The source checkout venv is development-only fallback.
runtime_root={str(paths.runtime_base)!r}
python_bin={str(runtime_python)!r}
fallback_python={str(fallback_python)!r}

if [[ ! -x "$python_bin" ]]; then
  python_bin="$fallback_python"
fi
exec "${{python_bin}}" -I -m lwm.cli "$@"
'''


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    if path.suffix == ".sh" or path.name == "lwm":
        path.chmod(0o755)
    return path


def _merge_marked_block(path: Path, block: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    # Detect either HTML markers or shell (# comment) markers.
    marker_start, marker_end = MARKER_START, MARKER_END
    if SHELL_MARKER_START in existing and SHELL_MARKER_END in existing and MARKER_START not in existing:
        marker_start, marker_end = SHELL_MARKER_START, SHELL_MARKER_END
    if marker_start in existing and marker_end in existing:
        before = existing.split(marker_start, 1)[0].rstrip()
        after = existing.split(marker_end, 1)[1].lstrip()
        content = "\n\n".join(part for part in (before, block.rstrip(), after.rstrip()) if part)
    elif existing.strip():
        content = existing.rstrip() + "\n\n" + block.rstrip()
    else:
        content = block.rstrip()
    path.write_text(content + "\n", encoding="utf-8")
    return path


def _normalize_legacy_context_reference(path: Path, root: Path, *, tool: str) -> Path:
    """Move one known checkout-based startup command without touching user text.

    Older global steering files may contain a hand-written context command
    outside the generated marker. Replace only a quoted path that clearly
    names an LLM-WorkMem checkout; leave all other commands and prose intact.
    """

    if not path.is_file():
        return path
    existing = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(lwm hub context --tool {re.escape(tool)}\s+)([\"'])([^\"']*"
        rf"(?:LLM-WorkMem|llm-workmem|lwm-workmem)[^\"']*)([\"'])",
        re.IGNORECASE,
    )
    updated, count = pattern.subn(rf"\g<1>\g<2>{root}\g<4>", existing)
    if count and updated != existing:
        path.write_text(updated, encoding="utf-8")
    return path


def _cursor_global_paths(home: Path) -> tuple[Path, ...]:
    """Cursor rule files that should receive the LLM-WorkMem block.

    Order of precedence (most-preferred first): the modern ``.cursor/rules/*.mdc``
    location is what Cursor 2026 actually loads, so we always write a dedicated
    rule file there. The legacy ``.cursor/.cursorrules`` file is still honored
    by older Cursor installs, so we keep a copy at the legacy path too.
    """
    return (
        home / ".cursor" / "rules" / "llm-workmem.mdc",
        home / ".cursor" / ".cursorrules",
    )


def _gemini_global_paths(home: Path) -> tuple[Path, ...]:
    return (home / ".gemini" / "GEMINI.md",)


def _vscode_global_path(home: Path) -> Path:
    return (
        home
        / "Library"
        / "Application Support"
        / "Code"
        / "User"
        / "prompts"
        / "llm-workmem.instructions.md"
    )


def _vscode_instruction_block(root: Path) -> str:
    """VS Code/Copilot user instruction with an explicit global match rule."""
    return f'''---
name: llm-workmem
description: Shared workflow and memory source for all VS Code agent sessions
applyTo: "**"
---

{_context_block(root, tool="vscode").strip()}
'''


def _opencode_global_path(home: Path) -> Path:
    return home / ".config" / "opencode" / "AGENTS.md"


def _write_gemini_append(path: Path, body: str) -> Path:
    """Idempotent append for ``~/.gemini/GEMINI.md``.

    Gemini CLI has no native marker protocol, so we use a banner + a sentinel
    line. If the sentinel already exists, we replace the previous LLM-WorkMem
    section in place instead of duplicating.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_start = "<!-- LBM-WIKI:GEMINI:START -->"
    sentinel_end = "<!-- LBM-WIKI:GEMINI:END -->"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    section = f"{sentinel_start}\n{body.rstrip()}\n{sentinel_end}"
    if sentinel_start in existing and sentinel_end in existing:
        before = existing.split(sentinel_start, 1)[0].rstrip()
        after = existing.split(sentinel_end, 1)[1].lstrip()
        parts = [p for p in (before, section, after) if p]
        content = "\n\n".join(parts)
    elif existing.strip():
        content = existing.rstrip() + "\n\n" + section
    else:
        content = section
    path.write_text(content + "\n", encoding="utf-8")
    return path


def _write_cursor_rule(path: Path, body: str) -> Path:
    """Write a Cursor rule file, replacing any previous LLM-WorkMem block.

    Modern ``.cursor/rules/*.mdc`` files are independent — we overwrite ours.
    The legacy ``.cursor/.cursorrules`` file is treated like GEMINI.md: a
    sentinel-bracketed block is replaced in place so user-authored rules above
    and below are preserved.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".mdc":
        path.write_text(body.rstrip() + "\n", encoding="utf-8")
        return path
    sentinel_start = "<!-- LBM-WIKI:CURSOR:START -->"
    sentinel_end = "<!-- LBM-WIKI:CURSOR:END -->"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    section = f"{sentinel_start}\n{body.rstrip()}\n{sentinel_end}"
    if sentinel_start in existing and sentinel_end in existing:
        before = existing.split(sentinel_start, 1)[0].rstrip()
        after = existing.split(sentinel_end, 1)[1].lstrip()
        parts = [p for p in (before, section, after) if p]
        content = "\n\n".join(parts)
    elif existing.strip():
        content = existing.rstrip() + "\n\n" + section
    else:
        content = section
    path.write_text(content + "\n", encoding="utf-8")
    return path


def _antigravity_global_paths(home: Path) -> tuple[Path, ...]:
    return (
        home / ".agents" / "AGENTS.md",
        home / ".agents" / "GLOBAL.md",
    )


def _antigravity_hooks_path(home: Path) -> Path:
    """Return the global Antigravity lifecycle-hook configuration path."""

    return home / ".gemini" / "config" / "hooks.json"


def _codex_hooks_path(home: Path) -> Path:
    """Return Codex's user-level native hook configuration path."""

    return home / ".codex" / "hooks.json"


def _cursor_hooks_path(home: Path) -> Path:
    """Return Cursor's user-level native hook configuration path."""

    return home / ".cursor" / "hooks.json"


def _gemini_cli_hooks_path(home: Path) -> Path:
    """Return Gemini CLI's global settings file containing its hooks object."""

    return home / ".gemini" / "settings.json"


def _antigravity_hook_command(root: Path, *, home: Path, phase: str) -> str:
    """Use the installed runtime, never the iCloud source checkout, for hooks."""

    paths = runtime_paths(root, home=home)
    return shlex.join(
        [
            str(paths.app_venv / "bin" / "python"),
            "-I",
            "-m",
            "adapters.hooks.antigravity_native",
            "--root",
            str(root.resolve()),
            "--phase",
            phase,
        ]
    )


def _is_antigravity_generated_handler(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    command = value.get("command")
    return isinstance(command, str) and "adapters.hooks.antigravity_native" in command


def _native_hook_command(root: Path, *, home: Path, module: str, phase: str) -> str:
    """Render a native hook command against the installed runtime only."""

    paths = runtime_paths(root, home=home)
    return shlex.join(
        [
            str(paths.app_venv / "bin" / "python"),
            "-I",
            "-m",
            module,
            "--root",
            str(root.resolve()),
            "--phase",
            phase,
        ]
    )


def _is_generated_native_handler(value: object, module: str) -> bool:
    if not isinstance(value, dict):
        return False
    command = value.get("command")
    return isinstance(command, str) and module in command


def _write_cursor_hooks(path: Path, root: Path, *, home: Path) -> Path:
    """Merge Cursor lifecycle hooks while preserving user-owned handlers."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"refusing to overwrite invalid Cursor hooks file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"refusing to overwrite non-object Cursor hooks file: {path}")
    else:
        payload = {}

    version = payload.get("version", 1)
    if not isinstance(version, int):
        raise ValueError(f"refusing to overwrite invalid Cursor hooks version: {path}")
    configured = payload.get("hooks")
    if configured is None:
        configured = {}
    if not isinstance(configured, dict):
        raise ValueError(f"refusing to overwrite non-object Cursor hooks section: {path}")

    hooks = dict(configured)
    for event, phase in (("sessionStart", "session-start"), ("sessionEnd", "session-end")):
        current = hooks.get(event, [])
        if not isinstance(current, list):
            raise ValueError(f"refusing to overwrite invalid Cursor {event} handlers: {path}")
        retained = [
            item
            for item in current
            if not _is_generated_native_handler(item, "adapters.hooks.cursor_native")
        ]
        retained.append(
            {
                "command": _native_hook_command(
                    root,
                    home=home,
                    module="adapters.hooks.cursor_native",
                    phase=phase,
                ),
                "timeout": 15,
            }
        )
        hooks[event] = retained

    payload["version"] = version
    payload["hooks"] = hooks
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_native_lifecycle_hooks(
    path: Path,
    root: Path,
    *,
    home: Path,
    module: str,
    events: tuple[tuple[str, str], ...],
    matcher: str | None = "",
) -> Path:
    """Merge generated lifecycle groups while preserving all user handlers."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"refusing to overwrite invalid native hooks file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"refusing to overwrite non-object native hooks file: {path}")
    else:
        payload = {}

    configured = payload.get("hooks")
    if configured is None:
        configured = {}
    if not isinstance(configured, dict):
        raise ValueError(f"refusing to overwrite non-object hooks section: {path}")
    hooks = dict(configured)

    for event, phase in events:
        current = hooks.get(event, [])
        if not isinstance(current, list):
            raise ValueError(f"refusing to overwrite invalid {event} handlers: {path}")
        retained_groups: list[object] = []
        for group in current:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained_groups.append(group)
                continue
            handlers = group["hooks"]
            retained_handlers = [
                item for item in handlers if not _is_generated_native_handler(item, module)
            ]
            if len(retained_handlers) == len(handlers):
                retained_groups.append(group)
            elif retained_handlers:
                updated_group = dict(group)
                updated_group["hooks"] = retained_handlers
                retained_groups.append(updated_group)
        generated_group = {
            "hooks": [
                {
                    "type": "command",
                    "command": _native_hook_command(
                        root, home=home, module=module, phase=phase
                    ),
                    "timeout": 15,
                    "statusMessage": "LLM-WorkMem lifecycle bridge",
                }
            ],
        }
        if matcher is not None:
            generated_group["matcher"] = matcher
        retained_groups.append(generated_group)
        hooks[event] = retained_groups

    payload["hooks"] = hooks
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_codex_hooks(path: Path, root: Path, *, home: Path) -> Path:
    """Merge stable Codex session and per-turn hooks without changing trust."""

    return _write_native_lifecycle_hooks(
        path,
        root,
        home=home,
        module="adapters.hooks.codex_native",
        events=(
            ("SessionStart", "SessionStart"),
            ("UserPromptSubmit", "UserPromptSubmit"),
            ("Stop", "Stop"),
            ("SessionEnd", "SessionEnd"),
        ),
    )


def _write_gemini_cli_hooks(path: Path, root: Path, *, home: Path) -> Path:
    """Merge Gemini CLI SessionStart/SessionEnd hooks."""

    return _write_native_lifecycle_hooks(
        path,
        root,
        home=home,
        module="adapters.hooks.gemini_cli_native",
        events=(("SessionStart", "SessionStart"), ("SessionEnd", "SessionEnd")),
        # Gemini lifecycle hooks use exact source/reason matchers. Omitting
        # the matcher is the documented way to receive every lifecycle event;
        # an empty string is not a reliable wildcard.
        matcher=None,
    )


def _write_antigravity_hooks(path: Path, root: Path, *, home: Path) -> Path:
    """Merge only the LLM-WorkMem named hook into Antigravity's hooks.json."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"refusing to overwrite invalid Antigravity hooks file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"refusing to overwrite non-object Antigravity hooks file: {path}")
    else:
        payload = {}

    existing = payload.get("llm-workmem")
    if existing is None:
        hook = {}
    elif isinstance(existing, dict):
        hook = dict(existing)
    else:
        raise ValueError("refusing to overwrite non-object Antigravity llm-workmem hook")

    for event, phase in (("PreInvocation", "pre-invocation"), ("Stop", "stop")):
        current = hook.get(event, [])
        if not isinstance(current, list):
            raise ValueError(f"refusing to overwrite invalid Antigravity {event} handlers")
        retained = [item for item in current if not _is_antigravity_generated_handler(item)]
        retained.append(
            {
                "type": "command",
                "command": _antigravity_hook_command(root, home=home, phase=phase),
                "timeout": 15,
            }
        )
        hook[event] = retained

    payload["llm-workmem"] = hook
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _minimax_agent_paths(home: Path) -> tuple[Path, ...]:
    return tuple(
        home / ".minimax" / "agents" / name / "agent.md"
        for name in ("coder", "general", "mavis", "verifier")
    )


def write_global_adapters(root: Path) -> AdapterReport:
    root = canonical_data_root(root)
    target = root / "adapters"
    blocks = {
        "codex": _context_block(root, tool="codex"),
        "claude-code": _context_block(root, tool="claude-code"),
        "vscode": _context_block(root, tool="vscode"),
        "kiro": _context_block(root, tool="kiro"),
        "trae": _context_block(root, tool="trae"),
        "antigravity": _context_block(root, tool="antigravity"),
        "minimax": _context_block(root, tool="minimax"),
        "opencode": _context_block(root, tool="opencode"),
    }
    cursor_block = _cursor_rules_block(root)
    gemini_block = _gemini_block(root)
    written = [
        _write(target / "AGENTS.md", blocks["codex"]),
        _write(target / "CLAUDE.md", blocks["claude-code"]),
        _write(target / "copilot-instructions.md", blocks["vscode"]),
        _write(target / "kiro-steering-llm-workmem.md", blocks["kiro"]),
        _write(target / "traerules", blocks["trae"]),
        _write(target / "antigravity-agents.md", blocks["antigravity"]),
        _write(target / "antigravity-global.md", blocks["antigravity"]),
        _write(target / "minimax-agent.md", blocks["minimax"]),
        _write(target / "cursor-rules.mdc", cursor_block),
        _write(target / "gemini-context.md", gemini_block),
        _write(target / "llm-workmem-shell-context.sh", _shell_context(root)),
        _write(
            target / "adapter-manifest.json",
            json.dumps(
                {
                    "root": str(root),
                    "compact_context": str(root / "llms.txt"),
                    "full_context": str(root / "llms-full.txt"),
                    "manifest": str(root / "llms.json"),
                    "adapters": {
                        "codex": "AGENTS.md",
                        "claude-code": "CLAUDE.md",
                        "github-copilot": "copilot-instructions.md",
                        "vscode": "~/Library/Application Support/Code/User/prompts/llm-workmem.instructions.md",
                        "kiro": "kiro-steering-llm-workmem.md",
                        "trae": "traerules",
                        "antigravity": "antigravity-agents.md",
                        "antigravity-global": "antigravity-global.md",
                        "minimax": "minimax-agent.md",
                        "cursor": "cursor-rules.mdc",
                        "gemini-cli": "gemini-context.md",
                        "opencode": "~/.config/opencode/AGENTS.md",
                        "shell": "llm-workmem-shell-context.sh",
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
        ),
    ]
    return AdapterReport(root=root, target=target, written=tuple(written))


def attach_project(root: Path, project: Path) -> AttachReport:
    root = canonical_data_root(root)
    project = project.resolve()
    blocks = {
        "codex": _context_block(root, tool="codex", project=project),
        "claude-code": _context_block(root, tool="claude-code", project=project),
        "vscode": _context_block(root, tool="vscode", project=project),
        "kiro": _context_block(root, tool="kiro", project=project),
        "trae": _context_block(root, tool="trae", project=project),
        "antigravity": _context_block(root, tool="antigravity", project=project),
    }
    cursor_block = _cursor_rules_block(root, project=project)
    gemini_block = _gemini_block(root, project=project)
    written = [
        _merge_marked_block(project / ".agents" / "AGENTS.md", blocks["antigravity"]),
        _merge_marked_block(project / ".agents" / "GLOBAL.md", blocks["antigravity"]),
        _merge_marked_block(project / "AGENTS.md", blocks["codex"]),
        _merge_marked_block(project / "CLAUDE.md", blocks["claude-code"]),
        _merge_marked_block(project / ".github" / "copilot-instructions.md", blocks["vscode"]),
        _merge_marked_block(project / ".kiro" / "steering" / "llm-workmem.md", blocks["kiro"]),
        _merge_marked_block(project / ".traerules", blocks["trae"]),
        _write(project / ".cursor" / "rules" / "llm-workmem.mdc", cursor_block),
        _write_cursor_rule(project / ".cursorrules", cursor_block),
        _write_gemini_append(project / "GEMINI.md", gemini_block),
        _write(project / ".llm-workmem" / "shell-context.sh", _shell_context(root)),
        _write(
            project / ".llm-workmem" / "context.json",
            json.dumps(
                {
                    "wiki_root": str(root),
                    "llms_txt": str(root / "llms.txt"),
                    "llms_full_txt": str(root / "llms-full.txt"),
                    "llms_json": str(root / "llms.json"),
                    "project": str(project),
                },
                ensure_ascii=False,
                indent=2,
            ),
        ),
    ]
    return AttachReport(root=root, project=project, written=tuple(written))



def install_global_adapters(root: Path, *, home: Path | None = None) -> AttachReport:
    root = canonical_data_root(root)
    home = (home or Path.home()).expanduser().resolve()
    # Keep MiniMax's generated shell wrapper and MCP identity in the same
    # installer path used by the dedicated host installer.
    from lwm.hooks_gen import install_gemini_cli, install_minimax

    minimax_install = install_minimax(home, root=root)
    gemini_install = install_gemini_cli(home, root=root)
    blocks = {
        "codex": _context_block(root, tool="codex"),
        "claude-code": _context_block(root, tool="claude-code"),
        "kiro": _context_block(root, tool="kiro"),
        "trae": _context_block(root, tool="trae"),
        "antigravity": _context_block(root, tool="antigravity"),
        "minimax": _context_block(root, tool="minimax"),
        "opencode": _context_block(root, tool="opencode"),
    }
    cursor_block = _cursor_rules_block(root)
    gemini_block = _gemini_block(root)
    vscode_block = _vscode_instruction_block(root)
    shell_source = f"""{SHELL_MARKER_START}
# LLM-WorkMem shell context
if [ -f {str(root / 'adapters' / 'llm-workmem-shell-context.sh')!r} ]; then
  source {str(root / 'adapters' / 'llm-workmem-shell-context.sh')!r}
fi
if [ -f {str(home / '.minimax' / 'lwm-shell.sh')!r} ]; then
  source {str(home / '.minimax' / 'lwm-shell.sh')!r}
fi
{SHELL_MARKER_END}
"""
    written = [
        *(_merge_marked_block(path, blocks["antigravity"]) for path in _antigravity_global_paths(home)),
        _write_antigravity_hooks(_antigravity_hooks_path(home), root, home=home),
        _write_codex_hooks(_codex_hooks_path(home), root, home=home),
        _write_cursor_hooks(_cursor_hooks_path(home), root, home=home),
        gemini_install.config_path,
        *(_merge_marked_block(path, blocks["minimax"]) for path in _minimax_agent_paths(home)),
        minimax_install.config_path,
        home / ".minimax" / "mcp" / "mcp.json",
        _merge_marked_block(home / ".codex" / "AGENTS.md", blocks["codex"]),
        # Claude Code's documented user-scope memory is ~/.claude/CLAUDE.md.
        # Keep ~/CLAUDE.md as a compatibility entrypoint for older setups.
        _merge_marked_block(home / ".claude" / "CLAUDE.md", blocks["claude-code"]),
        _merge_marked_block(home / "CLAUDE.md", blocks["claude-code"]),
        _merge_marked_block(home / ".traerules", blocks["trae"]),
        _normalize_legacy_context_reference(
            _merge_marked_block(
                home / ".kiro" / "steering" / "llm-workmem.md", blocks["kiro"]
            ),
            root,
            tool="kiro",
        ),
        _merge_marked_block(home / ".zshrc", shell_source),
        _write(home / ".local" / "bin" / "lwm", _global_lwm_launcher(root, home=home)),
        *(_write_cursor_rule(path, cursor_block) for path in _cursor_global_paths(home)),
        *(_write_gemini_append(path, gemini_block) for path in _gemini_global_paths(home)),
        _write(_vscode_global_path(home), vscode_block),
        _merge_marked_block(_opencode_global_path(home), blocks["opencode"]),
        _write(home / ".config" / "lwm" / "context.json", json.dumps(
            {
                "wiki_root": str(root),
                "llms_txt": str(root / "llms.txt"),
                "llms_full_txt": str(root / "llms-full.txt"),
                "llms_json": str(root / "llms.json"),
                "adapters": str(root / "adapters"),
            },
            ensure_ascii=False,
            indent=2,
        )),
    ]
    return AttachReport(root=root, project=home, written=tuple(written))


def render_adapter_report(report: AdapterReport) -> str:
    lines = [
        f"# Adapter Report — {report.root.name}",
        "",
        f"- Adapter directory: {report.target}",
        f"- Files written: {len(report.written)}",
        "",
        "## Written Files",
    ]
    lines.extend(f"- `{path}`" for path in report.written)
    return "\n".join(lines)


def render_attach_report(report: AttachReport) -> str:
    lines = [
        f"# Attach Report — {report.project.name}",
        "",
        f"- Wiki root: {report.root}",
        f"- Project: {report.project}",
        f"- Files written: {len(report.written)}",
        "",
        "## Written Files",
    ]
    lines.extend(f"- `{path}`" for path in report.written)
    return "\n".join(lines)
