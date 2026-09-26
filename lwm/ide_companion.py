"""Package and install the VS Code-compatible LLM-WorkMem companion."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator, Mapping
from zipfile import ZIP_DEFLATED, ZipFile


SUPPORTED_TOOLS = ("vscode", "cursor", "trae", "kiro")
_INTEGRATIONS = {
    "vscode": "vscode-extension",
    "cursor": "cursor-extension",
    "trae": "trae-extension",
    "kiro": "kiro-extension",
}
_HOST_COMMANDS = {
    "vscode": (
        "code",
        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
    ),
    "cursor": (
        "cursor",
        "/Applications/Cursor.app/Contents/Resources/app/bin/cursor",
    ),
    "trae": (
        "trae",
        "/Applications/Trae.app/Contents/Resources/app/bin/trae",
        "/usr/local/bin/trae",
    ),
    "kiro": (
        "kiro",
        "/Applications/Kiro.app/Contents/Resources/app/bin/code",
    ),
}


@dataclass(frozen=True)
class CompanionInstall:
    tool: str
    host_command: tuple[str, ...]
    vsix_path: Path | None
    installed: bool
    detail: str = ""


@contextmanager
def _source_path() -> Iterator[Path]:
    checkout = Path(__file__).resolve().parents[1] / "integrations" / "ide-companion"
    if checkout.is_dir():
        yield checkout
        return
    resource = files("lwm.resources").joinpath("ide-companion")
    with as_file(resource) as path:
        yield path


def _package_json(source: Path, *, tool: str) -> dict[str, object]:
    payload = json.loads((source / "package.json").read_text(encoding="utf-8"))
    properties = payload["contributes"]["configuration"]["properties"]
    properties["llmWorkmem.toolId"]["default"] = tool
    properties["llmWorkmem.integration"]["default"] = _INTEGRATIONS[tool]
    return payload


def package_companion(output: Path, *, tool: str = "vscode") -> Path:
    """Create a local VSIX containing the companion and host identity defaults."""

    if tool not in SUPPORTED_TOOLS:
        raise ValueError(f"unsupported companion tool: {tool}")
    with _source_path() as source:
        if not (source / "package.json").is_file() or not (source / "extension.js").is_file():
            raise FileNotFoundError("LLM-WorkMem companion resource is incomplete")

        package = _package_json(source, tool=tool)
        manifest = f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<PackageManifest Version=\"2.0.0\" xmlns=\"http://schemas.microsoft.com/developer/vsx-schema/2011\">
  <Metadata>
    <Identity Id=\"ethan-lau.llm-workmem-companion\" Version=\"{package['version']}\" Language=\"en\" Publisher=\"{package['publisher']}\" />
    <DisplayName>LLM-WorkMem Companion</DisplayName>
    <Description>Bounded LLM-WorkMem context and lifecycle bridge.</Description>
    <Tags>memory,workflow,context</Tags>
  </Metadata>
  <Installation>
    <InstallationTarget Id=\"Microsoft.VisualStudio.Code\" Version=\"[1.85.0,)\" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type=\"Microsoft.VisualStudio.Code.Manifest\" Path=\"extension/package.json\" />
    <Asset Type=\"Microsoft.VisualStudio.Services.Content.Details\" Path=\"extension/README.md\" />
  </Assets>
</PackageManifest>
"""
        readme = (
            "# LLM-WorkMem Companion\n\n"
            "This extension sends bounded session lifecycle requests to the local "
            "LLM-WorkMem bridge. It does not collect host conversation text.\n"
        )
        output = output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("extension.vsixmanifest", manifest)
            archive.writestr(
                "extension/package.json",
                json.dumps(package, ensure_ascii=True, indent=2) + "\n",
            )
            archive.writestr("extension/extension.js", (source / "extension.js").read_bytes())
            archive.writestr("extension/README.md", readme)
    return output


def host_command(
    tool: str,
    *,
    path_lookup: Mapping[str, str] | None = None,
) -> tuple[str, ...] | None:
    """Resolve a host launcher without modifying the host or its settings."""

    if tool not in _HOST_COMMANDS:
        return None
    if path_lookup and path_lookup.get(tool):
        return (str(path_lookup[tool]),)
    for candidate in _HOST_COMMANDS[tool]:
        resolved = shutil.which(candidate) if "/" not in candidate else candidate
        if resolved and Path(resolved).is_file() and os.access(resolved, os.X_OK):
            return (resolved,)
    return None


def install_companion(
    tool: str,
    *,
    dry_run: bool = False,
    path_lookup: Mapping[str, str] | None = None,
) -> CompanionInstall:
    """Install a host-specific VSIX, or report the exact command in dry-run mode."""

    command = host_command(tool, path_lookup=path_lookup)
    if command is None:
        raise FileNotFoundError(f"no executable host launcher found for {tool}")
    if dry_run:
        return CompanionInstall(tool, command + ("--install-extension",), None, False, "dry-run")

    with tempfile.TemporaryDirectory(prefix="lwm-ide-companion-") as directory:
        vsix = package_companion(Path(directory) / f"llm-workmem-{tool}.vsix", tool=tool)
        result = subprocess.run(
            [*command, "--install-extension", str(vsix)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "host installation failed").strip()
            raise RuntimeError(detail)
        return CompanionInstall(tool, command, None, True, (result.stdout or "").strip())


__all__ = [
    "CompanionInstall",
    "SUPPORTED_TOOLS",
    "host_command",
    "install_companion",
    "package_companion",
]
