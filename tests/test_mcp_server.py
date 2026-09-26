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


def _drive(
    root: Path,
    requests: list[bytes],
    *,
    default_root: Path | None = None,
    host_tool: str | None = None,
    host_integration: str | None = None,
) -> list[dict]:
    stream_in = io.BufferedReader(io.BytesIO(b"".join(requests)))
    stream_out = io.StringIO()
    _serve(
        stream_in,
        stream_out,
        default_root=default_root,
        host_tool=host_tool,
        host_integration=host_integration,
    )
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
    assert {"lwm_context", "lwm_retain", "lwm_recall", "lwm_handoff", "lwm_coverage", "lwm_health"} <= names
    record_receipt = next(
        tool for tool in responses[0]["result"]["tools"] if tool["name"] == "record_receipt"
    )
    assert record_receipt["inputSchema"]["properties"]["source"]["enum"] == [
        "cli-context",
        "explicit-smoke",
        "file-probe",
        "watcher-observed",
    ]


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


def test_record_event_fills_schema_defaults_for_sparse_payload(tmp_path: Path) -> None:
    response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "record_event",
                    "arguments": {
                        "root": str(tmp_path),
                        "event": {
                            "tool": "shell",
                            "project_path": str(tmp_path),
                            "event_type": "workflow_observation",
                        },
                    },
                },
                id_=30,
            )
        ],
    )[0]

    assert response["result"]["content"][0]["data"]["ingested"] is True


def test_mcp_uses_the_server_default_root_when_call_omits_root(tmp_path: Path) -> None:
    response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "record_event",
                    "arguments": {
                        "event": {
                            "tool": "minimax",
                            "project_path": str(tmp_path),
                            "event_type": "workflow_observation",
                            "task": "default root smoke",
                        }
                    },
                },
                id_=31,
            )
        ],
        default_root=tmp_path,
    )[0]

    assert response["result"]["content"][0]["data"]["ingested"] is True
    assert list((tmp_path / "raw" / "events" / "inbox").rglob("*.json"))


def test_canonical_mcp_writes_are_explicit_observations(tmp_path: Path) -> None:
    event = {
        "tool": "minimax",
        "project_path": str(tmp_path),
        "event_type": "decision",
        "task": "canonical MCP observation",
        "decisions": ["keep the source explicit"],
    }
    response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "lwm_retain",
                    "arguments": {"root": str(tmp_path), "event": event},
                },
                id_=32,
            )
        ],
    )[0]

    assert response["result"]["content"][0]["data"]["ingested"] is True
    from lwm.capabilities import load

    receipt = load(tmp_path)["minimax"]
    assert receipt["source"] == "watcher-observed"
    assert receipt["status"] == "observed"


def test_registered_minimax_mcp_bridge_records_bounded_proof(tmp_path: Path) -> None:
    from lwm.capability_proof import capability_status, latest_proof_receipts
    from lwm.project_id import record_project

    project_id = record_project(tmp_path, tmp_path).project_id
    _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "query_context",
                    "arguments": {
                        "root": str(tmp_path),
                        "tool": "minimax",
                        "project": str(tmp_path),
                    },
                },
                id_=33,
            )
        ],
        host_tool="minimax",
        host_integration="minimax-mcp",
    )
    _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "lwm_retain",
                    "arguments": {
                        "root": str(tmp_path),
                        "event": {
                            "tool": "minimax",
                            "project_path": str(tmp_path),
                            "project_id": project_id,
                            "event_type": "workflow_observation",
                            "task": "bounded bridge proof",
                        },
                    },
                },
                id_=34,
            )
        ],
        host_tool="minimax",
        host_integration="minimax-mcp",
    )

    read, write = latest_proof_receipts(
        tmp_path, tool="minimax", expected_project_id=project_id
    )
    assert read is not None
    assert write is not None
    assert capability_status(
        read_receipt=read,
        write_receipt=write,
        expected_project_id=project_id,
    ) == "verified_bidirectional"
    assert {read.source, write.source} == {"mcp-bridge"}
    for receipt in (read, write):
        evidence = tmp_path / receipt.evidence_path
        assert receipt.status == "verified"
        assert evidence.is_file()
        body = json.loads(evidence.read_text(encoding="utf-8"))
        assert body["integration"] == "minimax-mcp"
        assert set(body) <= {
            "schema_version",
            "tool",
            "integration",
            "direction",
            "project_id",
            "operation",
            "operation_id",
            "event_id",
        }
        assert not any(key in body for key in ("prompt", "transcript", "model"))


def test_unbound_or_mismatched_mcp_stays_observation_only(tmp_path: Path) -> None:
    event = {
        "tool": "minimax",
        "project_path": str(tmp_path),
        "event_type": "workflow_observation",
        "task": "unbound bridge attempt",
    }
    _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "lwm_retain",
                    "arguments": {"root": str(tmp_path), "event": event},
                },
                id_=35,
            )
        ],
    )
    _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "lwm_retain",
                    "arguments": {"root": str(tmp_path), "event": event},
                },
                id_=36,
            )
        ],
        host_tool="minimax",
        host_integration="wrong-integration",
    )

    from lwm.capability_proof import load

    history = load(tmp_path).get("_history", {}).get("minimax", [])
    assert history
    assert all(item.get("source") != "mcp-bridge" for item in history)
    assert all(item.get("status") == "observed" for item in history)


def test_registered_gemini_mcp_bridge_records_read_proof(tmp_path: Path) -> None:
    from lwm.capability_proof import latest_proof_receipts
    from lwm.project_id import record_project

    project_id = record_project(tmp_path, tmp_path).project_id
    response = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "query_context",
                    "arguments": {
                        "root": str(tmp_path),
                        "tool": "gemini-cli",
                        "project": str(tmp_path),
                    },
                },
                id_=37,
            )
        ],
        host_tool="gemini-cli",
        host_integration="gemini-cli-mcp",
    )[0]

    assert "result" in response
    read, write = latest_proof_receipts(
        tmp_path, tool="gemini-cli", expected_project_id=project_id
    )
    assert read is not None
    assert read.source == "mcp-bridge"
    assert read.status == "verified"
    assert write is None


def test_get_project_memory_via_mcp(tmp_path: Path) -> None:
    payload = make_event(
        tool="shell",
        project_path=str(tmp_path),
        project_id="git-mcp-2",
        event_type="decision",
        task="memory test",
        decisions=["mcp memory test"],
        verification=["smoke-ok"],
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
        event_type="decision",
        task="mcp context",
        decisions=["mcp context"],
        verification=["smoke-ok"],
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


def test_recall_via_mcp_returns_evidence_packet(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    from lwm.project_id import record_project

    project_id = record_project(tmp_path, project).project_id
    event_dir = tmp_path / "raw" / "events" / "processed" / "2026-07-18"
    event_dir.mkdir(parents=True)
    (event_dir / "event.json").write_text(
        json.dumps(
            {
                "event_id": "event-mcp-recall",
                "timestamp": "2026-07-18T12:00:00+08:00",
                "tool": "shell",
                "project_path": str(project),
                "project_id": project_id,
                "event_type": "decision",
                "importance": "project",
                "privacy": "sanitized",
                "task": "mcp evidence packet",
                "decisions": ["mcp evidence packet"],
                "verification": ["mcp test"],
            }
        ),
        encoding="utf-8",
    )
    out = _drive(
        tmp_path,
        [
            _rpc(
                "tools/call",
                params={
                    "name": "recall",
                    "arguments": {
                        "root": str(tmp_path),
                        "question": "mcp evidence packet",
                        "project": str(project),
                    },
                },
                id_=7,
            )
        ],
    )[0]["result"]["content"][0]["data"]
    assert out["packet"]["evidence"][0]["fact_id"] == "event-mcp-recall"
    assert out["scope"] == "project"


def test_parse_error_is_returned(tmp_path: Path) -> None:
    """Bad JSON should surface a -32700 parse error response."""

    response = _drive(tmp_path, [b"not-json\n"])[0]
    assert response["error"]["code"] == -32700


def test_unknown_method_returns_minus_32601(tmp_path: Path) -> None:
    response = _drive(tmp_path, [_rpc("tools/bogus", id_=1)])[0]
    assert response["error"]["code"] == -32601


def test_mcp_receipt_is_observation_only(tmp_path: Path) -> None:
    observed = _drive(
        tmp_path,
        [_rpc("tools/call", params={
            "name": "record_receipt",
            "arguments": {"root": str(tmp_path), "tool": "codex", "direction": "read"},
        }, id_=8)],
    )[0]["result"]["content"][0]["data"]
    assert observed["status"] == "observed"

    refused = _drive(
        tmp_path,
        [_rpc("tools/call", params={
            "name": "record_receipt",
            "arguments": {
                "root": str(tmp_path),
                "tool": "codex",
                "direction": "read",
                "source": "native-hook",
                "evidence_path": "raw/events/inbox/host.json",
                "operation_id": "host-read-1",
            },
        }, id_=9)],
    )[0]
    assert refused["error"]["code"] == -32602
    assert "MCP cannot write host proof receipts" in refused["error"]["message"]

    refused_bridge = _drive(
        tmp_path,
        [_rpc("tools/call", params={
            "name": "record_receipt",
            "arguments": {
                "root": str(tmp_path),
                "tool": "minimax",
                "direction": "read",
                "source": "mcp-bridge",
                "evidence_path": "state/receipts/mcp-bridge/fake.json",
                "operation_id": "fake-bridge-1",
            },
        }, id_=11)],
    )[0]
    assert refused_bridge["error"]["code"] == -32602
    assert "MCP cannot write host proof receipts" in refused_bridge["error"]["message"]

    (tmp_path / "smoke").mkdir(parents=True, exist_ok=True)
    (tmp_path / "smoke" / "read.json").write_text("read evidence\n", encoding="utf-8")
    observed_with_evidence = _drive(
        tmp_path,
        [_rpc("tools/call", params={
            "name": "record_receipt",
            "arguments": {
                "root": str(tmp_path),
                "tool": "codex",
                "direction": "read",
                "source": "file-probe",
                "evidence_path": "smoke/read.json",
                "operation_id": "probe-read-1",
            },
        }, id_=10)],
    )[0]["result"]["content"][0]["data"]
    assert observed_with_evidence["status"] == "observed"
