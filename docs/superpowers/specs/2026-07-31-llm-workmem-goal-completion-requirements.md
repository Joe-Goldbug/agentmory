# LLM-WorkMem Goal Completion Requirements

- Date: 2026-07-31
- Status: Draft for user review
- Workflow: Requirements first
- Scope: Local multi-tool workflow and memory system architecture-level refactor
- Deployment scope: Local code and local runtime only; no cloud deployment

## 0. Document Authority

This document defines what the LLM-WorkMem goal-completion refactor must achieve.
It is a requirements specification, not an implementation plan.

After user approval, the delivery order is:

```text
approved requirements
-> high-level design (HLD)
-> low-level design (LLD)
-> implementation plan
-> code changes
-> migration preview
-> explicit migration approval
-> local runtime cutover and verification
```

The existing file
`docs/superpowers/plans/2026-07-31-llm-workmem-goal-completion.md`
is implementation input only. It must not be executed until it is regenerated
from this approved requirements specification and the later HLD/LLD.

If this document conflicts with an older LLM-WorkMem design or implementation
plan, the conflict must be recorded in the HLD. The implementation must not
silently choose one side.

## 1. Problem Statement

LLM-WorkMem is intended to be Ethan's unified local behavior, workflow, and
memory interface across IDEs and shell-launched CLI tools. It must
automatically collect meaningful work evidence from registered local tools,
organize that evidence into project memory, reusable workflows, relationships,
and open loops, then return a bounded shared context to every supported tool
when work starts or moves between tools.

The target loop is:

```text
local IDE / shell CLI activity
-> automatic registered-source capture
-> sanitize, deduplicate, and classify
-> organize project memory and reusable workflow knowledge
-> optional LLM analysis of relationships and conflicts
-> bounded behavior + project + handoff context
-> inject or expose context to every supported IDE / CLI
-> verified work returns as new evidence
```

The current implementation has useful Retain, Recall, Reflect, event, adapter,
audit, health, and launchd components, but this end-to-end product loop is not
yet complete.

The verified gaps are:

1. Two independent launchd jobs can write memory and state, so there is no
   single scheduled writer or stable migration baseline.
2. The advertised environment API provider is a non-functional stub; there is
   no bounded LLM analysis capability for conflicts, recurring evidence, or
   candidate synthesis.
3. A single adapter or optional CBMEM failure can fail the whole scheduled
   cycle.
4. The existing overwrite-style `CycleReceipt` is incompatible with the
   immutable, source-level audit evidence needed by the target system.
5. Several affected tests are absent from the existing implementation plan,
   which makes the plan's file boundary incomplete.
6. The active runtime contains unregistered executable, state, anomaly, and
   generated-artifact paths.
7. The live data root contains unregistered generated artifacts, cursor state,
   migration residue, and adapter output.
8. The active scheduled jobs continuously change the data while hashes and
   migration manifests are being prepared.
9. The requirements do not yet make automatic collection coverage across all
   registered IDE and CLI tools a P0 product capability.
10. The requirements do not yet require startup context injection, cross-tool
    handoff, and proven reverse delivery to every supported tool.
11. The phrase "auxiliary evidence only" does not distinguish memory authority
    from the user-owned cross-tool behavior contract and can therefore
    understate the unified behavior-interface goal.

The refactor must close these gaps without turning LLM-WorkMem into a second
answering agent, a platform-level instruction override, a full conversation
archive, or an unbounded LLM service.

## 2. Verified Baseline

The following are verified facts as of 2026-07-31 and must be rechecked
immediately before implementation because runtime state can drift.

| ID | Verified fact | Requirement consequence |
| --- | --- | --- |
| B-01 | `com.ethan.lwm.harvest` is loaded and runs every 900 seconds. Its last observed exit code is 1. | Migration baselines are unstable until this job is paused. |
| B-02 | `com.ethan.lwm.dream` is loaded and runs at 03:00. Its last observed exit code is 0. | Both jobs, not only harvest, must be included in the freeze gate. |
| B-03 | `lwm-dream.sh` invokes the same editable `LWM_BIN`, runs ingest, health, insights, and auto-promote, and writes `wiki/daily`. | Dream is a second memory writer and must not remain an independent authority. |
| B-04 | Runtime Python imports `lwm` from the iCloud source checkout through an editable install. | Source edits are live runtime edits until the jobs are paused and the runtime is replaced. |
| B-05 | `EnvApiProvider.complete()` and `classify()` raise `NotImplementedError`. | A real provider contract and implementation are required for the LLM goal. |
| B-06 | `_run_cycle_stages()` ORs adapter, shell sweep, optional CBMEM, audit, and health failures into one process exit code. | Per-source failure isolation and core-failure semantics are required. |
| B-07 | `CycleReceipt` already exists with a small v1 shape and overwrites `last-<kind>.json`. | The target receipt requires an explicit backward-compatible v1-to-v2 migration. |
| B-08 | `reflect_project()` renders directly from all processed project events. | Durable admission must be applied before derived project memory is rendered. |
| B-09 | Insight candidates can be generated from recurring tags and auto-promoted into `wiki/global`. | Candidate generation and promotion must consume admitted evidence and stable claim identity only. |
| B-10 | CBMEM state participates in strict background health. | CBMEM must become optional, on-demand code evidence rather than a core cycle dependency. |
| B-11 | The runtime contains `app/`, `bin/`, `item/`, `llm-workmem/`, `logs/`, and a separate top-level `state/`. | All current physical entities require an ownership and migration decision. |
| B-12 | `DATA_ROOT` also contains `knowledge-digest.*`, `state.pre-link/`, `adapters/`, `lwm-sources.json`, and `.lwm-*-state.json`. | Backup, rollback, allowed-path, and ownership manifests must include these paths. |
| B-13 | Current project/global memory includes lifecycle and command/instruction noise. | Durable admission, deterministic rebuild, and promotion filtering are required. |
| B-14 | `watcher-observed` can currently count as native integration proof. | Capability status must distinguish observation from verified read/write evidence. |

## 3. Goals

### 3.1 Primary Goal

LLM-WorkMem must become Ethan's truthful, low-noise, source-backed, locally
operated unified behavior, workflow, and memory interface that:

- automatically captures meaningful sanitized evidence from every registered
  and supported local IDE and shell-launched CLI;
- identifies the same person, project, session, and task across tools;
- organizes captured evidence into project memory, workflow patterns,
  relationships, verified changes, risks, and open loops;
- deterministically decides which evidence may enter durable memory;
- optionally uses a bounded LLM provider to analyze admitted evidence;
- never lets LLM output become durable truth without validation;
- isolates optional-source failures from the core evidence loop;
- returns the same versioned personal behavior contract plus bounded project
  and handoff context to every supported tool;
- records proof that each tool actually received and/or wrote context instead
  of assuming integration from file presence;
- runs from a self-contained local installation rather than editable iCloud
  source;
- records immutable, inspectable evidence for every scheduled cycle; and
- can be migrated and rolled back without losing raw evidence.

### 3.2 User Outcomes

The user must be able to:

- start Codex, Claude Code, OpenCode, AGY or another registered IDE/CLI and
  receive the same current personal working preferences plus the relevant
  project objective, decisions, verified changes, risks, and open questions;
- continue the same task in another tool without manually copying the previous
  conversation or reconstructing the project state;
- inspect which local tools are registered, which capture and delivery
  mechanisms they use, and whether each direction has actually been verified;
- tell which statements are verified evidence, generated analysis, unresolved
  conflict, or missing information;
- keep working when one adapter, CBMEM, or the optional LLM API is unavailable;
- inspect why a cycle, source, analysis, or promotion succeeded or failed;
- approve destructive or ownership-changing migration only after seeing an
  exact manifest and rollback package; and
- change between OpenAI-compatible cloud or local endpoints without changing
  the core memory model.

### 3.3 System Outcomes

The system must have:

- one versioned user-owned behavior contract distributed through tool-native
  adapters without duplicating independent copies;
- one registered-source coverage model for local IDEs and shell CLIs;
- one fail-open startup delivery and cross-tool handoff contract;
- one scheduled write authority;
- one physical owner for each mutable data class;
- one durable-admission contract;
- one candidate-analysis state machine;
- one health model that separates core availability, source degradation,
  analysis availability, and quality;
- one immutable receipt per cycle plus a replaceable latest pointer; and
- one approved migration path with raw-evidence preservation.

## 4. Non-Goals

This refactor must not:

- override platform, system, security, or tool-native safety rules;
- erase project-local instructions or tool-native memory;
- generate final user answers on behalf of the active agent;
- introduce a second memory repository, database, vector store, resident model,
  or always-on web service;
- archive full IDE or shell conversations by default;
- treat commands, prompts, environment dumps, lifecycle receipts, or generated
  pages as durable facts merely because text exists;
- require an external LLM API for Retain, Recall, deterministic rebuild, or
  core health;
- make cloud deployment, GitHub synchronization, or cross-Mac portable runtime
  synchronization part of this delivery;
- delete raw processed evidence;
- silently delete migration residue or anomalous paths;
- claim semantic correctness from passing unit tests alone; or
- let generated analysis overwrite human-reviewed source documents.

The unified behavior interface is not a prohibited "second instruction
authority." It is the user-owned cross-tool default contract. Platform/system
rules remain higher priority, project-local rules can specialize it, and the
current explicit user request can update the active task within those
boundaries.

## 5. Actors and Trust Boundaries

| Actor | Responsibility | Trust boundary |
| --- | --- | --- |
| User/operator | Approves requirements, provider opt-in, promotion policy, and destructive migration. | Final authority for destructive changes and global promotion. |
| Personal behavior contract | Holds Ethan's versioned cross-tool defaults for collaboration, execution, verification, memory, and handoff. | User-owned default; cannot override platform/system safety or silently replace project-local rules. |
| Native agent/tool | Receives behavior/project/handoff context and writes structured work evidence. | Remains responsible for its platform rules, tool behavior, and final answers. |
| Tool registry | Records supported tools, projects, capture methods, delivery methods, permissions, and proof state. | Coverage truth; registration does not equal verified integration. |
| Source adapter | Converts one external source into sanitized candidate events. | May fail independently; cannot decide global cycle success. |
| Deterministic core | Sanitizes, deduplicates, classifies, stores, rebuilds, retrieves, validates, and reports. | Only component allowed to admit or reject durable evidence. |
| Memory Compiler | Coordinates optional LLM analysis over bounded admitted evidence. | Produces candidates, never durable truth directly. |
| LLM provider | Returns schema-constrained analysis. | Untrusted external or local dependency; output must be validated. |
| CBMEM | Supplies current code evidence on demand. | Optional evidence source, not scheduled-cycle authority. |
| Supervisor | Runs the single bounded cycle and records receipt evidence. | Single scheduled writer after cutover. |
| Audit/eval | Measures graph integrity, retrieval quality, and policy compliance. | Can lower quality status without inventing core data failure. |

## 6. Core Definitions

| Term | Definition |
| --- | --- |
| Source event | A structured event submitted by a tool or adapter before durable admission. |
| Raw evidence | Sanitized, append-only source evidence retained for provenance and rebuild. |
| Durable event | A raw event accepted by the deterministic admission contract for derived memory. |
| Operational event | Useful runtime/session evidence that must not become durable project or global memory. |
| Rejected event | Malformed, privacy-blocked, secret-bearing, or policy-prohibited input. |
| Analysis candidate | A bounded group of admitted evidence awaiting optional LLM analysis. |
| Analyzed candidate | A candidate whose provider output passed schema validation but has not yet passed memory policy. |
| Accepted candidate | An analyzed or deterministic candidate that passed evidence and policy validation. |
| Promoted memory | Accepted evidence rendered into an approved durable project/global memory target. |
| Core failure | A condition that prevents safe raw evidence preservation, all recall, or immutable cycle receipt creation. |
| Source degradation | Failure of one optional source while the core remains safe and usable. |
| Quality warning | Audit/eval failure that blocks a completion claim but does not corrupt the core evidence store. |
| Analysis pending | LLM analysis was not attempted or completed, while deterministic memory remains usable. |
| Personal behavior contract | The one human-reviewed cross-tool default describing how Ethan wants agents to collaborate, execute, verify, remember, and hand off work. |
| Registered tool | A local IDE or CLI with an explicit registry entry, identity, approved source scope, capture mechanism, and delivery mechanism. |
| Coverage status | Truthful per-tool state for discovery, capture, delivery, read proof, write proof, and freshness. |
| Startup context | The bounded behavior, project, and active-handoff packet returned when a supported tool session begins. |
| Handoff packet | A source-backed task continuation packet containing objective, state, decisions, changes, verification, risks, open questions, and next action. |

## 7. Functional Requirements

### Requirement 1: Authority and Requirements Precedence

**Priority:** P0

**User story:** As the owner, I want one explicit requirements authority so
that engineers do not implement conflicting historical designs.

#### Acceptance Criteria

1. THE system SHALL treat `GLOBAL.md` as the canonical user-owned cross-tool
   behavior contract while preserving platform/system safety rules, explicit
   current user intent, project-local specialization, and tool-native
   precedence.
2. THE approved version of this requirements document SHALL be the source for
   the new HLD, LLD, implementation plan, and acceptance matrix.
3. WHEN an older design conflicts with an approved requirement, THE HLD SHALL
   record the conflict and its resolution.
4. THE implementation SHALL NOT execute the existing 2026-07-31 implementation
   plan unchanged.
5. THE implementation completion report SHALL map every approved requirement
   ID to code, tests, and runtime evidence.

### Requirement 2: Single Scheduled Write Authority

**Priority:** P0

**User story:** As the operator, I want one bounded scheduled writer so that
memory, state, hashes, and migration manifests cannot drift through competing
jobs.

#### Acceptance Criteria

1. BEFORE any source edit or baseline hash, THE implementation workflow SHALL
   verify and pause both `com.ethan.lwm.harvest` and `com.ethan.lwm.dream`.
2. WHILE either current job remains capable of writing, THE workflow SHALL NOT
   declare the baseline frozen.
3. AFTER cutover, THE system SHALL have exactly one active scheduled authority
   for ingest, derived-memory rebuild, optional analysis, audit, health, and
   receipt creation.
4. THE legacy dream job SHALL NOT independently run ingest, health, insights,
   promotion, or write `wiki/daily`.
5. IF a daily digest remains a product requirement, THE single supervisor
   SHALL generate it as a non-authoritative derived artifact after the cycle
   receipt is committed.
6. THE implementation SHALL preserve the old job definitions in the rollback
   package until final verification succeeds.

### Requirement 3: Complete Runtime and Data Ownership Inventory

**Priority:** P0

**User story:** As the operator, I want every active path classified so that
backup, migration, rollback, and health checks operate on the real system.

#### Acceptance Criteria

1. THE HLD SHALL classify every current top-level runtime entity: `app/`,
   `bin/`, `item/`, `llm-workmem/`, `logs/`, and top-level `state/`.
2. THE HLD SHALL classify `knowledge-digest.html`,
   `knowledge-digest.pages/`, `state.pre-link/`, `adapters/`,
   `lwm-sources.json`, `.lwm-antigravity-state.json`, and
   `.lwm-minimax-state.json`.
3. THE target runtime SHALL have one physical owner for every mutable data
   class.
4. THE live data root SHALL own wiki, raw evidence, operational state,
   generated exports, adapter output, and source cursor state.
5. THE source checkout MAY expose access links but SHALL NOT contain a second
   writable copy of live data.
6. `knowledge-digest.*` SHALL be classified as rebuildable generated artifacts,
   not source evidence.
7. `state.pre-link/` and `item/` SHALL be migration archive candidates and
   SHALL NOT be deleted without manifest-bound approval.
8. THE top-level runtime dream state SHALL be migrated or archived so that it
   cannot remain a third live state owner.

### Requirement 4: Durable Evidence Admission and Deterministic Rebuild

**Priority:** P0

**User story:** As a tool user, I want long-term memory to contain meaningful
decisions and verified work rather than commands, prompts, and lifecycle noise.

#### Acceptance Criteria

1. WHEN a source event is ingested, THE deterministic core SHALL classify it as
   `durable`, `operational`, or `rejected` before derived memory rendering.
2. THE durable category SHALL require structured decision, change,
   verification, status, risk, or open-question evidence.
3. THE operational category SHALL include session lifecycle, adapter probes,
   watcher observations, and command-only activity unless accompanied by
   independently structured durable evidence.
4. THE rejected category SHALL include malformed input, secret-bearing input,
   complete instruction blocks, environment dumps, and privacy-policy
   violations.
5. THE system SHALL preserve valid sanitized raw evidence independently of
   whether it is durable or operational.
6. WHEN project memory is rebuilt from unchanged admitted events, THE output
   SHALL be byte-stable.
7. THE rebuild SHALL order evidence deterministically and retain event IDs and
   source paths.
8. THE rebuild SHALL NOT manually rewrite, synthesize, or delete processed raw
   history.
9. WHEN no durable evidence exists for a registered project, THE context output
   SHALL state that evidence is insufficient rather than render operational
   noise as project memory.

### Requirement 5: Bounded Memory Compiler

**Priority:** P0

**User story:** As the owner, I want LLM assistance for cross-event analysis
and conflict detection without allowing the model to become the source of
truth.

#### Acceptance Criteria

1. THE system SHALL provide a Memory Compiler that can create analysis
   candidates only from admitted, sanitized, bounded evidence.
2. THE Memory Compiler SHALL support recurring-pattern synthesis, conflict
   identification, context distinction, uncertainty description, and candidate
   wording.
3. THE Memory Compiler SHALL NOT infer a durable fact without supporting event
   IDs.
4. THE Memory Compiler SHALL NOT directly write `GLOBAL.md`, project pages,
   approved global pages, raw source events, or native tool instructions.
5. THE provider response SHALL be treated as untrusted input and SHALL pass
   strict schema, evidence-reference, privacy, and policy validation.
6. WHEN provider output adds unsupported facts, missing evidence IDs,
   instructions, secrets, or invalid fields, THE candidate SHALL be rejected
   or returned to retry without changing durable memory.
7. WHEN evidence conflicts, THE system SHALL preserve the conflict and context
   rather than force one averaged conclusion.
8. THE deterministic core SHALL remain fully usable when the Memory Compiler is
   disabled.

### Requirement 6: Provider-Neutral Optional LLM API

**Priority:** P0

**User story:** As the operator, I want to choose a compatible cloud or local
model endpoint without changing the memory architecture.

#### Acceptance Criteria

1. THE provider layer SHALL expose a vendor-neutral OpenAI-compatible contract.
2. THE contract SHALL support an explicitly configured MiniMax, Qwen,
   OpenAI-compatible, or local compatible endpoint.
3. THE provider SHALL be disabled by default until the user explicitly
   configures and opts in to analysis.
4. THE provider SHALL read credentials from runtime environment or an approved
   secret mechanism and SHALL NOT store credentials in source, prompts,
   receipts, logs, or wiki pages.
5. BEFORE an external request, THE system SHALL minimize and privacy-filter the
   evidence payload.
6. THE provider request SHALL have a timeout, maximum output size, and strict
   structured-output contract.
7. THE system SHALL enforce configurable per-day request or token budget.
8. THE system SHALL cache analysis by provider, model, prompt-contract version,
   and evidence hash.
9. WHEN a transient request fails, THE system SHALL use bounded retry with
   backoff and a maximum attempt count.
10. WHEN the provider is unavailable, disabled, over budget, or invalid, THE
    cycle SHALL record `analysis_pending` and continue deterministic work.

### Requirement 7: Analysis Candidate State Machine

**Priority:** P0

**User story:** As the operator, I want every LLM-assisted conclusion to have
an inspectable lifecycle so that generated text cannot silently become truth.

#### Acceptance Criteria

1. THE system SHALL support at least these states:
   `pending_analysis`, `analyzing`, `analyzed`, `accepted`, `rejected`,
   `promotion_pending`, `promoted`, `retry_wait`, and `dead_letter`.
2. EVERY state transition SHALL record candidate ID, prior state, next state,
   timestamp, reason, evidence hash, and actor.
3. ONLY valid transitions defined by the HLD SHALL be accepted.
4. RE-RUNNING the same evidence and provider contract SHALL reuse the cache or
   produce an idempotent state result.
5. AN analyzed candidate SHALL NOT be equivalent to an accepted fact.
6. AN accepted project-level synthesis SHALL retain all supporting event IDs
   and unresolved counterevidence.
7. A global candidate SHALL require the separate promotion policy before it can
   become promoted memory.
8. A rejected or dead-letter candidate SHALL remain inspectable and SHALL NOT
   alter durable memory.

### Requirement 8: Per-Source Failure Isolation

**Priority:** P0

**User story:** As the user, I want memory to remain available when one optional
tool integration fails.

#### Acceptance Criteria

1. THE cycle SHALL record source-level status independently for each adapter,
   shell sweep, CBMEM query, LLM analysis, audit, eval, export, and renderer.
2. THE supported source/stage statuses SHALL include `ok`, `warning`,
   `degraded`, `analysis_pending`, `quality_warning`, `rebuild_required`, and
   `failed_core`.
3. WHEN one adapter fails or times out, THE cycle SHALL mark that adapter
   `degraded` and continue other sources.
4. WHEN one malformed Markdown or generated artifact is encountered, THE
   system SHALL quarantine or exclude it, record `warning`, and continue when
   core evidence remains safe.
5. CBMEM unavailability SHALL NOT make the scheduled cycle exit nonzero.
6. LLM unavailability SHALL NOT make the scheduled cycle exit nonzero.
7. AUDIT or eval failure SHALL produce `quality_warning` and block a
   completion/healthy claim without falsely reporting raw-store corruption.
8. INDEX corruption SHALL trigger deterministic rebuild and
   `rebuild_required`; only an unrecoverable loss of all recall paths may
   become `failed_core`.
9. ONLY inability to safely preserve core evidence, inability to provide all
   recall paths after rebuild, or inability to commit the immutable receipt
   SHALL force a nonzero core cycle result.

### Requirement 9: Immutable Cycle Receipt v2 and Compatibility

**Priority:** P0

**User story:** As the operator, I want one immutable record per cycle so that
health and troubleshooting are based on evidence rather than the latest
overwritten status.

#### Acceptance Criteria

1. THE implementation SHALL recognize the current overwrite-style receipt as
   schema v1 rather than treating the target receipt as a brand-new concept.
2. THE new receipt SHALL use schema version 2 and a unique cycle ID.
3. THE v2 receipt SHALL include cycle identity, runtime identity, timestamps,
   core status, overall status, per-source results, per-stage results,
   quality results, analysis results, event counts, artifacts, and bounded
   errors.
4. A completed v2 receipt SHALL be written once to a cycle-specific path and
   SHALL NOT be overwritten.
5. A separate latest pointer or latest-summary file MAY be replaced atomically.
6. THE receipt reader SHALL read both v1 and v2 during the compatibility
   window.
7. EXISTING v1 receipts SHALL remain preserved or be archived through the
   approved migration; they SHALL NOT be silently rewritten.
8. IF an immutable receipt cannot be committed, THE cycle SHALL return
   `failed_core`.
9. HEALTH SHALL derive cycle truth from the receipt contract rather than
   launchd loaded state alone.

### Requirement 10: Bounded Context and Evidence Recall

**Priority:** P0

**User story:** As an active agent, I want compact relevant evidence rather than
the full memory store.

#### Acceptance Criteria

1. `lwm hub context` SHALL prefer current project durable memory, then approved
   global memory, then bounded recent operational activity.
2. CONTEXT output SHALL label durable evidence, operational activity,
   generated analysis, conflict, and missing evidence distinctly.
3. CONTEXT output SHALL enforce section and total-size budgets defined in the
   HLD.
4. CONTEXT output SHALL deduplicate normalized statements.
5. CONTEXT output SHALL exclude archived, generated-report, lifecycle,
   adapter-probe, and command-only noise from durable sections.
6. EVERY durable or analyzed statement SHALL expose evidence IDs or
   inspectable source references.
7. WHEN evidence is missing or contradictory, THE system SHALL say so instead
   of guessing.
8. CBMEM SHALL be queried on demand only when code evidence is relevant to the
   request.

### Requirement 11: Cross-Project Candidate and Promotion Integrity

**Priority:** P0

**User story:** As the owner, I want reusable global memory to represent a
real cross-project pattern rather than repeated tags or automation noise.

#### Acceptance Criteria

1. ONLY admitted durable evidence SHALL support a cross-project candidate.
2. LIFECYCLE, session, adapter, shell, and command-only tags SHALL be excluded
   from global promotion.
3. A candidate SHALL have a stable claim key independent of the number of
   supporting projects.
4. A candidate SHALL reference at least two distinct projects and qualifying
   evidence from each project.
5. A project-count change SHALL update one stable candidate rather than create
   a new numbered duplicate page.
6. LLM wording MAY clarify an eligible candidate but SHALL NOT replace its
   evidence or promotion gates.
7. GLOBAL promotion SHALL be recorded as an explicit decision with actor,
   reason, evidence IDs, and target.
8. AUTO-PROMOTION SHALL be disabled unless the approved HLD defines an
   equivalent explicit policy gate and rollback.

### Requirement 12: Truthful Tool Capability Evidence

**Priority:** P0

**User story:** As the owner, I want integration status to say what has actually
been proven.

#### Acceptance Criteria

1. CONFIGURATION presence SHALL produce no stronger status than
   `configured_unverified`.
2. WATCHER observation SHALL NOT prove a native read or write.
3. VERIFIED read or write status SHALL require a qualifying receipt with tool,
   project, operation, timestamp, and inspectable evidence.
4. VERIFIED bidirectional status SHALL require both qualifying read and write
   receipts for the same tool and project within the defined window.
5. THE capability report SHALL distinguish observation evidence from proof
   evidence.
6. EXPIRED proof SHALL lower the current status without deleting the historical
   receipt.

### Requirement 13: Self-Contained Local Runtime

**Priority:** P0

**User story:** As the operator, I want the scheduled runtime to execute the
installed package rather than partially edited iCloud source.

#### Acceptance Criteria

1. THE installed runtime SHALL use Python 3.11 or newer, consistent with the
   package contract.
2. THE scheduled executable SHALL import all `lwm` Python modules and packaged
   resources from the installed runtime application directory.
3. `sys.path`, `lwm.__file__`, and resource paths SHALL NOT resolve into
   `/Mobile Documents/`.
4. THE installed application SHALL be a versioned, rollback-capable unit
   containing environment and runtime manifest.
5. THE runtime manifest SHALL record source commit or source hash, package
   version, Python version, resource hashes, installation time, and executable
   path.
6. LIVE mutable data SHALL remain outside the versioned application unit.
7. A failed application cutover SHALL be reversible without changing raw
   evidence.
8. THE local runtime SHALL NOT require cloud deployment.

### Requirement 14: Health, Audit, Eval, and Completion Truth

**Priority:** P0

**User story:** As the user, I want health to tell me whether core memory,
optional integrations, analysis, and quality are actually working.

#### Acceptance Criteria

1. HEALTH SHALL expose separate core, sources, analysis, quality, runtime, and
   schedule sections.
2. HEALTH SHALL distinguish `healthy`, `degraded`, and `failed_core`.
3. A single source degradation or `analysis_pending` SHALL NOT become
   `failed_core`.
4. A quality warning SHALL prevent a fully healthy/completed claim until
   required audit and eval checks pass.
5. AUDIT analysis SHALL be computed once per cycle and passed to health rather
   than recomputed with weaker settings.
6. THE authoritative eval suite SHALL be packaged or otherwise version-bound
   to the installed runtime.
7. HEALTH SHALL include the immutable receipt ID and runtime identity used for
   its conclusion.
8. LOADED launchd state, configured adapters, or green unit tests alone SHALL
   NOT produce a healthy result.
9. COMPLETION SHALL require focused tests, full tests, static checks, migration
   checks, a fresh local cycle, audit, eval, health, context smoke, and recall
   smoke.

### Requirement 15: Safe Preview, Approval, Migration, and Rollback

**Priority:** P0

**User story:** As the owner, I want to see exactly what will change before any
destructive or ownership-changing operation.

#### Acceptance Criteria

1. THE migration workflow SHALL freeze both current launchd writers before
   computing baseline hashes.
2. THE preview SHALL inventory every affected source, runtime, data, symlink,
   launchd, generated, state, archive-candidate, and anomaly path.
3. THE preview SHALL record path type, physical target, size, hash where
   applicable, proposed action, expected owner, and rollback source.
4. THE rollback package SHALL preserve job definitions, application unit,
   state, generated artifacts, symlink metadata, and all paths proposed for
   archive or removal.
5. THE approval SHALL bind to the exact manifest SHA-256.
6. IF any protected path changes after preview, THE approval SHALL become
   invalid and a new preview SHALL be required.
7. THE migration SHALL be idempotent or stop safely when the observed state
   differs from the approved manifest.
8. RAW processed evidence SHALL be hash-verified before and after migration and
   SHALL NOT be deleted or rewritten.
9. `state.pre-link/`, `item/`, legacy runtime code, old job files, or generated
   artifacts SHALL NOT be removed without explicit manifest-bound approval.
10. IF any post-cutover core verification fails, THE workflow SHALL restore the
    previous application and ownership wiring using the rollback package.

### Requirement 16: Compatibility and No-Loss Guarantees

**Priority:** P0

**User story:** As the owner, I want the refactor to preserve useful history and
existing tool access while correcting false semantics.

#### Acceptance Criteria

1. THE system SHALL preserve processed raw events and qualifying source
   provenance.
2. THE system SHALL rebuild derived pages from source evidence rather than
   manually editing historical conclusions.
3. THE system SHALL keep existing supported CLI entry points compatible or
   provide explicit deprecation messages and replacement commands.
4. THE system SHALL read v1 cycle receipts during the compatibility window.
5. THE system SHALL preserve historical capability receipts while recalculating
   current truthful status.
6. THE system SHALL preserve approved global memory unless the migration
   manifest identifies a policy violation with source evidence and the user
   approves the action.
7. THE implementation SHALL update every affected existing test, including
   cycle state, health, runner loop, and project reflection behavior.
8. THE implementation SHALL add missing tests for provider calls, candidate
   transitions, source isolation, promotion integrity, single-writer runtime,
   and migration rollback.

### Requirement 17: Operator Visibility and Engineer Handoff

**Priority:** P1

**User story:** As a non-expert owner, I want engineers to report changes in
plain language with evidence so I can verify the result.

#### Acceptance Criteria

1. THE HLD SHALL explain the architecture in both technical terms and plain
   language.
2. THE LLD SHALL identify exact modules, interfaces, state schemas, file
   ownership, migration commands, and test files.
3. THE implementation plan SHALL contain no placeholders such as `TBD`,
   `TODO`, or unspecified error handling.
4. EVERY implementation task SHALL state what it changes, what it does not
   change, its focused tests, and its stop condition.
5. THE completion report SHALL show requirement-by-requirement evidence rather
   than only a summary.
6. WHEN a requirement is not verified, THE report SHALL label it `unverified`
   or `blocked` and SHALL NOT claim complete delivery.

### Requirement 18: Automatic Local IDE and CLI Collection

**Priority:** P0

**User story:** As Ethan, I want LLM-WorkMem to automatically collect
meaningful work from every registered local IDE and shell-launched CLI so that
my memory does not depend on manual note-taking.

#### Acceptance Criteria

1. THE system SHALL maintain one tool registry covering every detected or
   explicitly configured local IDE and CLI.
2. THE initial HLD audit SHALL include at least Codex, Claude Code, OpenCode,
   AGY/Antigravity, Kiro, VS Code/Cursor, Trae, MiniMax, and shell-launched
   tools that are actually present on the machine.
3. FOR every detected tool, THE registry SHALL record one of `supported`,
   `partially_supported`, `unsupported`, or `pending_integration` with a plain
   reason.
4. A supported tool SHALL declare its identity, approved source scope, project
   resolution method, capture mechanism, delivery mechanism, and permission
   boundary.
5. THE capture mechanism SHALL prefer native hooks, then explicit lifecycle or
   CLI integration, then bounded file-tail or watcher integration; it SHALL NOT
   silently scan all local files or conversations.
6. WHEN a registered IDE session or shell CLI starts, THE adapter SHALL record
   bounded operational lifecycle evidence and resolve the active project.
7. WHEN meaningful work completes, THE adapter SHALL submit structured
   objective, decision, change, verification, risk, open-question, or handoff
   evidence without requiring the user to copy it manually.
8. SESSION lifecycle, command history, and complete conversations SHALL remain
   operational or excluded unless they contain separately structured durable
   evidence.
9. A failure in one tool adapter SHALL update only that tool's coverage and
   source status.
10. THE coverage report SHALL show last capture, last successful write, capture
    freshness, current mechanism, and the reason for every coverage gap.
11. A tool SHALL NOT be described as automatically collected until a real
    source event from that tool is proven.

### Requirement 19: Reverse Context Delivery and Cross-Tool Handoff

**Priority:** P0

**User story:** As Ethan, I want every supported IDE and CLI to receive the
same relevant working context when it starts so that I can continue work
without repeating myself.

#### Acceptance Criteria

1. WHEN a supported IDE session or shell CLI starts, THE integration SHALL
   request a bounded startup context for the resolved project.
2. THE startup context SHALL include the current personal behavior contract,
   project objective, admitted decisions, verified changes, risks, open
   questions, and active handoff when available.
3. THE context SHALL be rendered for each tool's native mechanism while
   preserving the same source IDs, contract version, and semantic content.
4. DELIVERY MAY use a native hook, generated instruction pointer, MCP call,
   shell wrapper, or explicit CLI context command, but SHALL NOT create
   independently maintained copies of the behavior contract.
5. WHEN delivery exceeds its time budget or LLM-WorkMem is unavailable, THE
   tool SHALL start normally and record a truthful delivery degradation.
6. A configuration file or generated pointer SHALL NOT count as successful
   delivery without a qualifying read receipt or explicit smoke proof.
7. WHEN work moves from one tool to another, THE source tool or user SHALL be
   able to create one handoff packet and THE destination tool SHALL retrieve
   the same packet by project and active-task identity.
8. A handoff packet SHALL include objective, current state, decisions, changes,
   verification, risks, open questions, next action, evidence IDs, source tool,
   and timestamp.
9. WHEN the destination tool records new verified work, THE new evidence SHALL
   return through the same retain/admission loop and become available to later
   tools.
10. THE system SHALL prevent stale handoff packets from silently replacing a
    newer active task state.
11. EVERY supported tool SHALL have an end-to-end test proving at least one
    real read path and one real write path or SHALL remain labeled
    `partially_supported`.

### Requirement 20: Unified Personal Behavior Contract and Interface

**Priority:** P0

**User story:** As Ethan, I want all my IDE and CLI agents to work with the same
collaboration, execution, verification, and memory defaults so that switching
tools does not change how they work with me.

#### Acceptance Criteria

1. `GLOBAL.md` SHALL be the single human-reviewed canonical personal behavior
   contract for cross-tool defaults.
2. THE behavior contract SHALL cover collaboration style, truth-first
   execution, change boundaries, verification, persistence, memory write-back,
   handoff, and reporting.
3. THE behavior contract SHALL have a version and content hash exposed in every
   generated adapter and startup context.
4. GENERATED adapters SHALL contain a compact pointer and tool-specific
   integration instructions rather than divergent full copies of the contract.
5. WHEN `GLOBAL.md` changes, THE next adapter generation and startup context
   SHALL expose the new version without requiring manual edits in every tool.
6. THE system SHALL preserve and label platform/system rules, the current
   explicit user request, project-local rules, and the cross-tool default
   instead of silently merging conflicting instructions.
7. WHEN a tool cannot consume the contract through a verified mechanism, THE
   coverage report SHALL say so rather than claim behavioral consistency.
8. THE public interaction surface SHALL provide consistent Retain, Recall,
   Context, Handoff, Health, and Coverage operations across CLI, MCP, and
   generated adapters where the tool supports them.
9. THE behavior contract SHALL NOT contain changing project facts; project
   memory and active handoff SHALL remain separate scoped inputs.
10. THE user SHALL NOT need to paste the same behavior prompt into each
    supported IDE or CLI.

### Requirement 21: Workflow and Relationship Synthesis

**Priority:** P0

**User story:** As Ethan, I want collected work to become reusable workflow
knowledge and visible relationships across projects and ideas, not merely a
larger folder of passive notes.

#### Acceptance Criteria

1. THE system SHALL organize admitted evidence into distinct project memory,
   workflow candidates, cross-project relationships, verified reusable rules,
   risks, and open loops.
2. A repeated event count or recurring tag alone SHALL NOT become a workflow or
   global rule.
3. A workflow candidate SHALL describe trigger, context, action sequence,
   verification, outcome, exceptions, and supporting evidence IDs.
4. A relationship candidate SHALL identify the related projects, ideas,
   decisions, or tools and SHALL explain the evidence-backed relationship
   without inventing causation.
5. THE optional Memory Compiler MAY propose workflow and relationship
   candidates, but deterministic validation and promotion policy SHALL govern
   acceptance.
6. ACCEPTED workflow knowledge SHALL remain versioned and SHALL preserve
   counterexamples, context limits, and superseded relationships.
7. CONTEXT and Recall SHALL return relevant accepted workflows and
   relationships when they help the active task, subject to the same size and
   provenance bounds.
8. THE system SHALL distinguish a personal working preference from a
   project-specific workflow and a cross-project reusable rule.
9. WORKFLOW and relationship indexes SHALL be rebuildable from preserved
   admitted evidence and accepted promotion decisions.
10. THE user SHALL be able to inspect why two projects, ideas, or behaviors
    were linked and reject or correct the candidate.

## 8. Non-Functional Requirements

### 8.1 Privacy and Security

- External analysis is opt-in.
- Only admitted, sanitized, bounded evidence may leave the machine.
- Secrets and direct credentials must be filtered before queueing and before
  provider dispatch.
- Provider request/response logs must contain metadata and hashes, not full
  sensitive payloads.
- Provider keys must never enter Git, wiki, raw events, receipts, or generated
  exports.
- LLM output must be treated as untrusted data.

### 8.2 Reliability

- The deterministic core must remain operational without network, CBMEM, or
  LLM service.
- Every durable write must be atomic or append-only.
- Scheduled cycles must be bounded by lock, timeout, and maximum work limits.
- Retry must be bounded; poison candidates must enter dead letter rather than
  loop forever.
- A cycle must be idempotent for unchanged source evidence.

### 8.3 Performance and Cost

- Context output must remain bounded regardless of total raw-event volume.
- Provider calls must be batched or deduplicated by evidence hash.
- Daily provider budget must be configurable and enforceable before dispatch.
- The core cycle must not wait indefinitely for optional analysis.
- HLD must define measurable latency and size budgets before implementation.

### 8.4 Observability

- Every cycle, source, analysis candidate, promotion, migration, and rollback
  must have an inspectable identifier.
- Logs must identify stage, source, status, duration, and bounded error.
- Health must link to the exact cycle receipt and runtime manifest.
- Generated reports must never be counted as independent source evidence.

### 8.5 Maintainability

- Deterministic policy, provider transport, candidate state machine, rendering,
  scheduling, and health classification must have separate interfaces.
- New providers must not require changes to admission, recall, or promotion
  policy.
- New tool adapters must implement one registry contract for identity, capture,
  startup delivery, write-back, receipts, coverage, and source-level status.
- Tool-specific rendering must remain separate from canonical behavior,
  project-memory, and handoff data.
- Schema versions and prompt-contract versions must be explicit.

## 9. Required State and Status Semantics

### 9.1 Cycle Core Status

| Status | Meaning | Process result |
| --- | --- | --- |
| `success` | Core evidence loop completed and immutable receipt committed. | Zero |
| `success_with_warnings` | Core completed; one or more optional sources, analysis, or quality checks need attention. | Zero |
| `failed_core` | Safe evidence preservation, all recall, or receipt commit failed. | Nonzero |

### 9.2 Source and Stage Status

| Status | Meaning |
| --- | --- |
| `ok` | Stage/source completed as expected. |
| `warning` | Local issue excluded or quarantined; core is safe. |
| `degraded` | Optional source unavailable or incomplete. |
| `analysis_pending` | Optional LLM analysis has not completed. |
| `quality_warning` | Audit/eval policy did not pass. |
| `rebuild_required` | Derived index/state must be rebuilt from preserved source evidence. |
| `failed_core` | Core safety or availability is broken. |

### 9.3 Overall Health

| Health | Required meaning |
| --- | --- |
| `healthy` | Core, runtime identity, required quality checks, and fresh cycle evidence all pass. |
| `degraded` | Core is usable, but a source, analysis, freshness, or quality condition needs attention. |
| `failed_core` | Core evidence safety or all recall is unavailable. |

## 10. Data Ownership Requirements

The HLD must produce a final ownership map that satisfies these outcomes:

| Data class | Required owner | Authority |
| --- | --- | --- |
| Installed code and resources | Versioned runtime application | Executable, non-editable |
| Raw processed evidence | Live data root | Append-only source evidence |
| Project/global wiki | Live data root | Derived or explicitly promoted |
| Operational state and cursors | Live data root | Non-authoritative runtime state |
| Analysis queue/cache/receipts | Live data root state | Non-authoritative until accepted |
| Generated exports and digest | Live data root | Rebuildable derivative |
| Runtime diagnostics | Runtime logs | Non-authoritative |
| Source documentation and approved specs | Git checkout | Human-reviewed source |

The HLD must explicitly decide the final paths for:

- immutable cycle receipts and latest pointers;
- analysis candidates, transitions, cache, retry queue, and dead letters;
- source cursor state currently stored in top-level dot files;
- legacy dream state;
- generated digest assets;
- archived migration residue; and
- the legacy runtime code mirror.

## 11. End-to-End Acceptance Scenarios

### Scenario E2E-01: Healthy Deterministic Cycle Without LLM

1. Provider analysis is disabled.
2. Two healthy adapters and one unavailable adapter are present.
3. The core ingests and classifies events.
4. The unavailable adapter is marked degraded.
5. Project memory rebuild and context succeed.
6. The cycle commits an immutable receipt.
7. Core result is zero and overall health is degraded only for the source.

### Scenario E2E-02: LLM Analysis and Promotion Boundary

1. Admitted evidence from two projects supports a recurring claim.
2. Memory Compiler creates a candidate with evidence IDs.
3. The provider returns valid structured analysis.
4. Validator accepts the analyzed candidate.
5. No global file changes before the promotion gate.
6. Promotion records actor, reason, evidence, and one stable claim key.
7. Re-running with the same evidence does not create a duplicate page or call.

### Scenario E2E-03: Invalid LLM Output

1. Provider returns malformed JSON or an unsupported claim.
2. Validator rejects the response.
3. Candidate enters retry or rejected/dead-letter state according to policy.
4. Durable memory remains byte-identical.
5. Cycle records `analysis_pending` or warning and core result remains zero.

### Scenario E2E-04: Recoverable Index Failure

1. A derived index is corrupted.
2. Core detects corruption and records `rebuild_required`.
3. Index is rebuilt from preserved raw events.
4. Recall and context succeed.
5. Cycle does not report `failed_core`.

### Scenario E2E-05: Core Failure

1. Raw evidence cannot be safely written or immutable receipt cannot be
   committed.
2. Cycle stops the unsafe write path.
3. Receipt fallback or error evidence is emitted where safe.
4. Core result is nonzero and health is `failed_core`.
5. Optional stages do not mask the failure.

### Scenario E2E-06: Receipt Compatibility

1. State contains a historical v1 receipt.
2. New code reads it without mutation.
3. A new cycle writes a cycle-specific immutable v2 receipt.
4. Latest pointer references the v2 cycle.
5. Health renders both historical compatibility and current truth correctly.

### Scenario E2E-07: Single-Writer Cutover

1. Both legacy jobs are frozen and backed up.
2. Manifest SHA is approved.
3. Self-contained runtime is installed.
4. Exactly one scheduled job is loaded.
5. No active path invokes `lwm-dream.sh`.
6. One real scheduled cycle succeeds.
7. Restart and direct-URL-equivalent CLI entry paths use the installed package.

### Scenario E2E-08: Migration Rollback

1. A protected post-cutover check fails.
2. Rollback restores prior application, job definitions, state ownership, and
   links from the approved bundle.
3. Raw evidence hashes match the pre-migration subset.
4. Previous local runtime can run again.
5. The failed migration and rollback remain auditable.

### Scenario E2E-09: Ather Project Context

1. Ather has admitted decisions, changes, verification, or open questions.
2. `lwm hub context --tool codex --project <Ather path>` returns bounded,
   meaningful project evidence.
3. It excludes complete prompts, environment dumps, command transcripts, and
   lifecycle/global noise.
4. Every durable statement is traceable.
5. If qualifying evidence is absent, the response says so explicitly.

### Scenario E2E-10: Automatic Multi-Tool Capture

1. A registered IDE starts work in Ather and the registry resolves the tool and
   project.
2. Startup lifecycle is captured as operational evidence.
3. The tool completes a meaningful code change and verification.
4. Structured work evidence enters the shared admission loop without manual
   copying.
5. A second registered shell CLI records another verified step for the same
   project.
6. Context shows both admitted contributions with their source tools and
   evidence IDs.
7. An unavailable third adapter is reported degraded without blocking either
   successful source.

### Scenario E2E-11: Reverse Delivery and Handoff

1. Codex or another source tool creates a handoff for an active Ather task.
2. Claude Code, OpenCode, AGY, or another registered destination starts in the
   same project.
3. The destination receives the current behavior-contract version, project
   memory, and active handoff through its declared native mechanism.
4. A qualifying receipt proves the read.
5. The destination continues the task, records verification, and writes one
   structured event back.
6. A later tool receives the updated state without the user pasting the prior
   conversation.

### Scenario E2E-12: Unified Behavior Contract

1. The user updates one cross-tool behavior rule in `GLOBAL.md`.
2. Adapter generation records the new version and hash.
3. Two different supported tools receive tool-specific renderings that point
   to the same canonical contract version.
4. A project-local rule is presented separately and does not silently mutate
   the global default.
5. Both tools follow the same reporting and verification defaults within their
   native platform constraints.
6. Coverage reports any tool that did not prove receipt of the new contract.

### Scenario E2E-13: Workflow and Relationship Synthesis

1. Admitted evidence from multiple projects shows a potentially reusable
   debugging workflow.
2. Memory Compiler proposes trigger, steps, verification, outcome, exceptions,
   and evidence links.
3. A conflicting example remains attached instead of being discarded.
4. Validation accepts or rejects the workflow candidate with a reason.
5. When accepted, Recall returns the workflow for a relevant task and not for
   an unrelated task.
6. The user can inspect, correct, or supersede the relationship.

## 12. Verification Matrix

The HLD/LLD and implementation plan must include at least:

| Verification area | Required proof |
| --- | --- |
| Tool registry | Discovery, identity, project resolution, supported/partial/unsupported status, and real coverage proof |
| Automatic capture | IDE start, shell CLI start, meaningful write-back, no manual copy, per-tool failure isolation |
| Reverse delivery | Startup context, fail-open timeout, semantic parity across renderers, read proof, stale handoff protection |
| Behavior contract | One `GLOBAL.md`, version/hash propagation, project-rule separation, no divergent adapter copies |
| Workflow synthesis | Evidence-backed workflow/relationship candidates, counterexamples, correction, rebuild, relevant recall |
| Admission | Durable, operational, rejected, privacy, truncation, and deterministic rebuild tests |
| Provider | Disabled, valid response, timeout, invalid JSON, unsupported claim, redaction, budget, cache, retry tests |
| State machine | Every valid transition and every invalid transition |
| Source isolation | Adapter, shell, CBMEM, LLM, audit, eval, renderer, index, and core-store failure tests |
| Receipt migration | v1 read, v2 immutable write, latest pointer, duplicate cycle ID, commit failure |
| Promotion | blocked tags, multi-project evidence, stable key, explicit gate, no direct LLM write |
| Context | bounds, deduplication, provenance, conflict, no-evidence response, Ather smoke |
| Runtime | non-editable import, resource identity, no iCloud path, rollback unit |
| Launchd | both legacy jobs frozen before baseline and exactly one writer after cutover |
| Migration | complete inventory, SHA-bound approval, drift invalidation, dry run, rollback, raw hash preservation |
| Existing regressions | full pytest and Ruff, including cycle state, health, runner loop, and project reflection tests |
| Product truth | audit, eval, health, real local cycle, context, recall, and inspected receipt |

Known existing tests that the LLD must review explicitly:

- `tests/test_cycle_state_v2.py`
- `tests/test_health.py`
- `tests/test_runner_loop.py`
- `tests/test_v2_control_plane.py`
- `tests/test_audit_health.py`
- `tests/test_supervisor_loop.py`
- `tests/test_central_hub.py`
- capability and lifecycle adapter tests

The LLD must add coverage for currently uncovered promotion and Memory Compiler
paths.

## 13. Requirements Traceability to Verified Gaps

| Verified gap | Closing requirements |
| --- | --- |
| A. Two active jobs; incomplete freeze | R2, R15, E2E-07 |
| B. No real LLM analysis layer | R5, R6, R7, E2E-02, E2E-03 |
| C. One optional source fails whole cycle | R8, R14, E2E-01 |
| D. Existing incompatible CycleReceipt | R9, R16, E2E-06 |
| E. Incomplete affected-test inventory | R16, R17, verification matrix |
| F. Unregistered runtime entities | R3, R13, R15 |
| G. Unregistered DATA_ROOT entities | R3, R10, R15 |
| H. Continuously drifting baseline | R2, R15 |
| I. Automatic all-tool collection not explicit | R18, E2E-10 |
| J. Reverse delivery and handoff not explicit | R19, E2E-11 |
| K. Unified behavior interface understated | R1, R20, E2E-12 |
| L. Workflow/relationship product outcome implicit | R5, R11, R21, E2E-13 |

## 13.1 Traceability to the Original Product Goal

| Original goal statement | Required product capability |
| --- | --- |
| Automatically collect local IDE and CLI work | R18 plus R4 admission and R8 failure isolation |
| Organize it into workflows and memory | R4 project memory, R5 Memory Compiler, R11 promotion, and R21 synthesis |
| Return it to all IDE and CLI tools | R10 bounded context, R12 proof, and R19 startup delivery/handoff |
| Become one unified personal behavior interface | R1 authority boundary and R20 canonical behavior contract |

## 14. Requirements Gate

This requirements stage is complete only when:

1. the user approves the goals, non-goals, and 21 requirement groups;
2. the user accepts the single-writer outcome;
3. the user accepts provider-neutral optional analysis rather than a
   vendor-locked or mandatory LLM;
4. the user accepts that LLM output remains a candidate until deterministic
   validation and promotion policy pass;
5. the user accepts per-source degradation without hiding core failure;
6. the user accepts the v1-to-v2 receipt compatibility requirement;
7. the user accepts manifest-bound migration approval and no raw-evidence
   deletion; and
8. the user accepts automatic registered-tool capture, startup reverse
   delivery, and cross-tool handoff as P0 outcomes;
9. the user accepts `GLOBAL.md` as the canonical user-owned cross-tool behavior
   default without overriding platform/system safety or project-local scope;
10. the user accepts workflow and relationship synthesis as a first-class
    product outcome rather than passive note storage; and
11. no unresolved contradiction or placeholder remains.

Approval of this document does not approve source edits, launchd changes,
runtime installation, data migration, deletion, or deployment. Those actions
remain behind the HLD/LLD, implementation, and migration gates.

## 15. Known Unknowns for HLD

These are design decisions, not missing requirements:

- exact provider HTTP client and structured-output fallback behavior;
- exact prompt contract and analysis JSON schema;
- exact queue/cache/receipt file layout under live state;
- exact daily budget defaults and retry intervals;
- exact context character and section budgets;
- exact source timeout and concurrency limits;
- exact health freshness windows;
- exact initial tool registry after inspecting all locally installed IDE and
  shell CLI integrations;
- exact native capture and delivery mechanism selected for each registered
  tool;
- exact startup delivery latency budget and handoff freshness window;
- exact behavior-contract precedence rendering for each tool's native
  instruction model;
- exact workflow and relationship candidate schemas;
- exact archive retention period for migration residue;
- exact compatibility-window duration for v1 receipts; and
- whether daily digest remains as a non-authoritative product artifact.

The HLD must resolve each item with one decision and rationale. None may remain
as `TBD` in the LLD or implementation plan.
