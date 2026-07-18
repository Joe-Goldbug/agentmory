"""Minimal MCP-compatible stdio server for the LLM-WorkMem hub.

The server speaks the JSON-RPC 2.0 protocol used by MCP and exposes four
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

import json
import re
import sys
from pathlib import Path

from lwm import context, inbox as lwm_inbox
from lwm import capabilities, health as lwm_health, memory_api
from lwm import project_memory
from lwm.events import validate_event
from lwm.project_id import record_project
from lwm.events import make_event as make_event_default


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
        "description": "Record a verified tool read/write receipt.",
        "properties": {"root": {"type": "string"}, "tool": {"type": "string"}, "direction": {"type": "string"}, "project_id": {"type": "string"}},
        "required": ["root", "tool", "direction"],
    },
    "health": {
        "description": "Return strict shared-memory health data.",
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


def _call_tool(name: str, arguments: dict) -> dict:
    """Dispatch one tool invocation and return the ``result`` payload."""

    if name not in TOOLS:
        raise KeyError(name)
    if name == "query_context":
        root = Path(arguments["root"]).resolve()
        report = context.build(
            root,
            tool=str(arguments["tool"]),
            project_path=str(arguments["project"]),
            limit=int(arguments.get("limit", 6)),
        )
        capabilities.record(root, tool=str(arguments["tool"]), direction="read", project_id=report.project_id, source="mcp")
        return {
            "format": "markdown",
            "markdown": report.markdown,
            "sections": list(getattr(report, "sections", []) or []),
        }
    if name == "record_event":
        root = Path(arguments["root"]).resolve()
        incoming = dict(arguments["event"])
        # Project id derivation mirrors the CLI: take what was passed
        # verbatim; only fill ``project_id`` from the path if missing.
        if incoming.get("project_path") and "project_id" not in incoming:
            resolution = record_project(root, str(incoming["project_path"]))
            incoming["project_id"] = resolution.project_id
        # Make sure event_id, timestamp, importance, privacy are populated
        # so the schema validator never fails on the most boring key
        # omissions. ``make_event`` fills exactly those defaults without
        # clobbering caller-supplied values.
        defaults = make_event_default(
            tool=incoming.get("tool", "shell"),
            project_path=incoming.get("project_path", ""),
            project_id=incoming.get("project_id", "adhoc"),
            event_type=incoming.get("event_type", "workflow_observation"),
            task=incoming.get("task", "mcp record"),
            timestamp=incoming.get("timestamp"),
            event_id=incoming.get("event_id"),
            importance=incoming.get("importance"),
            privacy=incoming.get("privacy"),
        )
        for key, value in defaults.items():
            incoming.setdefault(key, value)
        report = validate_event(incoming)
        if not report.ok:
            raise ValueError("; ".join(issue.message for issue in report.issues))
        rel = lwm_inbox.submit_event(root, incoming)
        capabilities.record(root, tool=str(incoming.get("tool", "unknown")), direction="write", project_id=str(incoming.get("project_id") or ""), source="mcp")
        return {"ingested": True, "path": str(rel), "event_id": incoming["event_id"]}
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
        return capabilities.record(
            root,
            tool=str(arguments["tool"]),
            direction=str(arguments["direction"]),
            project_id=str(arguments.get("project_id") or "") or None,
            source="mcp",
        )
    if name == "health":
        root = Path(arguments["root"]).resolve()
        snapshot = lwm_health.collect_and_write(root, strict=True)
        return {"status": snapshot.status, "cycle": snapshot.cycle, "capabilities": snapshot.capabilities, "quality": snapshot.quality}
    raise KeyError(name)


def _serve(stream_in, stream_out) -> None:
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
                content = _call_tool(params["name"], params.get("arguments") or {})
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
    if not argv:
        sys.stderr.write("usage: python -m mcp.lwm_server <root>\n")
        return 2
    _serve(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
