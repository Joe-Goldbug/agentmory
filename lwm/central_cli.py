"""New CLI subcommands for the central hub (Phases 1–4).

Adds:
    lwm record       — submit a work event
    lwm ingest       — process the in-box
    lwm context      — render the per-tool context
    lwm promote      — promote candidates or scan
    lwm insights     — list insight candidates
    lwm health       — health snapshot

These are exposed via :mod:`lwm.cli`. They live in a separate module so
the existing ``cli.py`` stays untouched and the surface area for the
central hub is reviewable on its own.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Optional

import typer

from lwm import context as lwm_context
from lwm import closure as lwm_closure
from lwm import forget as lwm_forget
from lwm import health as lwm_health
from lwm import hooks_gen as lwm_hooks_gen
from lwm import inbox as lwm_inbox
from lwm import insights as lwm_insights
from lwm import ingest as lwm_ingest
from lwm import promote as lwm_promote
from lwm import project_memory as lwm_project_memory
from lwm import shell_hook as lwm_shell_hook
from lwm import capabilities as lwm_capabilities
from lwm import memory_api as lwm_memory_api
from lwm.recall import render_recall_packet
from lwm import registry as lwm_registry
from lwm.events import validate_event
from lwm.project_id import record_project


hub_app = typer.Typer(
    name="hub",
    help="Central hub: events, ingest, context, promote, insights, health",
    no_args_is_help=True,
)


def _read_stdin() -> str:
    data = sys.stdin.read()
    return data if data is not None else ""


@hub_app.command("record")
def record_cmd(
    payload: Optional[str] = typer.Argument(
        None,
        help='JSON event payload (omit to read JSON from stdin). E.g. \'{"tool":"shell","task":"..."}\'',
    ),
    tool: str | None = typer.Option(None, "--tool", help="Tool name (default: shell if not in payload)."),
    project_path: str | None = typer.Option(None, "--project", "-p", help="Project path (default: cwd)."),
    project_id_value: str | None = typer.Option(
        None, "--project-id", help="Project id (skip auto-resolution)."
    ),
    task: str | None = typer.Option(None, "--task", help="Short task description."),
    event_type: str = typer.Option(
        "workflow_observation",
        "--type",
        help="Event type (default workflow_observation).",
    ),
    importance: str = typer.Option(
        "project", "--importance", help="scratch | project | cross_project | global"
    ),
    decision: list[str] = typer.Option(
        None, "--decision", help="Repeatable decision entry."
    ),
    change: list[str] = typer.Option(
        None, "--change", help="Repeatable change entry."
    ),
    verification: list[str] = typer.Option(
        None, "--verification", help="Repeatable verification entry."
    ),
    tag: list[str] = typer.Option(None, "--tag", help="Repeatable tag."),
    session_id: str | None = typer.Option(None, "--session-id", help="Session id."),
    confidence: float | None = typer.Option(None, "--confidence", help="Confidence 0..1"),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root.", exists=False),
) -> None:
    """Submit a work event into ``raw/events/inbox/``."""

    root = root.resolve()

    # Branch 1: explicit JSON payload positional argument wins.
    if payload is not None:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            typer.secho(f"invalid JSON: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
    # Branch 2: caller provided CLI flags directly (--tool, --project,
    # or --task). Build from those options without touching stdin.
    elif tool or project_path or task:
        parsed = {}
    # Branch 3: try stdin only when the caller actually piped JSON in.
    elif not sys.stdin.isatty():
        raw_stdin = _read_stdin()
        if raw_stdin.strip():
            try:
                parsed = json.loads(raw_stdin)
            except json.JSONDecodeError as exc:
                typer.secho(
                    f"invalid JSON from stdin: {exc}",
                    err=True,
                    fg=typer.colors.RED,
                )
                raise typer.Exit(2)
        else:
            typer.secho(
                "empty stdin; nothing recorded (pass --tool/--project or pipe JSON)",
                err=True,
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(2)
    # Branch 4: tty + no payload + no --tool/--project → user has to choose.
    else:
        typer.secho(
            "either --tool + --project, or a JSON payload/stdin is required",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)

    if not isinstance(parsed, dict):
        parsed = {}

    if tool:
        parsed["tool"] = tool
    if project_path:
        parsed["project_path"] = project_path
    if project_id_value:
        parsed["project_id"] = project_id_value
    if task:
        parsed["task"] = task
    if decision:
        parsed.setdefault("decisions", []).extend(decision)
    if change:
        parsed.setdefault("changes", []).extend(change)
    if verification:
        parsed.setdefault("verification", []).extend(verification)
    if tag:
        parsed.setdefault("tags", []).extend(tag)
    if session_id:
        parsed["session_id"] = session_id
    if confidence is not None:
        parsed["confidence"] = confidence

    parsed.setdefault("event_type", event_type)
    parsed.setdefault("importance", importance)
    parsed.setdefault("privacy", "sanitized")
    parsed.setdefault("event_id", str(uuid.uuid4()))
    parsed.setdefault(
        "timestamp",
        __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc).astimezone().isoformat(timespec="seconds"),
    )

    parsed.setdefault("tool", "shell")
    if not parsed.get("project_path"):
        parsed["project_path"] = os.getcwd()

    if not parsed.get("tool"):
        typer.secho("--tool is required", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    if not parsed.get("event_type"):
        parsed["event_type"] = "workflow_observation"

    if not parsed.get("project_id") and parsed.get("project_path"):
        resolution = record_project(root, parsed["project_path"])
        parsed["project_id"] = resolution.project_id

    validation = validate_event(parsed)
    if not validation.ok:
        typer.secho(
            "invalid event: " + "; ".join(i.render() for i in validation.issues),
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)

    target = lwm_inbox.submit_event(root, parsed)
    lwm_capabilities.record(
        root,
        tool=str(parsed["tool"]),
        direction="write",
        project_id=str(parsed.get("project_id") or "") or None,
        source="cli-record",
    )
    # ``raw/`` may be a symlink into the launchd runtime workspace. Resolve
    # both paths for storage, but do not assume the target remains below the
    # user-facing wiki root when rendering the report.
    try:
        display_target = target.relative_to(root)
    except ValueError:
        display_target = Path(os.path.relpath(target, root))
    typer.secho(f"recorded -> {display_target}", fg=typer.colors.GREEN)


@hub_app.command("ingest")
def ingest_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    no_lock: bool = typer.Option(False, "--no-lock", help="Skip lockfile acquisition."),
    no_promote: bool = typer.Option(False, "--no-promote", help="Skip auto-promotion."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
) -> None:
    """Process events from ``raw/events/inbox/`` into project memory."""

    report = lwm_ingest.run(
        root.resolve(),
        with_lock=not no_lock,
        auto_promote=not no_promote,
    )
    typer.echo(report.render())
    if report.processed:
        for event_id in report.processed:
            if verbose:
                typer.echo(f"processed: {event_id}")
    if report.rejected:
        for event_id, reason in report.rejected:
            typer.echo(f"rejected: {event_id} ({reason})")
    if report.failed:
        for event_id, reason in report.failed:
            typer.echo(f"failed:   {event_id} ({reason})")
    if report.failed:
        raise typer.Exit(3)
    if report.rejected:
        raise typer.Exit(2)
    raise typer.Exit(0)


@hub_app.command("context")
def context_cmd(
    tool: str = typer.Option(..., "--tool", help="Tool name (e.g. claude-code)."),
    project: Path | None = typer.Option(
        None, "--project", "-p", help="Project path for project memory lookup."
    ),
    format: str = typer.Option("markdown", "--format", help="markdown | json"),
    limit: int = typer.Option(6, "--limit", min=1, max=20),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Render the per-tool context (markdown or json)."""

    if format not in {"markdown", "json"}:
        typer.secho("--format must be markdown or json", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    report = lwm_context.build(
        root.resolve(),
        tool=tool,
        project_path=str(project.resolve()) if project else None,
        format=format,
        limit=limit,
    )
    receipt = lwm_capabilities.record(
        root.resolve(),
        tool=tool,
        direction="read",
        project_id=report.project_id,
        source="cli-context",
    )
    if receipt.get("status") != "verified":
        warnings = list(report.data.get("warnings") or [])
        warnings.append(f"Read receipt unavailable: {receipt.get('error', 'unknown error')}")
        data = {**report.data, "warnings": warnings}
        markdown = report.markdown.rstrip() + f"\n\nWarning: {warnings[-1]}\n"
        report = replace(report, markdown=markdown, data=data)
    typer.echo(report.markdown)


@hub_app.command("promote")
def promote_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    scan: bool = typer.Option(False, "--scan", help="Scan processed events first."),
    auto: bool = typer.Option(False, "--auto", help="Run promotion directly."),
) -> None:
    """Promote insight candidates to global memory.

    Without flags, ``--scan`` collects candidates from processed events,
    then ``--auto`` promotes eligible ones and writes the rest to
    ``wiki/review/candidate-*.md``.
    """

    root = root.resolve()
    if not scan and not auto:
        typer.secho("pass --scan and/or --auto", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(2)
    events = lwm_insights.load_processed_events(root)
    candidates = lwm_insights.collect_candidates(events)
    if not candidates:
        typer.echo("(no candidates)")
        raise typer.Exit(0)
    if scan:
        paths = lwm_insights.write_candidates(root, candidates)
        for path in paths:
            typer.echo(f"candidates -> {path.relative_to(root)}")
    if auto:
        decisions, leftovers = lwm_promote.auto_promote_all(root, candidates, events)
        for decision in decisions:
            if decision.approved and decision.target_path is not None:
                typer.echo(f"promoted: {decision.target_path.relative_to(root)}")
            else:
                typer.echo(
                    f"rejected: {decision.insight_title} ({'; '.join(decision.reasons)})"
                )
        if leftovers:
            lwm_insights.write_candidates(root, leftovers)


@hub_app.command("insights")
def insights_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    limit: int = typer.Option(8, "--limit", min=1, max=20),
) -> None:
    """List the latest insight-candidate pages under ``wiki/review/``."""

    review_dir = root.resolve() / "wiki" / "review"
    if not review_dir.is_dir():
        typer.echo("(no candidates yet)")
        raise typer.Exit(0)
    files = sorted(review_dir.glob("candidates-*.md"))[-limit:]
    for path in files:
        typer.echo(f"- {path}")


@hub_app.command("health")
def health_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Require a fresh successful full cycle."),
) -> None:
    """Health snapshot: infrastructure, data flow, quality."""

    snapshot = lwm_health.collect_and_write(root.resolve(), strict=strict)
    if json_output:
        payload = {
            "status": snapshot.status,
            "checked_at": snapshot.checked_at,
            "infrastructure": snapshot.infrastructure,
            "data_flow": snapshot.data_flow,
            "cycle": snapshot.cycle,
            "capabilities": snapshot.capabilities,
            "inbox_counts": snapshot.inbox_counts,
            "quality": snapshot.quality,
            "tools": [
                {
                    "tool": t.tool,
                    "last_event_at": t.last_event_at,
                    "last_event_type": t.last_event_type,
                    "last_project_id": t.last_project_id,
                    "event_count": t.event_count,
                }
                for t in snapshot.tools
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(snapshot.render())
    if snapshot.status == lwm_health.STATUS_FAILED:
        raise typer.Exit(2)
    if snapshot.status == lwm_health.STATUS_DEGRADED:
        raise typer.Exit(1)


@hub_app.command("closure")
def closure_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    source_root: Path | None = typer.Option(None, "--source-root", help="Source package root."),
    runtime_root: Path | None = typer.Option(None, "--runtime-root", help="Runtime package root."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    """Check whether the latest loop has enough evidence to close."""

    report = lwm_closure.check_closure(
        root.resolve(),
        source_root=source_root.resolve() if source_root else None,
        runtime_root=runtime_root.resolve() if runtime_root else None,
    )
    if json_output:
        payload = {"status": report.status, "checks": report.checks, "failed_checks": report.failed_checks}
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"# LLM-WorkMem Closure - {report.status}")
        for name, status in report.checks.items():
            typer.echo(f"- {name}: {status}")
        if report.failed_checks:
            typer.echo(f"- failed_checks: {', '.join(report.failed_checks)}")
    if report.status == "blocked":
        raise typer.Exit(2)
    if report.status == "degraded":
        raise typer.Exit(1)


@hub_app.command("capabilities")
def capabilities_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    """Probe installed adapters and verified tool read/write receipts."""

    payload = lwm_capabilities.probe(root.resolve())
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo("# LLM-WorkMem Tool Capabilities")
    for tool, result in payload.items():
        typer.echo(f"- {tool}: {result['status']}")


@hub_app.command("run-cycle")
def run_cycle_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Run one complete installed-runtime collection and audit cycle."""

    from lwm.runner import run_cycle

    raise typer.Exit(run_cycle(root.resolve()))


@hub_app.command("receipt")
def receipt_cmd(
    tool: str = typer.Option(..., "--tool"),
    direction: str = typer.Option(..., "--direction", help="read or write"),
    project_id: str | None = typer.Option(None, "--project-id"),
    source: str = typer.Option("cli", "--source"),
    detail: str = typer.Option("", "--detail"),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Record a verified tool read/write receipt."""

    result = lwm_capabilities.record(
        root.resolve(), tool=tool, direction=direction, project_id=project_id, source=source, detail=detail
    )
    typer.echo(json.dumps(result, ensure_ascii=False))


@hub_app.command("retain")
def retain_cmd(
    task: str = typer.Option(..., "--task"),
    project: str = typer.Option(..., "--project"),
    tool: str = typer.Option("shell", "--tool"),
    event_type: str = typer.Option("workflow_observation", "--type"),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Retain one structured work observation for later ingest."""

    result = lwm_memory_api.retain(root.resolve(), tool=tool, project_path=project, task=task, event_type=event_type)
    typer.echo(json.dumps({"path": result["path"], "project_id": result["project_id"]}, ensure_ascii=False))


@hub_app.command("recall")
def recall_cmd(
    question: str = typer.Argument(...),
    project: str | None = typer.Option(None, "--project"),
    limit: int = typer.Option(6, "--limit", min=1, max=20),
    mode: str = typer.Option("compact", "--mode", help="compact | deep"),
    format: str = typer.Option("json", "--format", help="json | markdown"),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Recall source-backed memory with progressive deterministic retrieval."""

    if format not in {"json", "markdown"}:
        typer.secho("--format must be json or markdown", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    result = lwm_memory_api.recall(
        root.resolve(), question, project_path=project, limit=limit, mode=mode
    )
    if format == "markdown":
        packet = result["packet"]
        from lwm.recall import RecallPacket, RecallPlan
        from lwm.evidence import EvidenceItem

        plan_data = packet["plan"]
        plan = RecallPlan(
            dimensions=tuple(plan_data["dimensions"]),
            checks=tuple(plan_data["checks"]),
            time_window=tuple(plan_data["time_window"]) if plan_data.get("time_window") else None,
            now=plan_data.get("now", ""),
        )
        evidence = tuple(
            EvidenceItem(
                **{
                    **item,
                    "source_event_ids": tuple(item.get("source_event_ids", [])),
                    "source_paths": tuple(item.get("source_paths", [])),
                    "verification": tuple(item.get("verification", [])),
                    "retrieval_reasons": tuple(item.get("retrieval_reasons", [])),
                }
            )
            for item in packet["evidence"]
        )
        packet_obj = RecallPacket(
            question=packet["question"],
            project_id=packet.get("project_id"),
            project_path=packet.get("project_path"),
            scope=packet["scope"],
            plan=plan,
            summary=packet["summary"],
            evidence=evidence,
            conflicts=(),
            missing=tuple(packet.get("missing", [])),
            coverage=packet["coverage"],
            warnings=tuple(packet.get("warnings", [])),
            trace_id=packet["trace_id"],
            token_estimate=packet["token_estimate"],
        )
        typer.echo(render_recall_packet(packet_obj).rstrip())
        return
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@hub_app.command("reflect")
def reflect_cmd(
    project_id: str = typer.Argument(...),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Reflect processed evidence into one project STATE.md."""

    typer.echo(lwm_memory_api.reflect_project(root.resolve(), project_id))


@hub_app.command("register-project")
def register_project_cmd(
    project: Path = typer.Argument(...),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Register one canonical project for shared memory and CBMEM."""

    typer.echo(json.dumps(lwm_registry.register(root.resolve(), project), ensure_ascii=False, indent=2))


@hub_app.command("run-supervisor")
def run_supervisor_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    force: bool = typer.Option(False, "--force", help="Run a full cycle now, regardless of the 12-hour due check."),
) -> None:
    """Run the 15-minute supervisor; execute the full cycle only when due."""

    from lwm.supervisor import run_supervisor

    raise typer.Exit(run_supervisor(root.resolve(), force=force))


@hub_app.command("install-shell-hook")
def install_shell_hook_cmd(
    ctx: typer.Context,
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    rc: Path | None = typer.Option(
        None, "--rc", help="Override rcfile path (default: ~/.zshrc)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be touched."
    ),
) -> None:
    """Install (or refresh) the LWM shell-history hook in ``~/.zshrc``."""

    resolved = root.resolve()
    if dry_run:
        typer.secho("dry-run: would install hook shim into ", fg=typer.colors.YELLOW, nl=False)
        typer.echo(str(rc or (Path.home() / ".zshrc")))
        raise typer.Exit(0)
    try:
        result = lwm_shell_hook.install(lwm_root=resolved, rc_path=rc)
    except FileNotFoundError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    verb = "refreshed" if result.already_installed else "installed"
    typer.secho(
        f"{verb} LBM shell hook ({result.hook_path}) in {result.rc_path}",
        fg=typer.colors.GREEN,
    )


@hub_app.command("uninstall-shell-hook")
def uninstall_shell_hook_cmd(
    rc: Path | None = typer.Option(
        None, "--rc", help="Override rcfile path (default: ~/.zshrc)."
    ),
) -> None:
    """Remove the LBM shell-hook marker block from the rcfile."""

    result = lwm_shell_hook.uninstall(rc_path=rc)
    if result.changed:
        typer.secho(
            f"removed LBM shell hook from {result.rc_path}",
            fg=typer.colors.GREEN,
        )
    else:
        typer.echo(f"(no shell hook in {result.rc_path})")


@hub_app.command("fixup-project-pages")
def fixup_project_pages_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Rewrite project pages to use the canonical inline-YAML frontmatter.

    Used after a schema migration so the audit stops reporting empty
    ``tags`` lists. No data is dropped — only the header is re-emitted.
    """

    rewritten = lwm_project_memory.normalize_existing_pages(root.resolve())
    for path in rewritten:
        typer.echo(f"rewrote {path.name}")
    typer.echo(f"({len(rewritten)} project page(s) updated)")


@hub_app.command("forget")
def forget_cmd(
    event_id: str = typer.Argument(..., help="event_id (uuid) to remove from memory"),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Remove a single event from raw/, event-index, and its project page."""

    result = lwm_forget.forget_event(root.resolve(), event_id)
    if not result.deleted_files and not result.index_updated:
        typer.secho(
            f"(no record of {event_id}; nothing to do)", fg=typer.colors.YELLOW
        )
        raise typer.Exit(0)
    for path in result.deleted_files:
        typer.echo(f"deleted {path}")
    if result.page_updated and result.page_path is not None:
        typer.echo(f"updated {result.page_path}")


@hub_app.command("retention")
def retention_cmd(
    days: int = typer.Option(30, "--days", help="Delete events older than N days."),
    bucket: str = typer.Option(
        "processed", "--bucket", help="inbox|processed|rejected|failed"
    ),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Drop event JSON files older than --days from one bucket."""

    if bucket == "inbox":
        typer.secho(
            "refusing to apply retention against inbox (pending events are sacred)",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    removed = lwm_forget.apply_retention(
        root.resolve(), bucket=bucket, older_than_days=days
    )
    for path in removed:
        typer.echo(f"pruned {path}")
    typer.echo(f"({len(removed)} file(s) removed)")


@hub_app.command("install-ide-hooks")
def install_ide_hooks_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    home: Path | None = typer.Option(
        None,
        "--home",
        help="Override $HOME (used by tests). Defaults to Path.home().",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report what would be touched without writing.",
    ),
    tools: str = typer.Option(
        "claude-code,codex,kiro,trae,minimax",
        "--tools",
        help="Comma-separated list of IDE tools to install hooks for.",
    ),
) -> None:
    """Generate Level 1 native hook configurations for each IDE."""

    target_home = (home or Path.home()).resolve()
    tool_list = tuple(t.strip() for t in tools.split(",") if t.strip())
    if dry_run:
        typer.secho("dry-run: would write hook configs under ", fg=typer.colors.YELLOW, nl=False)
        typer.echo(str(target_home))
        return
    installs = lwm_hooks_gen.install_ide_hooks(target_home, tools=tool_list)
    for entry in installs:
        typer.echo(f"{entry.tool}: {entry.config_path} ({entry.detail})")


def register(app: typer.Typer) -> None:
    """Mount the hub subcommand tree onto the main Typer app."""

    app.add_typer(hub_app, name="hub")


__all__ = ["hub_app", "register"]
