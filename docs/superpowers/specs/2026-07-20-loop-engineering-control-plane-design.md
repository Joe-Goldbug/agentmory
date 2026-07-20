# Loop Engineering Control Plane Design

- Date: 2026-07-20
- Status: approved direction; implementation follows in this task
- Scope: LLM-WorkMem control-plane loop and final closure verification

## Goal

Make LLM-WorkMem execute one bounded, source-backed work loop at a time. Each
loop must define its objective, predict the expected result, perform an action,
compare the actual evidence with the prediction, update canonical state, and
choose a verifiable exit state.

This absorbs the useful parts of the supplied Loop Engineering image without
adding a second memory system or a permanently running LLM.

## Current Evidence and Root Cause

- The repository already has `cycle_state`, `supervisor`, `runner`, `health`,
  Retain/Recall/Reflect, project state, and tool receipts.
- The current cycle receipt records timing and ingest counts, but it does not
  record the current objective, expected result, actual result, next action, or
  an explicit exit gate.
- The supervisor can decide whether a 12-hour cycle is due, but it cannot
  distinguish a verified completion from a failed or incomplete loop at the
  control-plane level.
- The generated export and iCloud source/runtime copies can drift. Therefore
  source readability, export freshness, and runtime execution must be explicit
  closure checks.

## Design

### 1. Loop Contract

Add a small deterministic `LoopState` contract with these fields:

- `loop_id`
- `objective`
- `constraints`
- `success_criteria`
- `phase`
- `expected_observation`
- `expected_outcome`
- `actual_observation`
- `actual_outcome`
- `evidence`
- `criteria_met`
- `attempt`
- `next_action`
- `exit_state`
- `human_gate`
- timestamps

The phase sequence is:

`observe -> define -> decompose -> execute -> evaluate -> update`

The exit states are:

`continue`, `completed_verified`, `human_required`, `blocked`.

The contract is JSON and lives at `state/active-loop.json` while active and
`state/last-loop.json` after closure. It is control state, not a second memory
source. Durable facts continue to live in events, project `STATE.md`,
`GLOBAL.md`, and approved wiki pages.

### 2. Prediction and Evaluation

Before execution, the runner records an expected observation and expected
outcome. After execution it records:

- the actual observation from command output, audit, health, or receipt;
- whether success criteria were met;
- the evidence paths or receipt IDs;
- the next action when the loop is not complete.

No LLM is required. The initial runner uses deterministic evidence such as
exit codes, audit status, health status, receipt status, and output freshness.

### 3. Human Feedback Gate

The loop automatically continues for low-risk deterministic work. It sets
`human_required` when the objective is ambiguous, evidence conflicts, the
scope must expand, a destructive/security/deployment decision is involved, or
the final result lacks an external proof signal. This is the human-side loop
from the image translated into an explicit machine state.

### 4. Deferred Decoding

Intermediate loop state stays compact and structured. The runner does not
generate a long synthesis after every adapter or command. Human-readable
detail is rendered only by `context`, `recall`, `health`, or the final closure
report. This preserves token budget and keeps `llms.txt` useful to agents.

### 5. Closure Gate

The final closure command must check all of the following:

1. source package is readable;
2. runtime package is present and imports successfully;
3. export files are newer than the latest meaningful source/event change;
4. the active loop is closed with `completed_verified`;
5. the latest full receipt is successful;
6. strict health is healthy, not merely configured;
7. launchd is loaded and has a recent successful run;
8. tests and lint pass.

Any missing condition yields `human_required` or `blocked`, never a success
claim.

## File Boundary

- Create `lwm/loop_state.py` for the immutable contract and transitions.
- Modify `lwm/runner.py` to open, evaluate, and close one scheduled loop.
- Modify `lwm/supervisor.py` to preserve `not_due` as an explicit loop outcome.
- Modify `lwm/health.py` to expose loop exit state and closure evidence.
- Modify `lwm/context.py` only if the loop summary is absent from the compact
  agent context.
- Add focused tests for state transitions, prediction/evaluation, and closure
  blocking.

## Non-Goals

- no database, vector store, graph database, or always-on LLM;
- no complete chat capture from every IDE;
- no automatic promotion of every observation into global rules;
- no deletion or migration of existing raw evidence;
- no claim that a static adapter file proves a live IDE read/write connection.

## Acceptance Criteria

- A scheduled full cycle leaves a structured loop state with objective,
  expected outcome, actual outcome, evidence, and exit state.
- A cycle with failed audit or health cannot close as `completed_verified`.
- A cycle with no due work leaves a successful `continue`/`not_due` state and
  does not overwrite the previous full-cycle evidence.
- An unreadable source/runtime package is visible as a blocking health issue.
- The loop state survives process restart through JSON round-trip.
- Existing tests remain green and new tests prove each exit path.
