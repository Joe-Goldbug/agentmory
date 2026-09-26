# LLM-WorkMem Requirements Verification Matrix

Date: 2026-08-16

Scope: local source code, tests, package artifacts, isolated temporary roots,
the local app runtime venv, the approved Task 9B data-owner migration, and one
manual supervisor cycle. No launchd reload or deployment was performed, and no
raw evidence was deleted; the app venv was rebuilt from the post-fix wheel with
the previous venv retained as a backup.

## Status Meaning

- `PASS-CODE`: the implementation and focused tests prove the contract in the
  source/package boundary.
- `PARTIAL-RUNTIME`: the code is present, but current live runtime or host
  evidence is still required.
- `BLOCKED-BOUNDARY`: the remaining proof requires the explicitly excluded
  runtime migration, launchd action, or real host interaction.

## Latest Local-Only Verification (2026-08-16)

- `647` source tests pass; Ruff, zsh syntax and `git diff --check` pass.
- Tool Registry v5 now exposes a read-only `host_probe` in `hub tools list` and
  `hub coverage`, alongside `configured`. The probe distinguishes executable
  availability, app-bundle presence, not-found and not-applicable. It never
  promotes a tool to verified capability; read/write status remains gated by
  real host-generated receipts.
- The refreshed non-editable runtime is
  `runtime-20260816T020548Z-aa7ee6ed`, importing from runtime `site-packages`
  with `icloud_on_path=[]`. Local discovery currently finds executables for
  Codex, Claude Code, OpenCode, Antigravity and Trae; app bundles for VS Code,
  Kiro, MiniMax and Gemini; and no Cursor host executable. This is host
  availability evidence, not bidirectional proof.
- `explicit-smoke` is observation-only even with an evidence file, and the
  public JSON bridge rejects proof-bearing requests unless the trusted host
  adapter path is used. Health capability output now declares
  `capabilities_scope=all_projects`, matching the global coverage view.
- Task 9B was applied with the current 342-entry manifest
  `/private/tmp/lwm-goal-completion-manifest-20260814T145119Z.json` and
  approval id `lwm9b-a75435dffeb58934`; ownership scope was
  `data-owner-only`. Ownership issues are `0`, and all seven mutable runtime
  entities are physical owners. No deployment, launchd reload, or raw-event
  deletion occurred.
- The one authorized manual cycle `cycle-10d657108685` completed with
  `core_status=success`, `overall_status=success`, `processed=24`,
  `rejected=64`, `failed=0`, audit `0`, eval `2/2`, and CBMEM healthy.
- The runtime was refreshed after the cycle to install the final snapshot
  redaction fix. Strict verification consequently returns
  `runtime_manifest_hash_mismatch` and `health_status:degraded`; the old
  receipt remains immutable and is not claimed as proof for the newer runtime.
  Non-strict health is healthy, but launchd is intentionally unloaded.
- Credential-shaped scanning of raw and derived pages returns `0` files after
  reversible quarantine/redaction under `/private/tmp`.

## Matrix

| Requirement | Status | Evidence | Remaining proof |
| --- | --- | --- | --- |
| R1 Authority and requirements precedence | PASS-CODE | Lean Core precedence text, approved HLD/LLD, `tests/test_goal_contract.py` | None in the code package |
| R2 Single scheduled write authority | BLOCKED-BOUNDARY | `lwm/lockfile.py` atomically guards the cycle, `lwm/harvest.py` claims `state/scheduler-owner.json` and rejects a second label, materialization retires the legacy dream script with a rollback backup, and the canonical plist now directly invokes the non-editable runtime; read-only `launchctl print` finds neither job loaded | Inspect existing launchd definitions and complete the approved single-owner cutover |
| R3 Runtime and data ownership inventory | PASS-RUNTIME | Fresh 336-entry manifest `/private/tmp/lwm-goal-completion-manifest-20260809T172857Z-task9b.json`, `apply_data_owner_migration()` returned `applied=true`, physical runtime data entities, matching repository access symlinks, and owner-root supervisor acceptance | Keep launchd pointed at the reviewed DATA_ROOT when a future reload is explicitly approved |
| R4 Durable evidence admission and deterministic rebuild | PASS-CODE | `lwm/project_memory.py`, `lwm/ingest.py`, `tests/test_truthful_core.py`, `tests/test_ingest.py` | None in the code package |
| R5 Bounded Memory Compiler | PASS-CODE | `lwm/memory_compiler.py`, explicit structured-to-analysis seeding, review/recall service, strict provider payload/state tests, supervisor optional stage | A live cycle with configured provider is optional evidence, not required for deterministic core |
| R6 Provider-neutral optional LLM API | PASS-CODE | `lwm/providers/env_api.py`, local transport/schema tests in `tests/test_central_hub.py`, compiler failure tests | Real external provider call remains opt-in and was not run |
| R7 Candidate state machine | PASS-CODE | `lwm/structured_candidates.py`, `tests/test_structured_candidates.py`; repeated synthesis preserves pending/accepted/rejected/corrected records and supports one-shot evidence iterators | None in the code package |
| R8 Per-source failure isolation | PASS-RUNTIME | Runner source/stage isolation, `tests/test_runner_loop.py`, and the real cycle with all listed source rows `ok` or `hook_only` and `0` failed stages | Future cycles should continue to prove source freshness |
| R9 Immutable Cycle Receipt v2 | PARTIAL-RUNTIME | The authorized immutable schema-v2 receipt `cycle-fd14856a63d1` was successful at cycle time and is preserved with receipt SHA-256 `84e747675d6fac31dc6e78ec90ea78b183ec8bd69d234ee67a23a5f102b391fd`; after the post-cycle lock-error fix, the non-editable runtime was rebuilt as `runtime-20260810T020309Z-aa7ee6ed` with manifest SHA-256 `3444b7991af6cfc3fd03cd8a4fc4cfdd2b3043862b12cebc21605c21c44f78f6`. Strict verification now truthfully returns `valid=false` for the old receipt with only `runtime_manifest_hash_mismatch`; no receipt was rewritten and no second cycle was run | A newly bound successful receipt requires separate authorization for another manual cycle; launchd remains intentionally unloaded |
| R10 Bounded Context and evidence recall | PASS-CODE | `lwm/context.py`, structured and accepted compiler-candidate recall tests, bridge/context tests, size and noise assertions | Verify against current runtime data after owner cutover |
| R11 Cross-project promotion integrity | PASS-CODE | `lwm/stable_promotion.py`, `hub_service.promote_analysis`, explicit evidence-id selection, rollback/audit tests, and legacy `auto_promote` fail-closed regression | User review is still required before promoting any live candidate |
| R12 Truthful tool capability evidence | PARTIAL-RUNTIME | `lwm/capability_proof.py`, host-binding tests, registry proof bindings, and the capture-event allowlist; real bidirectional receipts now prove Codex, Claude Code, OpenCode, generic shell, VS Code, Kiro and Trae. Kiro evidence is start `83ddbaca-07f2-463b-b88b-dcd91c088e5d` plus stop `a168bd59-d8f0-49fa-9f35-1eea3a1e14ec`, bound to one session and `kiro-extension`. Cursor native hooks are installed and registered as `cursor-hook`, but no real host receipt exists. Gemini CLI native hooks now use the correct omitted-matcher contract and are installed, but no real host receipt exists. Antigravity and MiniMax also have configured bridges without real host receipts. Durable verification events do not refresh capture freshness | Real host-generated read and write receipts, or an explicitly documented unsupported/observer-only boundary for the remaining hosts |
| R13 Self-contained local runtime | PASS-CODE | Current installed non-editable runtime `runtime-20260814T141000Z-aa7ee6ed`, wheel `lwm-0.1.0-py3-none-any.whl`, import from runtime `site-packages`, and `icloud_on_path=[]`; full package tests passed | A future rollback selection remains unexecuted |
| R14 Health, audit, eval, and completion truth | PARTIAL-RUNTIME | The authorized cycle itself reported core/overall `success`, health `healthy`, audit `0`, eval `2/2`, CBMEM healthy, and `0` failed stages. After the runtime rebuild, strict verification correctly reports only `runtime_manifest_hash_mismatch`; current health cannot be called fresh until a newly authorized cycle binds the new manifest. launchd is also intentionally not loaded | Do not run another cycle or reload launchd under the current authorization; perform both only under separate approval |
| R15 Safe preview, approval, migration, and rollback | PASS-RUNTIME | Fresh execution manifest `552b718f9dbaeffc4d542c645a4378c1a0262c7d3955100dd59349e0aa7859e0` with approval id `lwm9b-552b718f9dbaeffc` and archive `92d8c77de392cc4608d75c342c1d626ab0d7e359afbd7bf69f4ea100344dd376` passed preflight, backup/hash verification, owner-boundary execution, and strict cycle verification; rollback was not executed | Keep the archive and manifest paired; execute rollback only for a separately approved recovery |
| R16 Compatibility and no-loss guarantees | PASS-RUNTIME | The pre-cycle baseline contained `3,226` raw event JSON files and every pre-existing event byte remained present after ingest; `7` inbox paths moved unchanged to processed/rejected, event IDs remained unique, and sanitized verification write-backs were appended after the cycle. The current raw event set has `3,228` unique IDs. No raw event was deleted | Continue append-only raw policy and distinguish lifecycle relocation from deletion |
| R17 Operator visibility and engineer handoff | PASS-CODE | HLD/LLD, implementation plan, this matrix, code-package audit, handoff tests | Completion report must be refreshed after runtime gates |
| R18 Automatic local IDE and CLI collection | PARTIAL-RUNTIME | Versioned registry, seven ready session collectors, native/shell lifecycle mappings, and current coverage: Codex, Claude Code, OpenCode, shell, VS Code, Kiro and Trae are fresh and supported. Cursor now has installed native `sessionStart`/`sessionEnd` hooks but no capture event; Gemini CLI has corrected native lifecycle hooks but no capture event; Antigravity is stale and MiniMax has observer capture only | Generate fresh bounded source events through real host activity, or document the local-host boundary for Cursor, Gemini CLI, Antigravity and MiniMax |
| R19 Reverse Context delivery and cross-tool handoff | PARTIAL-RUNTIME | Shared JSON bridge plus real bidirectional proof for Codex, Claude Code, OpenCode, shell, VS Code, Kiro and Trae; Kiro proof is bound to `kiro-extension` and one session. Cursor has a registered native hook adapter with isolated package proof but no real host receipt. Gemini CLI has corrected native hooks plus a registered `gemini-cli-mcp` bridge but no real host receipt. Antigravity and MiniMax have configured bridges without live receipts. Simulation cannot satisfy this gate | Every remaining registered host needs real read and structured write proof, or an explicit unsupported/observer-only product boundary |
| R20 Unified personal behavior contract and interface | PARTIAL-RUNTIME | Source `GLOBAL.md` and runtime snapshot match SHA-256 `f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29`; installed runtime now reports `status=verified`, and bridge Context carries the same verified hash without the stale warning; behavior-contract tests cover matching, missing, and changed-source cases | Verify native startup/launchd delivery after a separately approved reload |
| R21 Workflow and relationship synthesis | PARTIAL-RUNTIME | Admission-gated synthesis, structured-to-analysis queue, tag-only rejection test, stable claim keys, optional compiler, explicit review/promotion tests, and no legacy auto-promotion bypass | Real multi-project durable evidence plus explicit review/promotion |

## Code-Package Verdict

The local package, derived-audit repair, behavior snapshot and approved local
data-owner migration implement the architecture and safety gates. The latest
manual supervisor cycle is healthy at the core and has an immutable receipt
bound to the current runtime manifest, and the fresh migration manifest has
valid rollback evidence. Overall health remains degraded because launchd was
not reloaded, and several host integrations still lack real bidirectional proof.
It is not truthful to call the whole LLM-WorkMem system complete yet.

The current safe claim is:

> The code package and local data owner are cut over and verified for
> preservation; the current read-only audit and core cycle are clean, but the
> unified behavior and memory interface is not yet proven healthy end-to-end
> because launchd was not reloaded and per-tool bidirectional receipts remain
> incomplete.

## Latest Local Code Correction

The Codex, Claude Code and Gemini CLI native hooks reject incomplete host
payloads without writing a receipt, preventing missing `cwd` or `session_id`
from becoming fabricated verified evidence. Full source verification is
`620 passed`; the local non-editable runtime is
`runtime-20260810T061952Z-aa7ee6ed`. Codex, Gemini CLI, Claude Code and
Antigravity native stop hooks also forward only explicitly named structured
handoff objects; ordinary prompt/task/transcript fields are ignored. This
changes failure behavior and handoff forwarding only; it does not create real
host receipts, so R12, R18, R19 and R20 remain
`PARTIAL-RUNTIME` until the real host boundary is verified or explicitly
documented as unsupported/observer-only.

The entity renderer now repairs legacy joined delimiters and fills missing
entity frontmatter without touching raw evidence. Gemini CLI is registered as
a bounded harvest source through `~/.gemini/GEMINI.md` only. After the local
harvest, schema, review and analysis issues are all `0`, eval is `2/2`, CBMEM is
`1/1`, and the audit is `OK`; this does not change the four-host bidirectional
proof gap or the intentionally unloaded launchd state.

The Antigravity native `Stop` adapter now obeys the local hook contract by
returning `{"decision":"allow"}` after the shared bridge write. Installed
runtime smoke passes, but capability remains `configured_unverified` until a
real Antigravity host event supplies the proof receipt.

The behavior-contract loader now compares a runtime snapshot with its recorded
source path. A snapshot is `verified` when the source still exists and has the
same SHA-256, and remains `stale` when the source is missing or changed. This
prevents every installed host adapter from receiving a false stale warning
while preserving fail-closed behavior for drift. The full source suite is
`622 passed`; the refreshed non-editable runtime is
`runtime-20260810T064856Z-aa7ee6ed` with `editable=false` and
`icloud_on_path=[]`.

## Latest Legacy Promotion Boundary Correction (2026-08-15)

The old `lwm/promote.py:auto_promote_all` path is now compatibility-only and
fail-closed: it records a withheld decision but cannot write `wiki/global/`.
The old `hub promote --auto` CLI returns exit code `2` and directs operators to
`hub review-analysis` plus `hub promote-analysis`. This closes the code-level
second promotion authority while preserving historical candidate and raw data.

Focused promotion/CLI/health tests passed `46`; the full source suite passed
`638`. The installed runtime smoke returned exit code `2` and wrote no files in
its isolated root. Runtime `runtime-20260815T143452Z-aa7ee6ed` imports from
non-editable `site-packages` with `icloud_on_path=[]`. This is a code/package
and local-runtime correction only; R2, R9, R12, R14, R18, R19, R20 and R21
remain subject to their documented launchd, real-host, strict-cycle or human
review boundaries.

## Latest Ingest Compatibility Boundary Correction (2026-08-15)

The public `ingest.run(..., auto_promote=True)` compatibility parameter is
explicitly observation-only and has a regression test proving that it cannot
write `wiki/global/`. Global memory remains gated by the stateful
`review-analysis` plus `promote-analysis` flow. Focused ingest/promotion/CLI
tests passed `46`; the full source suite passed `638`. Runtime
`runtime-20260815T143452Z-aa7ee6ed` is non-editable and imports without an
iCloud path. This closes a code/API bypass only and does not create real host
proof or a fresh strict cycle.

## Latest Trusted Host Propagation Correction (2026-08-15)

The VS Code-family IDE companion and OpenCode plugin now propagate
`LWM_HOST_BRIDGE=1` only to their child bridge process when they submit a
registered `ide-extension` or `native-hook` proof request. Before this fix,
the public bridge correctly rejected the request because the marker was
missing, leaving an implementation-level gap in real host proof delivery.
The server-side fail-closed policy is unchanged: direct public JSON cannot
claim native proof.

Focused companion/OpenCode/bridge tests passed `44`; the full source suite
passed `639`; Ruff and diff checks passed. Installed-runtime smoke proved
untrusted rejection and trusted `host-reported` plus `verified` receipt output
inside an isolated temporary root. Runtime
`runtime-20260815T144851Z-aa7ee6ed` is non-editable and imports without an
iCloud path. This closes an adapter wiring gap; real host activity is still
required before changing the partial runtime status for any tool.

## Latest Scheduler Single-Writer Guard (2026-08-15)

`lwm schedule` now atomically claims `state/scheduler-owner.json` inside the
canonical runtime data root. The same label is idempotent, while a different
label is rejected before a second bundle is written. Installed-runtime smoke
confirmed the rejection and made no `launchctl` invocation. This closes the
future code-level duplicate-writer path, but it cannot prove or remove an
already-loaded launchd writer; R2 therefore remains `BLOCKED-BOUNDARY` until
the separately authorized launchd inspection and cutover.

The full source suite passed `640`; scheduler-focused tests passed `20`; Ruff
and diff checks passed. Runtime `runtime-20260815T145926Z-aa7ee6ed` is
non-editable and imports without an iCloud path.

## Latest Legacy Dream Writer Retirement (2026-08-15)

Runtime materialization now backs up the historical `bin/lwm-dream.sh` and
replaces it with a fail-closed stub that exits `2`; it can no longer run
ingest, health, insights, promotion or write `wiki/daily` as an independent
authority. The existing `com.ethan.lwm.dream.plist` was not edited or loaded,
and read-only `launchctl print` found neither the dream nor harvest service in
the GUI domain. The rollback copy remains under the runtime backup directory.

The full source suite passed `641`; the retirement regression passed `2`;
shell syntax, Ruff and diff checks passed. Runtime
`runtime-20260815T151054Z-aa7ee6ed` is non-editable and imports without an
iCloud path. R2 remains a boundary until the existing plist definitions are
handled under the separately authorized launchd cutover.

## Latest Scheduler Runtime Binding Correction (2026-08-15)

The schedule generator no longer prefers the global `~/.local/bin/lwm` wrapper,
because that wrapper has a development-only source-checkout fallback when the
runtime is missing. It now prefers the concrete non-editable runtime launcher;
when that launcher is absent, it leaves the expected path in the bundle rather
than silently creating a source-import path. Regression coverage proves both
the runtime preference and the no-fallback behavior.

The existing canonical schedule was locally re-written without `--load`.
`state/scheduler-owner.json` now claims only `com.ethan.lwm.harvest`, and the
LaunchAgent plist directly invokes
`~/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm`. Read-only
launchd inspection still reports both services absent; no supervisor cycle was
run and no raw event changed during the operation. The full suite is `643
passed`; focused schedule/runtime tests are `32 passed`; Ruff and diff checks
pass. Runtime is `runtime-20260815T152311Z-aa7ee6ed`, non-editable, with no
iCloud import path. R2 remains `BLOCKED-BOUNDARY` because the actual launchd
cutover and fresh cycle are intentionally outside this authorization.

## Latest Native Host Contract Completion (2026-08-16)

Gemini CLI settings now omit the empty lifecycle matcher for `SessionStart` and
`SessionEnd`. The local installer preserves existing settings and MCP servers;
the generated commands point to the isolated non-editable runtime. Cursor now
has a merged `~/.cursor/hooks.json` with native `sessionStart` and `sessionEnd`
handlers. The Cursor adapter accepts only host-provided workspace/session
identifiers, returns context on session start, writes lifecycle receipts through
the trusted bridge, and fails open on incomplete input.

Focused native-hook, installer and registry tests passed, and the isolated
Cursor package smoke produced two receipts in a temporary root. This does not
count as real host proof. The installed runtime is
`runtime-20260816T020548Z-aa7ee6ed`; the current source suite is `647 passed`,
with Ruff, zsh syntax and `git diff --check` passing. No deployment, launchd
reload, second supervisor cycle, raw deletion, or Ather operation occurred.

The focused native-host, bridge and installer regression suite passed `62`
tests in an isolated temporary root. It proves package contracts for
Antigravity, Cursor, Gemini CLI and Codex, but intentionally does not count as
real host proof.

## Current Host Availability And Health Recheck (2026-08-16)

The installed runtime health command was run with `--no-strict` only. It
returned `status=healthy`, audit `0`, eval `2/2`, CBMEM healthy, and
`failed=0`; capability scope is `all_projects`. The last successful receipt is
still `cycle-10d657108685`, and `due=true` is expected because launchd remains
unloaded and no second supervisor cycle is authorized. This does not upgrade
the strict-cycle requirement.

The host probe currently finds executable hosts for Codex, Claude Code,
OpenCode, Antigravity (`agy`) and Trae; app bundles for VS Code, Kiro, MiniMax
and Gemini; and no Cursor host executable. Real bidirectional proof remains
available for Codex, Claude Code, OpenCode, shell, VS Code, Kiro and Trae.
Antigravity is configured with a native hook but has no live proof receipt;
Cursor, MiniMax and Gemini CLI also have no qualifying host receipt. No model
call, deployment, launchd action, second cycle, raw deletion, or Ather operation
occurred.

The separate strict health check returned `degraded` only because
`due=true` while launchd is intentionally unloaded and the last successful
receipt is historical. It did not report an audit, eval, CBMEM or source-stage
failure. This strict result remains an open completion gate and was not
overridden by the non-strict `healthy` snapshot.

The optional workflow/relationship compiler was exercised with
`hub analyze --pending`. The current queue was empty and returned
`status=disabled`, `analyzed=0`, `deferred=0`, `dead_letter=0` and `errors=0`.
No model call or candidate-state mutation occurred.

The deterministic workflow, cross-project relationship, optional compiler
state-machine, conflict-insight and stable-promotion regression suite passed
`58` tests. This proves the admission, evidence-binding and review gates, but
does not create live multi-project evidence or auto-promote memory.

## Latest Task 9B Execution And Post-Cycle Correction (2026-08-16)

Current ownership verification passes: runtime data entities are physical
owners, checkout paths point to the canonical DATA_ROOT, and the owner guard
returns no issues. Because Task 9B was already applied, no duplicate migration
was performed.

The single authorized manual cycle is `cycle-d76c20fc721a`. It passed the
owner gate and runtime import boundary, processed `18` events with `0` failed,
but returned `success_with_warnings` because the audit encountered a parser
false positive. The parser and source-path resolver were corrected afterward;
current schema issues are `0`, while six genuine historical missing-source
items remain in review. The immutable receipt is not rewritten and no second
cycle is run, so current health remains truthfully `degraded`.

Full verification is `650` tests passed, Ruff passed, and `git diff --check`
passed. Runtime `runtime-20260816T031038Z-aa7ee6ed` is non-editable with no
iCloud import path. Raw JSON count remained `3,423`; excluding three identified
CBMEM snapshot refreshes, the remaining `3,420` content hashes are identical.
No raw event was deleted or rewritten. Launchd was not restarted or loaded,
there was no deployment, and Ather was not touched.

The six remaining missing-source review items were checked against current
Downloads, Documents, Desktop, and active Codex/Claude/Trae configuration
locations. No original or approved replacement source exists in those paths.
They remain explicit provenance gaps and keep audit/health degraded; removing
the references or substituting unrelated files would be an evidence regression.

## Latest Source-Gap Quality Gate (2026-08-16)

The analyzer now classifies each missing source as `local` or `external` and
retains the resolved path in a structured `SourceGap`. The review queue still
counts every gap under the compatible `missing-source` category, so this is
observability and repair routing, not a relaxation of R4, R10 or R14. The live
read-only audit remains `FAILED` with `1` local gap, `5` external gaps, eval
`2/2`, and CBMEM `1/1`.

The complete source suite passes `652`, Ruff and `git diff --check` pass, and
the source-gap regression tests cover both scopes. No source reference was
removed, no runtime was rebuilt, no deployment or launchd action occurred, no
second supervisor cycle ran, and Ather was not read or modified.

## Latest Non-Editable Runtime Refresh (2026-08-16)

The source-gap fix is now present in the actual local runtime, not only the
checkout: `runtime-20260816T093217Z-aa7ee6ed`, wheel SHA-256
`bc958d29c0606b587664ed863070cf7942efd105daa4f3e65f230405c6454315`, and
manifest SHA-256
`0bec9c16492c93a7137cfd9884e77110f7441a35532a8f6ac988ad4dac1e4c8f`.
Installed import is non-editable from `site-packages` with no iCloud path, and
the installed review command still reports six source gaps rather than hiding
them. Source tests remain `652 passed`; Ruff and diff checks pass. No
deployment, launchd action, second supervisor cycle, raw deletion or Ather
operation occurred.

## Latest Antigravity Host Load Check (2026-08-16)

The real local `agy agent` host loaded the configured hook and logged
`loaded 1 named hooks from 1 hooks.json file(s)`. This proves host discovery,
not a lifecycle proof receipt: no prompt or model request was sent and no full
agent execution occurred. Antigravity remains `partially_supported` until a
real session produces both read and write receipts. No deployment, launchd
action, second supervisor cycle, raw deletion or Ather operation occurred.

## Latest Coverage Reason Contract And Runtime Refresh (2026-08-16)

The coverage contract now exposes a plain `status_reason` for every tool,
derived from evidence rather than configuration. It explains the current
boundary for missing hosts, stale captures, missing lifecycle events and
verified bidirectional proof while preserving the existing status and proof
semantics. Installed runtime verification shows seven verified tools and four
partial tools with explicit reasons. Source verification is `653 passed` and
Ruff passes. No deployment, launchd action, second supervisor cycle, raw
deletion or Ather operation occurred.

## Latest Audit Count Correction And Runtime Recheck (2026-08-16)

The audit now keeps missing-source messages in the analyzer's raw error list
for compatibility, while counting each `SourceGap` once in the review queue.
The same provenance gap is therefore no longer reported as both an analysis
error and a review item. A focused regression test covers this invariant.

The source suite passes `656` tests and Ruff passes. The refreshed non-editable
runtime is `runtime-20260816T125130Z-aa7ee6ed`; its health snapshot reports
`issues=6`, broken down as `analysis_errors=0`, `schema_issues=0`,
`review_items=6`, with source gaps `local=1` and `external=5`. The overall
status remains `degraded` for the real unresolved boundaries: launchd is not
loaded, the cycle is due, and the six provenance gaps remain open. No source
reference was removed, no raw event was deleted or rewritten, no deployment,
launchd action or second supervisor cycle occurred, and Ather was not touched.

## Unified Behavior And Context Smoke (2026-08-16)

`hub behavior verify` returns `valid=true` for the canonical `GLOBAL.md`
contract with SHA-256
`f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29`.
Read-only `hub context --format json` calls for all eleven registered tools
returned `exit=0` and resolved the same project identity
`git-9f1cb19971812dd3`. These direct CLI calls are correctly labeled
`observation only`; they prove the common context interface is callable, not
that eleven live hosts have emitted native read receipts. Native proof status
therefore remains unchanged at seven verified tools and four partial tools.
No model call, source substitution, raw deletion, deployment, launchd action,
second supervisor cycle or Ather operation occurred.

## Local Host Probe Without Model Calls (2026-08-16)

The no-model host probe returned Antigravity CLI version `1.1.13`. The
`minimax` and `gemini` executables are not present on `PATH`; their app/config
presence is therefore not equivalent to a runnable CLI lifecycle host. The
probe did not emit a lifecycle event, so native proof coverage did not change:
Antigravity, MiniMax and Gemini CLI remain unverified, and Cursor remains
unavailable on this machine. No model call, source substitution, deployment,
launchd action, second supervisor cycle, raw deletion or Ather operation
occurred.

## Current Native Host And Supervisor Verification (2026-08-16)

The real host identity was corrected from an incomplete probe. The executable
`~/.local/bin/agy` is Antigravity CLI `1.1.13`; its own logs identify the
product as `antigravity`, and its configured `hooks.json` loaded the native
bridge. It uses Gemini models, but it is not the Google `gemini` CLI. The
adapter now accepts host casing variants and falls back to the hook subprocess
working directory when Antigravity sends `workspacePaths: []`, which was the
actual cause of the earlier missing proof.

A real no-op `agy --print` session produced both native receipts for project
`git-9f1cb19971812dd3`: one read receipt and one write receipt. The installed
runtime is non-editable `runtime-20260816T132256Z-aa7ee6ed`, and the focused
Antigravity suite passes `6` tests. Coverage should therefore mark
Antigravity as `verified_bidirectional`; this does not promote MiniMax or the
Google Gemini CLI, which still have no real host lifecycle proof. Cursor is
intentionally out of scope.

LaunchAgent `com.ethan.lwm.harvest` was reloaded from the source checkout, not
from the runtime data directory. Its `RunAtLoad` execution created the one
authorized formal receipt `cycle-180f0df8f945`; no second forced cycle was run.
The receipt is bound to the current runtime: recorded and independently
computed manifest SHA-256 are both
`0d454af31ee1f58b8f816e5b1cac8481983a1402140acaecebc13011421b01e4`, and
`runtime_import_independent=true`. Core stages completed with
`success_with_warnings`, `failed=0`, and the overall status is `degraded`
because the audit still has six unresolved provenance gaps. Launchd remains
loaded with a 900-second interval; the supervisor process is not currently
running because that degraded cycle exited with code `1`.

The six historical source references remain intact and unresolved: one local
`user/board` source and five external Codex/Trae files. Searches of the
relevant local folders, Spotlight metadata, runtime evidence and available
archive-like locations found neither the originals nor an approved archive.
They cannot be marked restored, deleted, or replaced by unrelated files. The
remaining completion action is to recover the originals or provide an
explicit human-approved archive/source decision.

This verification is local only: no deployment, raw deletion, raw rewrite,
or Ather operation occurred. With the permitted temporary uv cache, the
complete source suite passes `658` tests; Ruff and `git diff --check` also
pass.
