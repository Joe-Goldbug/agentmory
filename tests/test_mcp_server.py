"""MCP server smoke tests.

Scope Lock:
- Solves: confirms ``initialize``, ``tools/list``, ``tools/call``
  return valid JSON-RPC and that each tool actually touches the same
  tree the CLI uses (record → inbox, search → wiki).
- Does not solve: real MCP wire transport (sock, pipe, …); we test the
  in-process function ``_serve(stream_in, stream_out)`` for stability.
- Acceptance: 6 tests cover all four tools + initialize + parse-error.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from lwm.events import make_event
from mcp.lwm_server import _serve


def _rpc(method: str, params=None, id_=None) -> bytes:
    body: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if id_ is not None:
        body["id"] = id_
    return (json.dumps(body) + "\n").encode("utf-8")


def _drive(root: Path, requests: list[bytes]) -> list[dict]:
    stream_in = io.BufferedReader(io.BytesIO(b"".join(requests)))
    stream_out = io.StringIO()
    _serve(stream_in, stream_out)
    return [
        json.loads(line)
        for line in stream_out.getvalue().splitlines()
        if line.strip()
    ]


def test_initialize_responds_with_capabilities(tmp_path: Path) -> None:
    responses = _drive(tmp_path, [_rpc("initialize", id_=1)])
    assert responses[0]["result"]["serverInfo"]["name"] == "lwm-mcp"
    assert "tools" in responses[0]["result"]["capabilities"]


def test_tools_list_includes_all_four(tmp_path: Path) -> None:
    responses = _drive(tmp_path, [_rpc("tools/list", id_=2)])
    names = {tool["name"] for tool in responses[0]["result"]["tools"]}
    assert {"query_context", "record_event", "search_memory", "get_project_memory"} <= names


def test_record_event_via_mcp(tmp_path: Path) -> None:
    payload = make_event(
        tool="shell",
        project_path=str(tmp_path),
        project_id="git-mcp-1",
        event_type="workflow_observation",
        task="mcp test event",
    )
    response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "record_event",
                    "arguments": {"root": str(tmp_path), "event": payload},
                },
                id_=3,
            )
        ],
    )[0]
    assert response["result"]["content"][0]["data"]["ingested"] is True
    inbox_file = tmp_path / "raw" / "events" / "inbox"
    files = list(inbox_file.rglob("*.json"))
    assert files, "event should have landed in raw/events/inbox"


def test_get_project_memory_via_mcp(tmp_path: Path) -> None:
    payload = make_event(
        tool="shell",
        project_path=str(tmp_path),
        project_id="git-mcp-2",
        event_type="workflow_observation",
        task="memory test",
    )
    record = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "record_event",
                    "arguments": {"root": str(tmp_path), "event": payload},
                },
                id_=1,
            ),
            _rpc(
                "tools/call",
                params={
                    "name": "get_project_memory",
                    "arguments": {"root": str(tmp_path), "project_id": payload["project_id"]},
                },
                id_=2,
            ),
        ],
    )
    memory_response = record[1]["result"]["content"][0]["data"]
    assert memory_response["content"] is None  # page only exists after ingest
    # Run ingest to materialise the project page, then re-query.
    from lwm.ingest import run as ingest_run

    ingest_run(tmp_path, with_lock=False)
    memory_response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "get_project_memory",
                    "arguments": {
                        "root": str(tmp_path),
                        "project_id": payload["project_id"],
                    },
                },
                id_=4,
            )
        ],
    )[0]["result"]["content"][0]["data"]
    assert memory_response["content"] is not None
    assert "memory test" in memory_response["content"]


def test_search_memory_finds_pages(tmp_path: Path) -> None:
    """Pre-seed a wiki page, then search for a unique substring via MCP."""

    wiki = tmp_path / "wiki" / "global"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "antigravity-policy.md").write_text(
        "---\ntitle: Antigravity policy\n---\n\nAlways use git for Antigravity writes.\n",
        encoding="utf-8",
    )
    out = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "search_memory",
                    "arguments": {"root": str(tmp_path), "query": "antigravity"},
                },
                id_=5,
            )
        ],
    )[0]["result"]["content"][0]["data"]
    paths = [hit["path"] for hit in out["hits"]]
    assert any("antigravity-policy" in p for p in paths)


def test_query_context_returns_markdown(tmp_path: Path) -> None:
    payload = make_event(
        tool="claude-code",
        project_path=str(tmp_path),
        project_id="git-mcp-3",
        event_type="session_summary",
        task="mcp context",
    )
    _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "record_event",
                    "arguments": {"root": str(tmp_path), "event": payload},
                },
                id_=1,
            )
        ],
    )
    from lwm.ingest import run as ingest_run

    ingest_run(tmp_path, with_lock=False)
    out = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "query_context",
                    "arguments": {
                        "root": str(tmp_path),
                        "tool": "claude-code",
                        "project": str(tmp_path),
                    },
                },
                id_=6,
            )
        ],
    )[0]["result"]["content"][0]["data"]
    assert out["format"] == "markdown"
    assert "mcp context" in out["markdown"]


def test_parse_error_is_returned(tmp_path: Path) -> None:
    """Bad JSON should surface a -32700 parse error response."""

    response = _drive(tmp_path, [b"not-json\n"])[0]
    assert response["error"]["code"] == -32700


def test_unknown_method_returns_minus_32601(tmp_path: Path) -> None:
    response = _drive(tmp_path, [_rpc("tools/bogus", id_=1)])[0]
    assert response["error"]["code"] == -32601
