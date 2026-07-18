# LLM-WorkMem Evidence Recall B2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade LLM-WorkMem Recall from page matching into a project-scoped, source-backed evidence packet while keeping the current file-based system and CLI surface.

**Architecture:** Add two focused modules: `lwm/evidence.py` owns immutable evidence records, state arbitration, deduplication, and packet serialization; `lwm/recall.py` owns deterministic planning, event/page retrieval, ledger construction, and coverage checks. Existing query, project memory, CBMEM, adapters, CLI, and MCP remain the surrounding interfaces.

**Tech Stack:** Python 3.11, existing dataclasses, JSON events, Markdown project pages, existing deterministic query engine, Typer CLI, pytest, Ruff. No new runtime dependency or database.

## Global Constraints

- Preserve `AGENTS.md`, `GLOBAL.md`, project state, raw events, and generated views as the existing information ownership model.
- Project ID is the isolation boundary; tool name is only provenance.
- Do not add PostgreSQL, pgvector, Neo4j, Chroma, Docker, a second memory repository, or an always-on LLM service.
- LLM-WorkMem returns source-backed evidence; the active IDE or Shell agent produces the final answer.
- Receipt and trace writes are best-effort and must never block Context or Recall.
- Never delete or rewrite existing raw events or unrelated user changes.
- Use deterministic tests with a fixed `now` and timezone for relative-date behavior.

---

### Task 1: Add the evidence data contract and deterministic state rules

**Files:**
- Create: `lwm/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: processed event dictionaries and optional wiki query hits.
- Produces: `EvidenceItem`, `EvidenceLedger`, `EvidenceCoverage`, `build_evidence_item()`, `deduplicate_evidence()`, `arbitrate_state()`, `render_evidence_json()`.

- [ ] **Step 1: Write the failing tests**

Add tests covering:

```python
def test_current_fact_supersedes_historical_fact():
    old = build_evidence_item({"fact_id": "old", "statement": "old", "valid_to": "2026-07-18T00:00:00+08:00"})
    new = build_evidence_item({"fact_id": "new", "statement": "new", "valid_to": None, "verification": ["ok"]})
    ledger = arbitrate_state([old, new])
    assert ledger[0].state == "current"
    assert ledger[0].fact_id == "new"

def test_conflicting_current_facts_are_not_silently_selected():
    left = build_evidence_item({"fact_id": "left", "statement": "A", "valid_to": None})
    right = build_evidence_item({"fact_id": "right", "statement": "B", "valid_to": None})
    ledger = arbitrate_state([left, right])
    assert {item.state for item in ledger} == {"conflicted"}

def test_duplicate_evidence_is_removed_by_fact_id_and_dedup_key():
    first = build_evidence_item({"fact_id": "same", "statement": "fact"})
    second = build_evidence_item({"fact_id": "same", "statement": "fact"})
    assert len(deduplicate_evidence([first, second])) == 1
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_evidence.py -q`

Expected: FAIL because `lwm.evidence` does not yet exist.

- [ ] **Step 3: Implement the minimal immutable data contract**

Use frozen dataclasses. `EvidenceItem` must contain `fact_id`, `project_id`, `fact_type`, `statement`, `observed_at`, `valid_from`, `valid_to`, `state`, `source_event_ids`, `source_paths`, `verification`, `confidence`, `supersedes`, and `retrieval_reasons`. Default missing timestamps to an empty string and default missing confidence to `0.5`; do not infer verification.

Implement state rules in this order:

1. `valid_to` present means `historical` unless the item is explicitly `conflicted`.
2. Two current items with different normalized statements are both `conflicted`.
3. A current item with verification outranks an unverified current item only when their statements agree.
4. `supersedes` marks the referenced item historical but never deletes it.
5. Items without enough metadata remain `unverified`.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pytest tests/test_evidence.py -q`

Expected: all evidence contract tests pass.

- [ ] **Step 5: Commit the isolated evidence contract**

Run: `git add lwm/evidence.py tests/test_evidence.py && git commit -m "feat: add evidence ledger contract"`

### Task 2: Implement deterministic Recall planning and packet construction

**Files:**
- Create: `lwm/recall.py`
- Modify: `lwm/query.py:59-76,293-363` only where the existing plan needs to expose normalized dimensions.
- Test: `tests/test_recall_packet.py`

**Interfaces:**
- Consumes: `root`, question, optional project path, limit, mode, fixed `now`, and existing `run_query()` results.
- Produces: `RecallPacket`, `plan_question()`, `build_recall_packet()`, `render_recall_packet()`.

- [ ] **Step 1: Write the failing tests**

Add tests for project isolation, current-state selection, relative time, conflict visibility, code-dimension selection, and explicit missing coverage:

```python
FIXED_NOW = datetime.fromisoformat("2026-07-19T12:00:00+08:00")

def seed_project_event(root, project_path, project_id, statement, verification=None):
    event = {
        "schema_version": 2,
        "event_id": f"event-{project_id}-{statement}",
        "timestamp": "2026-07-18T12:00:00+08:00",
        "tool": "shell",
        "project_path": str(project_path),
        "project_id": project_id,
        "event_type": "verification" if verification else "decision",
        "task": statement,
        "decisions": [statement],
        "changes": [],
        "verification": verification or [],
        "open_questions": [],
        "source": {"kind": "test"},
        "privacy": "sanitized",
    }
    path = root / "raw" / "events" / "processed" / "2026-07-18"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{event['event_id']}.json").write_text(json.dumps(event), encoding="utf-8")

def test_plan_detects_current_timeline_and_verification():
    plan = plan_question("当前项目上周什么时候完成验证？", now=FIXED_NOW)
    assert plan.dimensions == ("current_state", "timeline", "verification", "project")
    assert plan.time_window == ("2026-07-12", "2026-07-18")

def test_packet_does_not_return_another_project(tmp_path):
    project_a = tmp_path / "project-a"
    project_a.mkdir()
    seed_project_event(tmp_path, project_a, project_id="git-a", statement="B2 决策")
    packet = build_recall_packet(tmp_path, "B2 决策", project_path=str(project_a), now=FIXED_NOW)
    assert all(item.project_id == "git-a" for item in packet.evidence)

def test_packet_marks_missing_verification_as_partial(tmp_path):
    project_a = tmp_path / "project-a"
    project_a.mkdir()
    seed_project_event(tmp_path, project_a, project_id="git-a", statement="planned only")
    packet = build_recall_packet(tmp_path, "是否完成验证？", project_path=str(project_a), now=FIXED_NOW)
    assert packet.coverage in {"partial", "insufficient"}
    assert packet.missing
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_recall_packet.py -q`

Expected: FAIL because the packet API does not exist.

- [ ] **Step 3: Implement the planner**

`plan_question(question, now, timezone_name)` returns dimensions from the fixed list `current_state`, `timeline`, `decision`, `verification`, `conflict`, `cross_project`, `code`, and `project`. Always include `project` when a project path is supplied. Resolve `昨天`, `上周`, `最近`, `when`, and `latest` using the supplied `now`; never use file modification time.

- [ ] **Step 4: Implement retrieval and ledger construction**

`build_recall_packet()` must:

1. Resolve the project ID from the supplied project path.
2. Load only processed events matching that project ID, plus global pages when the question requests cross-project context.
3. Convert event evidence into `EvidenceItem` objects.
4. Run the existing deterministic wiki query with the same project filter; use page hits only as supporting evidence, not as the sole answer.
5. Call CBMEM only when `code` is in the plan and keep a failure warning instead of raising.
6. Deduplicate, arbitrate current/history/conflict state, sort stably, and cap the requested limit.
7. Set `coverage` to `complete`, `partial`, or `insufficient` based on plan dimensions and source presence.

- [ ] **Step 5: Run focused tests and a manual JSON check**

Run: `pytest tests/test_recall_packet.py -q`

Then run:

```bash
lwm hub recall "B2 为什么选择轻量证据召回层？" --project "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem" "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
```

Expected: JSON contains `project_id`, `plan`, `evidence`, `coverage`, and source paths; it must not return an unrelated project as the top evidence.

- [ ] **Step 6: Commit the packet implementation**

Run: `git add lwm/recall.py lwm/query.py tests/test_recall_packet.py && git commit -m "feat: build project-scoped recall packets"`

### Task 3: Wire project-scoped packets into the public memory API

**Files:**
- Modify: `lwm/memory_api.py:47-59`
- Modify: `lwm/context.py` project resolution and output sections
- Test: `tests/test_memory_api_recall.py`, `tests/test_context.py`

**Interfaces:**
- Consumes: `build_recall_packet()`.
- Produces: backward-compatible `hits` plus `packet`, `scope`, `coverage`, and `warnings` in `lwm.memory_api.recall()`; Context auto-detects cwd project.

- [ ] **Step 1: Write tests for the public contract**

Assert that `memory_api.recall()` preserves `question`, `project_path`, `mode`, `hits`, and `notes`, while adding `packet`, `scope`, `coverage`, and `warnings`. Add a context test showing a supplied project path returns the project packet and a missing project returns an explicit `global-only` marker.

- [ ] **Step 2: Run the tests and verify the old implementation fails the new assertions**

Run: `pytest tests/test_memory_api_recall.py tests/test_context.py -q`

Expected: new packet and scope assertions fail.

- [ ] **Step 3: Wire the packet without removing legacy fields**

Call `build_recall_packet()` from `memory_api.recall()`. Return the packet as JSON-safe dictionaries. Pass `project_path` through to query and packet construction. In Context, when no project path is explicitly provided, use the caller cwd only if it resolves to a registered project; otherwise return global-only context with a warning.

- [ ] **Step 4: Run focused and regression tests**

Run: `pytest tests/test_memory_api_recall.py tests/test_context.py tests/test_query_recall.py -q`

Expected: all pass, including the existing legacy hit assertions.

- [ ] **Step 5: Commit the API integration**

Run: `git add lwm/memory_api.py lwm/context.py tests/test_memory_api_recall.py tests/test_context.py && git commit -m "feat: expose evidence packets through memory api"`

### Task 4: Make receipts and traces fail-open

**Files:**
- Modify: `lwm/capabilities.py:record`
- Modify: `lwm/central_cli.py:context_cmd`
- Modify: `mcp/lwm_server.py` only if its context/recall wrapper assumes receipt writes succeed
- Test: `tests/test_capabilities_fail_open.py`, `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: existing capability receipt calls.
- Produces: `record()` returns a status object with `status=verified|unavailable`, `error` when writes fail; callers continue returning useful Context/Recall.

- [ ] **Step 1: Write the failing test**

Monkeypatch the receipt path to raise `PermissionError`, call Context or the public API, and assert the context text still returns with a warning and no exception.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/test_capabilities_fail_open.py -q`

Expected: FAIL with the current `PermissionError` behavior.

- [ ] **Step 3: Implement best-effort receipt handling**

Catch `OSError`, `TypeError`, and JSON write errors inside the receipt boundary. Return an unavailable receipt object. Do not catch errors from the actual Context or Recall construction. The CLI and MCP response must append a warning only when the receipt write failed.

- [ ] **Step 4: Run focused and MCP tests**

Run: `pytest tests/test_capabilities_fail_open.py tests/test_mcp_server.py -q`

Expected: all pass and the receipt failure is visible as degraded metadata.

- [ ] **Step 5: Commit the fail-open boundary**

Run: `git add lwm/capabilities.py lwm/central_cli.py mcp/lwm_server.py tests/test_capabilities_fail_open.py tests/test_mcp_server.py && git commit -m "fix: keep memory reads alive when receipts fail"`

### Task 5: Stop repeated adapter events before inbox creation

**Files:**
- Modify: `lwm/memory_api.py:retain`
- Modify: `lwm/inbox.py` or existing dedup helper only if the pre-inbox key can be checked without changing raw evidence semantics
- Test: `tests/test_retain_dedup.py`

**Interfaces:**
- Consumes: existing event payload and dedup key logic.
- Produces: unchanged retain output for new events; a stable `duplicate=true` result for unchanged repeated checkpoint/session events.

- [ ] **Step 1: Write the failing test**

Call retain twice with the same tool, project, session, type, and normalized payload. Assert the second call does not create a second inbox JSON file.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/test_retain_dedup.py -q`

Expected: FAIL because both calls currently create inbox files.

- [ ] **Step 3: Implement pre-submit idempotency**

Use the existing dedup key function or extract it into a shared pure helper. Check processed, deduplicated, rejected, and inbox indexes before writing. Preserve the original event evidence and return the existing event ID/path when a duplicate is found.

- [ ] **Step 4: Run event and ingest regressions**

Run: `pytest tests/test_retain_dedup.py tests/test_dedup.py tests/test_ingest.py -q`

Expected: all pass and existing duplicate classification remains unchanged.

- [ ] **Step 5: Commit the duplicate control**

Run: `git add lwm/memory_api.py lwm/inbox.py tests/test_retain_dedup.py && git commit -m "fix: prevent repeated retain events"`

### Task 6: Upgrade evaluation from page hits to evidence coverage

**Files:**
- Modify: `lwm/eval.py`
- Modify: `tests/test_eval.py`
- Create: `tests/fixtures/recall-eval-b2.txt`

**Interfaces:**
- Consumes: question cases with expected project, fact IDs, state, and coverage.
- Produces: deterministic evaluation report with evidence recall accuracy, source coverage, conflict handling, and project isolation.

- [ ] **Step 1: Add the B2 fixture cases**

Create 18 cases across current state, timeline, decision, verification, conflict, and cross-tool handoff. Each case must specify expected project ID, expected fact ID pattern, expected coverage, and whether a conflict should be surfaced.

- [ ] **Step 2: Write failing evaluation assertions**

Add tests that reject a result with the right top page but wrong project, missing source, or wrong current/history state.

- [ ] **Step 3: Implement packet-based evaluation**

Keep the old slug matcher for compatibility, but add packet assertions. Report `fact_match`, `source_match`, `scope_match`, `coverage_match`, and `conflict_match` separately. Do not call an external model.

- [ ] **Step 4: Run evaluation and regression tests**

Run: `pytest tests/test_eval.py tests/test_query_recall.py -q`

Expected: old tests pass and B2 fixture cases report separate failure reasons.

- [ ] **Step 5: Commit the evaluation contract**

Run: `git add lwm/eval.py tests/test_eval.py tests/fixtures/recall-eval-b2.txt && git commit -m "test: evaluate evidence recall coverage"`

### Task 7: Integrate CLI/MCP output and run the full verification bundle

**Files:**
- Modify: `lwm/central_cli.py`
- Modify: `mcp/lwm_server.py`
- Modify: `README.md` and `README.zh-CN.md` with the compact usage contract
- Test: `tests/test_cli.py`, `tests/test_mcp_server.py`, `tests/test_v2_control_plane.py`

**Interfaces:**
- Consumes: public `RecallPacket` and fail-open receipt result.
- Produces: JSON and Markdown output that clearly shows scope, coverage, evidence, missing items, and warnings.

- [ ] **Step 1: Add CLI and MCP contract tests**

Assert that `lwm hub recall --project ...` returns `packet.scope`, `packet.coverage`, `packet.evidence`, and `packet.missing`, while legacy `hits` remain present. Assert MCP returns the same packet fields.

- [ ] **Step 2: Implement output wiring**

Keep command names and arguments stable. Add only optional `--mode compact|deep` and `--format json|markdown` if existing Typer parsing permits them without breaking current callers. Render unknown and conflict warnings prominently in Markdown.

- [ ] **Step 3: Update user documentation**

Document the four daily actions: session Context, meaningful Retain, explicit Recall, and scheduled Reflect. State that an adapter file is not proof of a real read/write connection.

- [ ] **Step 4: Run static and full tests**

Run:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/uv-venv uv run --extra dev ruff check .
UV_CACHE_DIR=/private/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/uv-venv uv run --extra dev pytest -q
```

Expected: Ruff passes and the full suite passes.

- [ ] **Step 5: Run real project smoke checks**

Run:

```bash
lwm hub recall "B2 为什么选择轻量证据召回层？" --project "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem" "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
lwm hub health --json --strict "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
```

Expected: the B2 decision is returned from the correct project with source paths; health reports actual receipt and cycle state without claiming unsupported tools are verified.

- [ ] **Step 6: Commit the integration and verification result**

Run: `git add lwm/central_cli.py mcp/lwm_server.py README.md README.zh-CN.md tests/test_cli.py tests/test_mcp_server.py tests/test_v2_control_plane.py && git commit -m "feat: expose verified evidence recall across tools"`

## Final review checklist

- [ ] `memory_api.recall()` filters by project ID.
- [ ] Recall returns EvidenceItem records with source paths and state.
- [ ] Current, historical, conflict, and unknown facts are distinguishable.
- [ ] Receipt failures do not block Context or Recall.
- [ ] Repeated no-change events do not create inbox noise.
- [ ] Existing Retain/Recall/Reflect, CLI, MCP, and CBMEM contracts remain compatible.
- [ ] Full Ruff, pytest, recall smoke, and strict health checks are recorded.
