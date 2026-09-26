# LLM-WorkMem Goal Completion Implementation Plan

> **For agentic workers:** Prefer `superpowers:subagent-driven-development` or `superpowers:executing-plans` when available. If the executing tool does not provide either skill, use its native task tracker and preserve the same gate: implement one Task at a time, run that Task's focused tests, and request an independent code review before advancing.

**Goal:** Make LLM-WorkMem a reliable, source-backed, low-noise auxiliary memory layer that can retain verified work across tools, return relevant project context, run independently of the iCloud checkout, and prove its own health without overstating integration status.

**Architecture:** Preserve the existing file-based Retain/Recall/Reflect architecture, event inbox, project pages, deterministic recall, adapters, CBMEM bridge, audit, health, and launchd supervisor. Add one strict durable-event admission contract, rebuild derived project memory from preserved raw events, constrain cross-project promotion and context selection, make the installed runtime genuinely self-contained, and make every health/capability claim depend on external evidence.

**Tech Stack:** Python 3.11 or newer (current runtime: Python 3.11.15), Typer, pytest, Ruff, Markdown/YAML frontmatter, JSON event envelopes, macOS launchd, `uv`, existing `lwm` CLI.

## Execution Status (2026-08-09)

- Tasks 0-8: code and package implementation complete; current source evidence
  is `589 passed`, full Ruff pass, clean diff check, local wheel integrity check,
  and an independent Python 3.11 install smoke.
- Task 9A: the historical post-cleanup preview remains
  `/private/tmp/lwm-goal-completion-manifest-20260805-final.json`, SHA-256
  `e9e5e6d1426207c57775aa6c6e8fd269e3cf60bed9ab8725da01c009a1a93a14`. A
  fresh post-runtime-refresh preview is
  `/private/tmp/lwm-goal-completion-manifest-20260809-task9b.json`, SHA-256
  `894baa3e35760018468e09407cf59dc273393bbc4a1c53109510196899b1183a`, with
  approval id `lwm9b-894baa3e35760018`.
- The manifest-bound migration executor is implemented, tested, and was
  executed after explicit approval. The fresh manifest checked 329 entries,
  bound a valid rollback archive, confirmed the already-migrated physical
  runtime owners, and stayed within the approved data-owner scope.
- The execution manifest was
  `/private/tmp/lwm-goal-completion-manifest-20260809-task9b.json` with SHA-256
  `894baa3e35760018468e09407cf59dc273393bbc4a1c53109510196899b1183a`. After
  the sanitized verification write-back, the current read-only manifest is
  `/private/tmp/lwm-goal-completion-manifest-20260809-task9b-current.json` with
  SHA-256 `13eb131afc9681595251435a5418db6f4ac913b3b6e39d47e50f03d81c111978`;
  it was verified but not re-applied.
- Task 9B: approved and executed locally. The migrated runtime data root passed
  the owner boundary. The latest authorized manual cycle produced immutable
  receipt `cycle-5c2002c7bd5f` with `core_status=success`, `overall_status=success`,
  audit `0` issues, eval `2/2`, CBMEM `1/1`, and independent runtime import.
  Historical receipts remain immutable and are not rewritten. No launchd reload
  or deployment was performed; raw event IDs were preserved.
  A current rollback archive exists and is bound by the fresh manifest; rollback
  itself was not executed. Strict verification of the latest receipt reports
  only the intentionally unloaded launchd health boundary.
- Post-cycle code correction: the supervisor no longer rewrites health after
  receipt commit, and strict receipt verification preserves the full
  `last-attempt.json` pointer for warning/failed cycles. The installed local
  runtime is the non-editable wheel SHA-256
  `c20e0d822656d84255be8a77007a0844525524945b5b6566e258cb8dcfeac426` and
  runtime generation `runtime-20260809T050549Z-aa7ee6ed`.
- Post-cycle derived-audit repair: curated summary pages are now included in
  graph analysis, generated historical source links are excluded from current
  broken-link review, and the derived runtime index contains the two concept
  pages and two curated summaries that were previously orphaned. Installed
  runtime audit is `0` analyze errors, `0` schema issues, `0` review items,
  eval `2/2`, CBMEM `1/1`.
- Behavior contract snapshot: source `GLOBAL.md` is verified at SHA-256
  `f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29e`;
  `hub behavior sync` refreshed runtime `state/behavior/current.json` at
  `2026-08-09T04:57:51+00:00`. Context reports the same hash as a truthful
  `stale` fallback; `GLOBAL.md` remains the only writable human source.
  Verification event `fb662605-bc16-4d1e-9551-ad56d06f57e2` records the
  sanitized proof.
- Local host adapter cutover: Claude Code hooks, global adapters, stable
  launcher, zsh context source and shell-history hook were refreshed to the
  runtime owner. The shell hook now selects the packaged wheel resource even
  when the migrated data root still contains a legacy `lwm/` code mirror.
  The user configuration rollback archive is
  `/private/tmp/lwm-global-adapters-before-runtime-root-20260806.tar.gz`.
- Owner-path normalization correction: `canonical_data_root()` now converts a
  migrated repository access path back to the single runtime data owner before
  any write-bearing global adapter, IDE hook or shell-hook installation. An
  ordinary checkout or temporary test root is unchanged. Source tests and an
  installed-wheel temporary-owner probe prove that generated commands contain
  the owner path and not the repository access path.
- OpenCode ownership correction: the installer now recognizes both historical
  `lwm-workmem` and canonical `llm-workmem` names, migrates a known generated
  checkout plugin to `~/.config/opencode/plugins/llm-workmem.ts`, preserves
  unrelated plugins, and remains idempotent. The local OpenCode registration
  now points to that canonical user plugin rather than the iCloud checkout.
- Reference-owner correction: OpenCode `references.llm-workmem.path` and a
  legacy Kiro startup command are now normalized to the runtime data owner;
  only the known WorkMem pointers are changed and unrelated user config is
  preserved. The post-fix local wheel was repacked offline from the audited
  wheel because `hatchling` was unavailable in the offline build cache.
- Additional safety correction: schedule generation now prepares runtime
  directories without migrating repository ownership; only an explicitly
  approved migration path may change ownership.
- Additional bridge safety correction: `bridge-contract --simulate` now runs
  against a disposable root containing only the Tool Registry. Source and
  installed-wheel smoke both prove zero raw/state file-tree changes in the
  requested project root.
- Authorized local cleanup is complete: the runtime `state` symlink was
  dereferenced, exactly 33 simulation events and 12 simulation handoffs were
  moved to `/private/tmp/lwm-simulation-cleanup-authorized-20260805`, the
  active pointer was removed from the live state, and the receipt hash matches
  the pre-test backup. No deployment or launchd reload was performed.
- Task 9C Antigravity native-hook implementation is complete in the source
  package and active local runtime. `PreInvocation` and `Stop` use the shared
  session bridge, forward only `conversationId` and `workspacePaths`, and
  emit verified read/write proof without persisting host prompt or model text.
  The global `~/.gemini/config/hooks.json` was created/merged idempotently and
  its commands point to the non-iCloud runtime venv. A temporary installed-
  runtime smoke proved context injection, verified read/write receipts, and
  no host-text persistence. Real Antigravity host firing is still required
  before the integration can be called production-verified.
- Kiro remains observation-only for this cutover. The installed local CLI is
  `2.10.0`; the standalone `.kiro/hooks/*.json` contract documented for CLI 3.x
  does not match this host, and no unambiguous 2.x agent-config hook path was
  identified. No speculative Kiro hook was installed.
- Task 9D Codex/Gemini CLI native-hook cutover is complete in the local source
  and installed runtime. Codex uses `~/.codex/hooks.json` with
  `SessionStart`/`SessionEnd`; Gemini CLI uses `~/.gemini/settings.json` with
  `SessionStart`/`SessionEnd`; both installers merge only generated handlers,
  preserve unrelated user settings, and leave Codex trust/approval state
  untouched. The existing Gemini `mcpServers.codegraph` entry was preserved.
  Real host proof is intentionally still absent, so coverage remains
  `configured_unverified` until each host emits a qualifying receipt.
- Current post-cutover package/runtime evidence is wheel
  `/Users/ethan/Library/Application Support/llm-workmem-runtime/app/.wheels/lwm-0.1.0-py3-none-any.whl` with
  SHA-256 `c20e0d822656d84255be8a77007a0844525524945b5b6566e258cb8dcfeac426`
  and runtime generation `runtime-20260809T050549Z-aa7ee6ed`. The wheel has 99
  RECORD rows with zero invalid hashes; the installed runtime is non-editable
  and imports `lwm`, Codex native hooks and Gemini native hooks from
  `site-packages`.
- Historical receipt `cycle-e545e55cfad0` remains immutable with receipt
  SHA-256 `39082a55e3e912984900e30873ea981d8b5bba55c7109f059dc62b5904b705e`.
  The latest authorized receipt `cycle-5c2002c7bd5f` is core-success and is
  bound to manifest `e29ac916...`. Later local Codex and shell-hook runtime
  refreshes moved the current manifest to `4ee82938...`; strict verification
  therefore reports the truthful `runtime_manifest_hash_mismatch` plus the
  intentionally unloaded `health_status:degraded` launchd boundary. Historical
  receipts are not rewritten and no second cycle was run.
- Sanitized local verification event
  `0395722c-65a8-471b-ba22-872d92f80d37` was appended to the runtime inbox;
  it contains test, package, runtime-import, and raw-preservation evidence
  only, with no prompt, transcript, or model text.
- Final Task 9D verification event `2db400b7-4174-4a6c-a9cb-09fb83715d91`
  records the direct CLI default-path correction, final wheel/runtime hashes,
  `579`-test/Ruff/diff-check evidence, and installed CLI Gemini coverage. It
  contains no prompt, transcript, or model text.
- Task 9B current-cycle verification event
  `84041b11-9b50-4be8-a67a-38919519cb7b` records the owner-boundary result,
  current receipt, audit/eval/CBMEM proof, and raw event-ID retention. It is
  sanitized and append-only.
- Task 9B current evidence refresh event
  `ac22a0db-1242-4f4c-987a-4b3a4f2d75d5` records the fresh manifest, rollback
  archive, owner-boundary result, strict-cycle reasons and raw-ID count. It is
  sanitized and contains no prompt, transcript, model, completion or
  environment payload.
- Task 9E truthful coverage repair is complete: capture freshness now accepts
  only lifecycle/bounded observation event types, so durable verification
  write-backs cannot impersonate host capture. The installed runtime reports
  Codex's actual historical capture time, Gemini CLI `no_capture_event`, and
  Antigravity stale. Final verification event:
  `6f111328-dcfe-4d6f-b4dd-879319f5a0ac`.
- Native hook installer parity correction: the public `hub install-ide-hooks`
  CLI default and Python helper now include Antigravity, matching the existing
  global adapter path. The isolated installer suite and full suite pass; real
  Antigravity host firing remains unverified by design.
- Local runtime refresh after the parity correction completed without a
  deployment, launchd reload, supervisor cycle or raw mutation. The installed
  wheel is now SHA-256
  `046fb166a090bb26c23535639fd88cfafadec6daead2db25a7c02482a92fc670`,
  runtime id `runtime-20260809T145527Z-aa7ee6ed`, and manifest SHA-256
  `513dc081f8114d2821fd739d85ea702757b904a1bff6418aaf89210e1072644c`.
- Runtime import-isolation and owner-path correction completed locally. Coverage
  and strict cycle verification now normalize repository access symlinks to the
  physical runtime owner before resolving evidence. The generated launcher and
  native hooks use Python `-I`, and the live launcher plus Claude/Codex/Gemini/
  Antigravity hook JSON files were updated without touching launchd. Full tests
  are `582 passed`; Ruff passed. The latest non-editable runtime is
  `runtime-20260809T151200Z-aa7ee6ed`, wheel SHA-256
  `b733b3ff1238c63979acf83da24160db8a8105b4edfd366b57d13156418ee34e`, and
  manifest SHA-256
  `4c488e446a70a2fa1136ac340f2c8a85d02e6ba3a0da4b317dc0ebf9331954a7`.
  Installed wrapper coverage reports Claude Code and OpenCode as
  `verified_bidirectional` with no gaps. The prior authorized cycle remains
  immutable; strict verification correctly reports its old manifest hash and
  the intentionally unloaded launchd health boundary, so no second cycle was
  run.
- Final local subprocess/owner correction completed after the previous runtime
  refresh. The legacy Claude installer, common hook recorder, shell recorder,
  adapter runner, and source user wrapper now force Python `-I`; `record_event`,
  startup Context, analysis review, and promotion normalize migrated checkout
  access paths to the physical runtime owner. Full tests are `584 passed`, Ruff
  and shell syntax checks passed. The latest non-editable runtime is
  `runtime-20260809T152234Z-aa7ee6ed`, wheel SHA-256
  `efde62bd3fedbb4d62ecfb4f992f96eeb7030f05059c59a3acf4175a1c4cebd5`, and
  manifest SHA-256
  `5f76f20e44c7ce7a3c6510a58697a9ae6f004b5db4041fda1014ac9606c54975`.
  An installed-wheel temporary-owner smoke proved both event and Context
  receipt writes use the physical owner. No second cycle was run.
- Proof-gate correction completed locally. Direct `hub receipt` proof writes now
  fail closed for `native-hook`, `lifecycle-hook`, and `explicit-smoke`; only a
  real host bridge can claim a proof source. The legacy capabilities facade now
  also normalizes migrated checkout access paths to the physical owner. Full
  tests are `586 passed`, Ruff, shell syntax and diff checks passed. The latest
  runtime is `runtime-20260809T153213Z-aa7ee6ed`, wheel SHA-256
  `ca44ecdbbd93fa97d3e16c20e03721a5fe3aee7ca389ff5f1fd3cfa460bee50e`, and
  manifest SHA-256
  `e29ac916ef858d6212d86f6bc28445d878dc5cae3b4c9a95f9481fc26ccbbefc`.
  Installed legacy/new coverage agree: Claude Code and OpenCode are
  `verified_bidirectional`; the other nine remain honestly unverified until
  their real host lifecycle produces read and write receipts.
- Codex host-contract correction completed locally on 2026-08-10. The installed
  Codex 0.147 hook schema uses `SessionStart`/`SessionEnd`, not Claude's
  `Stop`. The source generator, native handler, migration cleanup and tests now
  agree; the live `~/.codex/hooks.json` was refreshed from the current runtime.
  The isolated installed-runtime smoke passed, while live Codex coverage stays
  `configured_unverified` until Codex itself fires both hooks.
- Shell lifecycle proof correction completed locally. The registry now binds
  `shell-hook`; the packaged zsh hook emits only sanitized `shell_session_start`
  and `shell_session_end` host metadata through the common bridge, while the
  existing filtered preexec/precmd observer remains the only place that stores
  command text. The source suite is `589 passed`, Ruff and zsh syntax checks
  pass, and an installed-runtime isolated zsh smoke produced verified read/write
  receipts with zero lifecycle command fields. A controlled local interactive
  zsh then ran against the physical runtime owner as session
  `shell-proof-20260810`; events `ae3ea039-d178-4744-912b-b847e2ce5902` and
  `94924959-42cc-40f9-bb27-3949e453b0f1` promoted shell to
  `verified_bidirectional`. The lifecycle proof contains no command field.
- The current installed runtime after that shell correction is
  `runtime-20260809T171036Z-aa7ee6ed`, wheel SHA-256
  `f3431e595242a7e8cfdbd983db3aa05fea935c0ffc9eb181d9ccde5512fa29fe`, and
  manifest SHA-256
  `4ee8293879fd9512173e1d2426e865e23814e4c14e2bbbf47b9b532e8187f7dc`.
  The local `~/.zshrc` hook fingerprint was refreshed after backup
  `/private/tmp/lwm-zshrc-before-shell-proof-refresh-20260810`; no deployment,
  launchd restart or supervisor cycle was performed.
- Historical Task 9B re-validation before the current explicit authorization
  used receipt `cycle-5c2002c7bd5f` and is retained as immutable evidence. It
  recorded core/overall success, audit `0`, eval `2/2`, CBMEM `1/1`, and no
  failed stages, but later runtime refreshes made its strict verification
  honestly report a manifest mismatch and unloaded-launchd boundary. Its
  sanitized event `562c75a1-aa3a-4b72-a507-12f90a489595` remains historical;
  the current receipt and proof are recorded in the next bullet.
- Task 9B explicit local execution was completed with the fresh manifest
  `/private/tmp/lwm-goal-completion-manifest-20260809T172857Z-task9b.json`
  (SHA-256 `552b718f9dbaeffc4d542c645a4378c1a0262c7d3955100dd59349e0aa7859e0`,
  approval id `lwm9b-552b718f9dbaeffc`) and rollback archive
  `/private/tmp/lwm-goal-completion-backup-20260809T172857Z-task9b.tar.gz`
  (SHA-256 `92d8c77de392cc4608d75c342c1d626ab0d7e359afbd7bf69f4ea100344dd376`).
  The migration returned `applied=true` with `data-owner-only` scope. The one
  authorized manual cycle is `cycle-fd14856a63d1`: it was successful at cycle
  time with core/overall status `success`, processed `6`, accepted `6`,
  rejected `1`, failed `0`, audit `0`, eval `2/2`, and health `healthy`. Its
  receipt was bound to the then-current runtime manifest
  `4ee8293879fd9512173e1d2426e865e23814e4c14e2bbbf47b9b532e8187f7dc`.
  After the lock-error semantic fix, the installed non-editable runtime is
  now `runtime-20260810T020309Z-aa7ee6ed` with manifest SHA-256
  `3444b7991af6cfc3fd03cd8a4fc4cfdd2b3043862b12cebc21605c21c44f78f6`.
  Strict verification therefore returns `valid=false` only for
  `runtime_manifest_hash_mismatch`; the immutable receipt was not rewritten
  and no second cycle was run under this authorization.
  The pre-cycle `3,226` raw event JSON bytes remain present; `7` inbox paths
  moved unchanged to processed/rejected, and the post-cycle sanitized
  verification event is `60562ac3-f05e-4177-ab5a-c88ebfd4c0c7`. No deployment,
  launchd reload, or raw event deletion occurred.

- The current installed runtime after the lock-error semantic fix is
  non-editable `runtime-20260810T020309Z-aa7ee6ed`; its wheel SHA-256 is
  `08dda75b925159e3bbf12ee255754212aadcc01933b1421d2189d9e2723600da` and
  its manifest SHA-256 is
  `3444b7991af6cfc3fd03cd8a4fc4cfdd2b3043862b12cebc21605c21c44f78f6`.
  Installed import resolves from runtime `site-packages` with no iCloud path.
  Lock-open permission failures now return nonzero instead of being mistaken
  for a clean concurrent-cycle exit. No deployment, launchd restart, raw
  deletion or supervisor cycle was performed after this rebuild.

## Global Constraints

- Native Codex, Claude Code, IDE, and shell instructions remain authoritative. LLM-WorkMem supplies auxiliary evidence only.
- `docs/superpowers/specs/2026-07-28-llm-workmem-lean-core-design.md` is the current architecture boundary.
- The older V2 control-plane documents remain historical rationale. Their runtime-truth, privacy, identity, deduplication, and verification requirements still apply, but their “unique authority”, second control plane, and `projects/<id>/STATE.md` hierarchy do not.
- Do not add a database, vector store, resident LLM, web service, second memory repository, new orchestration authority, or full-chat archive.
- Preserve `raw/events/processed/` as source evidence. Repair derived wiki pages by deterministic rebuild; do not manually rewrite history.
- Never promote shell commands, complete prompts, `AGENTS.md`, environment dumps, lifecycle receipts, or watcher observations into durable memory merely because their `task` field is non-empty.
- Never label an integration `verified_bidirectional` from file presence or watcher observation alone.
- Runtime code executed by launchd must not import Python modules from the iCloud checkout.
- Preserve the current top-level runtime layout: executable environment under `llm-workmem-runtime/app/venv/`, live data under `llm-workmem-runtime/llm-workmem/`, and logs under the existing runtime/data log paths. Do not invent `llm-workmem/app/venv/` or require a nonexistent `bin/run-harvest`.
- Live mutable data has one entity owner: the non-iCloud runtime data root. Repository paths are access links, not second writable copies.
- Cross-Mac Git synchronization of absolute-symlink targets is not proven by this plan. Do not describe runtime-owned `wiki/` or `raw/` content as Git-synchronized until a separate portable export/import design is approved and verified.
- Modify only files listed in each task. Preserve unrelated dirty changes in `.codebase-memory/` and `global/config/`.
- Existing green assertions that encode rejected semantics may be changed only in the test files explicitly named by this plan. Do not optimize for retaining the historical `310` test count; optimize for all current tests passing with corrected semantics.
- One task has one stop condition. Do not continue to the next task while its focused tests fail.
- A clean test suite is necessary but insufficient. Completion also requires a successful real scheduled cycle, clean audit, healthy health report, and inspected context output.
- Task 9 is split into a non-destructive preview gate and an explicitly approved migration. No project-page rewrite, active global-page removal, symlink-direction change, or launchd reload may occur before the user approves the preview manifest and rollback bundle.
- Because the current `APP_VENV` is an editable install, source changes are live runtime changes even without reload. Do not modify source code before Task 0 receives approval and pauses `com.ethan.lwm.harvest`.
- Before approval, Task 0 may only read and hash the plist. After explicit approval it may back up the plist, boot out the job, and move the live plist to the declared paused-plist path so reboot cannot reload it. It may not rewrite data, install code, alter data symlinks, or register a replacement job.

## 1. Source-of-Truth Decision

### 1.1 What LLM-WorkMem is

LLM-WorkMem is a local evidence layer with one bounded loop:

```text
source event
→ sanitize and deduplicate
→ classify durability
→ preserve raw evidence
→ materialize bounded project/global memory
→ deterministic context or recall
→ tool uses evidence under its own native rules
→ verified work writes one structured event back
→ audit and health verify the loop
```

### 1.2 What LLM-WorkMem is not

- It is not the final answer generator.
- It is not a replacement for Codex memory, tool-native instructions, Git, project documentation, or issue tracking.
- It is not allowed to infer facts from command history or complete conversations.
- It is not allowed to claim a tool can read or write memory unless a qualifying receipt proves that operation.
- It is not allowed to treat generated wiki pages as new source evidence.

### 1.3 Canonical layers

| Layer | Logical path | Physical entity after Task 9B | Mutability |
| --- | --- | --- | --- |
| Repository rules | `GLOBAL.md`, `docs/superpowers/**` | Source checkout | Human-reviewed |
| Wiki policy | `wiki/purpose.md` | Runtime data root, reached through repo link | Human-reviewed live data |
| Current synthesis | `wiki/overview.md` | Runtime data root, reached through repo link | Generated/curated current snapshot |
| Durable project memory | `wiki/projects/<project_id>.md` | Runtime data root, reached through repo link | Derived from admitted events |
| Durable global memory | `wiki/global/*.md` | Runtime data root, reached through repo link | Explicitly promoted, source-backed |
| Raw evidence | `raw/events/processed/**/*.json` | Runtime data root, reached through repo link | Append-only |
| Operational state | `state/*.json` | Runtime data root, reached through repo link | Runtime-generated, non-authoritative |
| Tool pointers | `adapters/*` and native adapter targets | Source checkout plus generated runtime copy | Generated auxiliary instructions |
| AI exports | `llms.txt`, `llms-full.txt`, `llms.json` | Runtime data root, reached through repo links | Generated, non-authoritative |

“Logical path” is the API used by `lwm` commands. “Physical entity” answers which file is real. A link and its target are not two copies and must never be described as a mirror pair.

## 2. Verified Baseline on 2026-07-31

The following facts were verified against the current checkout and local runtime before writing this plan:

| Area | Verified result | Consequence |
| --- | --- | --- |
| Unit/integration tests | `310 passed` | Existing behavior has broad coverage, but tests currently encode some incorrect semantics. |
| Ruff | Passed | No current static-style blocker. |
| Wiki analysis | 124 pages, 0 broken links, 0 missing sources, 1 duplicate slug | `_archive_*` review content is incorrectly included in the active graph. |
| Audit | Failed: analyze 5, schema 0, review 1, eval 1/2 | The repository is not completion-ready. |
| Health | Failed; scheduled cycle due; last exit code 1 | Background memory refresh is not healthy. |
| launchd | `com.ethan.lwm.harvest` loaded, 900-second interval | Scheduling exists, but loaded does not mean healthy. |
| Runtime import | `_editable_impl_lwm.pth` points to the iCloud checkout, so even isolated runtime Python imports `lwm` from there | Runtime independence is not achieved; Task 7 must replace the editable install with a wheel install. |
| Runtime layout | Executable is `~/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm`; launchd calls it directly | The earlier nested `llm-workmem/app/venv` and `bin/run-harvest` assumptions were wrong. |
| Data ownership | `wiki/`, `raw/`, and exports are runtime entities reached from the repo by absolute symlinks; runtime `state` points back to repo `state` | Current mutable ownership is split and must be normalized before health/runtime boundaries are truthful. |
| Python contract | `pyproject.toml` and `uv.lock` require Python `>=3.11`; runtime is Python 3.11.15 | Python 3.12 must not be required by this plan. |
| Ather context | Returned project scope, but durable status contains a complete instruction/environment dump | Event admission is allowing operational noise into long-term memory. |
| Global context | Repeated `recurring-tag-lifecycle-across-39/40/41-projects` pages | Promotion and context selection amplify lifecycle noise. |
| Capability receipts | `watcher-observed` counts as native bidirectional proof | Integration status is overstated. |
| Audit call path | `lwm/audit.py::run_audit()` already calls `analyze_wiki()` directly | Task 2 must not reimplement this; the real gap is stale/generated analysis participation and weaker re-auditing in health. |
| Destructive migration scope | 27 generated project pages, 3 lifecycle global pages, one state ownership reversal, and launchd registration | Only Task 9A preview is pre-approved; Task 9B requires explicit user approval. |

## 2.1 Audit Conflict Resolution

These decisions supersede conflicting language elsewhere in this document:

| Conflict | Resolution |
| --- | --- |
| Runtime directory | Keep the current top-level split: `RUNTIME_BASE/app/venv` for executable code and `RUNTIME_BASE/llm-workmem` for live data. |
| launchd entrypoint | Keep direct invocation of `app/venv/bin/lwm hub run-supervisor <DATA_ROOT>`. No wrapper is required for correctness. |
| Mutable data entity | Make `DATA_ROOT/{wiki,raw,automation,exports,state}` the only live entities. Repository mutable paths become links into `DATA_ROOT`. |
| Current reversed `state` link | Treat as migration debt. Task 7 implements support; Task 9A previews it; Task 9B reverses it only after approval and backup. |
| Git synchronization | Mark portable durable-memory sync as unverified/out of scope. The current absolute symlinks do not make their targets Git content. |
| Existing green tests | Intentionally replace only the named assertions that encode watcher-overclaim, mixed ownership, or stale behavior. Test count is not an acceptance criterion. |
| Real data rewrite/deletion | Stop after dry-run, hashes, backup paths, and rollback commands. Continue only after explicit user approval. |
| Audit implementation | Preserve the existing direct `analyze_wiki()` call. Pass one computed `AuditReport` into health instead of performing a second weaker audit without eval. |
| Skill availability | Use the named superpowers skills when the active tool exposes them; otherwise use native task tracking plus focused tests and independent review. |
| Editable runtime during implementation | Pause launchd under Task 0 approval before the first source edit; otherwise Task 1 must not start. |
| Eval suite ownership | Move the authoritative eval suite into packaged source at `lwm/resources/eval-suite.txt`; do not edit live `wiki/eval-suite.txt` in Task 1-8. |

Known unknowns that must remain explicit:

- Portable cross-Mac synchronization for runtime-owned durable Wiki and raw evidence is not designed or verified here.
- Task 9A counts are currently 27 project pages and 3 lifecycle global pages, but the manifest must recompute them immediately before approval because background tools can add events.
- The user has not approved Task 9B merely by approving this document.

## 3. Target Contracts

### 3.1 Durable event admission

Add an explicit classification result in `lwm/project_memory.py`:

```python
from dataclasses import dataclass
from typing import Literal

Durability = Literal["durable", "operational", "rejected"]

@dataclass(frozen=True)
class EventAdmission:
    durability: Durability
    reason: str
    section: str | None

def classify_event(event: dict[str, object]) -> EventAdmission:
    ...
```

Required behavior:

| Input | Classification |
| --- | --- |
| `decision` with non-empty `decisions` | `durable`, section `decisions` |
| `bugfix` with bounded `changes` and `verification` | `durable`, section `bugfixes` |
| `verification` with non-empty `verification` | `durable`, section `verifications` |
| `project_status` with bounded task plus a structured durable field | `durable`, section `status` |
| Explicit unresolved question attached to durable work | `durable`, section `open_questions` |
| `session_start`, `session_idle`, `session_deleted`, `adapter_probe` | `operational` |
| `workflow_observation` containing only a command/transcript/prompt | `operational` |
| Complete instruction blocks, environment dumps, secrets, malformed fields | `rejected` |

Durable text limits:

```python
MAX_TASK_CHARS = 240
MAX_ENTRY_CHARS = 480
MAX_ITEMS_PER_FIELD = 8
MAX_ITEM_CHARS = 240
```

The classifier must reject or truncate before rendering. It must identify these high-signal noise markers case-insensitively:

```python
NOISE_MARKERS = (
    "<environment_context>",
    "<permissions instructions>",
    "# agents.md instructions",
    "you are codex",
    "command timed out",
)
```

Raw evidence remains untouched regardless of whether a derived-memory event is durable.

### 3.2 Project memory rebuild

Add:

```python
@dataclass(frozen=True)
class RebuildReport:
    scanned_events: int
    admitted_events: int
    operational_events: int
    rejected_events: int
    pages_written: int
    pages_removed: int

def rebuild_project_pages(root: Path) -> RebuildReport:
    ...
```

Rules:

- Read only valid JSON files under `raw/events/processed/`.
- Sort by `(timestamp, event_id)` for deterministic output.
- Apply `classify_event`.
- Build pages in memory and write each page once.
- Remove a previously generated project page only when no durable event remains for that same project.
- Never delete raw events.
- Re-running with unchanged input must produce byte-identical page bodies except a generated timestamp; prefer deriving `updated` from the latest admitted event so the whole file is byte-identical.
- Keep at most 12 status entries, 20 decisions, 20 bugfixes, 20 verifications, and 20 open questions per page. Raw evidence remains the full history.

### 3.3 Context packet

`lwm context` must return a bounded evidence packet, not a dump.

```python
CONTEXT_LIMITS = {
    "global_rules": 6,
    "status": 6,
    "decisions": 8,
    "bugfixes": 6,
    "verifications": 8,
    "open_questions": 8,
    "insight_candidates": 2,
    "recent_activity": 12,
}
MAX_CONTEXT_CHARS = 12_000
```

Selection rules:

- Global rules come only from explicitly promoted pages whose frontmatter has `type: principle` and `status: approved`.
- Exclude filenames beginning with `recurring-tag-lifecycle-` and tags containing `lifecycle`, `session`, `adapter`, or `workflow_observation`.
- Project sections use the newest bounded entries and deduplicate identical normalized text.
- Recent activity is operational context and must be labeled as such; it cannot appear under durable project memory.
- Paths in JSON can be repository-relative. Markdown output must not print user-home absolute paths unless the caller requests `--include-paths`.
- If no durable project page exists, say `Project is registered but has no admitted durable evidence yet.` Do not refer to the retired `STATE` page.

### 3.4 Cross-project promotion

Only events already classified as durable may become candidates.

```python
BLOCKED_PROMOTION_TAGS = {
    "lifecycle",
    "session",
    "adapter",
    "workflow_observation",
    "shell",
}

MIN_PROMOTION_PROJECTS = 2
MIN_VERIFIED_PROJECTS = 2
```

A candidate must contain:

- The normalized claim.
- At least two different project IDs.
- At least one admitted durable event from each supporting project.
- At least two verification entries in total.
- Event IDs and repository-relative evidence paths.
- A stable claim key independent of the current project count.

The stable target must be:

```text
wiki/global/<normalized-claim-key>.md
```

Do not create a new page when project count changes from 39 to 40 to 41. Update the same candidate or approved principle.

### 3.5 Capability evidence

Replace the current receipt source semantics with:

```python
PROOF_RECEIPT_SOURCES = {"native-hook", "lifecycle-hook", "ide-extension", "mcp-bridge"}
OBSERVATION_RECEIPT_SOURCES = {"watcher-observed", "cli-context", "file-probe", "explicit-smoke"}
```

Statuses:

| Status | Meaning |
| --- | --- |
| `not_configured` | No supported adapter/configuration found |
| `configured_unverified` | Configuration exists, no qualifying proof |
| `observed_read` | Watcher or CLI observed a read-like event only |
| `observed_write` | Watcher observed a write-like artifact only |
| `verified_read` | A proof source identifies tool, project, operation, timestamp, and evidence |
| `verified_write` | Same requirements for write |
| `verified_bidirectional` | Both qualifying read and write receipts exist for the same tool and project within the verification window |

`watcher-observed` alone must never produce `verified_read`, `verified_write`, or `verified_bidirectional`.

### 3.6 Self-contained runtime

Preserve these existing top-level paths:

```text
RUNTIME_BASE = ~/Library/Application Support/llm-workmem-runtime
APP_VENV     = $RUNTIME_BASE/app/venv
LWM_BIN      = $APP_VENV/bin/lwm
DATA_ROOT    = $RUNTIME_BASE/llm-workmem
```

Target ownership:

```text
$RUNTIME_BASE/
├── app/
│   ├── venv/                 # self-contained Python environment and lwm package
│   └── runtime-manifest.json # installed source/resource/import identity
├── llm-workmem/              # the only entity owner for mutable LLM-WorkMem data
│   ├── wiki/
│   ├── raw/
│   ├── automation/
│   ├── state/
│   ├── llms.txt
│   ├── llms-full.txt
│   └── llms.json
└── logs/                     # installer/runtime diagnostics not owned by DATA_ROOT
```

Runtime/source boundary:

- Build an installable wheel from the source checkout, then install that wheel into `APP_VENV`. Do not use an editable install.
- Treat `RUNTIME_BASE/app` as the atomic install and rollback unit; `venv/` and `runtime-manifest.json` must always move together.
- `LWM_BIN` is the launchd executable. It must import package code from `APP_VENV`, not from the source checkout or `DATA_ROOT/lwm`.
- launchd continues to call `LWM_BIN hub run-supervisor DATA_ROOT` directly. A `bin/run-harvest` wrapper is not required.
- `DATA_ROOT` owns all mutable live data, including `state`. The source checkout exposes mutable paths through symlinks into `DATA_ROOT`.
- The current `DATA_ROOT/state -> source-checkout/state` direction is migration debt. After approved migration, `DATA_ROOT/state` is a physical directory and source-checkout `state` points to it.
- `health.json` has one entity at `DATA_ROOT/state/health.json`; it is not copied or mirrored.
- `DATA_ROOT/lwm` is a legacy code mirror. After the wheel-based runtime passes import and rollback checks, stop generating it and remove it only through the approved Task 9B manifest.
- `sys.path` and `lwm.__file__` must not contain `/Mobile Documents/`.
- Absolute repo symlinks are local access wiring. They do not provide portable or Git-based cross-Mac synchronization.

### 3.7 Health truth

A healthy result requires all of:

```python
healthy = all((
    runtime_import_independent,
    last_cycle_exit_code == 0,
    last_success_at is not None,
    audit_ok,
    eval_pass == eval_total,
    inbox_failed == 0,
    context_smoke_ok,
))
```

Loaded launchd state, configured adapters, or passing unit tests cannot independently make health healthy.

## 4. Acceptance Criteria

| ID | Requirement |
| --- | --- |
| LWM-G01 | Lean Core is named as the authoritative architecture; conflicting V2 authority language is marked superseded. |
| LWM-G02 | Complete prompts, instructions, environment dumps, and command-only observations never enter durable project memory. |
| LWM-G03 | Project pages rebuild deterministically from preserved processed events. |
| LWM-G04 | `lwm context` returns bounded, deduplicated, source-backed project evidence without lifecycle/global noise. |
| LWM-G05 | Cross-project promotion uses admitted durable events and a stable claim key; project-count changes do not create duplicate pages. |
| LWM-G06 | Archive directories and generated reports do not participate in the active wiki graph. |
| LWM-G07 | Watcher observation cannot produce a verified integration status. |
| LWM-G08 | The launchd runtime imports all Python code outside iCloud Drive. |
| LWM-G09 | Audit runs against freshly computed analysis and mandatory eval results, not a stale report. |
| LWM-G10 | A successful scheduled cycle writes one consistent receipt and updates `last_success_at`. |
| LWM-G11 | A real Ather context packet contains meaningful decisions/changes/verifications or explicitly reports insufficient durable evidence. |
| LWM-G12 | Full pytest, Ruff, audit, health, context smoke, recall smoke, and launchd cycle all pass before completion is claimed. |
| LWM-G13 | `wiki`, `raw`, generated exports, and `state` each have one physical entity under `DATA_ROOT`; repo paths are access links and are never called mirrors. |
| LWM-G14 | Before Task 9B, the only permitted launchd change is the explicitly approved Task 0 pause; no live data, symlink direction, legacy runtime code, replacement app, or launchd registration is changed without an approved Task 9A manifest hash and rollback bundle. |

## 5. Implementation Tasks

### Task 0: Freeze the editable production runtime before source edits

The current launchd job imports directly from the source checkout through `_editable_impl_lwm.pth`. Therefore a source edit is already a production runtime change. Task 0 is a hard prerequisite for Tasks 1-8.

**Files:**
- Read only: `~/Library/LaunchAgents/com.ethan.lwm.harvest.plist`
- Approved paused copy: `~/Library/Application Support/llm-workmem-runtime/paused-launchd/com.ethan.lwm.harvest.plist`
- Backup only: `/private/tmp/com.ethan.lwm.harvest.plist.before-goal-completion`

**Preview commands:**

```bash
launchctl print "gui/$(id -u)/com.ethan.lwm.harvest"
shasum -a 256 \
  "$HOME/Library/LaunchAgents/com.ethan.lwm.harvest.plist"
```

- [ ] Show the current job, editable import evidence, proposed paused/backup paths, and live plist hash to the user.
- [ ] Request explicit approval to pause the local job for the implementation window.
- [ ] If approved, copy the plist to the declared `/private/tmp` backup and verify its hash.
- [ ] Run `launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.ethan.lwm.harvest.plist"`.
- [ ] Move the live plist out of `~/Library/LaunchAgents` to the approved paused-plist path.
- [ ] Verify the paused plist and `/private/tmp` backup hashes equal the previewed live plist hash.
- [ ] Verify the live plist is absent and `launchctl print "gui/$(id -u)/com.ethan.lwm.harvest"` no longer finds a loaded job.
- [ ] Do not modify plist contents, live data, runtime app, data symlinks, or source code in Task 0.
- [ ] Keep the job paused until the approved Task 9B installs and reloads the reviewed runtime.

**Stop condition:** The job is paused with explicit approval and a verified plist backup exists. If approval is withheld, stop before Task 1 and report that implementation is blocked by the editable-runtime safety gate.

**Tasks 1-8 recurring guard:** Before every Task, assert both conditions below. If either fails, stop immediately and repeat Task 0 approval instead of continuing.

```bash
test ! -e "$HOME/Library/LaunchAgents/com.ethan.lwm.harvest.plist"
! launchctl print "gui/$(id -u)/com.ethan.lwm.harvest" >/dev/null 2>&1
```

### Task 1: Lock architecture precedence and executable acceptance tests

**Files:**
- Modify: `GLOBAL.md`
- Modify: `docs/superpowers/specs/2026-07-28-llm-workmem-lean-core-design.md`
- Modify: `docs/superpowers/specs/2026-07-18-llm-workmem-v2-control-plane-design.md`
- Create: `tests/test_goal_contract.py`

**Interfaces:**
- `tests/test_goal_contract.py` reads the two design documents and verifies the authority/supersession wording.
- The test also calls public APIs used by LWM-G02, G04, G07, and G08 as they are introduced.

- [ ] Add a `Design precedence` section to Lean Core: Lean Core is current; V2 contributes only non-conflicting acceptance requirements.
- [ ] Add a top-of-file historical notice to V2: unique control-plane authority and `STATE.md` hierarchy are superseded.
- [ ] Correct `GLOBAL.md`: Git synchronizes source code, tests, adapters, and reviewed source documents, but current absolute runtime symlink targets are local and not proven cross-Mac Git content.
- [ ] Write contract tests for the four current false claims: noisy event admitted, archive scanned, watcher marked verified, runtime imports source.
- [ ] Mark each not-yet-implemented contract with strict `pytest.mark.xfail(strict=True, reason="LWM-Gxx implemented by Task N")` so the red phase is explicit without leaving the focused suite failed.
- [ ] Each owning Task must remove its matching `xfail` marker when implementation begins; an unexpected pass is a failure because `strict=True`.
- [ ] Run `uv run --extra dev pytest -q tests/test_goal_contract.py` and confirm only the four named contracts are reported as expected xfails.

**Stop condition:** The precedence text is unambiguous, the focused command exits zero, and exactly four strict xfails map one-to-one to Tasks 2, 3, 6, and 7. Final verification permits zero remaining xfails in `tests/test_goal_contract.py`.

### Task 2: Exclude inactive archives and generated reports from the live graph

**Files:**
- Modify: `lwm/analysis.py`
- Modify: `tests/test_analysis.py`
- Modify: `tests/test_audit_health.py`

**Implementation:**

```python
IGNORED_WIKI_PART_PREFIXES = ("_archive", ".archive")
IGNORED_GENERATED_PAGES = {"current-radar.md"}

def _is_ignored_page(path: Path, wiki_dir: Path) -> bool:
    relative = path.relative_to(wiki_dir)
    if any(
        part.startswith(IGNORED_WIKI_PART_PREFIXES)
        for part in relative.parts[:-1]
    ):
        return True
    if path.name in {"log.md", *IGNORED_GENERATED_PAGES}:
        return True
    return path.parent.name == "summaries" and path.name.startswith("source-events-")
```

- [ ] Pass `wiki_dir` into `_is_ignored_page`.
- [ ] Add a fixture with active and `_archive_*` pages sharing a slug; assert no duplicate.
- [ ] Assert `current-radar.md` cannot report broken links about its own previous output.
- [ ] Preserve the existing direct `run_audit() -> analyze_wiki()` call; add a regression test so it cannot be replaced by reading `current-radar.md`.
- [ ] Do not make `health._audit_summary()` the authoritative cycle audit. Task 8 will pass the full audit/eval result forward instead of running this second weaker `eval_suite=None` audit.
- [ ] Run `uv run --extra dev pytest -q tests/test_analysis.py tests/test_audit_health.py`.

**Stop condition:** The real repository reports zero duplicate slugs without deleting the archived evidence.

### Task 3: Implement the durable-event admission contract

**Files:**
- Modify: `lwm/project_memory.py`
- Modify: `lwm/ingest.py`
- Modify: `tests/test_project_memory.py`
- Modify: `tests/test_ingest.py`

**Implementation:**

```python
DURABLE_EVENT_TYPES = {"decision", "bugfix", "verification", "project_status"}
OPERATIONAL_EVENT_TYPES = {
    "session_start",
    "session_idle",
    "session_deleted",
    "adapter_probe",
    "workflow_observation",
}

def classify_event(event: dict[str, object]) -> EventAdmission:
    event_type = str(event.get("event_type") or "").strip()
    task = str(event.get("task") or "").strip()
    fields = {
        key: _bounded_items(event.get(key))
        for key in ("decisions", "changes", "verification", "open_questions")
    }
    combined = "\n".join([task, *(item for values in fields.values() for item in values)])
    if _contains_noise_marker(combined):
        return EventAdmission("rejected", "instruction_or_environment_dump", None)
    if event_type not in DURABLE_EVENT_TYPES:
        return EventAdmission("operational", "non_durable_event_type", None)
    if event_type == "decision" and fields["decisions"]:
        return EventAdmission("durable", "structured_decision", "decisions")
    if event_type == "bugfix" and fields["changes"] and fields["verification"]:
        return EventAdmission("durable", "verified_bugfix", "bugfixes")
    if event_type == "verification" and fields["verification"]:
        return EventAdmission("durable", "structured_verification", "verifications")
    if event_type == "project_status" and task and any(fields.values()):
        return EventAdmission("durable", "structured_project_status", "status")
    return EventAdmission("operational", "insufficient_durable_fields", None)
```

- [ ] Replace `_is_meaningful_event()` with `classify_event()`.
- [ ] Make `event_entry()` accept the classification and bounded normalized fields.
- [ ] Ensure `ingest.run()` still preserves accepted raw JSON even when materialization classifies it operational.
- [ ] Add tests for `AGENTS.md`, `<environment_context>`, shell command, long text, malformed arrays, valid decision, verified bugfix, verification, and structured status.
- [ ] Assert no secret-like fixture text appears in the rendered project page.
- [ ] Run `uv run --extra dev pytest -q tests/test_project_memory.py tests/test_ingest.py tests/test_privacy.py`.

**Stop condition:** Operational evidence remains in raw storage but cannot update a project page.

### Task 4: Rebuild all project pages from admitted source events

**Files:**
- Modify: `lwm/project_memory.py`
- Modify: `lwm/central_cli.py`
- Create: `tests/test_project_rebuild.py`

**CLI:**

```text
lwm hub rebuild-projects <root> [--dry-run] [--project-id ID]
```

**Implementation sequence:**

```python
def rebuild_project_pages(root: Path, project_id: str | None = None, dry_run: bool = False) -> RebuildReport:
    events = load_processed_events(root)
    admitted = [
        event for event in events
        if matches_project(event, project_id)
        and classify_event(event).durability == "durable"
    ]
    pages = aggregate_project_pages(admitted)
    return reconcile_generated_pages(root, pages, dry_run=dry_run)
```

- [ ] Build pages in a temporary in-memory map; do not append to existing derived content.
- [ ] Deduplicate by `event_id`; for legacy missing IDs use a stable hash of project, timestamp, event type, and normalized content.
- [ ] Derive `updated` from the newest admitted timestamp.
- [ ] Implement `--dry-run` report with counts and target paths but no writes.
- [ ] Test byte-identical second rebuild.
- [ ] Test that a polluted existing page is replaced from clean raw durable events.
- [ ] Test that raw files are unchanged by comparing hashes before and after.
- [ ] Run dry-run against the real `DATA_ROOT` and save the removal/write manifest for Task 9A.
- [ ] Do not run the real rebuild in Task 4; Task 9B owns all real project-page writes after approval.

**Stop condition:** Isolated fixtures prove deterministic cleanup, the real dry-run enumerates all 27 current project pages without writing them, and raw event hashes are unchanged.

### Task 5: Bound context and eliminate promotion noise

**Files:**
- Modify: `lwm/context.py`
- Modify: `lwm/insights.py`
- Modify: `lwm/promote.py`
- Modify: `tests/test_context.py`
- Modify: `tests/test_conflict_insights.py`
- Modify: `tests/test_promotion.py`

**Implementation:**

```python
def _approved_global_pages(root: Path) -> list[Path]:
    pages = []
    for path in sorted((root / "wiki" / "global").glob("*.md")):
        metadata = read_frontmatter(path)
        tags = {tag.lower() for tag in metadata.tags}
        if metadata.page_type != "principle" or metadata.status != "approved":
            continue
        if tags & BLOCKED_PROMOTION_TAGS:
            continue
        pages.append(path)
    return pages

def stable_claim_key(tag: str, summary: str) -> str:
    normalized = normalize_claim(summary)
    return slugify(f"{tag}-{sha256(normalized.encode()).hexdigest()[:12]}")
```

- [ ] Replace unfiltered `wiki/global/*.md` loading with `_approved_global_pages()`.
- [ ] Bound and deduplicate every project section using `CONTEXT_LIMITS`.
- [ ] Replace the stale `STATE page` warning.
- [ ] Remove absolute paths from default Markdown rendering.
- [ ] Filter candidate generation through `classify_event()`.
- [ ] Block lifecycle/session/adapter/shell tags.
- [ ] Use stable claim keys so project-count changes update one page.
- [ ] Add a cleanup planner that lists existing `recurring-tag-lifecycle-*` pages and confirms raw support remains; it must not remove them outside Task 9B.
- [ ] Run `uv run --extra dev pytest -q tests/test_context.py tests/test_conflict_insights.py tests/test_promotion.py`.

**Stop condition:** Isolated context fixtures contain no complete instructions, environment dumps, or recurring lifecycle pages and remain below `MAX_CONTEXT_CHARS`; real cleanup remains preview-only until Task 9B.

### Task 6: Correct capability receipt semantics

**Files:**
- Modify: `lwm/capabilities.py`
- Modify: `lwm/lifecycle.py`
- Modify: `lwm/runner.py`
- Modify: `tests/test_capability_probe.py`
- Modify: `tests/test_lifecycle.py`
- Modify: `tests/test_codex_export.py`

**Implementation:**

```python
PROOF_RECEIPT_SOURCES = {"native-hook", "lifecycle-hook", "ide-extension", "mcp-bridge"}
OBSERVATION_RECEIPT_SOURCES = {"watcher-observed", "cli-context", "file-probe", "explicit-smoke"}

def capability_status(read_receipt: dict | None, write_receipt: dict | None) -> str:
    read_verified = is_current_proof(read_receipt)
    write_verified = is_current_proof(write_receipt)
    if read_verified and write_verified:
        return "verified_bidirectional"
    if read_verified:
        return "verified_read"
    if write_verified:
        return "verified_write"
    if read_receipt:
        return "observed_read"
    if write_receipt:
        return "observed_write"
    return "configured_unverified"
```

- [ ] Stop treating `watcher-observed` as `NATIVE_RECEIPT_SOURCES`.
- [ ] Include `evidence_path`, `project_id`, `operation_id`, and `timestamp` in proof receipts.
- [ ] Require read/write proof for the same project.
- [ ] Update watcher assertions only in `tests/test_capability_probe.py`, `tests/test_lifecycle.py`, and `tests/test_codex_export.py` to expect observed statuses.
- [ ] Do not edit unrelated green tests merely to preserve the old test count or suppress a failure.
- [ ] Add one explicit smoke receipt fixture that qualifies as bidirectional.
- [ ] Ensure health and adapter rendering use the corrected statuses.
- [ ] Run `uv run --extra dev pytest -q tests/test_capability_probe.py tests/test_lifecycle.py tests/test_codex_export.py`.

**Stop condition:** No watcher-only fixture is reported as verified, all named focused tests pass under the corrected contract, and the final suite is reported by pass/fail rather than comparison with the historical `310` count.

### Task 7: Make the launchd runtime genuinely self-contained

**Files:**
- Modify: `lwm/harvest.py`
- Create: `lwm/resources/__init__.py`
- Create: `lwm/resources/eval-suite.txt`
- Modify: `pyproject.toml` only if Hatch does not include the resource by default
- Modify: `tests/test_schedule.py`
- Create: `tests/test_runtime_install.py`

**Implementation requirements:**

```python
@dataclass(frozen=True)
class RuntimePaths:
    runtime_base: Path
    app_venv: Path
    lwm_bin: Path
    data_root: Path
    state_root: Path

@dataclass(frozen=True)
class RuntimeInstallReport:
    paths: RuntimePaths
    staging_root: Path
    staged_venv: Path
    manifest_path: Path
    source_revision: str
    package_version: str
    file_hashes: dict[str, str]
    import_probe: dict[str, object]

def runtime_paths(root: Path, *, home: Path | None = None) -> RuntimePaths:
    ...

def build_runtime_app_staging(root: Path, *, home: Path | None = None) -> RuntimeInstallReport:
    ...

def verify_runtime_import(python_path: Path) -> tuple[bool, dict[str, object]]:
    ...
```

Runtime probe command generated by `verify_runtime_import`:

```bash
"$STAGED_VENV/bin/python" -I -c \
  'import json,lwm,sys; print(json.dumps({"module": lwm.__file__, "path": sys.path}))'
```

- [ ] Make `runtime_paths()` return the current real split: `runtime_base/app/venv` and `runtime_base/llm-workmem`; do not nest `app` under `data_root`.
- [ ] Build a wheel from the checkout into a temporary staging directory.
- [ ] Create a staging venv and install the wheel non-editably. Do not install with `pip install -e` and do not add the source checkout to a `.pth` file.
- [ ] Run `verify_runtime_import(report.staged_venv / "bin" / "python")`; reject any result that imports from the live app, source checkout, or `DATA_ROOT/lwm`.
- [ ] Do not replace the live `runtime_base/app` in Task 7. Return `staging_root`, `staged_venv`, `manifest_path`, and install/rollback actions for Task 9A review.
- [ ] Keep launchd's direct `app/venv/bin/lwm hub run-supervisor DATA_ROOT` contract. Do not add a required `bin/run-harvest`.
- [ ] Stop `_render_schedule_runner()` from inserting `DATA_ROOT` into `sys.path`; installed code must come from `APP_VENV`.
- [ ] Define `staging_root` as a complete candidate app directory containing `venv/` and `runtime-manifest.json`.
- [ ] Store source revision, wheel hash, package version, packaged-resource hash, and import evidence in `staging_root/runtime-manifest.json`; do not write into live `runtime_base/app`.
- [ ] Test paths containing spaces and an unavailable source checkout after installation.
- [ ] Seed `lwm/resources/eval-suite.txt` from the current cases so wheel-resource packaging can be tested before Task 8 changes audit semantics.
- [ ] Test that `lwm.__file__`, traceback paths, `sys.path`, and installed `.pth` files contain no `Mobile Documents`.
- [ ] Test with `importlib.resources` that the built wheel contains a readable, non-empty `lwm/resources/eval-suite.txt`.
- [ ] Keep `materialize_runtime_layout()` returning `DATA_ROOT` for existing callers; cover the exact return contract in `tests/test_schedule.py`.
- [ ] Add a non-destructive `plan_mutable_ownership_migration()` report for the current reversed `state` link and legacy `DATA_ROOT/lwm` tree. This function must not modify either path.
- [ ] Do not reinstall or reload launchd in Task 7. Task 9B owns that operation after approval.
- [ ] Run `uv run --extra dev pytest -q tests/test_schedule.py tests/test_runtime_install.py`.

**Stop condition:** The staging runtime imports only from `report.staged_venv`, the generated plist still points to the future live `LWM_BIN` and `DATA_ROOT`, and the live `runtime_base/app`, data links, and launchd registration are unchanged.

### Task 8: Make supervisor, audit, eval, and health one truthful transaction

**Files:**
- Modify: `lwm/runner.py`
- Modify: `lwm/supervisor.py`
- Modify: `lwm/health.py`
- Modify: `lwm/audit.py`
- Modify: `lwm/central_cli.py`
- Modify: `lwm/cycle_state.py`
- Modify: `lwm/loop_state.py`
- Modify: `lwm/resources/eval-suite.txt`
- Modify: `tests/test_supervisor_loop.py`
- Modify: `tests/test_audit_health.py`
- Modify: `tests/test_eval.py`

**Receipt:**

```python
@dataclass(frozen=True)
class CycleReceipt:
    cycle_id: str
    started_at: str
    completed_at: str
    source_revision: str
    runtime_revision: str
    runtime_manifest_sha256: str
    runtime_module_path: str
    runtime_sys_path: tuple[str, ...]
    ingest_failed: int
    audit_ok: bool
    eval_pass: int
    eval_total: int
    eval_suite_sha256: str
    context_smoke_ok: bool
    context_sha256: str
    health_sha256: str
    exit_code: int
    evidence_hashes: dict[str, str]
```

- [ ] Add `audit_report: AuditReport | None = None` to `health.collect()` and `health.collect_and_write()`.
- [ ] When `audit_report` is provided, health must use that exact analysis/schema/review/eval result. When absent, a quick diagnostic may run but `eval_verified` remains false and strict health cannot become healthy.
- [ ] Run stages in this order: adapters → ingest → project rebuild → analysis/audit/eval → context smoke → exports → single-entity health write.
- [ ] Keep one in-memory `AuditReport`; remove the authoritative use of `health._audit_summary(root)` with `eval_suite=None`.
- [ ] Move the authoritative eval cases to packaged `lwm/resources/eval-suite.txt`; load them with `importlib.resources`. Keep `wiki/eval-suite.txt` untouched until Task 9B decides whether to archive it.
- [ ] Make `lwm audit ROOT` and the scheduled cycle use the packaged suite by default while preserving an explicit `--eval-suite PATH` override.
- [ ] Write one cycle receipt atomically to `DATA_ROOT/state`. Repository access follows its `state` symlink; do not write or describe a second mirror.
- [ ] Store each immutable receipt at `DATA_ROOT/state/cycles/<cycle_id>.json` using exclusive creation. Never overwrite a cycle-ID receipt; update `last-cycle.json` only as a pointer containing the selected cycle ID and receipt hash.
- [ ] Hash the runtime manifest, packaged eval suite, context smoke output, health payload, and every evidence file before committing the receipt.
- [ ] Update `last_success_at` only when every healthy predicate passes.
- [ ] Preserve the last successful receipt when a later cycle fails; write failure separately as `last_attempt`.
- [ ] A supervisor `not_due` receipt must not replace the last full-cycle success used by health.
- [ ] Add `lwm hub verify-cycle ROOT --strict`: read the immutable cycle receipt selected by `last-cycle.json`, verify its receipt hash, all `evidence_hashes`, runtime module/sys.path, audit/eval/context/health fields, print the verdict, and do not collect or write a new health snapshot.
- [ ] Limit error summaries while linking to full logs.
- [ ] Add tests for success, audit failure, eval failure, context failure, interrupted write, stale receipt, and a `not_due` supervisor pass after a failed full cycle.
- [ ] Run `uv run --extra dev pytest -q tests/test_supervisor_loop.py tests/test_audit_health.py tests/test_eval.py`.

**Stop condition:** A controlled success produces healthy state from one full audit/eval object; `verify-cycle --strict` can validate it without writing state; a controlled failure or `not_due` supervisor pass cannot overwrite full-cycle truth or claim health.

### Task 9: Preview, approve, then perform migration

**Files:**
- Generated via supported commands: `wiki/projects/*.md`
- Generated via supported commands: approved `wiki/global/*.md` cleanup
- Generated: `wiki/insights/current-radar.md`
- Generated: `wiki/overview.md`
- Generated: `llms.txt`, `llms-full.txt`, `llms.json`
- Generated runtime state and logs

#### Task 9A: Non-destructive preview gate

Task 9A is pre-approved because it reads and hashes data but does not rewrite, remove, relink, reload, or stage live files.

- [ ] Capture `git status --short`; record the pre-existing unrelated dirty paths separately.
- [ ] Record `ls -ld` plus `readlink` for repo/runtime `wiki`, `raw`, `state`, exports, `LWM_BIN`, and the launchd plist.
- [ ] Record the current inbox/processed file lists, including `/private/tmp/lwm-raw-events-before.files`. Hash every existing file under physical `DATA_ROOT/raw/events/processed` into `/private/tmp/lwm-raw-events-before.sha256`.
- [ ] Hash the 27 current project pages and 3 current `recurring-tag-lifecycle-*` pages into `/private/tmp/lwm-derived-pages-before.sha256`.
- [ ] Create a read-only backup bundle under `/private/tmp/lwm-goal-completion-backup-<timestamp>/` containing the complete live `RUNTIME_BASE/app` directory, complete `DATA_ROOT/wiki`, `DATA_ROOT/state` or its current link metadata plus repo-owned state, `DATA_ROOT/lwm`, `overview.md`, `current-radar.md`, all three exports, repo mutable-link metadata, and the Task 0 paused launchd plist.
- [ ] Hash every backup artifact and archive the bundle as `/private/tmp/lwm-goal-completion-backup-<timestamp>.tar.gz`.
- [ ] Build a fresh final staging app from the post-Task-8 source revision; record its revision, wheel hash, staging path, and import probe. Do not reuse an earlier Task 7 staging build.
- [ ] Use the staged Python to read and parse packaged `lwm/resources/eval-suite.txt`; record resource path/hash/case count and run a read-only staged `lwm audit DATA_ROOT` smoke before approval.
- [ ] Run `lwm hub rebuild-projects "$DATA_ROOT" --dry-run`.
- [ ] Run `plan_mutable_ownership_migration()` without applying it.
- [ ] Render the candidate plist without installing it and include its exact diff from the backed-up live plist.
- [ ] Produce `/private/tmp/lwm-goal-completion-manifest-<timestamp>.json` with exact `write`, `remove`, `replace_symlink`, `install_app`, `remove_legacy_runtime_code`, and `reload_launchd` actions plus explicit `allowed_generated_paths` and `allowed_append_only_paths`.
- [ ] Include rollback commands and backup hashes in the manifest.
- [ ] Compute the manifest SHA-256 and derive `approval_id = lwm9b-<first 16 hex characters>`.
- [ ] Stop and request explicit user approval of that exact `approval_id` and full SHA-256. Generic “continue”, approval of an older manifest, or silence is not approval.

Use the same locale and ordering contract for the before/after raw file lists:

```bash
find "$DATA_ROOT/raw/events/processed" -type f -name '*.json' -print \
  | LC_ALL=C sort \
  > /private/tmp/lwm-raw-events-before.files

while IFS= read -r path; do
  shasum -a 256 "$path"
done < /private/tmp/lwm-raw-events-before.files \
  > /private/tmp/lwm-raw-events-before.sha256
```

**Task 9A stop condition:** The user has received the exact immutable manifest path/hash/approval ID, existing-raw hash, complete backup path/hash, launchd diff, and rollback procedure. No live path has changed.

#### Task 9B: Approved live migration

Do not execute any item in Task 9B until Task 9A receives explicit approval.

Execution record for the approval received on 2026-08-05: the manifest-bound
data-owner subset was executed locally. Manifest verification, backup/hash
verification, physical `state` ownership cutover, repository access-link
verification, raw preservation, and one owner-root manual cycle are complete.
The app venv was rebuilt after two receipt-contract fixes. The plist install,
launchd reload/kickstart, legacy code-mirror removal, and any deployment were
intentionally not executed.

Current bounded re-validation on 2026-08-09:

- **PASS:** Execution manifest `/private/tmp/lwm-goal-completion-manifest-20260809-task9b.json` verified with approval id `lwm9b-894baa3e35760018`; current post-verification manifest `/private/tmp/lwm-goal-completion-manifest-20260809-task9b-current.json` also verifies with approval id `lwm9b-13eb131afc968159`.
- **PASS:** Execution rollback archive `/private/tmp/lwm-goal-completion-backup-20260809T110000Z.tar.gz` exists and is bound by the execution manifest with SHA-256 `f4abbf0f43c5d480ec21b9cd7e42001a37d63839226bb424bfa59abf64beea81`; current post-verification archive `/private/tmp/lwm-goal-completion-backup-20260809T111500Z.tar.gz` has SHA-256 `dcca3865e922bd280e06072fbb6a439706d2e4f7de9e04638117b379bf3c2409`.
- **PASS:** `hub migrate-data-owner` returned `applied=true`, `scope=data-owner-only`; ownership issues remain empty and all runtime entities are physical owners with repository access symlinks.
- **PASS:** launchd plist mtimes are unchanged; no deployment, reload, or kickstart occurred; raw event IDs remain unique and no processed raw event record was deleted.
- **PASS-CORE / PARTIAL-BOUNDARY:** `cycle-5c2002c7bd5f` is core-success and immutable. It is bound to the runtime generation active when that cycle ran, not the later current manifest; strict verification now reports `runtime_manifest_hash_mismatch` and `health_status:degraded` because the runtime was refreshed afterward and launchd remains unloaded. No second cycle was run under the one-cycle authorization.
- **PASS:** The refreshed installed runtime directly executes the Antigravity-only
  CLI install path in a temporary home, writes `~/.gemini/config/hooks.json`,
  and imports `lwm` from runtime `site-packages`; this is configuration proof,
  not real Antigravity host firing proof.
- **NOT RUN:** Launchd reload, legacy code-mirror removal, rollback execution, and human Ather-context review remain outside this bounded run.

- [ ] Verify the approved manifest's full SHA-256 and `approval_id`; abort and return to Task 9A for reapproval on any manifest drift.
- [ ] Verify Task 9A backup and all pre-existing source hashes still match immediately before migration; abort on drift.
- [ ] Confirm the Task 0 launchd pause is still in effect before changing `state` ownership.
- [ ] Copy repo-owned `state` to a staging directory under `DATA_ROOT`, compare file hashes, atomically replace the current reverse state symlink, then replace repo `state` with a symlink into `DATA_ROOT/state`.
- [ ] Re-verify the staged self-contained app and atomically install the complete candidate directory as `RUNTIME_BASE/app`, including both `venv/` and `runtime-manifest.json`; retain the prior complete app as one rollback generation.
- [ ] Verify import independence before removing the legacy `DATA_ROOT/lwm` code mirror.
- [ ] Run the approved project rebuild and supported generated-global cleanup. Do not use broad recursive deletion.
- [ ] Perform a pre-reload changed-path comparison with the approved manifest; abort and roll back on any extra path.
- [ ] Install the reviewed plist only if its `ProgramArguments` remain `LWM_BIN hub run-supervisor DATA_ROOT`.
- [ ] Reload and kickstart `com.ethan.lwm.harvest`.
- [ ] Wait for one bounded cycle to complete.
- [ ] Run the full verification commands below.
- [ ] Inspect Ather context manually for relevance and absence of prompt/environment leakage.
- [ ] Verify every pre-migration processed raw file still exists with the same content hash. List newly processed event files separately, validate their JSON/event IDs, and tie them to the new cycle; new append-only files do not invalidate old-file preservation.
- [ ] Confirm each mutable repo path resolves to exactly one entity under `DATA_ROOT`.
- [ ] Record one sanitized `verification` event containing exact commands and results.
- [ ] Perform a final changed-path comparison after the cycle, context checks, and verification event. Permit only exact manifest actions, the named generated files, cycle-ID state/receipt files, declared append-only logs, and separately validated new raw event IDs. Roll back on any other path.
- [ ] Stage only files changed by this plan; leave pre-existing unrelated worktree changes untouched.

**Rollback boundary:**

- Restore the prior launchd plist from the Task 0 paused copy and restore the prior complete `RUNTIME_BASE/app` generation.
- Restore repo `state` from the Task 9A archive and restore the original `DATA_ROOT/state -> repo/state` symlink.
- Restore derived pages from the archive.
- Do not roll back or rewrite `raw/events/processed`. Every pre-migration file hash must remain identical; separately validated new append-only events remain present and do not participate in the old-file-set equality check.

**Task 9B stop condition:** Every LWM-G acceptance criterion has current external evidence, and the final report distinguishes code tests, runtime proof, migration proof, and human context review.

## 6. Required Test Fixtures

Use these exact semantic fixtures:

```python
NOISY_EVENTS = [
    {"event_type": "workflow_observation", "task": "# AGENTS.md instructions\nYou are Codex..."},
    {"event_type": "workflow_observation", "task": "<environment_context>...</environment_context>"},
    {"event_type": "workflow_observation", "task": "git status --short"},
    {"event_type": "session_start", "task": "Ather session started"},
]

DURABLE_EVENTS = [
    {
        "event_type": "decision",
        "task": "Lock the auxiliary evidence boundary",
        "decisions": ["Native tool instructions remain authoritative"],
        "verification": ["Lean Core design reviewed"],
    },
    {
        "event_type": "bugfix",
        "task": "Exclude archived review pages from active analysis",
        "changes": ["Ignore wiki path parts beginning with _archive"],
        "verification": ["analysis test reports zero duplicate slugs"],
    },
    {
        "event_type": "verification",
        "task": "Verify scheduled memory cycle",
        "verification": ["launchd exit code 0", "audit passed", "health healthy"],
    },
]
```

Tests must assert meaning, not only file existence:

- No string from `NOISY_EVENTS` appears in project Markdown or context Markdown.
- Every durable output can be traced to an event ID.
- Rebuild twice gives the same output.
- Changing event order does not change output.
- A watcher receipt remains observed.
- An explicit smoke receipt can become verified.
- Runtime import path is outside iCloud.
- Health fails if any one required predicate is false.

## 7. Full Verification Commands

Set the root once:

```bash
ROOT="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
ATHER="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather"
RUNTIME_BASE="$HOME/Library/Application Support/llm-workmem-runtime"
DATA_ROOT="$RUNTIME_BASE/llm-workmem"
APP_PY="$RUNTIME_BASE/app/venv/bin/python"
LWM_BIN="$RUNTIME_BASE/app/venv/bin/lwm"
cd "$ROOT"
```

Static and automated verification:

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
! rg -n 'pytest[.]mark[.]xfail' tests/test_goal_contract.py
```

Runtime verification:

```bash
launchctl print "gui/$(id -u)/com.ethan.lwm.harvest"
"$LWM_BIN" analyze "$DATA_ROOT"
"$LWM_BIN" audit "$DATA_ROOT"
"$LWM_BIN" hub verify-cycle "$DATA_ROOT" --strict
"$APP_PY" \
  -I -c 'import json,lwm,sys; print(json.dumps({"module":lwm.__file__,"path":sys.path}, indent=2))'
plutil -p "$HOME/Library/LaunchAgents/com.ethan.lwm.harvest.plist"
```

The runtime output must contain no `/Mobile Documents/`.
The plist must invoke `$RUNTIME_BASE/app/venv/bin/lwm hub run-supervisor $DATA_ROOT`.

Mutable ownership verification after approved Task 9B:

```bash
for path in wiki raw state llms.txt llms-full.txt llms.json; do
  ls -ld "$ROOT/$path"
  readlink "$ROOT/$path"
done

test ! -L "$DATA_ROOT/wiki"
test ! -L "$DATA_ROOT/raw"
test ! -L "$DATA_ROOT/state"
```

Every repo link must resolve into `DATA_ROOT`. The three `DATA_ROOT` directories must be physical directories, not links.

Real context and recall verification:

```bash
"$LWM_BIN" hub context \
  --tool codex \
  --project "$ATHER" \
  "$DATA_ROOT"

"$LWM_BIN" hub recall \
  "What verified decisions and fixes are current for Ather?" \
  --project "$ATHER" \
  "$DATA_ROOT"
```

Leak check:

```bash
rg -n -i \
  '(<environment_context>|# agents\.md instructions|you are codex|command timed out)' \
  "$ROOT/wiki/projects" "$ROOT/wiki/global" "$ROOT/llms.txt" "$ROOT/llms-full.txt"
```

Expected exit status: `rg` returns 1 because no match exists.

Generated-noise check:

```bash
find "$ROOT/wiki/global" -maxdepth 1 -name 'recurring-tag-lifecycle-*' -print
```

Expected output: empty.

Raw preservation check:

```bash
shasum -a 256 -c /private/tmp/lwm-raw-events-before.sha256

find "$DATA_ROOT/raw/events/processed" -type f -name '*.json' -print \
  | LC_ALL=C sort \
  > /private/tmp/lwm-raw-events-after.files

comm -13 \
  /private/tmp/lwm-raw-events-before.files \
  /private/tmp/lwm-raw-events-after.files \
  > /private/tmp/lwm-raw-events-new.files
```

Expected result: every pre-migration hash reports `OK`. New files are allowed only when separately validated as append-only events produced by the approved verification cycle.

## 8. Engineer Completion Report

The implementing engineer must report in this exact structure:

```text
Verified:
- Task 0 editable-runtime freeze:
- Full tests:
- Ruff:
- Audit/eval:
- Health:
- Runtime module path:
- Runtime/data ownership:
- Scheduled cycle receipt:
- Ather context review:
- Raw event hash comparison:
- Task 9A manifest approval:
- Task 9B migration/rollback evidence:

Changed:
- Source files:
- Generated files:
- Runtime files:

Not changed:
- Raw source evidence:
- Native tool authority:
- Unrelated dirty worktree files:

Remaining unknowns:
- None, or list each unverified item with owner and next command.

Acceptance:
- LWM-G01 ... PASS/FAIL + evidence
- LWM-G02 ... PASS/FAIL + evidence
- LWM-G03 ... PASS/FAIL + evidence
- LWM-G04 ... PASS/FAIL + evidence
- LWM-G05 ... PASS/FAIL + evidence
- LWM-G06 ... PASS/FAIL + evidence
- LWM-G07 ... PASS/FAIL + evidence
- LWM-G08 ... PASS/FAIL + evidence
- LWM-G09 ... PASS/FAIL + evidence
- LWM-G10 ... PASS/FAIL + evidence
- LWM-G11 ... PASS/FAIL + evidence
- LWM-G12 ... PASS/FAIL + evidence
- LWM-G13 ... PASS/FAIL + evidence
- LWM-G14 ... PASS/FAIL + evidence
```

## 9. Definition of Done

This plan is complete only when:

1. The active architecture has one explicit authority boundary.
2. Durable memory contains verified work, not tool exhaust.
3. Derived project pages can be deleted and rebuilt from preserved source evidence.
4. Context is bounded, relevant, and source-traceable.
5. Promotions are stable claims, not changing project-count reports.
6. Capability labels reflect real proof strength.
7. launchd executes self-contained runtime code outside iCloud.
8. Audit, eval, health, and scheduled cycle agree on one result.
9. A real Ather recall demonstrates useful cross-session evidence.
10. Every mutable logical path resolves to one physical entity under `DATA_ROOT`.
11. Task 9B received explicit approval and completed with verified rollback evidence. If approval is withheld, the implementation remains incomplete at the migration gate and must be reported that way.
12. The engineer supplies current evidence for all fourteen acceptance criteria.

Passing unit tests alone, creating a new command, loading launchd, or producing a context response does not satisfy this Definition of Done.
