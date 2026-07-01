"""Typer CLI for lwiki."""

from __future__ import annotations

from pathlib import Path

import typer

from lwiki import __version__
from lwiki.harvest import (
    harvest_sources,
    load_schedule_bundle,
    render_source_groups,
    write_schedule_bundle,
)
from lwiki.compile import compile_raw_sources, render_compile_report
from lwiki.query import QueryReport, render_query_report, run_query, save_query_report
from lwiki.eval import render_eval_report, run_eval
from lwiki.audit import render_audit_report, run_audit
from lwiki.init_scaffold import DEFAULT_SOURCE_TYPES, init_wiki_tree
from lwiki.raw_tracker import run_raw_status, run_raw_sync
from lwiki.analysis import analyze_wiki, render_analysis_report, write_analysis_report
from lwiki.dashboard import serve_wiki, write_dashboard_html
from lwiki.export import render_export_report, write_ai_exports
from lwiki.review import build_review_report, render_review_report, write_review_page
from lwiki.schema import render_schema_report, validate_schema
from lwiki.profiles import DEFAULT_PROFILE, profile_choices
from lwiki.watch import render_watch_report, run_watch
from lwiki.structure import render_structure_text
from lwiki import cbmem as lwiki_cbmem
from lwiki.adapters import (
    attach_project,
    install_global_adapters,
    render_adapter_report,
    render_attach_report,
    write_global_adapters,
)

app = typer.Typer(
    name="lwiki",
    help="LLM Wiki: init wiki trees, inspect knowledge graphs, query the wiki, harvest tool memory, and track raw/ drift",
    no_args_is_help=True,
)
raw_app = typer.Typer(help="Compare or sync raw/ with files.log")
sources_app = typer.Typer(help="Inspect configured tool-memory sources")
cbmem_app = typer.Typer(help="Query the codebase-memory graph for any indexed project")
app.add_typer(raw_app, name="raw")
app.add_typer(sources_app, name="sources")
app.add_typer(cbmem_app, name="cbmem")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(0)


@app.callback()
def cli(
    version: bool | None = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True
    ),
) -> None:
    """lwiki — LLM Wiki CLI"""



@app.command("adapters")
def adapters_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to export adapters from",
        exists=False,
    ),
) -> None:
    """Write reusable Codex/Claude/Copilot/Kiro/Trae/Antigravity/MiniMax/shell adapter files."""
    root = root.resolve()
    report = write_global_adapters(root)
    typer.echo(render_adapter_report(report).rstrip())
    raise typer.Exit(0)



@app.command("install-global")
def install_global_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to install global adapters from",
        exists=False,
    ),
) -> None:
    """Install global Codex/Claude/Trae/Kiro/Antigravity/MiniMax/shell entrypoints for this user."""
    root = root.resolve()
    write_global_adapters(root)
    report = install_global_adapters(root)
    typer.echo(render_attach_report(report).rstrip())
    raise typer.Exit(0)


@app.command("attach")
def attach_cmd(
    project: Path = typer.Argument(
        ...,
        help="Project directory that should read this llm-wiki",
        exists=False,
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Wiki root directory to attach from",
        exists=False,
    ),
) -> None:
    """Install per-tool context entrypoints into a project directory."""
    root = root.resolve()
    project = project.resolve()
    report = attach_project(root, project)
    typer.echo(render_attach_report(report).rstrip())
    raise typer.Exit(0)


@sources_app.command("list")
def sources_list_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory with optional lwiki-sources.json",
        exists=False,
    ),
) -> None:
    """List default and configured tool-memory sources."""
    root = root.resolve()
    typer.echo(render_source_groups(root).rstrip())
    raise typer.Exit(0)


@cbmem_app.command("doctor")
def cbmem_doctor_cmd() -> None:
    """Check that `codebase-memory` is installed and healthy."""
    try:
        result = lwiki_cbmem.doctor()
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        typer.secho(
            "\nInstall hint:\n"
            "  curl -sSL -o /tmp/cbmem.tar.gz \\\n"
            "    https://github.com/DeusData/codebase-memory-mcp/releases/download/v0.8.1/codebase-memory-mcp-darwin-arm64.tar.gz\n"
            "  tar -xzf /tmp/cbmem.tar.gz -C ~/bin/\n"
            "  rm /tmp/cbmem.tar.gz && chmod +x ~/bin/codebase-memory-mcp\n"
            "  ln -sf ~/bin/codebase-memory-mcp ~/bin/cbmem\n"
            "Then retry: lwiki cbmem doctor",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_doctor_report(result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("index")
def cbmem_index_cmd(
    project: Path = typer.Argument(
        ...,
        help="Project directory to index into the code graph",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Discard existing graph and re-index from scratch",
    ),
    timeout: float = typer.Option(
        600.0,
        "--timeout",
        help="Max seconds to wait for the indexer",
    ),
) -> None:
    """Build or refresh the code graph for a project directory."""
    try:
        result = lwiki_cbmem.index_project(project, force=force, timeout=timeout)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_index_report(project.resolve(), result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("index-status")
def cbmem_index_status_cmd(
    project: Path = typer.Argument(
        ...,
        help="Project directory whose graph status to report",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Print the current indexing status of a project directory."""
    try:
        result = lwiki_cbmem.index_status(project)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(result.stdout.rstrip() or "(no output)")
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("search")
def cbmem_search_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory to search",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    symbol: str = typer.Argument(
        ...,
        help="Symbol name (function, class, route, etc.) to look up",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        min=1,
        max=200,
    ),
) -> None:
    """Search the code graph by symbol name."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.search(project, symbol, limit=limit)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_search_report(symbol, result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("architecture")
def cbmem_architecture_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """One-call architecture summary: languages, packages, routes, hotspots."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.architecture(project)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_architecture_report(result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("trace")
def cbmem_trace_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    symbol: str = typer.Argument(
        ...,
        help="Symbol to start tracing from",
    ),
    depth: int = typer.Option(
        3,
        "--depth",
        min=1,
        max=10,
    ),
) -> None:
    """Follow call-graph edges out from a symbol."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.trace_path(project, symbol, depth=depth)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_trace_report(symbol, result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("changes")
def cbmem_changes_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed git project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    base: str = typer.Option(
        "HEAD",
        "--base",
        help="Git ref to diff against (e.g. HEAD~1, main, v1.0.0)",
    ),
) -> None:
    """Map a git diff to affected symbols with risk classification."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.detect_changes(project, base=base)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_changes_report(result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("dead")
def cbmem_dead_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """List symbols with no incoming callers (dead code candidates)."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.dead_code(project)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_dead_code_report(result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("query")
def cbmem_query_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    cypher: str = typer.Argument(
        ...,
        help="Cypher-like query string",
    ),
) -> None:
    """Run a Cypher-like graph query."""
    if not cypher or not cypher.strip():
        typer.secho(
            "Cypher / search string must be non-empty.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        # The binary exposes `search_graph` for ad-hoc graph queries. Map the
        # Cypher-style string to a `search` call so the user keeps the
        # familiar `lwiki cbmem query` UX.
        result = lwiki_cbmem.search(project, cypher)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    typer.echo(lwiki_cbmem.render_query_report(result))
    raise typer.Exit(0 if result.ok else 1)


@cbmem_app.command("semantic")
def cbmem_semantic_cmd(
    project: Path = typer.Argument(
        ...,
        help="Indexed project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    query: str = typer.Argument(
        ...,
        help="Natural-language query for vector search",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        min=1,
        max=100,
    ),
) -> None:
    """Vector search over indexed symbols (bundled Nomic embeddings)."""
    if not lwiki_cbmem.is_indexed(project):
        typer.secho(
            f"{project} has no .codebase-memory/graph.db.zst — run `lwiki cbmem index {project}` first",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(2)
    try:
        result = lwiki_cbmem.semantic_search(project, query, limit=limit)
    except lwiki_cbmem.CbmemNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.echo(lwiki_cbmem.render_query_report(result))
    raise typer.Exit(0 if result.ok else 1)


@app.command("structure")
def structure_cmd(
    profile: str = typer.Option(
        DEFAULT_PROFILE,
        "--profile",
        "-p",
        case_sensitive=False,
        help=f"Wiki profile to describe: {', '.join(profile_choices())}",
    ),
) -> None:
    """Print the canonical wiki directory layout (what `lwiki init` creates)."""
    typer.echo(render_structure_text(profile.lower()).rstrip())


@app.command("analyze")
def analyze_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to inspect",
        exists=False,
    ),
    write: bool = typer.Option(
        False,
        "--write",
        help="Write the analysis report to wiki/insights/",
    ),
) -> None:
    """Inspect a wiki for hubs, orphans, broken links, and source drift."""
    root = root.resolve()
    analysis = analyze_wiki(root)
    report = render_analysis_report(analysis)
    typer.echo(report.rstrip())
    if write:
        out_path = write_analysis_report(root, analysis)
        typer.secho(f"Wrote analysis report to {out_path}", fg=typer.colors.GREEN)
    raise typer.Exit(0 if not analysis.errors else 1)


@app.command("query")
def query_cmd(
    question: str = typer.Argument(
        ...,
        help="Wiki question to answer from local pages",
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Wiki root directory to inspect",
        exists=False,
    ),
    mode: str = typer.Option(
        "standard",
        "--mode",
        case_sensitive=False,
        help="Query depth: quick, standard, deep, thesis, list",
    ),
    limit: int = typer.Option(
        6,
        "--limit",
        min=1,
        max=20,
        help="Maximum matches to return",
    ),
    save_as: str | None = typer.Option(
        None,
        "--save-as",
        help="Save the synthesized answer as wiki/insights/<slug>.md",
    ),
) -> None:
    """Query the wiki and optionally save the synthesis as an insight page."""
    root = root.resolve()
    mode_value = mode.lower()
    if mode_value not in {"quick", "standard", "deep", "thesis", "list"}:
        typer.secho("Invalid --mode. Use quick, standard, deep, thesis, or list.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)
    report: QueryReport = run_query(root, question, mode=mode_value, limit=limit)
    typer.echo(render_query_report(report).rstrip())
    if save_as:
        out_path = save_query_report(root, report, slug=save_as)
        typer.secho(f"Wrote query synthesis to {out_path}", fg=typer.colors.GREEN)


@app.command("harvest")
def harvest_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to inspect and refresh",
        exists=False,
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Open the refreshed dashboard snapshot after harvest",
    ),
) -> None:
    """Harvest tool memory sources into raw/ and refresh wiki summaries."""
    root = root.resolve()
    outcome = harvest_sources(root)
    typer.secho(
        "Harvested "
        f"{len(outcome.captured)} snapshots, "
        f"{len(outcome.missing)} missing slots; "
        f"raw sync -> {outcome.sync_code}; "
        f"compiled pages -> {outcome.compiled_count}",
        fg=typer.colors.GREEN if outcome.sync_code == 0 else typer.colors.YELLOW,
    )
    typer.echo(f"Governance: {outcome.governance_page}")
    typer.echo(f"Snapshot: {outcome.snapshot_page}")
    typer.echo(f"Analysis: {outcome.analysis_report_path}")
    typer.echo(f"Dashboard: {outcome.dashboard_page}")
    if open_browser:
        import webbrowser

        webbrowser.open(outcome.dashboard_page.as_uri())
    raise typer.Exit(outcome.sync_code)


@app.command("watch")
def watch_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to monitor and refresh",
        exists=False,
    ),
    eval_suite: Path | None = typer.Option(
        None,
        "--eval-suite",
        help="Optional eval suite file (question | expected_slug)",
        exists=False,
    ),
    eval_mode: str = typer.Option(
        "standard",
        "--eval-mode",
        case_sensitive=False,
        help="Eval query mode: quick, standard, deep, thesis, list",
    ),
) -> None:
    """Detect source drift, refresh the wiki if inputs changed, and audit the result."""
    root = root.resolve()
    suite = eval_suite.resolve() if eval_suite else None
    mode_value = eval_mode.lower()
    if mode_value not in {"quick", "standard", "deep", "thesis", "list"}:
        typer.secho("Invalid --eval-mode. Use quick, standard, deep, thesis, or list.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)
    report = run_watch(root, eval_suite=suite, eval_mode=mode_value)
    typer.echo(render_watch_report(report).rstrip())
    raise typer.Exit(0 if report.audit.ok else 1)


@app.command("export")
def export_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to export",
        exists=False,
    ),
) -> None:
    """Write agent-consumable exports: llms.txt, llms-full.txt, and llms.json."""
    root = root.resolve()
    report = write_ai_exports(root)
    typer.echo(render_export_report(report).rstrip())
    raise typer.Exit(0)


@app.command("compile")
def compile_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to compile",
        exists=False,
    ),
) -> None:
    """Compile raw sources into deterministic summary pages."""
    root = root.resolve()
    report = compile_raw_sources(root)
    typer.echo(render_compile_report(report).rstrip())
    raise typer.Exit(0)


@app.command("schedule")
def schedule_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to prepare for automation",
        exists=False,
    ),
    label: str = typer.Option(
        "com.ethan.llmwiki.harvest",
        "--label",
        help="Launchd label for the generated schedule bundle",
    ),
    load: bool = typer.Option(
        False,
        "--load",
        help="Install and load the LaunchAgent immediately after writing it",
    ),
) -> None:
    """Write a launchd bundle that runs watch+audit at load and every 12 hours."""
    root = root.resolve()
    bundle = write_schedule_bundle(root, label=label)
    typer.secho(f"Wrote schedule script to {bundle.script_path}", fg=typer.colors.GREEN)
    typer.secho(f"Wrote schedule runner to {bundle.runner_path}", fg=typer.colors.GREEN)
    typer.secho(f"Wrote launch runner to {bundle.launch_runner_path}", fg=typer.colors.GREEN)
    typer.secho(f"Wrote launchd plist to {bundle.plist_path}", fg=typer.colors.GREEN)
    typer.secho(
        f"Wrote LaunchAgents plist to {bundle.launch_agents_plist_path}",
        fg=typer.colors.GREEN,
    )
    typer.secho(f"Runtime workspace is {bundle.runtime_root}", fg=typer.colors.GREEN)
    if load:
        load_schedule_bundle(bundle)
        typer.secho(f"Loaded launchd job {bundle.label}", fg=typer.colors.GREEN)


@app.command("schema")
def schema_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to validate",
        exists=False,
    ),
) -> None:
    """Validate controlled schema keys and allowed page types."""
    root = root.resolve()
    report = validate_schema(root)
    typer.echo(render_schema_report(report).rstrip())
    raise typer.Exit(0 if report.ok else 1)


@app.command("review")
def review_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to review",
        exists=False,
    ),
    write: bool = typer.Option(
        False,
        "--write",
        help="Write review queue page into wiki/review/",
    ),
) -> None:
    """Build a deterministic review queue from analysis + schema issues."""
    root = root.resolve()
    report = build_review_report(root)
    typer.echo(render_review_report(report).rstrip())
    if write:
        out_path = write_review_page(root, report)
        typer.secho(f"Wrote review queue page to {out_path}", fg=typer.colors.GREEN)
    raise typer.Exit(0 if not report.items else 1)


@app.command("eval")
def eval_cmd(
    suite: Path = typer.Argument(
        ...,
        help="Path to eval suite file: one case per line -> question | expected_slug",
        exists=False,
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Wiki root directory",
        exists=False,
    ),
    mode: str = typer.Option(
        "standard",
        "--mode",
        case_sensitive=False,
        help="Query depth: quick, standard, deep, thesis, list",
    ),
    limit: int = typer.Option(
        3,
        "--limit",
        min=1,
        max=20,
        help="Max matches per eval case",
    ),
) -> None:
    """Run a reproducible query eval suite against current wiki."""
    root = root.resolve()
    suite = suite.resolve()
    mode_value = mode.lower()
    if mode_value not in {"quick", "standard", "deep", "thesis", "list"}:
        typer.secho("Invalid --mode. Use quick, standard, deep, thesis, or list.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)
    report = run_eval(root, suite, mode=mode_value, limit=limit)
    typer.echo(render_eval_report(report).rstrip())
    raise typer.Exit(0 if report.pass_count == report.total else 1)


@app.command("audit")
def audit_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to audit",
        exists=False,
    ),
    eval_suite: Path | None = typer.Option(
        None,
        "--eval-suite",
        help="Optional eval suite file (question | expected_slug)",
        exists=False,
    ),
    eval_mode: str = typer.Option(
        "standard",
        "--eval-mode",
        case_sensitive=False,
        help="Eval query mode: quick, standard, deep, thesis, list",
    ),
) -> None:
    """Run unified health audit: analyze + schema + review (+ optional eval)."""
    root = root.resolve()
    suite = eval_suite.resolve() if eval_suite else None
    mode_value = eval_mode.lower()
    if mode_value not in {"quick", "standard", "deep", "thesis", "list"}:
        typer.secho("Invalid --eval-mode. Use quick, standard, deep, thesis, or list.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)
    report = run_audit(root, eval_suite=suite, eval_mode=mode_value)
    typer.echo(render_audit_report(report).rstrip())
    raise typer.Exit(0 if report.ok else 1)


@app.command("dashboard")
def dashboard_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to inspect",
        exists=False,
    ),
    out: Path = typer.Option(
        Path("knowledge-digest.html"),
        "--out",
        help="Output HTML file for the desktop snapshot",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Open the generated snapshot in your default browser",
    ),
) -> None:
    """Write a desktop-style HTML dashboard snapshot."""
    root = root.resolve()
    out_path = out.resolve()
    written = write_dashboard_html(root, out_path)
    typer.secho(f"Wrote dashboard snapshot to {written}", fg=typer.colors.GREEN)
    if open_browser:
        import webbrowser

        webbrowser.open(written.as_uri())
    raise typer.Exit(0)


@app.command("serve")
def serve_cmd(
    root: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to serve",
        exists=False,
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host to bind",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        help="Port to bind",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Open the workspace in your default browser",
    ),
) -> None:
    """Run a local desktop-like workspace in the browser."""
    serve_wiki(root.resolve(), host=host, port=port, open_browser=open_browser)


@raw_app.command("status")
def raw_status(
    raw: Path = typer.Argument(
        Path("raw"),
        help="Path to raw/ directory (often relative to wiki root)",
        exists=False,
    ),
) -> None:
    """Report new/modified/deleted files vs files.log (no write). Exit 1 if drift."""
    raw = raw.resolve()
    code, msg = run_raw_status(raw)
    typer.echo(msg)
    raise typer.Exit(code)


@raw_app.command("sync")
def raw_sync(
    raw: Path = typer.Argument(
        Path("raw"),
        help="Path to raw/ directory",
        exists=False,
    ),
) -> None:
    """Rewrite files.log to match raw/."""
    raw = raw.resolve()
    code, msg = run_raw_sync(raw)
    typer.echo(msg)
    raise typer.Exit(code)


@app.command("checkout")
def checkout_alias(
    raw: Path = typer.Argument(
        Path("raw"),
        help="Path to raw/ directory",
        exists=False,
    ),
) -> None:
    """Alias for `lwiki raw sync` (updates files.log)."""
    raw = raw.resolve()
    code, msg = run_raw_sync(raw)
    typer.echo(msg)
    raise typer.Exit(code)


@app.command("init")
def init_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Wiki root directory to create",
        exists=False,
    ),
    domain: str = typer.Option(
        "My Wiki",
        "--domain",
        "-d",
        help="One-line domain / purpose for AGENTS.md and overview",
    ),
    source_types: str = typer.Option(
        DEFAULT_SOURCE_TYPES,
        "--sources",
        "-s",
        help=f'Source types line for AGENTS.md (optional; default: "{DEFAULT_SOURCE_TYPES}")',
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite if wiki markers already exist (dangerous)",
    ),
    profile: str = typer.Option(
        DEFAULT_PROFILE,
        "--profile",
        "-p",
        case_sensitive=False,
        help=f"Wiki profile to scaffold: {', '.join(profile_choices())}",
    ),
) -> None:
    """Create a new wiki directory structure (INIT)."""
    root = path.resolve()
    try:
        init_wiki_tree(
            root,
            domain=domain,
            source_types=source_types,
            force=force,
            profile=profile.lower(),
        )
    except ValueError as e:
        typer.secho(str(e), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from e
    except FileExistsError as e:
        typer.secho(str(e), err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from e

    raw_dir = root / "raw"
    code, msg = run_raw_sync(raw_dir)
    typer.secho(f"Initialized wiki at {root}", fg=typer.colors.GREEN)
    typer.echo(msg)
    raise typer.Exit(code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
