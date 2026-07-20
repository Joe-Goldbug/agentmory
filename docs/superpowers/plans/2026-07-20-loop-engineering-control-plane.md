# Loop Engineering Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic Loop Engineering state contract to LLM-WorkMem so each scheduled cycle records its objective, prediction, evidence, evaluation, next action, and verified exit state.

**Architecture:** Add one focused `lwm/loop_state.py` module for durable loop state and transition rules. The existing runner and supervisor will write this state around their existing cycle work; health will expose the state and closure evidence. Existing events, project state, Retain/Recall/Reflect, and receipts remain the canonical memory layers.

**Tech Stack:** Python 3.11, frozen dataclasses, JSON state files, existing pytest and Ruff suite, existing launchd runner.

## Global Constraints

- Keep one canonical memory source; loop state is control state, not a second knowledge base.
- Do not add a database, vector store, graph database, always-on LLM, or new runtime dependency.
- Preserve all existing raw evidence and unrelated user changes.
- Use test-first development for behavior changes.
- Do not claim a loop is complete without external evidence and a fresh verification command.
- A static adapter file is not proof of a live tool connection.

---

### Task 1: Add the durable LoopState contract

**Files:**
- Create: `lwm/loop_state.py`
- Test: `tests/test_loop_state.py`

**Interfaces:**
- Consumes: objective, constraints, criteria, expected result, evidence, and transition updates.
- Produces: `LoopState`, `begin_loop()`, `record_evaluation()`, `close_loop()`, `read_active()`, `read_last()`, `write_state()`.

- [ ] **Step 1: Write failing tests for the four exit states**

```python
from pathlib import Path

from lwm.loop_state import begin_loop, close_loop, read_last, record_evaluation, write_state


def test_loop_round_trip_records_prediction_evidence_and_verified_completion(tmp_path: Path) -> None:
    state = begin_loop(
        "scheduled memory refresh",
        constraints=("one bounded cycle",),
        success_criteria=("audit passes", "health passes"),
        expected_observation="fresh source and runtime inputs",
        expected_outcome="updated export with a successful audit",
    )
    state = record_evaluation(
        state,
        actual_observation="audit=ok; health=healthy",
        actual_outcome="export updated",
        evidence=("state/last-cycle.json", "state/health.json"),
        criteria_met=True,
        next_action="",
    )
    state = close_loop(state, exit_state="completed_verified", human_gate=False)
    write_state(tmp_path, state)

    loaded = read_last(tmp_path)
    assert loaded is not None
    assert loaded.exit_state == "completed_verified"
    assert loaded.expected_outcome == "updated export with a successful audit"
    assert loaded.evidence == ("state/last-cycle.json", "state/health.json")


def test_loop_evaluation_cannot_close_as_verified_when_criteria_fail() -> None:
    state = begin_loop("refresh", success_criteria=("audit passes",))
    state = record_evaluation(
        state,
        actual_observation="audit=failed",
        actual_outcome="no verified export",
        evidence=("state/last-cycle.json",),
        criteria_met=False,
        next_action="repair audit failure",
    )
    closed = close_loop(state, exit_state="completed_verified", human_gate=False)
    assert closed.exit_state == "continue"
    assert closed.next_action == "repair audit failure"


def test_loop_can_close_as_human_required_or_blocked() -> None:
    state = begin_loop("decide ambiguous scope")
    assert close_loop(state, exit_state="human_required", human_gate=True).human_gate is True
    assert close_loop(state, exit_state="blocked", human_gate=False).exit_state == "blocked"
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_loop_state.py -q`

Expected: FAIL because `lwm.loop_state` does not exist.

- [ ] **Step 3: Implement the minimal frozen dataclass and transitions**

Implement a JSON-safe frozen dataclass with these fields: `loop_id`, `objective`, `constraints`, `success_criteria`, `phase`, `expected_observation`, `expected_outcome`, `actual_observation`, `actual_outcome`, `evidence`, `criteria_met`, `attempt`, `next_action`, `exit_state`, `human_gate`, `started_at`, and `finished_at`.

`begin_loop()` starts at `observe` with `exit_state="continue"`. `record_evaluation()` moves to `evaluate`, stores the evidence, and sets `phase="update"` when criteria are met or `phase="decompose"` when the next action remains. `close_loop()` must downgrade `completed_verified` to `continue` whenever `criteria_met` is false or evidence is empty. It must write `active-loop.json` while `exit_state="continue"` and `last-loop.json` after any terminal state.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pytest tests/test_loop_state.py -q`

Expected: all loop-state tests pass.

### Task 2: Wrap the scheduled runner with prediction and evaluation

**Files:**
- Modify: `lwm/runner.py`
- Test: `tests/test_runner_loop.py`

**Interfaces:**
- Consumes: existing `run_cycle(root)` execution and its return code.
- Produces: `state/last-loop.json` with expected/actual observations and a valid exit state.

- [ ] **Step 1: Write failing runner tests**

```python
from pathlib import Path

import lwm.runner as runner
from lwm.loop_state import read_last


def test_runner_records_verified_completion_when_cycle_and_audit_succeed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "_run_adapter", lambda *args: (0, "adapter ok"))
    monkeypatch.setattr(runner, "_sweep_shell_events", lambda root: 0)
    monkeypatch.setattr(runner, "sync_registered_projects", lambda root: {"status": "healthy", "projects": {}})
    monkeypatch.setattr(runner, "ingest_run", lambda root, with_lock=True: type("I", (), {"failed": False, "render": lambda self: "ingest ok"})())
    monkeypatch.setattr(runner, "run_watch", lambda *args, **kwargs: type("W", (), {"audit": type("A", (), {"ok": True})()})())
    monkeypatch.setattr(runner, "render_watch_report", lambda watch: "watch ok")
    monkeypatch.setattr(runner, "write_global_adapters", lambda root: None)
    monkeypatch.setattr(runner, "collect_and_write", lambda root: type("H", (), {"status": "healthy", "render": lambda self: "healthy"})())

    assert runner.run_cycle(tmp_path) == 0
    state = read_last(tmp_path)
    assert state is not None
    assert state.exit_state == "completed_verified"
    assert "audit" in state.actual_observation


def test_runner_records_human_gate_when_execution_has_no_external_proof(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "_run_adapter", lambda *args: (0, "adapter ok"))
    monkeypatch.setattr(runner, "_sweep_shell_events", lambda root: 0)
    monkeypatch.setattr(runner, "sync_registered_projects", lambda root: {"status": "healthy", "projects": {}})
    monkeypatch.setattr(runner, "ingest_run", lambda root, with_lock=True: type("I", (), {"failed": False, "render": lambda self: "ingest ok"})())
    monkeypatch.setattr(runner, "run_watch", lambda *args, **kwargs: type("W", (), {"audit": type("A", (), {"ok": True})()})())
    monkeypatch.setattr(runner, "render_watch_report", lambda watch: "watch ok")
    monkeypatch.setattr(runner, "write_global_adapters", lambda root: None)
    monkeypatch.setattr(runner, "collect_and_write", lambda root: type("H", (), {"status": "unknown", "render": lambda self: "unknown"})())

    assert runner.run_cycle(tmp_path) != 0
    state = read_last(tmp_path)
    assert state is not None
    assert state.exit_state in {"human_required", "blocked"}
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_runner_loop.py -q`

Expected: FAIL because the runner does not write loop state.

- [ ] **Step 3: Implement one bounded loop around existing runner stages**

Open a loop before adapters. Set the objective to `scheduled memory refresh`, expected observation to `all configured sources are readable`, and expected outcome to `ingest, audit, export, and health have fresh evidence`. After existing stages, build a compact actual observation from adapter return codes, CBMEM status, ingest failure, watch audit status, and health status. Use evidence paths `state/last-cycle.json`, `state/health.json`, and the current export path when they exist. Close as `completed_verified` only when the return code is zero, audit is OK, health is healthy, and at least one evidence path exists. Otherwise close as `human_required` for missing/unknown proof or `continue` for a repairable failed cycle.

- [ ] **Step 4: Run the focused tests and then the existing runner-adjacent tests**

Run: `pytest tests/test_runner_loop.py tests/test_cycle_state_v2.py tests/test_v2_control_plane.py -q`

Expected: all pass.

### Task 3: Make supervisor and health expose loop closure

**Files:**
- Modify: `lwm/supervisor.py`
- Modify: `lwm/health.py`
- Test: `tests/test_supervisor_loop.py`

**Interfaces:**
- Consumes: `LoopState` and existing cycle receipts.
- Produces: explicit `loop` section in health and a persisted `not_due` loop outcome.

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from lwm.cycle_state import finish, begin, write_receipt
from lwm.health import collect
from lwm.loop_state import read_last
from lwm import supervisor


def test_not_due_supervisor_preserves_last_full_evidence_and_records_loop(tmp_path: Path) -> None:
    previous = finish(begin("full", "due"), status="success")
    write_receipt(tmp_path, previous)
    assert supervisor.run_supervisor(tmp_path) == 0
    state = read_last(tmp_path)
    assert state is not None
    assert state.exit_state == "continue"
    assert state.next_action == "wait for the next due window"
    assert read_last(tmp_path).loop_id != previous.receipt_id


def test_health_reports_loop_exit_and_fails_strictly_for_unclosed_loop(tmp_path: Path) -> None:
    snapshot = collect(tmp_path, strict=True)
    assert snapshot.cycle["loop_exit_state"] in {"continue", "human_required", "blocked", None}
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_supervisor_loop.py -q`

Expected: FAIL because supervisor and health do not expose loop state.

- [ ] **Step 3: Implement not-due state and health projection**

When no full cycle is due, create and close a loop with `exit_state="continue"`, `next_action="wait for the next due window"`, and `human_gate=False`; do not overwrite `last-cycle.json`. Add `loop` fields to the health snapshot payload and render: active/last loop ID, phase, exit state, objective, next action, and evidence count. Strict health must treat `human_required`, `blocked`, or a missing loop as degraded/failed according to the existing strict status contract, never healthy.

- [ ] **Step 4: Run supervisor, health, and full regression tests**

Run: `pytest tests/test_supervisor_loop.py tests/test_cycle_state_v2.py tests/test_health.py tests/test_audit_health.py -q`

Expected: all pass.

### Task 4: Add closure audit and documentation

**Files:**
- Create: `lwm/closure.py`
- Modify: `lwm/health.py` only if source/runtime/export checks belong in the health projection.
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Create: `docs/superpowers/specs/2026-07-20-loop-engineering-closure-checklist.md`
- Test: `tests/test_loop_closure.py`

**Interfaces:**
- Consumes: source/runtime/export paths, loop state, receipts, health, and launchd status.
- Produces: deterministic closure checklist with `pass`, `degraded`, or `blocked` per condition.

- [ ] **Step 1: Write failing closure tests**

```python
from pathlib import Path

from lwm.loop_state import begin_loop, close_loop, write_state
from lwm.closure import check_closure


def test_closure_blocks_when_loop_is_not_verified(tmp_path: Path) -> None:
    state = close_loop(begin_loop("refresh"), exit_state="human_required", human_gate=True)
    write_state(tmp_path, state)
    report = check_closure(tmp_path, source_root=tmp_path, runtime_root=tmp_path)
    assert report.status == "blocked"
    assert "loop" in report.failed_checks


def test_closure_accepts_verified_loop_with_fresh_local_evidence(tmp_path: Path) -> None:
    (tmp_path / "llms.txt").write_text("# context\n", encoding="utf-8")
    state = begin_loop("refresh", success_criteria=("evidence exists",))
    state = state.__class__(**{**state.__dict__, "evidence": ("llms.txt",), "actual_outcome": "fresh"})
    state = close_loop(state, exit_state="completed_verified", human_gate=False)
    write_state(tmp_path, state)
    report = check_closure(tmp_path, source_root=tmp_path, runtime_root=tmp_path)
    assert report.status == "pass"
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_loop_closure.py -q`

Expected: FAIL because `lwm.closure` does not exist.

- [ ] **Step 3: Implement deterministic closure checks**

Create `lwm/closure.py` with `ClosureReport(status, checks, failed_checks)`. Check loop terminal state, evidence existence, source readability, runtime importability, export existence/freshness, latest successful full receipt, strict health, and launchd presence. A check may be `degraded` when the platform cannot be probed, but the overall status is `pass` only when every required check passes. Use explicit paths and never infer freshness from a stale generated file.

- [ ] **Step 4: Document the loop and closure contract**

Add the five-step loop to both READMEs and document that `completed_verified` requires external proof. Add the command contract and report fields to `docs/superpowers/specs/2026-07-20-loop-engineering-closure-checklist.md`.

- [ ] **Step 5: Run the full verification bundle**

Run:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/uv-venv uv run --extra dev ruff check .
UV_CACHE_DIR=/private/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/uv-venv uv run --extra dev pytest -q
```

Expected: Ruff exits 0 and pytest reports zero failures.

### Task 5: Execute real closure verification

**Files:**
- No source edits unless a verification failure identifies a root cause.
- Output: `state/last-loop.json`, `state/health.json`, and the closure report.

- [ ] **Step 1: Run the focused loop smoke test**

Run the installed runtime cycle once and capture its complete output.

- [ ] **Step 2: Inspect launchd truth**

Check the exact active labels, `launchctl print`, interval, runner path, latest output/error log times, and latest receipt.

- [ ] **Step 3: Run strict health and closure**

Run the health and closure commands against the actual runtime root, not only the iCloud source path.

- [ ] **Step 4: Report every acceptance criterion separately**

Report only evidence-backed `pass`, `degraded`, or `blocked` results. Do not translate a configured file into an active connection.
