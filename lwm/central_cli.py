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
from pathlib import Path
from typing import Optional

import typer

from lwm import behavior_contract
from lwm import closure as lwm_closure
from lwm import forget as lwm_forget
from lwm import health as lwm_health
from lwm import hooks_gen as lwm_hooks_gen
from lwm import insights as lwm_insights
from lwm import ingest as lwm_ingest
from lwm import promote as lwm_promote
from lwm import project_memory as lwm_project_memory
from lwm import shell_hook as lwm_shell_hook
from lwm import capabilities as lwm_capabilities
from lwm import lifecycle as lwm_lifecycle
from lwm import memory_api as lwm_memory_api
from lwm import hub_service
from lwm import ide_companion as lwm_ide_companion
from lwm import migration as lwm_migration
from lwm import memory_federation as lwm_memory_federation
from lwm import session_bridge
from lwm.harvest import mutable_ownership_issues, runtime_paths
from lwm.recall import render_recall_packet
from lwm import registry as lwm_registry
from lwm.capability_proof import PROOF_RECEIPT_SOURCES


hub_app = typer.Typer(
    name="hub",
    help="Central hub: events, ingest, context, promote, insights, health",
    no_args_is_help=True,
)
tools_app = typer.Typer(help="List registered tools and their real collectors.", no_args_is_help=True)
behavior_app = typer.Typer(help="Show and verify the canonical GLOBAL.md contract.", no_args_is_help=True)
handoff_app = typer.Typer(help="Create and inspect cross-tool task handoffs.", no_args_is_help=True)
federation_app = typer.Typer(help="Compile and restore the unified native-memory release.", no_args_is_help=True)
hub_app.add_typer(tools_app, name="tools")
hub_app.add_typer(behavior_app, name="behavior")
hub_app.add_typer(handoff_app, name="handoff")
hub_app.add_typer(federation_app, name="federation")


@tools_app.command("list")
def tools_list_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    home: Path | None = typer.Option(None, "--home", help="Override the tool discovery home."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    rows = hub_service.list_tools(root.resolve(), home=home.resolve() if home else None)
    if json_output:
        typer.echo(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for row in rows:
        collectors = ", ".join(row["collector_modules"]) or "hook/lifecycle"
        host_status = str((row.get("host_probe") or {}).get("status") or "unknown")
        typer.echo(
            f"- {row['tool_id']}: {row['coverage_status']} "
            f"host={host_status}; {row['status_reason']} "
            f"[{collectors} ({row['capture_mode']})]"
        )


@tools_app.command("probe")
def tools_probe_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    home: Path | None = typer.Option(None, "--home", help="Override the tool discovery home."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    """Probe discovery and collector availability without claiming proof."""

    rows = hub_service.list_tools(root.resolve(), home=home.resolve() if home else None)
    if json_output:
        typer.echo(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for row in rows:
        discovered = "discovered" if row["discovered"] else "not-discovered"
        importable = (
            "collector-ready"
            if row["collector_status"] == "ready"
            else "collector-missing"
            if row["collector_status"] == "missing"
            else row["capture_mode"]
        )
        host_status = str((row.get("host_probe") or {}).get("status") or "unknown")
        typer.echo(
            f"- {row['tool_id']}: {discovered}, {importable}, "
            f"host={host_status}, coverage={row['coverage_status']}; "
            f"{row['status_reason']}"
        )


@hub_app.command("coverage")
def coverage_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    tool: str | None = typer.Option(None, "--tool"),
    project_id: str | None = typer.Option(None, "--project-id"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    payload = hub_service.coverage_report(root.resolve(), tool=tool, project_id=project_id)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for tool_id, row in payload.items():
        gap = ", ".join(row.get("gaps") or ())
        typer.echo(f"- {tool_id}: {row['status']}" + (f" ({gap})" if gap else ""))


@behavior_app.command("show")
def behavior_show_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    payload = hub_service.behavior_show(root.resolve())
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2) if json_output else payload.get("text", ""))


@behavior_app.command("verify")
def behavior_verify_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    expected_sha256: str | None = typer.Option(None, "--sha256"),
) -> None:
    payload = hub_service.behavior_verify(root.resolve(), expected_sha256=expected_sha256)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["valid"]:
        raise typer.Exit(1)


@behavior_app.command("snapshot")
def behavior_snapshot_cmd(
    source: Path = typer.Option(Path("GLOBAL.md"), "--source", help="Human-reviewed GLOBAL.md."),
    root: Path = typer.Option(Path("."), "--root", help="Runtime data root."),
) -> None:
    """Create a versioned runtime snapshot without changing GLOBAL.md."""

    source_path = source.expanduser()
    if not source_path.is_absolute():
        source_path = (Path.cwd() / source_path).resolve()
    target = behavior_contract.write_snapshot(root.resolve(), source_path)
    typer.echo(json.dumps({"snapshot": str(target), **behavior_contract.verify(root.resolve())}, ensure_ascii=False, indent=2))


@behavior_app.command("sync")
def behavior_sync_cmd(
    source: Path = typer.Option(Path("GLOBAL.md"), "--source", help="Human-reviewed GLOBAL.md."),
    root: Path = typer.Option(Path("."), "--root", help="Runtime data root."),
) -> None:
    """Synchronize a reviewed behavior contract into a runtime snapshot."""

    source_path = source.expanduser()
    if not source_path.is_absolute():
        source_path = (Path.cwd() / source_path).resolve()
    target = behavior_contract.write_snapshot(root.resolve(), source_path)
    typer.echo(json.dumps({"snapshot": str(target), **behavior_contract.verify(root.resolve())}, ensure_ascii=False, indent=2))


@hub_app.command("analyze")
def analyze_pending_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    pending: bool = typer.Option(False, "--pending", help="Process pending candidates."),
) -> None:
    if not pending:
        typer.echo("pass --pending to process optional analysis candidates")
        raise typer.Exit(2)
    typer.echo(json.dumps(hub_service.analyze_pending(root.resolve()), ensure_ascii=False, indent=2))


@hub_app.command("review-analysis")
def review_analysis_cmd(
    candidate_id: str = typer.Argument(..., help="Analysis candidate id."),
    decision: str = typer.Option(..., "--decision", help="accept | reject | promote"),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
) -> None:
    """Review one validated compiler result without auto-promoting it."""

    try:
        payload = hub_service.review_analysis(
            root.resolve(), candidate_id, decision=decision
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@federation_app.command("compile")
def federation_compile_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
) -> None:
    """Compile current Codex/OpenCode native memory into one release."""

    typer.echo(json.dumps(lwm_memory_federation.compile_federated_memory(root.resolve()), ensure_ascii=False, indent=2))


@federation_app.command("restore")
def federation_restore_cmd(
    release_id: str = typer.Argument(..., help="Previously generated release id."),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
) -> None:
    """Restore a previous unified-memory release."""

    typer.echo(json.dumps(lwm_memory_federation.restore_federated_release(root.resolve(), release_id), ensure_ascii=False, indent=2))


@hub_app.command("promote-analysis")
def promote_analysis_cmd(
    candidate_id: str = typer.Argument(..., help="Accepted analysis candidate id."),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
) -> None:
    """Explicitly promote one accepted candidate through stable evidence gates."""

    try:
        payload = hub_service.promote_analysis(root.resolve(), candidate_id)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@hub_app.command("verify-cycle")
def verify_cycle_cmd(
    cycle_id: str = typer.Argument("", help="Cycle id, or a data root to verify its latest receipt."),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root."),
    strict: bool = typer.Option(False, "--strict"),
) -> None:
    effective_root = root.resolve()
    if cycle_id and Path(cycle_id).is_dir() and str(root) == ".":
        effective_root = Path(cycle_id).resolve()
        from lwm.cycle_receipt import load_last_attempt, load_latest

        latest = load_latest(effective_root) or load_last_attempt(effective_root) or {}
        cycle_id = str(latest.get("cycle_id") or latest.get("receipt_id") or "")
    if not cycle_id:
        typer.secho("No cycle id or latest receipt found.", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    payload = hub_service.verify_cycle(effective_root, cycle_id, strict=strict)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["valid"]:
        raise typer.Exit(1)


@handoff_app.command("create")
def handoff_create_nested_cmd(
    project_id: str = typer.Option(..., "--project-id", "-p"),
    task_id: str = typer.Option(..., "--task-id", "-t"),
    objective: str = typer.Option("", "--objective", "-o"),
    current_state: str = typer.Option("", "--current-state", "-s"),
    source_tool: str = typer.Option("codex", "--source-tool"),
    supersedes: str | None = typer.Option(None, "--supersedes"),
    next_action: str = typer.Option("", "--next-action"),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    from lwm.handoff import create_handoff

    packet = create_handoff(
        root.resolve(),
        project_id=project_id,
        task_id=task_id,
        objective=objective,
        current_state=current_state,
        source_tool=source_tool,
        supersedes=supersedes,
        next_action=next_action,
    )
    typer.echo(packet.handoff_id)


@handoff_app.command("current")
def handoff_current_nested_cmd(
    project_id: str = typer.Option(..., "--project-id", "-p"),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    from lwm.handoff import load_active, render_handoff_markdown

    packet = load_active(root.resolve(), project_id=project_id)
    if packet is None:
        raise typer.Exit(1)
    typer.echo(render_handoff_markdown(packet))


@handoff_app.command("ack")
def handoff_ack_nested_cmd(
    handoff_id: str = typer.Option(..., "--handoff-id"),
    target_tool: str = typer.Option(..., "--target-tool"),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    from lwm.handoff import ack_handoff

    ack_handoff(root.resolve(), handoff_id=handoff_id, target_tool=target_tool)
    typer.echo("ack recorded")


@handoff_app.command("close")
def handoff_close_nested_cmd(
    handoff_id: str = typer.Option(..., "--handoff-id"),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    from lwm.handoff import close_handoff

    closed = close_handoff(root.resolve(), handoff_id=handoff_id)
    typer.echo(closed.closed_at)


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

    try:
        result = hub_service.record_event(root, parsed, receipt_source="cli-record")
    except ValueError as exc:
        typer.secho(f"invalid event: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    typer.secho(f"recorded -> {result['path']}", fg=typer.colors.GREEN)


@hub_app.command("ingest")
def ingest_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    no_lock: bool = typer.Option(False, "--no-lock", help="Skip lockfile acquisition."),
    promote: bool = typer.Option(
        False,
        "--promote",
        help="Evaluate legacy candidates after ingest; never write global memory.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
) -> None:
    """Ingest events; the legacy ``--promote`` flag is observation-only."""

    report = lwm_ingest.run(
        root.resolve(),
        with_lock=not no_lock,
        auto_promote=promote,
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
    report, _receipt = hub_service.context_for_tool(
        root.resolve(), tool=tool, project_path=project, limit=limit
    )
    if format == "json":
        typer.echo(json.dumps(report.data, ensure_ascii=False, indent=2))
        return
    typer.echo(report.markdown)


@hub_app.command("lifecycle")
def lifecycle_cmd(
    phase: str = typer.Argument(..., help="start | stop"),
    tool: str = typer.Option(..., "--tool", help="Tool name."),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Current project path."),
    session_id: str | None = typer.Option(None, "--session-id", help="Host session id."),
    task_id: str | None = typer.Option(None, "--task-id", help="Structured task identity."),
    task: str | None = typer.Option(None, "--task", help="Sanitized end summary."),
    handoff_json: str | None = typer.Option(
        None,
        "--handoff-json",
        help="Bounded structured handoff summary JSON; raw prompts are not accepted as handoff state.",
    ),
    source: str = typer.Option(
        "watcher-observed",
        "--source",
        help="Receipt source; native-hook is reserved for a real host integration.",
    ),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root.", exists=False),
) -> None:
    """Handle a native lifecycle boundary with a canonical project root."""

    if phase not in {"start", "stop"}:
        typer.secho("phase must be start or stop", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    if source in PROOF_RECEIPT_SOURCES:
        typer.secho(
            "proof sources require a verified host integration; use `lwm hub bridge` "
            "with host_proof or keep this command observation-only",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    if phase == "start":
        result = lwm_lifecycle.start(
            root,
            tool=tool,
            project_path=project,
            session_id=session_id,
            task_id=task_id,
            source=source,
        )
        typer.echo(result.context_markdown)
        return
    handoff_summary = None
    if handoff_json:
        try:
            parsed_handoff = json.loads(handoff_json)
        except json.JSONDecodeError as exc:
            typer.secho(f"--handoff-json must be valid JSON: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(2) from exc
        if not isinstance(parsed_handoff, dict):
            typer.secho("--handoff-json must be a JSON object", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
        handoff_summary = parsed_handoff
    result = lwm_lifecycle.stop(
        root,
        tool=tool,
        project_path=project,
        session_id=session_id,
        task_id=task_id,
        task=task,
        handoff_summary=handoff_summary,
        source=source,
    )
    typer.echo(f"lifecycle stop -> {result.event_path}")
    if result.handoff_created:
        typer.echo(f"handoff created -> {result.handoff_id}")
    if result.warning:
        typer.secho(result.warning, err=True, fg=typer.colors.YELLOW)


@hub_app.command("bridge")
def bridge_cmd(
    request: str | None = typer.Argument(
        None,
        help="Versioned JSON request; omit it to read one JSON object from stdin.",
    ),
    output: str = typer.Option(
        "json",
        "--output",
        help="json for the machine contract, or markdown for direct Context delivery.",
    ),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root.", exists=False),
) -> None:
    """Run the shared JSON session bridge used by IDEs and CLIs."""

    raw = request
    if raw is None:
        if sys.stdin.isatty():
            typer.secho("bridge request is required", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
        raw = sys.stdin.read()
    if output not in {"json", "markdown"}:
        typer.secho("--output must be json or markdown", err=True, fg=typer.colors.RED)
        raise typer.Exit(2)
    try:
        parsed = json.loads(raw)
        result = session_bridge.dispatch(
            root.resolve(),
            parsed,
            trusted_host=os.environ.get("LWM_HOST_BRIDGE") == "1",
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        typer.secho(f"invalid bridge request: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    if output == "markdown":
        if result["phase"] not in {"context", "start"}:
            typer.secho(
                "--output markdown is only valid for context or start",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(2)
        typer.echo(result.get("context_markdown", ""))
        return
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@hub_app.command("bridge-stop")
def bridge_stop_cmd(
    tool: str = typer.Option(..., "--tool", help="Registered tool name."),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Current project path."),
    session_id: str | None = typer.Option(None, "--session-id", help="Host session id."),
    task_id: str | None = typer.Option(None, "--task-id", help="Structured task identity."),
    task: str | None = typer.Option(None, "--task", help="Sanitized end summary."),
    handoff_json: str | None = typer.Option(
        None,
        "--handoff-json",
        help="Bounded structured handoff summary JSON; raw prompts are not accepted.",
    ),
    source: str = typer.Option(
        "watcher-observed",
        "--source",
        help="Receipt source; native-hook is reserved for a real host integration.",
    ),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root.", exists=False),
) -> None:
    """Submit a structured stop through the shared JSON Session Bridge.

    This is a shell-friendly convenience wrapper. The canonical business
    contract remains ``lwm hub bridge`` and the legacy lifecycle command is
    compatibility-only.
    """

    handoff: dict[str, object] | None = None
    if source in PROOF_RECEIPT_SOURCES:
        typer.secho(
            "bridge-stop cannot claim a proof source without host_proof; "
            "use `lwm hub bridge` from the host integration",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    if handoff_json:
        try:
            parsed = json.loads(handoff_json)
        except json.JSONDecodeError as exc:
            typer.secho(f"--handoff-json must be valid JSON: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(2) from exc
        if not isinstance(parsed, dict):
            typer.secho("--handoff-json must be a JSON object", err=True, fg=typer.colors.RED)
            raise typer.Exit(2)
        handoff = parsed

    request: dict[str, object] = {
        "phase": "stop",
        "tool": tool,
        "project_path": str(project),
        "source": source,
    }
    if session_id:
        request["session_id"] = session_id
    if task_id:
        request["task_id"] = task_id
    if task:
        request["task"] = task
    if handoff is not None:
        request["handoff"] = handoff

    try:
        result = session_bridge.dispatch(root.resolve(), request)
    except (TypeError, ValueError) as exc:
        typer.secho(f"invalid bridge stop request: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@hub_app.command("bridge-contract")
def bridge_contract_cmd(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project path."),
    root: Path = typer.Option(Path("."), "--root", help="Wiki root.", exists=False),
    simulate: bool = typer.Option(
        False,
        "--simulate",
        help="Required: run an isolated contract check without claiming host proof.",
    ),
) -> None:
    """Exercise the bridge for each registered tool in simulation mode only."""

    if not simulate:
        typer.secho(
            "refusing live bridge-contract run; pass --simulate with a temporary root",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    result = session_bridge.simulate_registry_contract(root.resolve(), project.resolve())
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_contracts_pass"]:
        raise typer.Exit(1)


@hub_app.command("promote")
def promote_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    scan: bool = typer.Option(False, "--scan", help="Scan processed events first."),
    auto: bool = typer.Option(False, "--auto", help="Run promotion directly."),
) -> None:
    """Scan legacy insight candidates without bypassing review.

    ``--scan`` remains a read/derived-candidate compatibility operation.
    The old ``--auto`` writer is retired; global memory can only be written
    through ``hub review-analysis`` followed by ``hub promote-analysis``.
    """

    root = root.resolve()
    if auto:
        typer.secho(
            "legacy --auto is disabled; use hub review-analysis and "
            "hub promote-analysis",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
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
            "capabilities_scope": snapshot.capabilities_scope,
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
        payload = {
            "status": report.status,
            "checks": report.checks,
            "failed_checks": report.failed_checks,
            "degraded_checks": report.degraded_checks,
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"# LLM-WorkMem Closure - {report.status}")
        for name, status in report.checks.items():
            typer.echo(f"- {name}: {status}")
        if report.failed_checks:
            typer.echo(f"- failed_checks: {', '.join(report.failed_checks)}")
        if report.degraded_checks:
            typer.echo(f"- degraded_checks: {', '.join(report.degraded_checks)}")
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
    source: str = typer.Option("watcher-observed", "--source", help="Proof source or observation source."),
    evidence_path: str = typer.Option("", "--evidence-path", help="Evidence path for a qualifying proof receipt."),
    operation_id: str = typer.Option("", "--operation-id", help="Unique operation id for a qualifying proof receipt."),
    detail: str = typer.Option("", "--detail"),
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
) -> None:
    """Record a verified tool read/write receipt."""

    if source in PROOF_RECEIPT_SOURCES:
        typer.secho(
            "refusing direct proof receipt: use the real host bridge with host_proof; "
            "CLI receipt is observation-only",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)

    result = lwm_capabilities.record(
        root.resolve(),
        tool=tool,
        direction=direction,
        project_id=project_id,
        source=source,
        evidence_path=evidence_path,
        operation_id=operation_id,
        detail=detail,
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


@hub_app.command("rebuild-projects")
def rebuild_projects_cmd(
    root: Path = typer.Argument(Path("."), help="Wiki root.", exists=False),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report page writes/removals without modifying derived pages.",
    ),
) -> None:
    """Rebuild derived project memory from admitted processed evidence."""

    report = lwm_project_memory.rebuild_project_pages(root.resolve(), dry_run=dry_run)
    typer.echo(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))


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
    """Run the supervisor; execute the full cycle only when the 12-hour window is due."""

    resolved = root.resolve()
    issues = mutable_ownership_issues(resolved)
    if issues:
        typer.secho(
            "refusing supervisor write: mutable data is owned outside the selected root",
            err=True,
            fg=typer.colors.RED,
        )
        for issue in issues:
            typer.secho(f"- {issue}", err=True)
        raise typer.Exit(2)

    from lwm.supervisor import run_supervisor

    raise typer.Exit(run_supervisor(resolved, force=force))


@hub_app.command("migrate-data-owner")
def migrate_data_owner_cmd(
    manifest: Path = typer.Option(..., "--manifest", help="Reviewed read-only migration manifest."),
    approval_id: str = typer.Option(..., "--approval-id", help="Manifest-bound approval id."),
    root: Path = typer.Option(Path("."), "--root", help="LLM-WorkMem checkout root."),
    runtime_base: Path | None = typer.Option(
        None,
        "--runtime-base",
        help="Expected runtime base; defaults to the selected HOME layout.",
    ),
    home: Path | None = typer.Option(None, "--home", help="Override HOME for local verification."),
    json_output: bool = typer.Option(False, "--json", help="Emit the migration report as JSON."),
) -> None:
    """Apply only a verified, manifest-bound local data-owner migration."""

    resolved_root = root.expanduser().resolve()
    selected_runtime_base = (
        runtime_base.expanduser().resolve()
        if runtime_base is not None
        else runtime_paths(resolved_root, home=home).runtime_base.resolve()
    )
    try:
        report = lwm_migration.apply_data_owner_migration(
            manifest.expanduser(),
            approval_id,
            root=resolved_root,
            runtime_base=selected_runtime_base,
            home=home.expanduser().resolve() if home else None,
        )
    except (lwm_migration.MigrationApprovalError, OSError, RuntimeError) as exc:
        typer.secho(f"migration refused: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    if json_output:
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        typer.secho("local data-owner migration applied", fg=typer.colors.GREEN)
        typer.echo(f"runtime_root: {report['runtime_root']}")
        typer.echo(f"manifest: {report['manifest_path']}")
        typer.echo(f"approval_id: {report['approval_id']}")


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


@hub_app.command("install-ide-companion")
def install_ide_companion_cmd(
    tool: str = typer.Option("vscode", "--tool", help="vscode | cursor | trae | kiro."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Resolve the host without installing."),
) -> None:
    """Install the VS Code-compatible companion with a host-specific identity."""

    if tool not in lwm_ide_companion.SUPPORTED_TOOLS:
        typer.secho(
            f"unsupported companion tool: {tool}; choose one of {', '.join(lwm_ide_companion.SUPPORTED_TOOLS)}",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(2)
    try:
        result = lwm_ide_companion.install_companion(tool, dry_run=dry_run)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        typer.secho(f"companion install refused: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(2) from exc
    if dry_run:
        typer.secho(f"dry-run: host={result.host_command[0]}", fg=typer.colors.YELLOW)
        typer.echo(f"tool={result.tool}")
        typer.echo("no files were written")
        return
    typer.secho(f"installed LLM-WorkMem companion for {result.tool}", fg=typer.colors.GREEN)
    typer.echo(f"host={result.host_command[0]}")


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
        "claude-code,codex,cursor,kiro,opencode,trae,minimax,gemini-cli,antigravity",
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
    installs = lwm_hooks_gen.install_ide_hooks(target_home, root=root.resolve(), tools=tool_list)
    for entry in installs:
        typer.echo(f"{entry.tool}: {entry.config_path} ({entry.detail})")


@hub_app.command("handoff-create")
def handoff_create_cmd(
    project_id: str = typer.Option(..., "--project-id", "-p"),
    task_id: str = typer.Option(..., "--task-id", "-t"),
    objective: str = typer.Option("", "--objective", "-o"),
    current_state: str = typer.Option("", "--current-state", "-s"),
    source_tool: str = typer.Option("claude-code", "--source-tool"),
    supersedes: str | None = typer.Option(None, "--supersedes"),
    next_action: str = typer.Option("", "--next-action"),
    root: Path = typer.Argument(Path(".")),
) -> None:
    """Create a handoff packet for ``project_id`` (spec §4 / §11)."""

    from lwm.handoff import create_handoff

    packet = create_handoff(
        root.resolve(),
        project_id=project_id,
        task_id=task_id,
        objective=objective,
        current_state=current_state,
        source_tool=source_tool,
        supersedes=supersedes,
        next_action=next_action,
    )
    typer.echo(packet.handoff_id)


@hub_app.command("handoff-current")
def handoff_current_cmd(
    project_id: str = typer.Option(..., "--project-id", "-p"),
    root: Path = typer.Argument(Path(".")),
) -> None:
    """Print the active handoff (or nothing) for ``project_id``."""

    from lwm.handoff import load_active, render_handoff_markdown

    packet = load_active(root.resolve(), project_id=project_id)
    if packet is None:
        raise typer.Exit(1)
    typer.echo(render_handoff_markdown(packet))


@hub_app.command("handoff-ack")
def handoff_ack_cmd(
    handoff_id: str = typer.Option(..., "--handoff-id"),
    target_tool: str = typer.Option(..., "--target-tool"),
    root: Path = typer.Argument(Path(".")),
) -> None:
    """Record that ``target_tool`` read this handoff."""

    from lwm.handoff import ack_handoff

    ack_handoff(root.resolve(), handoff_id=handoff_id, target_tool=target_tool)
    typer.echo("ack recorded")


@hub_app.command("handoff-close")
def handoff_close_cmd(
    handoff_id: str = typer.Option(..., "--handoff-id"),
    root: Path = typer.Argument(Path(".")),
) -> None:
    """Close a handoff: stamp ``closed_at`` and clear the active pointer."""

    from lwm.handoff import close_handoff

    closed = close_handoff(root.resolve(), handoff_id=handoff_id)
    typer.echo(closed.closed_at)


def register(app: typer.Typer) -> None:
    """Mount the hub subcommand tree onto the main Typer app."""

    app.add_typer(hub_app, name="hub")


__all__ = ["hub_app", "register"]
