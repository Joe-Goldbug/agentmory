"""Minimal MCP-compatible stdio server for the LLM-WorkMem hub.

The server speaks the JSON-RPC 2.0 protocol used by MCP and exposes shared
tools that read from / write to the same wiki tree used by the CLI:

* ``query_context`` — returns the markdown context for a tool + project.
* ``record_event`` — submits an event into ``raw/events/inbox``.
* ``search_memory`` — case-insensitive substring search over wiki pages.
* ``get_project_memory`` — returns the project's wiki page.

We deliberately avoid the official MCP SDK to honour the project's
"minimal dependencies" rule. The wire protocol is JSON-RPC 2.0 over
stdin/stdout, which is the same shape used by every official SDK
underneath.

Run with ``python -m mcp.lwm_server <root>`` and pipe JSON-RPC requests
through stdin. The implementation keeps no module-level mutable state
beyond what the JSON-RPC request supplies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from lwm import capabilities, health as lwm_health, memory_api
from lwm import project_memory
from lwm import hub_service
from lwm.capability_proof import OBSERVATION_RECEIPT_SOURCES, PROOF_RECEIPT_SOURCES
from lwm.project_id import record_project
from lwm.tool_registry import ToolRegistry


TOOLS = {
    "query_context": {
        "description": "Return the markdown context the hub would render for a tool+project.",
        "properties": {
            "root": {"type": "string"},
            "tool": {"type": "string"},
            "project": {"type": "string"},
            "limit": {"type": "integer", "default": 6},
        },
        "required": ["root", "tool", "project"],
    },
    "record_event": {
        "description": "Submit an event into raw/events/inbox (same effect as `lwm hub record`).",
        "properties": {
            "root": {"type": "string"},
            "event": {"type": "object"},
        },
        "required": ["root", "event"],
    },
    "search_memory": {
        "description": "Search wiki pages for a query string.",
        "properties": {
            "root": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["root", "query"],
    },
    "get_project_memory": {
        "description": "Return the markdown body of one project page by project_id or path.",
        "properties": {
            "root": {"type": "string"},
            "project_id": {"type": "string"},
            "project_path": {"type": "string"},
        },
        "required": ["root"],
    },
    "recall": {
        "description": "Progressively recall source-backed shared memory.",
        "properties": {
            "root": {"type": "string"},
            "question": {"type": "string"},
            "project": {"type": "string"},
            "limit": {"type": "integer", "default": 6},
            "mode": {"type": "string", "enum": ["compact", "deep"], "default": "compact"},
        },
        "required": ["root", "question"],
    },
    "record_receipt": {
        "description": "Record an observation-only tool read/write receipt. Native proof receipts must come from the host lifecycle bridge, not a generic MCP call.",
        "properties": {
            "root": {"type": "string"},
            "tool": {"type": "string"},
            "direction": {"type": "string"},
            "project_id": {"type": "string"},
            "source": {
                "type": "string",
                "enum": sorted(OBSERVATION_RECEIPT_SOURCES),
            },
            "evidence_path": {"type": "string"},
            "operation_id": {"type": "string"},
        },
        "required": ["root", "tool", "direction"],
    },
    "health": {
        "description": "Return strict shared-memory health data.",
        "properties": {"root": {"type": "string"}},
        "required": ["root"],
    },
    # Canonical cross-tool names. Legacy names above remain for compatibility.
    "lwm_context": {
        "description": "Return the canonical startup context for one tool and project.",
        "properties": {"root": {"type": "string"}, "tool": {"type": "string"}, "project": {"type": "string"}, "limit": {"type": "integer", "default": 6}},
        "required": ["root", "tool", "project"],
    },
    "lwm_retain": {
        "description": "Retain one sanitized structured work event.",
        "properties": {"root": {"type": "string"}, "event": {"type": "object"}},
        "required": ["root", "event"],
    },
    "lwm_recall": {
        "description": "Recall source-backed memory with evidence and coverage.",
        "properties": {"root": {"type": "string"}, "question": {"type": "string"}, "project": {"type": "string"}, "limit": {"type": "integer", "default": 6}, "mode": {"type": "string", "default": "compact"}},
        "required": ["root", "question"],
    },
    "lwm_handoff": {
        "description": "Create, read, acknowledge, or close one active handoff.",
        "properties": {"root": {"type": "string"}, "action": {"type": "string"}, "project_id": {"type": "string"}, "handoff_id": {"type": "string"}, "target_tool": {"type": "string"}, "packet": {"type": "object"}},
        "required": ["root", "action"],
    },
    "lwm_coverage": {
        "description": "Return truthful per-tool capture and delivery coverage.",
        "properties": {"root": {"type": "string"}, "tool": {"type": "string"}, "project_id": {"type": "string"}},
        "required": ["root"],
    },
    "lwm_health": {
        "description": "Return strict cycle, quality, and capability health.",
        "properties": {"root": {"type": "string"}},
        "required": ["root"],
    },
}


def _ok(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _err(id_, code, message, data=None):
    payload = {
        "jsonrpc": "2.0",
        "id": id_,
        "error": {"code": code, "message": message},
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def _search_wiki(root: Path, query: str, limit: int) -> list[dict]:
    wiki = root / "wiki"
    if not wiki.is_dir():
        return []
    if not query.strip():
        return []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for path in sorted(wiki.rglob("*.md")):
        if not pattern.search(path.read_text(encoding="utf-8")):
            continue
        hits.append(
            {
                "path": str(path.relative_to(root)),
                "title": path.stem,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def _registered_bridge(
    root: Path,
    *,
    host_tool: str | None,
    host_integration: str | None,
):
    """Return a registry row only for an explicitly bound MCP host."""

    if not host_tool or not host_integration:
        return None
    definition = ToolRegistry.load(root).resolve(host_tool)
    if definition is None or host_integration not in definition.proof_integrations:
        return None
    return definition


def _mcp_bridge_receipt(
    root: Path,
    *,
    name: str,
    arguments: dict,
    result: dict,
    host_tool: str | None,
    host_integration: str | None,
) -> dict | None:
    """Record proof only for the registered MiniMax MCP read/write surface.

    The evidence is intentionally bounded to operation metadata. User content
    stays in the normal sanitized event path and is never copied into proof.
    """

    definition = _registered_bridge(
        root,
        host_tool=host_tool,
        host_integration=host_integration,
    )
    if definition is None:
        return None

    registry = ToolRegistry.load(root)
    operation: str
    direction: str
    project_id: str | None
    event_id: str | None = None
    if name in {"query_context", "lwm_context"}:
        requested = registry.resolve(str(arguments.get("tool") or ""))
        if requested is None or requested.tool_id != definition.tool_id:
            return None
        project_path = str(arguments.get("project") or root)
        project_id = record_project(root, project_path).project_id
        operation = "query_context"
        direction = "read"
    elif name == "lwm_retain":
        event = arguments.get("event")
        if not isinstance(event, dict):
            return None
        requested = registry.resolve(str(event.get("tool") or ""))
        if requested is None or requested.tool_id != definition.tool_id:
            return None
        project_id = str(event.get("project_id") or "") or record_project(
            root, str(event.get("project_path") or root)
        ).project_id
        operation = "lwm_retain"
        direction = "write"
        event_id = str(result.get("event_id") or "") or None
    else:
        return None

    operation_id = f"mcp-bridge:{uuid.uuid4().hex}"
    relative_evidence = Path("state/receipts/mcp-bridge") / f"{operation_id.split(':', 1)[1]}.json"
    evidence = {
        "schema_version": "1",
        "tool": definition.tool_id,
        "integration": host_integration,
        "direction": direction,
        "project_id": project_id,
        "operation": operation,
        "operation_id": operation_id,
    }
    if event_id:
        evidence["event_id"] = event_id
    evidence_path = root / relative_evidence
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return capabilities.record(
        root,
        tool=definition.tool_id,
        direction=direction,
        project_id=project_id,
        source="mcp-bridge",
        evidence_path=str(relative_evidence),
        operation_id=operation_id,
        detail="registered host-bound MCP bridge operation",
    )


def _call_tool(name: str, arguments: dict) -> dict:
    """Dispatch one tool invocation and return the ``result`` payload."""

    if name not in TOOLS:
        raise KeyError(name)
    alias = {
        "lwm_context": "query_context",
    "lwm_recall": "recall",
        "lwm_health": "health",
    }.get(name, name)
    if alias != name:
        return _call_tool(alias, arguments)
    if name == "lwm_retain":
        root = Path(arguments["root"]).resolve()
        result = hub_service.retain_event(
            root, arguments["event"], receipt_source="watcher-observed"
        )
        return {
            "ingested": not result["duplicate"],
            "duplicate": result["duplicate"],
            "path": result["path"],
            "event_id": result["event_id"],
            "existing_event_id": result.get("existing_event_id"),
        }
    if name == "lwm_coverage":
        return hub_service.coverage_report(
            Path(arguments["root"]).resolve(),
            tool=str(arguments["tool"]) if arguments.get("tool") else None,
            project_id=str(arguments["project_id"]) if arguments.get("project_id") else None,
        )
    if name == "lwm_handoff":
        from lwm.handoff import ack_handoff, close_handoff, create_handoff, load_active

        root = Path(arguments["root"]).resolve()
        action = str(arguments.get("action") or "current")
        if action == "current":
            packet = load_active(root, project_id=str(arguments["project_id"]))
            return {"packet": packet.to_dict() if packet else None}
        if action == "create":
            packet_data = dict(arguments.get("packet") or {})
            packet = create_handoff(root, **packet_data)
            return packet.to_dict()
        if action == "ack":
            return ack_handoff(root, handoff_id=str(arguments["handoff_id"]), target_tool=str(arguments["target_tool"])).to_dict()
        if action == "close":
            return close_handoff(root, handoff_id=str(arguments["handoff_id"])).to_dict()
        raise ValueError(f"unknown handoff action: {action}")
    if name == "query_context":
        root = Path(arguments["root"]).resolve()
        report, _receipt = hub_service.context_for_tool(
            root,
            tool=str(arguments["tool"]),
            project_path=str(arguments["project"]),
            limit=int(arguments.get("limit", 6)),
        )
        return {
            "format": "markdown",
            "markdown": report.markdown,
            "sections": list(getattr(report, "sections", []) or []),
        }
    if name == "record_event":
        root = Path(arguments["root"]).resolve()
        result = hub_service.record_event(
            root, arguments["event"], receipt_source="watcher-observed"
        )
        return {
            "ingested": True,
            "path": result["path"],
            "event_id": result["event_id"],
        }
    if name == "search_memory":
        root = Path(arguments["root"]).resolve()
        hits = _search_wiki(root, str(arguments["query"]), int(arguments.get("limit", 10)))
        return {"hits": hits}
    if name == "get_project_memory":
        root = Path(arguments["root"]).resolve()
        if arguments.get("project_id"):
            page = project_memory.project_page_path(
                root, str(arguments["project_id"])
            )
        else:
            resolution = record_project(root, str(arguments["project_path"]))
            page = project_memory.project_page_path(root, resolution.project_id)
        if not page.is_file():
            return {"content": None, "path": str(page)}
        return {"content": page.read_text(encoding="utf-8"), "path": str(page)}
    if name == "recall":
        root = Path(arguments["root"]).resolve()
        return memory_api.recall(
            root,
            str(arguments["question"]),
            project_path=str(arguments["project"]) if arguments.get("project") else None,
            limit=int(arguments.get("limit", 6)),
            mode=str(arguments.get("mode", "compact")),
        )
    if name == "record_receipt":
        root = Path(arguments["root"]).resolve()
        source = str(arguments.get("source") or "watcher-observed")
        if source in PROOF_RECEIPT_SOURCES:
            raise ValueError(
                "MCP cannot write host proof receipts; use the registered host bridge"
            )
        return capabilities.record(
            root,
            tool=str(arguments["tool"]),
            direction=str(arguments["direction"]),
            project_id=str(arguments.get("project_id") or "") or None,
            source=source,
            evidence_path=str(arguments.get("evidence_path") or ""),
            operation_id=str(arguments.get("operation_id") or ""),
        )
    if name == "health":
        root = Path(arguments["root"]).resolve()
        snapshot = lwm_health.collect_and_write(root, strict=True)
        return {"status": snapshot.status, "cycle": snapshot.cycle, "capabilities": snapshot.capabilities, "quality": snapshot.quality}
    raise KeyError(name)


def _serve(
    stream_in,
    stream_out,
    *,
    default_root: Path | None = None,
    host_tool: str | None = None,
    host_integration: str | None = None,
) -> None:
    for raw in stream_in:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            stream_out.write(json.dumps(_err(None, -32700, "parse error", str(exc))) + "\n")
            stream_out.flush()
            continue
        id_ = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "initialize":
            response = _ok(
                id_,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "lwm-mcp", "version": "0.1"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            )
        elif method == "tools/list":
            response = _ok(
                id_,
                {
                    "tools": [
                        {"name": name, **spec, "inputSchema": {"type": "object",
                                                               "properties": spec["properties"],
                                                               "required": spec.get("required", [])}}
                        for name, spec in TOOLS.items()
                    ]
                },
            )
        elif method == "tools/call":
            try:
                arguments = params.get("arguments") or {}
                if default_root is not None and isinstance(arguments, dict):
                    arguments = dict(arguments)
                    arguments.setdefault("root", str(default_root))
                content = _call_tool(params["name"], arguments)
                _mcp_bridge_receipt(
                    Path(arguments["root"]).resolve(),
                    name=str(params["name"]),
                    arguments=arguments,
                    result=content,
                    host_tool=host_tool,
                    host_integration=host_integration,
                )
            except KeyError:
                response = _err(id_, -32602, f"unknown tool: {params.get('name')}")
            except ValueError as exc:
                response = _err(id_, -32602, f"validation error: {exc}")
            except Exception as exc:  # pragma: no cover - defensive
                response = _err(id_, -32603, "internal error", str(exc))
            else:
                response = _ok(
                    id_,
                    {"content": [{"type": "json", "data": content}]},
                )
        elif method == "notifications/initialized":
            # No reply required; the spec uses notifications.
            continue
        else:
            response = _err(id_, -32601, f"unknown method: {method}")
        stream_out.write(json.dumps(response, ensure_ascii=False) + "\n")
        stream_out.flush()


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="python -m mcp.lwm_server")
    parser.add_argument("root", nargs="?", help="Default LLM-WorkMem root for tool calls.")
    parser.add_argument("--root", dest="root_option", help="Default LLM-WorkMem root for tool calls.")
    args = parser.parse_args(argv)
    configured_root = args.root_option or args.root or os.environ.get("LWM_ROOT")
    if not configured_root:
        sys.stderr.write("usage: python -m mcp.lwm_server <root>\n")
        return 2
    _serve(
        sys.stdin,
        sys.stdout,
        default_root=Path(configured_root).expanduser().resolve(),
        host_tool=os.environ.get("LWM_MCP_TOOL"),
        host_integration=os.environ.get("LWM_MCP_INTEGRATION"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
