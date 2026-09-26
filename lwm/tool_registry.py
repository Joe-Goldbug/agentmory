"""Versioned Tool Registry.

Spec: docs/superpowers/specs/
      2026-07-31-llm-workmem-unified-behavior-memory-interface.md
      -> Architecture And Interfaces / 2. Tool Registry

Replaces the hard-coded ``ADAPTER_MODULES`` tuple in :mod:`lwm.runner` and the
implicit list in :mod:`lwm.capabilities`. Every supported tool, CLI or shell
hook is one ``ToolDefinition`` row; the registry exposes discovery, project
recognition and the per-tool coverage that callers (runner, context, handoff,
MCP) consume.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping


REGISTRY_VERSION = 5
REGISTRY_PATH_DEFAULT = Path("state/tool-registry.json")

Surface = Literal["ide", "cli", "shell"]
CaptureMode = Literal[
    "native_hook", "session_adapter", "file_tail", "shell_lifecycle"
]
DeliveryMode = Literal[
    "native_hook", "instruction_pointer", "mcp", "shell_context"
]


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    display_name: str
    aliases: tuple[str, ...] = ()
    surfaces: tuple[Surface, ...] = ()
    discovery_paths: tuple[str, ...] = ()
    # Host launchers are separate from discovery paths: a config file proves
    # setup, while a launcher/app probe only proves local host availability.
    host_commands: tuple[str, ...] = ()
    host_app_paths: tuple[str, ...] = ()
    capture_mode: CaptureMode = "session_adapter"
    delivery_mode: DeliveryMode = "instruction_pointer"
    # Host integrations that are allowed to claim a proof receipt through the
    # lifecycle/session bridge. An empty tuple means observation only.
    proof_integrations: tuple[str, ...] = ()
    # ``collector_modules`` is the executable polling surface.  A tool may
    # intentionally have no collector when it is captured by a native hook
    # or by the shell lifecycle sweep.
    collector_modules: tuple[str, ...] = ()
    # Kept for saved registry files and callers written against registry v1.
    # New code must use ``collector_modules``.
    # Read-only/session observers run in the bounded cycle for hosts that also
    # have a native hook. They never claim a proof receipt.
    observer_modules: tuple[str, ...] = ()
    adapter_module: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.collector_modules and self.adapter_module:
            object.__setattr__(self, "collector_modules", (self.adapter_module,))
        if self.collector_modules and not self.adapter_module:
            object.__setattr__(self, "adapter_module", self.collector_modules[0])


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).strip().lower()).strip("-")


@dataclass(frozen=True)
class ToolCoverage:
    tool_id: str
    status: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "pending_integration",
    ]
    capture_status: str
    delivery_status: str
    read_status: str
    write_status: str
    last_capture_at: str | None = None
    capture_freshness: str = "missing"
    last_read_at: str | None = None
    last_write_at: str | None = None
    gaps: tuple[str, ...] = ()
    # Human-readable explanation derived from evidence, not configuration.
    status_reason: str = ""


def _defaults() -> tuple[ToolDefinition, ...]:
    return (
        ToolDefinition(
            tool_id="codex",
            display_name="Codex CLI",
            aliases=("codex-cli", "openai-codex"),
            surfaces=("cli", "shell"),
            discovery_paths=(".codex/AGENTS.md", ".codex/sessions"),
            host_commands=("codex",),
            capture_mode="native_hook",
            delivery_mode="native_hook",
            proof_integrations=("codex-hook",),
            collector_modules=(),
        ),
        ToolDefinition(
            tool_id="claude-code",
            display_name="Claude Code",
            aliases=("claude", "claude_code", "claude-code-cli", "cc"),
            surfaces=("cli", "ide"),
            discovery_paths=(
                ".claude/CLAUDE.md",
                ".claude/settings.json",
                "Library/Application Support/Claude Code/hooks",
            ),
            host_commands=("claude",),
            capture_mode="native_hook",
            delivery_mode="native_hook",
            proof_integrations=("claude-code-hook",),
            collector_modules=(),
        ),
        ToolDefinition(
            tool_id="opencode",
            display_name="OpenCode",
            aliases=("oc",),
            surfaces=("cli", "ide"),
            discovery_paths=(
                ".config/opencode/AGENTS.md",
                ".config/opencode/opencode.json",
            ),
            host_commands=("opencode",),
            capture_mode="shell_lifecycle",
            delivery_mode="instruction_pointer",
            proof_integrations=("opencode-plugin",),
            collector_modules=(),
        ),
        ToolDefinition(
            tool_id="shell",
            display_name="Generic shell CLI",
            aliases=("zsh", "bash"),
            surfaces=("shell",),
            discovery_paths=(".zshrc",),
            capture_mode="shell_lifecycle",
            delivery_mode="shell_context",
            proof_integrations=("shell-hook",),
            collector_modules=(),
        ),
        ToolDefinition(
            tool_id="vscode",
            display_name="VS Code / Copilot",
            aliases=("copilot", "vscode-copilot"),
            surfaces=("ide",),
            discovery_paths=(
                "Library/Application Support/Code/User/prompts",
                ".vscode/settings.json",
            ),
            host_commands=("code",),
            host_app_paths=("/Applications/Visual Studio Code.app",),
            capture_mode="session_adapter",
            delivery_mode="instruction_pointer",
            proof_integrations=("vscode-extension",),
            collector_modules=(
                "adapters.hooks.vscode_sessions",
                "adapters.hooks.vscode_tasks",
            ),
        ),
        ToolDefinition(
            tool_id="cursor",
            display_name="Cursor",
            aliases=("cursor-ide",),
            surfaces=("ide",),
            discovery_paths=(
                ".cursor/rules/llm-workmem.mdc",
                ".cursorrules",
                ".cursor/hooks.json",
                "Library/Application Support/Cursor/User/workspaceStorage",
            ),
            host_commands=("cursor",),
            host_app_paths=("/Applications/Cursor.app",),
            capture_mode="session_adapter",
            delivery_mode="instruction_pointer",
            proof_integrations=("cursor-extension", "cursor-hook"),
            collector_modules=("adapters.hooks.cursor_tasks",),
        ),
        ToolDefinition(
            tool_id="kiro",
            display_name="Kiro",
            aliases=(),
            surfaces=("ide",),
            discovery_paths=(".kiro/steering/llm-workmem.md",),
            host_commands=("kiro",),
            host_app_paths=("/Applications/Kiro.app",),
            capture_mode="session_adapter",
            delivery_mode="instruction_pointer",
            proof_integrations=("kiro-extension",),
            collector_modules=(
                "adapters.hooks.kiro_sessions",
                "adapters.hooks.kiro_steering_watch",
            ),
        ),
        ToolDefinition(
            tool_id="antigravity",
            display_name="Antigravity",
            aliases=("agy", "antigravity-agent"),
            surfaces=("cli", "ide"),
            discovery_paths=(".agents/AGENTS.md", ".agents/GLOBAL.md"),
            host_commands=("agy",),
            host_app_paths=("/Applications/Antigravity.app",),
            capture_mode="native_hook",
            delivery_mode="native_hook",
            proof_integrations=("antigravity-hook",),
            collector_modules=(),
            observer_modules=("adapters.hooks.antigravity_sessions",),
        ),
        ToolDefinition(
            tool_id="trae",
            display_name="Trae",
            aliases=("trae-solo",),
            surfaces=("ide",),
            discovery_paths=(".traerules",),
            host_commands=("trae",),
            host_app_paths=("/Applications/Trae.app",),
            capture_mode="session_adapter",
            delivery_mode="instruction_pointer",
            proof_integrations=("trae-extension",),
            collector_modules=("adapters.hooks.trae_sessions",),
        ),
        ToolDefinition(
            tool_id="minimax",
            display_name="MiniMax M3",
            aliases=("m3", "MiniMax-M3"),
            surfaces=("cli", "shell"),
            discovery_paths=(
                ".minimax/agents",
                ".minimax/config.yaml",
                ".minimax/v2/sqlite/runtime-state.sqlite",
                "Library/Application Support/MiniMax/agents",
                ".MiniMax/agent.md",
            ),
            host_commands=("minimax",),
            host_app_paths=(
                "/Applications/MiniMax Agent.app",
                "/Applications/MiniMax Code.app",
            ),
            capture_mode="session_adapter",
            delivery_mode="mcp",
            proof_integrations=("minimax-mcp",),
            collector_modules=("adapters.hooks.minimax_sessions",),
        ),
        ToolDefinition(
            tool_id="gemini-cli",
            display_name="Gemini CLI",
            aliases=("gemini",),
            surfaces=("cli",),
            discovery_paths=(
                ".gemini/GEMINI.md",
                ".gemini/settings.json",
                "GEMINI.md",
            ),
            host_commands=("gemini",),
            host_app_paths=("/Applications/Gemini.app",),
            capture_mode="native_hook",
            delivery_mode="native_hook",
            proof_integrations=("gemini-cli-hook", "gemini-cli-mcp"),
            collector_modules=(),
        ),
    )


class ToolRegistry:
    """Versioned, in-memory registry of tool definitions."""

    def __init__(self, definitions: Iterable[ToolDefinition] | None = None):
        self._definitions: dict[str, ToolDefinition] = {}
        self._alias_index: dict[str, str] = {}
        # Defaults provide the baseline; a persisted definition is an explicit
        # operator override and must win over the baseline row.
        for definition in list(_defaults()) + list(definitions or ()):
            self._add(definition)

    @property
    def version(self) -> int:
        return REGISTRY_VERSION

    def _add(self, definition: ToolDefinition) -> None:
        self._definitions[definition.tool_id] = definition
        # Rebuild the small alias index after an override. Otherwise a
        # persisted definition that intentionally changes aliases leaves the
        # old default aliases pointing at the overridden tool.
        self._alias_index = {}
        for current in self._definitions.values():
            self._alias_index[_norm(current.tool_id)] = current.tool_id
            for alias in current.aliases:
                self._alias_index[_norm(alias)] = current.tool_id

    def all(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._definitions.values())

    def enabled(self) -> tuple[ToolDefinition, ...]:
        return tuple(d for d in self._definitions.values() if d.enabled)

    def resolve(self, identifier: str) -> ToolDefinition | None:
        return self._definitions.get(self._alias_index.get(_norm(identifier), ""))

    def ids(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())

    def discover(self, home: Path | None = None) -> dict[str, bool]:
        home = (home or Path.home()).expanduser()
        out: dict[str, bool] = {}
        for definition in self.all():
            seen = False
            for relative in definition.discovery_paths:
                candidate = (home / relative).expanduser()
                if candidate.is_file() or (candidate.is_dir() and any(candidate.iterdir())):
                    seen = True
                    break
            out[definition.tool_id] = seen
        return out

    def host_probe(
        self,
        *,
        path_lookup: Mapping[str, str] | None = None,
    ) -> dict[str, dict[str, object]]:
        """Report local host availability without invoking any host or model.

        ``discovered`` remains the configuration probe. This separate result
        distinguishes an executable CLI, a GUI app without a CLI launcher,
        and a completely unavailable host.
        """

        path_lookup = path_lookup or {}
        result: dict[str, dict[str, object]] = {}
        for definition in self.all():
            checked_commands = list(definition.host_commands)
            checked_app_paths = list(definition.host_app_paths)
            if not checked_commands and not checked_app_paths:
                result[definition.tool_id] = {
                    "status": "not_applicable",
                    "locator": None,
                    "checked_commands": checked_commands,
                    "checked_app_paths": checked_app_paths,
                }
                continue

            locator: str | None = None
            override = path_lookup.get(definition.tool_id)
            if override:
                candidate = Path(override).expanduser()
                if candidate.is_file() and candidate.stat().st_mode & 0o111:
                    locator = str(candidate.resolve())
            else:
                for command in definition.host_commands:
                    found = shutil.which(command)
                    if found:
                        locator = str(Path(found).resolve())
                        break
            if locator:
                status = "available"
            else:
                for app_path in definition.host_app_paths:
                    candidate = Path(app_path).expanduser()
                    if candidate.is_dir():
                        locator = str(candidate.resolve())
                        break
                status = "app_present" if locator else "not_found"
            result[definition.tool_id] = {
                "status": status,
                "locator": locator,
                "checked_commands": checked_commands,
                "checked_app_paths": checked_app_paths,
            }
        return result

    def save(self, root: Path, *, path: Path | None = None) -> Path:
        target = path or (root / REGISTRY_PATH_DEFAULT)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "definitions": [asdict(d) for d in self.all()],
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return target

    @classmethod
    def load(cls, root: Path, *, path: Path | None = None) -> "ToolRegistry":
        target = path or (root / REGISTRY_PATH_DEFAULT)
        definitions: list[ToolDefinition] = []
        if target.is_file():
            try:
                payload = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = {}
            for row in payload.get("definitions", []) if isinstance(payload, dict) else []:
                if not isinstance(row, dict) or "tool_id" not in row:
                    continue
                definitions.append(_definition_from(row))
        return cls(definitions)

    def known_tool_ids(self) -> set[str]:
        return set(self._definitions.keys())


def _definition_from(row: dict[str, Any]) -> ToolDefinition:
    legacy_default = next(
        (definition for definition in _defaults() if definition.tool_id == str(row["tool_id"])),
        None,
    )
    proof_integrations = (
        tuple(row["proof_integrations"] or ())
        if "proof_integrations" in row
        else (legacy_default.proof_integrations if legacy_default else ())
    )
    observer_modules = (
        tuple(row["observer_modules"] or ())
        if "observer_modules" in row
        else (legacy_default.observer_modules if legacy_default else ())
    )
    return ToolDefinition(
        tool_id=str(row["tool_id"]),
        display_name=str(row.get("display_name") or row["tool_id"]),
        aliases=tuple(row.get("aliases", []) or ()),
        surfaces=tuple(row.get("surfaces", []) or ()),
        discovery_paths=tuple(row.get("discovery_paths", []) or ()),
        host_commands=tuple(
            row.get("host_commands", [])
            or (legacy_default.host_commands if legacy_default else ())
        ),
        host_app_paths=tuple(
            row.get("host_app_paths", [])
            or (legacy_default.host_app_paths if legacy_default else ())
        ),
        capture_mode=row.get("capture_mode", "session_adapter"),
        delivery_mode=row.get("delivery_mode", "instruction_pointer"),
        proof_integrations=proof_integrations,
        collector_modules=tuple(
            row.get("collector_modules")
            or ((row.get("adapter_module"),) if row.get("adapter_module") else ())
        ),
        observer_modules=observer_modules,
        adapter_module=row.get("adapter_module"),
        enabled=bool(row.get("enabled", True)),
    )


def default_registry() -> ToolRegistry:
    return ToolRegistry()


def all_known_tool_ids() -> frozenset[str]:
    return frozenset(d.tool_id for d in default_registry().all())


__all__ = [
    "CaptureMode",
    "DeliveryMode",
    "REGISTRY_PATH_DEFAULT",
    "REGISTRY_VERSION",
    "Surface",
    "ToolCoverage",
    "ToolDefinition",
    "ToolRegistry",
    "all_known_tool_ids",
    "default_registry",
]
