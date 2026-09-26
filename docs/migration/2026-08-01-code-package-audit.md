# LLM-WorkMem Code Package Audit

Date: 2026-08-16

Scope: local source code, tests, wheel, temporary staging, the local app
runtime venv, the approved Task 9B data-owner migration, the authorized manual
supervisor cycle, and the Task 9D Codex/Gemini native-hook cutover. No launchd reload or deployment was performed, and no raw
evidence was deleted. The explicitly authorized cleanup quarantined only
self-generated bridge simulation artifacts and restored the pre-test
capability receipt; the local app venv was materialized from the verified wheel
and the previous venv was retained.

## Latest Local-Only Verification (2026-08-16)

- Harvest snapshot privacy now redacts configuration key/value pairs,
  structured token values, PEM private-key blocks, and delimiter-containing
  `sk-` values before bounded tool snapshots are written. The final source
  suite is `647 passed`; Ruff and `git diff --check` also pass.
- Five initially affected snapshot/event files and two remaining historical
  Claude snapshots were backed up into permission-700 quarantine directories
  under `/private/tmp` and replaced in place with redacted content. No raw
  event was deleted. The final raw/derived credential-shaped scan found `0`
  matching files.
- The current non-editable runtime is
  `runtime-20260816T020548Z-aa7ee6ed`, importing from runtime `site-packages`
  with no iCloud path.
- The explicitly authorized Task 9B local data-owner migration used the
  current 342-entry manifest
  `/private/tmp/lwm-goal-completion-manifest-20260814T145119Z.json`, approval
  id `lwm9b-a75435dffeb58934`, and rollback archive
  `/private/tmp/lwm-goal-completion-backup-20260814T145119Z.tar.gz`. It
  returned `applied=true` with scope `data-owner-only`; no deployment,
  launchd reload, or project rebuild occurred.
- The one authorized manual supervisor cycle is `cycle-10d657108685`:
  `core_status=success`, `overall_status=success`, `processed=24`,
  `rejected=64`, `failed=0`, audit `0`, eval `2/2`, and CBMEM healthy. No
  second cycle was run.
- After that cycle, the security-rule correction required a runtime refresh.
  Strict receipt verification therefore truthfully reports only
  `runtime_manifest_hash_mismatch` and `health_status:degraded`; it is not
  valid to present the receipt as bound to the newer runtime. Non-strict health
  is `healthy`, while launchd remains intentionally unloaded.

Requirement-by-requirement status is tracked separately in
`docs/migration/2026-08-01-requirements-verification-matrix.md`; this report is
the implementation/package audit, not a live-host completion certificate.

## Latest Legacy Promotion Boundary Correction (2026-08-15)

The retired `lwm/promote.py:auto_promote_all` compatibility path no longer
writes `wiki/global/`. It records a fail-closed legacy decision instead. The
old `hub promote --auto` CLI is now rejected with exit code `2`; global memory
must use the stateful `hub review-analysis` followed by
`hub promote-analysis` path, which carries candidate state and explicit
evidence IDs. This removes the remaining code-level second promotion
authority without deleting historical candidate or raw evidence.

Focused promotion/CLI/health regression is `46 passed`; the full source suite
is `638 passed`, Ruff passes, and an installed-runtime smoke returned exit code
`2` with no files in its isolated root. The refreshed runtime is
`runtime-20260815T143452Z-aa7ee6ed`, with import from non-editable
`site-packages` and `icloud_on_path=[]`. No launchd reload, supervisor cycle,
deployment, raw deletion, or Ather operation occurred.

## Implemented In Code

- Truthful admission and deterministic project rebuild are the only path from
  processed raw events to durable project pages.
- Normal ingest no longer auto-promotes candidates. Promotion is explicit and
  supporting events must pass the durable-event admission contract.
- Cycle receipts are immutable per-cycle files. Successful cycles update
  `latest-cycle.json`; failed or warning cycles update `last-attempt.json` and
  do not replace the last successful cycle.
- Full-cycle supervisor health is committed exactly once before the immutable
  receipt is written; the supervisor no longer rewrites health after the
  receipt, and verification now reads the complete warning/failed pointer.
- The supervisor now runs the optional Memory Compiler stage after candidate
  synthesis and records its bounded result in `CycleReceiptV2`; disabled or
  unavailable analysis remains non-core and cannot be reported as verified.
  Structured candidates are now explicitly seeded into the compiler queue;
  human review and accepted-candidate Context recall are exposed through the
  shared hub service and CLI.
- `EnvApiProvider` is now a real vendor-neutral OpenAI-compatible transport:
  local endpoints can run without a key, remote endpoints require one, and
  requests enforce timeout, model/token bounds, response-size limits and
  structured JSON classification without persisting credentials. The Memory
  Compiler now rejects unknown provider fields/evidence drift, uses the
  documented `retry_wait` state, records valid transitions with actor and
  evidence hash, and reconciles conservative budget reservations with API
  `usage.total_tokens` when available.
- Workflow and relationship candidate synthesis now reuses the durable event
  admission classifier; operational observations and repeated tags alone do
  not create candidates. The public optional-analysis entry point also shares
  the cycle writer lock, so retry/usage/candidate state cannot race a full
  supervisor pass. Candidate persistence is idempotent: a repeated cycle
  cannot reset a pending, accepted, rejected or corrected review record, and
  one-shot evidence iterators are materialized once for both candidate kinds.
- Stable promotion now accepts an explicit evidence-id set from a validated
  compiler candidate, writes one claim-keyed global page with the correct
  pattern/relationship/principle type, and records event ids, reasons and a
  rollback backup when replacing an existing page. The old promotion module
  remains only as an explicit compatibility surface.
- `lwm hub tools probe` and `lwm hub behavior sync` are now exposed as stable
  public entry points. MCP/CLI receipt calls accept explicit evidence and
  operation IDs, while default calls remain observation-only.
- Event schema v2 now carries bounded `task_id`, `handoff_id`, operation and
  source-receipt links. A native Stop hook accepts only a structured summary:
  it creates one active handoff, emits a durable decision/bugfix/verification
  event when structured evidence exists, and binds the two with evidence IDs.
  Raw last-user text remains operational only and never becomes handoff data.
- Claude Code, OpenCode, Codex, Gemini CLI and Antigravity now have explicit
  native-hook proof bindings in the registry. Installation and temporary
  bridge smoke are not host proof: until the real host emits a qualifying
  receipt, coverage remains `configured_unverified`. Generic shell, VS Code,
  Kiro and Trae now have real local lifecycle proof; MiniMax remains a
  file/database observer.
- MCP sparse event requests now receive valid schema defaults instead of
  serializing `null` for `importance` or `privacy`.
- Shell sweep now processes every valid JSONL line instead of only the last
  line in each file, preserves compatibility with the old seen-key format,
  and identifies registered CLI names such as Gemini, OpenCode, Codex and
  Claude Code without storing a second copy of the command as identity.
- Tool probing now reports `collector_status=ready|missing|not_applicable`;
  an empty collector list is no longer reported as an importable collector.
  Generated Cursor/Gemini and shared tool instructions now expose the same
  bounded structured write-back and handoff command contract.
- The explicit shell recorder accepts a tool id, task id, handoff id, risks
  and other structured evidence fields, so shell-launched tools can write
  back through the same event schema rather than a shell-only event shape.
- CLI and MCP event submission plus startup Context rendering now call the
  same `lwm.hub_service` business functions. Sparse payload defaults,
  canonical project resolution, validation, inbox writes and observation
  receipts therefore cannot diverge by transport.
- Public lifecycle calls now default to `watcher-observed`; only an actual
  host integration that explicitly supplies `native-hook` can create a proof
  receipt. The default can no longer turn a manual CLI/Agent command into
  false native-integration evidence.
- `lwm hub retain`, MCP `lwm_retain` and the memory API now share the canonical
  Retain service and deterministic duplicate suppression.
- Generated MiniMax shell wrappers no longer contain an Ethan/iCloud absolute
  path; they use `LWM_ROOT` or the standard local runtime data-root fallback.
- Global installation dry-runs no longer write generated files. The generated
  launcher now resolves the canonical `Application Support/llm-workmem-runtime`
  app environment instead of guessing from a repository symlink.
- Direct Claude and shell hooks no longer fall back to an iCloud checkout. The
  shell hook uses the runtime data root, supports `LWM_SHELL_HOOK=0` with the
  legacy opt-out preserved, and the legacy Claude installer accepts `--root`.
- Shell CLI identity now resolves through the versioned Tool Registry, so
  aliases such as `agy`, `m3` and `cc` cannot silently become generic shell
  events. Generated adapters were refreshed from the current generator, and
  all emitted root/project commands quote paths containing spaces.
- Per-tool receipt filenames are sanitized so tool IDs or operation IDs cannot
  escape `state/receipts/tools/<tool>/`.
- Strict cycle verification binds the receipt to runtime import evidence,
  packaged eval-suite hash, health snapshot hash, context/evidence hashes and
  exit status.
- Migration preview generation is parameterized and read-only. It does not
  assume a fixed checkout, does not use the literal `$HOME` string, and does
  not perform backup, deletion, relinking or launchd operations.
- The behavior contract now has an explicit `state/behavior/current.json`
  snapshot writer and stale fallback reader. Adapters reference the actual
  contract source/snapshot path instead of blindly printing `DATA_ROOT/GLOBAL.md`.
- Tool coverage now separates configuration from capture evidence: the latest
  source event for the requested tool and project supplies `last_capture_at`,
  `capture_status` and `capture_freshness`. Read receipts are not treated as
  capture evidence, unrelated projects cannot satisfy coverage, and missing or
  stale source events remain visible as gaps.
- Runtime IDE and shell hooks no longer derive an import path from the iCloud
  source checkout. Child CLI environments remove iCloud checkout entries from
  `PYTHONPATH`, so the installed runtime package remains the import authority.
- The generated OpenCode plugin now captures lifecycle events and injects the
  current bounded Context during `experimental.session.compacting`, rather
  than only writing observation events.
- Runtime `DATA_ROOT` is canonicalized to `RUNTIME_BASE/llm-workmem`; checkout
  names can no longer create a second owner directory for scheduler bundles.
- Lean Core now explicitly supersedes the historical V2 control-plane design;
  the precedence contract is tested so old `STATE.md` authority language cannot
  silently re-enter the current architecture.
- Capability proof receipts now require an existing evidence file inside the
  current WorkMem root both when written and when read for coverage. Deleted,
  missing or outside-root evidence is observation-only; the legacy summary
  facade now uses the same verified coverage result instead of bypassing it.
  Evidence paths that start in `raw/events/inbox/` are resolved by their
  unique filename after normal ingest moves them to `processed/` or
  `rejected/`; outside-root and ambiguous evidence remains invalid.
- Lifecycle, hub event, and compatibility receipt entry points now resolve
  aliases through the Tool Registry before storage. `trae-solo` therefore
  cannot create a second tool identity beside canonical `trae`.
- `lwm.session_bridge` now provides the single versioned JSON contract for
  `context`, `start` and `stop`; it returns canonical tool identity, bounded
  context, event/operation ids, receipts and handoff status. The legacy
  parameter-based lifecycle command remains compatibility-only.
- Bridge simulation is now side-effect free by construction: it copies only
  the Tool Registry into a disposable temporary root before exercising the
  normal dispatch path. A regression test asserts that the requested data
  root has no file-tree change after simulation.
- The generated OpenCode native plugin now calls the shared JSON bridge for
  lifecycle and compaction Context delivery. `lwm hub bridge-contract --simulate`
  exercises every registered tool in an isolated root while explicitly marking
  the result simulated and unproven.
- All generated startup instruction blocks and the checked-in adapter outputs
  now point to `lwm hub bridge` for bounded Context delivery; the legacy
  `hub context` wording is no longer emitted by the adapter generator.
- Bridge verification now distinguishes `observed`, `simulated` and
  `host-reported`; an ordinary watcher observation can no longer be mislabeled
  as a simulation or native proof.
- Bridge CLI Context delivery supports `--output markdown`; generated host
  instructions now receive usable bounded Context directly while integrations
  retain the JSON response for machine workflows.
- `lwm hub bridge-stop` is now the shell-friendly structured handoff wrapper;
  generated adapters and checked-in adapter copies no longer direct tools to
  the compatibility-only `lwm hub lifecycle stop` path.
- MiniMax discovery now matches the actual `~/.minimax/agents` and
  `~/.minimax/v2/sqlite/runtime-state.sqlite` locations. Gemini discovery now
  matches `~/.gemini/GEMINI.md`. Cursor has an explicit project companion
  collector (`.llm-workmem/events.jsonl`) that writes canonical `tool=cursor`
  observations; it does not claim native Cursor transcript access.
- The IDE hook installer does not write speculative Codex `hooks.toml` or Trae
  `hooks.json` files. Codex now writes the known `~/.codex/hooks.json`
  contract and has a real host receipt; Kiro keeps its instruction/observer
  fallback beside the verified companion path. Gemini CLI writes only the
  known `hooks` section in `~/.gemini/settings.json` and preserves unrelated
  settings, but remains unverified until the host fires it; Codex
  trust/approval state is never mutated. VS Code/Cursor/Trae/Kiro use an
  explicit companion package path, not a guessed hook schema.
- The entity contract renderer now covers every enabled registry tool, including
  OpenCode, Cursor, MiniMax and Gemini CLI. The registry-to-entity check has no
  missing pages, with the Trae alias intentionally mapped to the canonical
  `trae-solo` page.
- The zsh capture hook now snapshots the previous command's exit status before
  any `precmd` work and JSON-escapes `pwd` and session fields. A real isolated
  interactive zsh test confirms a failing command remains `exit_code=1` and a
  directory containing a quote remains valid JSON.
- Kiro's IDE fallback installer now writes the same canonical
  `.kiro/steering/llm-workmem.md` path used by global adapters and Tool Registry
  discovery, and its returned install report points to the file actually
  written. The Claude installer binds generated hook commands to the requested
  `--home` root instead of the host user's home. Entity status text now agrees
  with the code: Codex/Gemini/Antigravity native contracts and the
  VS Code/Trae/Kiro companion bindings now have real host receipts; Cursor
  remains unverified because no local Cursor host is installed. Codex's native
  contract is also proven locally; Gemini/Antigravity remain pending host
  firing.
- Generated host instructions now state the intended authority split directly:
  `GLOBAL.md` is the shared personal behavior contract, while project memory,
  handoffs, Recall and review candidates are auxiliary evidence. The checked-in
  adapter copies were refreshed to the same wording.
- Shell identity, lifecycle canonicalization and the compatibility capability
  facade now all resolve aliases through the root's persisted Tool Registry;
  the real `claude` executable maps to `claude-code`, and registry overrides
  remove stale default aliases.
- Native proof claims now require a host binding. The registry explicitly binds
  Claude to `claude-code-hook` and OpenCode to `opencode-plugin`; bridge and
  lifecycle calls reject missing, mismatched or session-inconsistent
  `host_proof` before writing an event. The generated and checked-in OpenCode
  plugin plus Claude hooks send that binding, while the compatibility CLI
  remains observation-only.
- Tool Registry version 4 remains upgrade-safe: legacy persisted rows that omit
  `proof_integrations` inherit the default binding, while an explicit empty
  array still disables proof for an operator override.
- Generated and checked-in reverse adapters now bind each Context/write-back
  command to its canonical tool instead of emitting `<your-tool-name>`. Shell
  Context serializes `PWD` through JSON before calling the bridge, including
  paths containing quotes. The legacy shell adapter and the checked-in
  OpenCode plugin use the same bridge contract.
- Hatch source distribution excludes runtime-owned external symlinks, personal
  runtime data, migration backups, and generated workstation adapters. The
  wheel keeps the generator and hook code but omits checked-in adapter outputs,
  so a package install cannot inherit this Mac's absolute paths. Both the
  source archive and wheel build successfully from this checkout.
- Installed-runtime shell-hook setup now uses the packaged
  `lwm_shell_hook.zsh` whenever the target is a runtime data root, even if a
  legacy `DATA_ROOT/lwm` code mirror is still present. Only a source checkout
  with `pyproject.toml` may supply its local hook. Closure runtime checks
  likewise probe an explicit installed venv and reject iCloud/source imports;
  they no longer require a legacy code mirror under mutable data.
- Write-bearing installers now normalize a migrated repository access path to
  the single runtime data owner before rendering any adapter or hook command.
  The guard is shared by global adapters, IDE hooks and shell-hook setup; an
  ordinary checkout without a migrated `state` link remains unchanged.
- OpenCode installation now recognizes both legacy `lwm-workmem` and canonical
  `llm-workmem` plugin names. A known generated checkout plugin is migrated to
  the canonical user plugin path, unrelated plugins are preserved, and repeat
  installation is idempotent. The current local registration no longer points
  to the iCloud checkout.
- Runtime manifest serialization now uses
  `scripts/write-runtime-manifest.py` instead of shell quote substitution. It
  validates SHA-256/path records, parses the import probe, writes atomically,
  and has regression coverage for paths containing spaces and malformed hash
  input. Runtime staging installs declared dependencies, rebinds console
  scripts after the staging swap, and records a post-swap import probe.
- Schedule bundle generation now snapshots the reviewed `GLOBAL.md` into
  `state/behavior/current.json`; generated Cursor, Gemini and shell adapters
  expose the same contract version/hash and point at the source or runtime
  snapshot that actually exists.
- The supervisor now acquires an atomic `state/locks/cycle.lock` around the
  entire scheduled pass, including not-due bookkeeping, deterministic rebuild,
  exports, adapter rendering and health. A competing scheduler wake exits
  without writing; the existing ingest lock remains an inner compatibility
  guard rather than the only writer boundary.
- The public `run-cycle` entry point now uses the same cycle lock. Nested calls
  from the already-locked supervisor are reentrant in that process, while a
  competing manual or scheduled process exits without starting a second write
  transaction.
- Runtime staging now installs the wheel with its declared dependency closure;
  it no longer relies on a separate Typer-only install that can fail or leave
  an incomplete environment.
- Schedule generation now uses a non-migrating runtime preparation path. It
  creates runtime-side directories and adapter copies but does not convert
  repository data paths into symlinks. Ownership changes remain an explicit
  migration operation behind the Task 9A/9B gate.
- The materialize script is resilient to launchd/non-interactive environments:
  it supplies a minimal system `PATH` and resolves its own directory without
  depending on `dirname` being available through the host shell.
- The read-only migration manifest now binds the rollback archive, candidate
  plist, plist diff, and runtime-relevant dirty-worktree hash to one approval
  input.
- `lwm.migration` now binds the later data-owner operation to that exact
  manifest and approval id. It rechecks source/runtime/data hashes, rejects
  external symlinks and stale backups, and verifies the post-migration owner
  layout. The CLI refuses to run without both required values.
- The manifest dirty-worktree check is scoped to runtime-relevant source,
  adapter, script and contract files; audit/test documentation can be updated
  after preview without silently changing the reviewed runtime package.

## Local Verification

| Check | Result |
| --- | --- |
| Full pytest after the code changes | `586 passed` via local `.venv/bin/python -m pytest -q -p no:cacheprovider` with `UV_CACHE_DIR=/private/tmp/lwm-uv-cache-full5` |
| Latest focused architecture suite | `98 passed` for candidates, stable promotion, compiler, hub service, Context, CLI and runtime regressions |
| Shell/probe/write-back regression suite | `63 passed` |
| Ruff | Passed |
| `git diff --check` | Passed |
| Latest wheel | Installed runtime wheel at `~/Library/Application Support/llm-workmem-runtime/app/.wheels/lwm-0.1.0-py3-none-any.whl`; SHA-256 `c20e0d822656d84255be8a77007a0844525524945b5b6566e258cb8dcfeac426`; `RECORD` has 99 rows with 0 invalid hashes and zip integrity is verified |
| Latest source distribution | Current source built to `/private/tmp/lwm-dist-final-20260803a/lwm-0.1.0.tar.gz`; SHA-256 `ef877953b917573d339072e40bcbf9b377a2b325531d0182320bd61af1c3d81f`; forbidden runtime/data entries were absent |
| Latest package smoke | A fresh Python 3.11 venv at `/private/tmp/lwm-wheel-venv-final-20260803` installed the final wheel with dependencies; independent import resolved from `site-packages`, CLI help passed, and the installed simulation returned `true,11` |
| Portable package boundary | The wheel contains only `lwm`, `mcp`, and `adapters/hooks` code. Generated adapter markdown/shell files, `raw/state/global/projects`, `.codebase-memory`, personal rules, and migration backups are excluded from both package artifacts |
| Installed shell-hook smoke | The final wheel was installed non-editably into `/private/tmp/lwm-wheel-venv-20260801i`; installed `lwm` resolved from `site-packages`, and the wheel contained no iCloud checkout, `GLOBAL.md`, `raw/` or `state/` runtime data |
| Behavior snapshot/adapter regression | `12` focused tests passed for source-vs-snapshot references and schedule-time `GLOBAL.md` snapshot creation |
| Runtime/staging/migration regression | `18` focused runtime tests passed, including manifest-bound wrong-approval refusal, data-drift refusal, successful temporary-owner migration, valid hash/path JSON serialization, declared dependency installation, non-migrating schedule behavior, and materialize shell PATH/self-location contracts |
| Full materialize staging smoke | The local staging run from the audited wheel produced an independent import probe, final `bin/lwm` shebang and CLI help succeeded, and all 11 simulated bridge contracts remain covered |
| Local app runtime cutover | `~/Library/Application Support/llm-workmem-runtime/app/venv` was rebuilt from the final post-Task-9E wheel as `runtime-20260809T050549Z-aa7ee6ed`; manifest JSON is valid, import probe is independent, `editable=false`, and eighteen previous venv backups exist |
| Staged supervisor two-cycle smoke | `/private/tmp/lwm-supervisor-smoke-20260802` produced two immutable schema-v2 cycle receipts; the first receipt hash stayed unchanged and `last-attempt.json` advanced to the second receipt. Both were correctly `success_with_warnings` because the synthetic root intentionally lacked the reviewed behavior contract and complete eval input |
| Post-cutover live capability probe | All 11 registered tools report `installed=true`; OpenCode and Claude Code are `verified_bidirectional`, and the other 9 remain `configured_unverified`. Installation alone is not treated as bidirectional proof |
| Task 9B data-owner migration | Execution archive `/private/tmp/lwm-goal-completion-backup-20260809T110000Z.tar.gz` (SHA-256 `f4abbf0f43c5d480ec21b9cd7e42001a37d63839226bb424bfa59abf64beea81`) and execution manifest `/private/tmp/lwm-goal-completion-manifest-20260809-task9b.json` (SHA-256 `894baa3e35760018468e09407cf59dc273393bbc4a1c53109510196899b1183a`, approval id `lwm9b-894baa3e35760018`) passed preflight; `apply_data_owner_migration()` returned `applied=true` with scope `data-owner-only`. A current post-verification snapshot `/private/tmp/lwm-goal-completion-manifest-20260809-task9b-current.json` (SHA-256 `13eb131afc9681595251435a5418db6f4ac913b3b6e39d47e50f03d81c111978`, approval id `lwm9b-13eb131afc968159`) binds the newer archive `dcca3865e922bd280e06072fbb6a439706d2e4f7de9e04638117b379bf3c2409`; it was verified read-only and not re-applied. Runtime mutable entities are physical owners, repository paths are matching access symlinks, and launchd was not touched |
| Real owner-boundary guard | The first manual call with the repository root correctly returned exit `2` without writing; the migrated runtime data root then passed the owner boundary and accepted the one manual cycle |
| Local source-adapter smoke | Nine collector modules returned code `0` against a fresh temporary root and produced `678` bounded inbox events; no repository or live runtime data was written |
| Shared bridge contract smoke | Every enabled registry tool completed simulated `context/start/stop` through the same JSON bridge; source and installed-wheel runs returned `true,11`, and both had zero raw/state file-tree changes in the requested project root |
| Test-artifact cleanup | Authorized local cleanup dereferenced the runtime `state` symlink, moved exactly 33 simulation events and 12 simulation handoffs to `/private/tmp/lwm-simulation-cleanup-authorized-20260805`, restored the pre-test receipt SHA-256 `bef42d3e9fe1d5f06538aad89d4784b4ce0a63365bc3979e566165227ef3c3c4`, and verified marker count and active-pointer count are `0` |
| Raw preservation after migration and cycle | The historical migration baseline contained `6,515` raw files; the immediate pre-cycle check contained `6,545`, and the current runtime contains `6,555` raw files. `raw/events` contains `3,220` unique event IDs with no duplicates. The latest cycle processed `7` and rejected `9` through normal ingest; the verification write-back appended one sanitized inbox event. No processed raw event record was deleted |
| Historical manual supervisor cycle | `cycle-e545e55cfad0` remains immutable historical evidence from the pre-repair runtime: `success_with_warnings`/`degraded`, with `13` analyze errors and `15` review items |
| Latest authorized manual supervisor cycle | `cycle-5c2002c7bd5f` completed against the runtime data owner with `core_status=success` and `overall_status=success`; all source rows were `ok`/`hook_only`, ingest processed `7`, rejected `9`, failed `0`, audit was `0` issues, eval `2/2`, CBMEM `1/1`, and runtime import was independent. After the cycle, later local Codex and shell-hook runtime refreshes changed the current manifest from the receipt-bound `e29ac916...` to `4ee82938...`; strict verification therefore reports `runtime_manifest_hash_mismatch` and `health_status:degraded`. The receipt remains immutable and no second cycle was run |
| Task 9B explicit local execution on 2026-08-10 | Fresh manifest `/private/tmp/lwm-goal-completion-manifest-20260809T172857Z-task9b.json` SHA-256 `552b718f9dbaeffc4d542c645a4378c1a0262c7d3955100dd59349e0aa7859e0`, approval id `lwm9b-552b718f9dbaeffc`; rollback archive `/private/tmp/lwm-goal-completion-backup-20260809T172857Z-task9b.tar.gz` SHA-256 `92d8c77de392cc4608d75c342c1d626ab0d7e359afbd7bf69f4ea100344dd376`. Manifest-bound migration returned `applied=true`, scope `data-owner-only`; physical runtime owners and repository access symlinks re-verified. The one authorized manual cycle is `cycle-fd14856a63d1` (receipt SHA-256 `84e747675d6fac31dc6e78ec90ea78b183ec8bd69d234ee67a23a5f102b391fd`), successful at cycle time with processed `6`, accepted `6`, rejected `1`, failed `0`, audit `0`, eval `2/2`, health `healthy`, and receipt-bound manifest `4ee82938...`. After the lock-error semantic fix, the non-editable runtime was rebuilt as `runtime-20260810T020309Z-aa7ee6ed` with manifest SHA-256 `3444b799...`; strict verification now returns `valid=false` only for `runtime_manifest_hash_mismatch`. The receipt remains immutable and no second cycle was run. No deployment, launchd reload, or raw deletion occurred |
| Task 9B raw preservation proof | The pre-cycle baseline had `3,226` raw event JSON files; after ingest the same `3,226` event bytes remained, with `7` expected inbox-to-processed/rejected path moves and no missing event bytes. Event IDs remained unique. The sanitized post-cycle verification event `60562ac3-f05e-4177-ab5a-c88ebfd4c0c7` was appended after the cycle, bringing the event JSON count to `3,227`; no second cycle was run. Current snapshot/index files were refreshed by the cycle and are distinct from immutable event evidence |
| Task 9B verification write-back | Sanitized event `562c75a1-aa3a-4b72-a507-12f90a489595` was appended after the cycle with the manifest, receipt, owner-boundary, health and raw-preservation facts only; no prompt, transcript, model, completion or environment payload was recorded |
| Post-cycle derived-audit repair | Source analysis now excludes only generated `wiki/summaries/source-*.md`, retains curated summary pages, and ignores historical generated `source-*` links. The derived runtime index was completed with the two orphan concept pages and two curated summaries. Installed-runtime read-only audit now reports `0` analyze errors, `0` schema issues, `0` review items, eval `2/2`, and CBMEM `1/1`; no raw evidence changed |
| Receipt verification regression fix | Focused tests and the full suite prove warning/failed cycles retain the `last-attempt.json` receipt hash and full cycles do not rewrite health after receipt commit; the existing real receipt remains invalid under strict mode because its quality gates are genuinely degraded |
| Behavior contract snapshot | Source `GLOBAL.md` verified at SHA-256 `f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29e`; `hub behavior sync` refreshed `DATA_ROOT/state/behavior/current.json` at `2026-08-09T04:57:51+00:00`. Runtime context reports the same hash as a truthful `stale` fallback because the canonical file is not duplicated into the runtime owner; no leakage markers were found |
| Local host adapter cutover | Claude Code SessionStart/Stop hooks, global adapters, stable `lwm` launcher, zsh context source, and shell-history hook were refreshed against the runtime owner. Claude hooks use runtime Python; shell history uses the packaged `site-packages/lwm/lwm_shell_hook.zsh`; all checks passed and a rollback archive was saved under `/private/tmp/lwm-global-adapters-before-runtime-root-20260806.tar.gz` |
| Legacy code-mirror guard | New regression coverage proves a runtime data root containing a legacy `lwm/` directory still selects the installed wheel hook; source checkouts continue to use their local hook only when `pyproject.toml` is present |
| Repository-access owner normalization guard | `33` focused installer/shell tests passed; an installed-wheel temporary-owner probe passed `install-global` and Claude hook installation with `wiki_root=owner` and no repository path in generated commands |
| OpenCode runtime ownership migration | Local backups `/private/tmp/lwm-opencode-config-before-runtime-plugin-20260806.json` and `/private/tmp/lwm-opencode-config-before-task9b-20260806.json`; plugin and `references.llm-workmem.path` now point to the runtime owner, unrelated plugins/reference fields were preserved, and the active iCloud WorkMem path scan is empty |
| Kiro legacy-reference migration | The known legacy Kiro context command was replaced with the runtime owner while user-authored Kiro rules remained; active Kiro path scan is clean |
| Post-fix verification event | Appended sanitized event `62e6db9c-9caa-449f-bd2b-7e070b06baa3` with wheel/runtime/test/raw-preservation evidence; later verification event `84041b11-9b50-4be8-a67a-38919519cb7b` records the authorized cycle and raw-event retention |
| Post-repair verification events | Appended `00afd4c3-d2b8-471e-8fb1-a1343bd84cea` for the audit/snapshot repair and `a44eca11-d7d8-4579-8a5a-843cdd2e2761` for the host-adapter cutover; both are sanitized inbox evidence and do not rewrite historical raw |
| Task 9B current evidence refresh | Appended sanitized verification event `ac22a0db-1242-4f4c-987a-4b3a4f2d75d5` with the fresh manifest, rollback archive, owner-boundary result, strict-cycle reasons and raw-ID count; marker inspection found no prompt, transcript, model, completion or environment payload |
| Task 9B post-runtime-fix verification write-back | Appended sanitized verification event `75eeb470-c56c-4384-a947-dc93dc9d6bfd` after the non-editable runtime rebuild. It records the lock-error semantic fix, the `592`-test/Ruff result, the truthful receipt manifest mismatch, and the no-deploy/no-launchd/no-delete boundary; marker inspection found no prompt, transcript, model, completion or environment payload. Raw event IDs remain unique |
| Host-proof binding smoke | Unbound `native-hook` was rejected before event creation; registered OpenCode proof was `verified` with `opencode-plugin`; a mismatched integration for Codex was rejected |
| Registry/entity contract smoke | All 11 enabled registry tools have an entity contract page; generated pages were rendered in a temporary root and the missing-page set was empty |
| Read-only host discovery | Found local executables for Codex `0.146.0-alpha.9.2`, Claude Code `2.1.220`, OpenCode `1.17.15`, Trae `1.107.1`, and Antigravity CLI `1.1.8`; all 11 registry discovery/configuration probes returned `discovered`; this is not read/write proof |
| Read-only current coverage (historical pre-Task-9B snapshot) | The earlier snapshot recorded 9 tools with fresh capture; it is retained only as historical evidence and is superseded by the current installed coverage row below |
| Current installed coverage snapshot | `lwm hub coverage --json` reports OpenCode, Claude Code and generic shell as `supported` with `verified_bidirectional`; the other 8 tools remain `configured_unverified` or lack qualifying capture. Shell read/write proof was generated by real local session `shell-proof-20260810` with event ids `ae3ea039-d178-4744-912b-b847e2ce5902` and `94924959-42cc-40f9-bb27-3949e453b0f1`. Capture freshness remains 6 fresh (`codex`, `claude-code`, `opencode`, `shell`, `kiro`, `minimax`), 3 stale (`vscode`, `antigravity`, `trae`), and 2 missing (`cursor`, `gemini-cli`) by the current report; Codex and Gemini CLI remain configured with native hooks but unverified until real host receipts exist |
| Current registry/collector probe | `lwm hub tools probe` reports all 11 enabled tools discovered; 7 session collectors import as `ready`, while Claude Code, OpenCode, shell, and Gemini CLI correctly use native/shell lifecycle paths with `not_applicable` collectors |
| Antigravity native hook implementation | Added `adapters/hooks/antigravity_native.py`, registered `antigravity-hook`, merged global `~/.gemini/config/hooks.json` without replacing unrelated hook entries, and refreshed the active command to the non-iCloud runtime. Temporary runtime smoke proved context injection, verified read/write receipts, and no host metadata persistence; real Antigravity firing remains required for production coverage |
| Native hook installer parity | `lwm hub install-ide-hooks` and its Python helper now include Antigravity by default and write the same named `PreInvocation`/`Stop` hook surface as the global adapter installer. Isolated CLI/helper tests prove idempotency and user-config preservation; this fixes configuration reachability only, and does not promote Antigravity to `verified_bidirectional` without a real host receipt |
| Kiro host-contract boundary | Local Kiro CLI is `2.10.0`; standalone `.kiro/hooks/*.json` is a CLI 3.x contract, while the local 2.x agent-config path was not identifiable. No speculative Kiro hook was installed |
| Current post-Task-9E package/runtime | Installed runtime wheel `/Users/ethan/Library/Application Support/llm-workmem-runtime/app/.wheels/lwm-0.1.0-py3-none-any.whl`, SHA-256 `c20e0d822656d84255be8a77007a0844525524945b5b6566e258cb8dcfeac426`; `RECORD` 99 rows, invalid 0; runtime `runtime-20260809T050549Z-aa7ee6ed`; full tests `579 passed`, Ruff and diff check passed |
| Current local runtime refresh | After the installer-parity fix, `scripts/materialize-runtime.sh` rebuilt the non-editable local wheel and refreshed `app/venv` only. Current wheel SHA-256 is `046fb166a090bb26c23535639fd88cfafadec6daead2db25a7c02482a92fc670`, runtime id `runtime-20260809T145527Z-aa7ee6ed`, manifest SHA-256 `513dc081f8114d2821fd739d85ea702757b904a1bff6418aaf89210e1072644c`; old venv generations remain available for rollback. Direct `/Users/ethan/.local/bin/lwm` smoke installed Antigravity into a temporary home and resolved `lwm` from runtime `site-packages`; no launchd reload, cycle, deployment or raw mutation occurred |
| Runtime import-isolation and owner-path correction | `hub_service.coverage_report()` and `verify_cycle()` now normalize repository access symlinks to the physical runtime owner before resolving proof evidence. The generated launcher and native hook commands now use Python `-I`; the live wrapper and Claude/Codex/Gemini/Antigravity hook JSON files were updated locally. Focused isolation/owner tests passed, full suite is `582 passed`, Ruff passed, and installed wrapper coverage reports Claude/OpenCode `supported` with `verified_bidirectional` and no gaps |
| Latest local runtime refresh | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as runtime `runtime-20260809T151200Z-aa7ee6ed`; wheel SHA-256 `b733b3ff1238c63979acf83da24160db8a8105b4edfd366b57d13156418ee34e`, runtime manifest SHA-256 `4c488e446a70a2fa1136ac340f2c8a85d02e6ba3a0da4b317dc0ebf9331954a7`. Installed import resolves from runtime `site-packages`, `canonical_data_root` is present, raw remains preserved, and no launchd reload, deployment or supervisor cycle occurred |
| Runtime subprocess and hub-owner completion | Legacy Claude installer, common hook recorder, shell recorder, adapter runner and user wrapper now force `python -I`; `record_event`, startup Context, analysis review and promotion normalize migrated repository access paths to the physical owner. Focused tests passed (`40` owner/runtime/runner tests), full suite is `584 passed`, Ruff and shell syntax checks passed |
| Latest local runtime refresh | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as runtime `runtime-20260809T152234Z-aa7ee6ed`; wheel SHA-256 `efde62bd3fedbb4d62ecfb4f992f96eeb7030f05059c59a3acf4175a1c4cebd5`, runtime manifest SHA-256 `5f76f20e44c7ce7a3c6510a58697a9ae6f004b5db4041fda1014ac9606c54975`. Installed wrapper coverage remains Claude/OpenCode `supported` with `verified_bidirectional`; a temporary installed-wheel owner smoke proved event and Context receipt writes land in the physical owner. No launchd reload, deployment, raw deletion or second cycle occurred |
| Proof gate and compatibility facade completion | Direct `hub receipt` proof writes now fail closed for `native-hook`, `lifecycle-hook`, and `explicit-smoke`; only real host bridge code can claim a proof source. The legacy `lwm capabilities` facade now normalizes repository access paths to the physical owner. Proof-gate, facade, MCP, lifecycle and bridge tests passed; no false receipt was written |
| Latest local runtime refresh | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as runtime `runtime-20260809T153213Z-aa7ee6ed`; wheel SHA-256 `ca44ecdbbd93fa97d3e16c20e03721a5fe3aee7ca389ff5f1fd3cfa460bee50e`, runtime manifest SHA-256 `e29ac916ef858d6212d86f6bc28445d878dc5cae3b4c9a95f9481fc26ccbbefc`. Installed legacy and new coverage agree: Claude/OpenCode `verified_bidirectional`, other 9 `configured_unverified`; installed import is from `site-packages`. Full tests are `586 passed`, Ruff, shell syntax and diff checks passed. No deployment, launchd reload, raw deletion or second cycle occurred |
| Task 9D native-hook focused verification | `72 passed` across Codex/Gemini native handlers, global merge preservation, IDE installer idempotency, registry bindings and bridge regressions; independent wheel smoke returned valid SessionStart context and Stop/SessionEnd JSON with no prompt/transcript/completion persistence |
| Task 9D local configuration cutover | Backups at `/private/tmp/lwm-native-hooks-before-task9d-20260809`; `~/.codex/hooks.json` and `~/.gemini/settings.json` now point to the installed runtime, Gemini `mcpServers.codegraph` was preserved, Antigravity config was merged, and Codex trust/approval state was not changed |
| Receipt binding after local runtime refresh | Historical `cycle-e545e55cfad0` and `cycle-5433cad0bbdd` remain immutable. `cycle-5c2002c7bd5f` binds runtime manifest SHA-256 `e29ac916ef858d6212d86f6bc28445d878dc5cae3b4c9a95f9481fc26ccbbefc` and health SHA-256 `07fde81915539f270d471a9ce23ff632c95a7a467531ff8122f9ded604b15d29`; the current runtime manifest is `4ee8293879fd9512173e1d2426e865e23814e4c14e2bbbf47b9b532e8187f7dc` after the later Codex and shell refreshes. Strict verification correctly reports the manifest drift and the intentionally unloaded launchd boundary; no receipt was rewritten and no second cycle was run |
| Codex hook contract correction | Codex 0.147 local binary exposes `SessionStart`/`SessionEnd`; the source generator previously emitted the invalid `Stop` key. The generator now removes only the old LLM-WorkMem Codex handler, preserves user-owned Stop handlers, and emits the current pair. Full suite is `587 passed`, Ruff passed. Runtime `runtime-20260809T165559Z-aa7ee6ed`, wheel SHA-256 `18210c5792a27f4dc46d19bbe4be62394e559e5b88b052770082e2549e2d771e`, manifest SHA-256 `33a5cf1f13ffab1816da13cf6c6c1d97c0c5847455f9733ff94495e59c49f026`. Installed smoke passed; live Codex proof remains unverified until the host fires both hooks |
| Shell lifecycle proof correction | The registry now binds `shell-hook`; the packaged zsh hook emits sanitized `shell_session_start`/`shell_session_end` through the common bridge with `source=native-hook`, while filtered `preexec`/`precmd` remains the command observer. Full suite is `589 passed`, Ruff and zsh syntax checks pass. Installed-runtime isolated zsh smoke produced verified read/write receipts and zero lifecycle command fields; it used a temporary root and does not promote live shell coverage, which remains `configured_unverified` until an actual user shell lifecycle is observed |
| Real local shell lifecycle proof | A controlled interactive zsh using the installed runtime hook started and exited against the physical runtime data owner with session `shell-proof-20260810`. Events `ae3ea039-d178-4744-912b-b847e2ce5902` and `94924959-42cc-40f9-bb27-3949e453b0f1` contain only `shell_session_start`/`shell_session_end` host metadata; coverage is now shell `supported`, read `verified`, write `verified`, with no gaps. No supervisor cycle, launchd restart, deployment or raw deletion occurred |
| Latest local runtime after shell proof | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as `runtime-20260809T171036Z-aa7ee6ed`; wheel SHA-256 `f3431e595242a7e8cfdbd983db3aa05fea935c0ffc9eb181d9ccde5512fa29fe`, manifest SHA-256 `4ee8293879fd9512173e1d2426e865e23814e4c14e2bbbf47b9b532e8187f7dc`. Installed import resolves from `site-packages`; the shell hook fingerprint in `~/.zshrc` was refreshed after backup `/private/tmp/lwm-zshrc-before-shell-proof-refresh-20260810`. No deployment, launchd restart or supervisor cycle occurred |
| Latest local runtime after shell proof | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as `runtime-20260809T171036Z-aa7ee6ed`; wheel SHA-256 `f3431e595242a7e8cfdbd983db3aa05fea935c0ffc9eb181d9ccde5512fa29fe`, manifest SHA-256 `4ee8293879fd9512173e1d2426e865e23814e4c14e2bbbf47b9b532e8187f7dc`. Installed import resolves from `site-packages`; the shell hook fingerprint in `~/.zshrc` was refreshed after backup `/private/tmp/lwm-zshrc-before-shell-proof-refresh-20260810`. No deployment, launchd restart or supervisor cycle occurred |
| Latest local runtime after lock-error semantic fix | `scripts/materialize-runtime.sh` rebuilt the non-editable wheel as `runtime-20260810T020309Z-aa7ee6ed`; wheel SHA-256 `08dda75b925159e3bbf12ee255754212aadcc01933b1421d2189d9e2723600da`, manifest SHA-256 `3444b7991af6cfc3fd03cd8a4fc4cfdd2b3043862b12cebc21605c21c44f78f6`, `editable=false`, and installed import resolves from runtime `site-packages` with no iCloud path. Lock-open permission failures now return nonzero instead of being mistaken for a clean concurrent-cycle exit. No deployment, launchd restart, raw deletion or second supervisor cycle occurred |
| IDE companion bridge package | `integrations/ide-companion/` is a VS Code-compatible native bridge with explicit `vscode`, `cursor`, `trae`, and `kiro` identities. `lwm.ide_companion` packages host-specific VSIX files and the wheel force-includes the source; focused companion tests passed, Node syntax passed, offline wheel build passed, and a wheel-installed VSIX smoke contained `extension.vsixmanifest`, `extension/package.json`, and `extension/extension.js`. VS Code, Trae and Kiro have since produced real host receipts; Cursor remains unverified because its local host executable is unavailable |
| Latest local runtime after IDE companion refresh | `scripts/materialize-runtime.sh` installed wheel SHA-256 `a2d9918b9fafd1143807c468342e681d8bf0c7618f518048f9a48ba1154ee280` as runtime `runtime-20260810T030144Z-aa7ee6ed`; manifest SHA-256 `1ea59ddbcb84731ce3e7f7148444e0d930763a51a8be7332a44b54b905dae8e9`. Import resolves from runtime `site-packages`, `editable=false`, and iCloud is absent from the import path. Coverage now reports `vscode-extension`, `cursor-extension`, and `trae-extension` bindings while correctly keeping all three unverified. No deployment, launchd restart, supervisor cycle, or raw deletion occurred |
| Kiro companion implementation and real host proof | `integrations/ide-companion` now supports the canonical `kiro` identity and `kiro-extension` binding; focused companion/entity tests passed. The local runtime was refreshed as `runtime-20260810T033748Z-aa7ee6ed` from wheel SHA-256 `36ddb01afff4e135c990161442fee6533bdd7646f86d842fd7129f0d6e6b157a`, manifest SHA-256 `7dabae356e0fe05263a870e8167db57c59a28cfae329aaee1949d635c4f7bda5`, with `editable=false` and no iCloud import path. Real Kiro start `83ddbaca-07f2-463b-b88b-dcd91c088e5d` and stop `a168bd59-d8f0-49fa-9f35-1eea3a1e14ec` events share one session and project; coverage is now Kiro `supported`/`verified_bidirectional`. No deployment, launchd restart, supervisor cycle or raw deletion occurred |
| Current host coverage after Kiro proof | The latest runtime-owner coverage reports seven supported tools with qualifying project-bound proof: `codex`, `claude-code`, `opencode`, `shell`, `vscode`, `kiro`, and `trae`. `cursor`, `antigravity`, `minimax`, and `gemini-cli` remain `partially_supported`/`configured_unverified` or awaiting capture. The receipt reconciliation fix restored valid `ide-extension` receipts that were present in per-tool storage but had been lost from the aggregate index during concurrent writes. The report was run from the physical runtime owner, not `/private/tmp`, so the default-root trap is explicitly excluded |
| Shared MCP bridge installation | Local `mcp.lwm_server` now accepts a configured default root, and the MiniMax/Gemini installers merge `mcpServers.llm-workmem` without replacing existing servers. MiniMax backup `/private/tmp/lwm-minimax-mcp-before-20260810.json` SHA-256 `faeb35872433071d58fb0d0a06d0680c37390724400b677ed4d4e8d23460f2f8`; Gemini backup `/private/tmp/lwm-gemini-settings-before-mcp-20260810.json` SHA-256 `cbb2b93d2c39cd9d84a4ae8529e263b760e30e89c81f4d113e54823d7defe9f0`. Wire smoke returned 13 tools and 11-tool coverage; this proves local MCP reachability, not real host read/write proof |
| MiniMax MCP registry alignment | `lwm.tool_registry` now declares MiniMax primary delivery as `mcp`, matching the installed local `mcpServers.llm-workmem` bridge; the shell/session collector remains a fallback observation path. The change is covered by the registry, installer, MCP and entity tests, while runtime coverage truthfully remains `configured_unverified` because no real MiniMax host proof receipt exists |
| Capability receipt concurrency repair | `lwm.capability_proof` now locks aggregate receipt updates and merges the append-only per-tool receipt files when reading. Regression coverage reproduces a stale aggregate index and still returns both verified read/write receipts; focused lifecycle/bridge/capability tests passed `47` cases. The repair does not promote observations or create host proof; it only prevents valid existing receipts from disappearing due to concurrent writers |
| Local runtime refresh after MCP alignment | The audited local wheel was repacked offline because the build cache did not contain `hatchling`; wheel SHA-256 `6943ed64d8851b0d3146679d763c3bd9c5a0b2370fc928385c3cd4146ae6c245`, runtime `runtime-20260810T041026Z-aa7ee6ed`, manifest SHA-256 `ec099a4f8a8831baf28617e347c0c929e0607c69d93ee8f639377b07efa26e85`. The archived wheel and installed `lwm/tool_registry.py` are byte-identical, import is non-editable from `site-packages`, and iCloud is absent from `sys.path`; no deployment, launchd restart, supervisor cycle or raw deletion occurred |
| Latest local runtime after receipt repair | The audited wheel containing the receipt merge fix and MiniMax MCP alignment has SHA-256 `44f0bd3ebf11be3c957d3a720951876f9568be88ac2ee371337d9333854d5531`; runtime `runtime-20260810T042041Z-aa7ee6ed`; manifest SHA-256 `d79eabd27a737b859d4b294108abe93da969dcf8979d68dfc4b9e0eeb7921aa3`. Installed coverage now reports seven supported tools, while Cursor, Antigravity, MiniMax and Gemini CLI remain honestly unverified; no deployment, launchd restart, supervisor cycle or raw deletion occurred |
| Bridge cleanup and final simulation boundary | The prior authorized cleanup quarantine remains the only simulation cleanup: 33 events and 12 handoffs were moved to `/private/tmp/lwm-simulation-cleanup-authorized-20260805`; the current installed bridge simulation returns `all_contracts_pass=true`, `tool_count=11`, `verification_mode=simulated`, and leaves the requested root file tree unchanged. The six repeated IDs in the current raw scan are paired MiniMax date/current metadata snapshots, not bridge simulation events, so they were retained |
| Current sanitized verification write-back | Event `0395722c-65a8-471b-ba22-872d92f80d37` was appended to the runtime inbox with package/test/runtime/raw-preservation evidence; field inspection found no prompt, transcript, model, or completion payload |
| Latest sanitized verification write-back | Event `9453f6f4-291f-4d70-8548-a1e0752c8f9a` records the receipt concurrency repair, runtime `runtime-20260810T042041Z-aa7ee6ed`, byte-identical wheel/runtime install, `604`-test result, seven-tool coverage restoration, bridge simulation boundary, and no-deploy/no-launchd/no-raw-delete constraints; field inspection found no prompt, transcript, model, completion or environment payload |
| Final Task 9D verification write-back | Event `2db400b7-4174-4a6c-a9cb-09fb83715d91` records final wheel/runtime/CLI evidence; it is sanitized and append-only, with no prompt, transcript, model, or completion payload |
| Task 9E coverage freshness repair | `lwm/capability_proof.py` now filters capture events by lifecycle/observation type; regression coverage passed, and installed coverage no longer treats verification events as capture. Final event `6f111328-dcfe-4d6f-b4dd-879319f5a0ac` is sanitized and append-only |
| Latest staged structured handoff smoke | Final wheel CLI Stop accepted `task_id` from the summary and produced `session_summary` plus `bugfix` event and active handoff; `task_id`, `handoff_id`, `source_receipt_id` and evidence IDs were linked in the temporary root |
| Staged cycle smoke | Receipt `cycle-a15bb8b8f177` from the immediately prior staging build was written with `runtime_import_independent=true`; stages were `cbmem → ingest → project-rebuild → candidate-synthesis → optional-analysis → context-smoke → audit → exports → adapter-render`; audit degraded because the isolated run harvested current local sources with 17 analysis/review errors and eval `1/2`, so process exit was `1`. The final wheel's task-identity delta was verified separately by the final structured handoff smoke. |
| Read-only migration manifest | Historical Task 9A preview: 227 entries, SHA-256 `e9e5e6d1426207c57775aa6c6e8fd269e3cf60bed9ab8725da01c009a1a93a14`; execution manifest: 329 entries, SHA-256 `894baa3e35760018468e09407cf59dc273393bbc4a1c53109510196899b1183a`, approval id `lwm9b-894baa3e35760018`; current post-verification manifest: 329 entries, SHA-256 `13eb131afc9681595251435a5418db6f4ac913b3b6e39d47e50f03d81c111978`, approval id `lwm9b-13eb131afc968159`, current rollback archive SHA-256 `dcca3865e922bd280e06072fbb6a439706d2e4f7de9e04638117b379bf3c2409` |

The historical Task 9A manifest is at
`/private/tmp/lwm-goal-completion-manifest-20260802-final.json`. It is a preview,
not an approval token and not a migration result. The current post-cleanup
manifest is `/private/tmp/lwm-goal-completion-manifest-20260805-final.json` with
SHA-256 `e9e5e6d1426207c57775aa6c6e8fd269e3cf60bed9ab8725da01c009a1a93a14` and
approval id `lwm9b-e9e5e6d1426207c5`. Task 9B consumed this manifest and
completed the local data-owner migration before the manual cycle. Because the
source package was then corrected and the runtime venv was rebuilt, this
manifest remains the historical migration snapshot, not a new approval for
future changes.

The historical reviewed manifest references rollback archive
`/private/tmp/lwm-goal-completion-backup-20260802T010643Z.tar.gz`, which remains
missing and is not reused. The execution archive
`/private/tmp/lwm-goal-completion-backup-20260809T110000Z.tar.gz` passed the
execution manifest preflight; the current post-verification archive is
`/private/tmp/lwm-goal-completion-backup-20260809T111500Z.tar.gz` with SHA-256
`dcca3865e922bd280e06072fbb6a439706d2e4f7de9e04638117b379bf3c2409`, and its
paired current manifest passed `verify_manifest()` read-only. Rollback itself
remains unexecuted. This distinguishes missing historical evidence from the
current valid backups and makes no raw-data deletion claim.
The candidate plist is `/private/tmp/lwm-preview-plist-20260802.plist`; its
diff is `/private/tmp/lwm-preview-plist-20260802.diff`.

## Real Runtime Evidence

The final temporary staging binary was executed against the current runtime
data root without write commands:

- `lwm audit`: current installed-runtime read-only audit is `OK`: analyze errors
  `0`, schema issues `0`, review queue items `0`, eval `2/2`, CBMEM `1/1`.
  The earlier `12/14` result belongs to the single immutable cycle's historical
  input and was repaired in derived analysis/index code without rewriting raw.
- Read-only `lwm hub closure`: `blocked` on `receipt`; evidence, source,
  runtime and export checks pass, while health and launchd remain degraded.
- `lwm hub rebuild-projects DATA_ROOT --dry-run`: 200 events scanned, 15
  admitted, 153 operational, 32 rejected, 2 project pages to write; no live
  page was rewritten.
- `lwm hub context`: Ather is registered but has no admitted durable evidence;
  the runtime uses the last verified `GLOBAL.md` snapshot with status `stale`;
  no prompt or environment dump appeared in the project memory block. The
  capability warning is `observation only`, not a false native proof.
- `lwm hub verify-cycle cycle-e545e55cfad0 --root DATA_ROOT --strict`: the
  receipt pointer and hash are now found correctly, but strict verification
  rejects the real warning receipt for `audit_not_ok`,
  `health_status:failed`, `health_hash_mismatch`, and the expected
  `strict_core_status:success_with_warnings`; after the runtime venv update it
  also reports the receipt's older runtime-manifest hash, which is expected
  because this is the one cycle run before the post-fix runtime cutover.
- Read-only 2026-08-05 post-migration closure: `status=blocked`, with
  evidence, source, runtime and export checks passing; receipt is blocked
  because the one real cycle is degraded, while health and launchd remain
  degraded. The system did not claim a false completion.
- The real supervisor guard was exercised before the successful owner-root
  invocation: it returned exit `2` for the repository root and produced no
  receipt or health write. The subsequent owner-root invocation produced the
  receipt recorded above.
- The current installed runtime accepted the exact 329-entry manifest in a
  read-only `verify_manifest()` preflight, including the fresh rollback archive;
  `hub migrate-data-owner` returned `applied=true` within the data-owner-only
  scope. The same CLI rejects a wrong approval id before any migration code
  runs.

## Remaining Gates

These are not missing unit modules; they require runtime/data evidence or
explicit migration permission:

1. Keep `cycle-5c2002c7bd5f` as the latest immutable core-success evidence.
   Strict closure remains blocked only by the truthful health status `degraded`
   caused by the intentionally unloaded launchd. No further cycle is needed
   until a separate authorization is given.
2. The former `12` stale links and `14` review items are resolved in the derived
   audit/index path: the installed read-only audit is `0/0`. Raw evidence was
   not rewritten or deleted.
3. The reviewed `GLOBAL.md` is now materialized as a versioned `stale` runtime
   snapshot, without creating a second writable contract source.
4. Produce real read/write receipts for every registered tool, or explicitly
   change the product contract for a local host that is unavailable or
   observer-only. Seven tools now have proof; Cursor, Antigravity, MiniMax and
   Gemini CLI remain the blocking set. MCP configuration is now present for
   MiniMax, Gemini CLI and Antigravity, but configuration alone is not proof.
   Registry rows or watcher observations
   alone do not prove bidirectional support.
5. The local structured SessionStop path and shared JSON bridge now create an
   active handoff and a linked durable event when the host supplies a bounded
   task summary. Real per-tool native-hook evidence is still pending for hosts
   other than the Claude/OpenCode native paths, and a raw last-user message is
   intentionally not accepted as a handoff. The bridge contract smoke is not
   host proof.
6. Cross-project promotion remains an explicit review/promotion operation;
   optional LLM analysis creates validated candidates but does not silently
   write global facts.
7. The single-owner data migration is complete. The legacy runtime code mirror
   and any launchd registration change remain intentionally untouched until a
   separate approved cutover; no raw deletion is required for this step.

## Latest Local Security Correction (2026-08-10)

The generic MCP `record_receipt` surface previously accepted proof-source
labels such as `native-hook` and `explicit-smoke`, even though it had no host
binding. That could let an arbitrary MCP caller create a false capability
receipt. It now fails closed for every proof source and remains observation-only;
real proof must come through the registered native host bridge. The installed
non-editable runtime was refreshed from the audited local wheel after the
source fix. Installed smoke confirms forged proof is rejected and file-probe
observation remains accepted. Full source verification is `604 passed`, Ruff
passed, shell/Node syntax checks passed, and `git diff --check` passed.

Canonical MCP retain/record paths now also emit the registered
`watcher-observed` source explicitly instead of relying on the compatibility
facade to downgrade unknown `mcp` labels. The refreshed installed-runtime
smoke reports `retain_source=watcher-observed`, `retain_status=observed`, and
still rejects forged native proof. The final source verification is `605
passed`.

The MCP `tools/list` schema now exposes only `cli-context`, `file-probe`, and
`watcher-observed` for `record_receipt`; proof sources are absent from the
advertised enum as well as rejected by the runtime guard. Installed smoke
reports `proof_sources_exposed=false`.

The Tool Registry now separates `collector_modules` from read-only
`observer_modules`. Antigravity's local conversation metadata observer is
registered and executed by the bounded supervisor cycle as an observation
source; it is not treated as native proof and is not reported as `hook_only`.

The Codex, Claude Code and Gemini CLI native hooks now fail open when
`cwd`/`project_path` or `session_id` is absent. They return an empty response
and write no lifecycle receipt rather than inventing `.` or `unknown`
identities. The refreshed local non-editable runtime is
`runtime-20260810T054520Z-aa7ee6ed` with wheel SHA-256
`300bb4d0309bc59cdb8764bd7656f860c968d6b9ec01992baf05a9fc65341adb`.

## Latest Native Handoff Correction (2026-08-10)

Codex, Gemini CLI, Claude Code and Antigravity native stop hooks now forward
only an explicitly named structured object from `handoff`,
`handoff_summary` or `task_summary`. Ordinary `prompt`, `task` and
`transcript` fields are ignored and cannot be promoted into a handoff. The
focused native-hook suite passes `18` tests and the full source suite passes
`616` tests with the isolated uv cache; Ruff, syntax compilation and
`git diff --check` also pass.

The refreshed local non-editable runtime is
`runtime-20260810T055710Z-aa7ee6ed`. Its isolated import resolves from the
runtime venv with `icloud_on_path=[]`; registry v4 exposes the Antigravity
observer, incomplete native payloads fail open without raw writes, and an
explicit Codex handoff reaches `lifecycle.stop` in a temporary-root smoke.

## Latest Harvest and Derived-Page Correction (2026-08-10)

The entity renderer had two historical-format bugs: it did not add
frontmatter to an existing legacy page, and its delimiter index could join the
closing `---` to the first body line. A Gemini page also contained a joined
`type: entityupdated:` key. The renderer now normalizes these forms, preserves
the joined body text, and fills only missing entity defaults for `title`,
`type`, `tags`, `sources` and `updated`. Regression coverage is `9` focused
entity-render tests.

`lwm.harvest.default_source_groups()` now registers `gemini-cli` with the
bounded user-maintained source `~/.gemini/GEMINI.md`; conversation databases are
not part of automatic harvesting. The local harvest captured `165` snapshots,
reported `14` missing slots, returned raw sync code `0`, and left the raw JSON
file count at `3385`. Post-harvest verification is schema `0`, review `0`,
analysis `0`, eval `2/2`, CBMEM `1/1`, audit `OK`.

Full source verification is `620 passed` with Ruff, syntax compilation and
`git diff --check` passing. The refreshed non-editable runtime is
`runtime-20260810T061952Z-aa7ee6ed`, wheel SHA-256
`84320ba90497445ff5f7533fda9dd1360ad96d24f6c7637231a43ab7160ebf94`, with
`editable=false` and `icloud_on_path=[]`.

## Latest Antigravity Hook Contract Correction (2026-08-10)

The local Antigravity hooks contract requires a `decision` field on `Stop`
stdout. The native adapter now returns `{"decision":"allow"}` after the
shared stop bridge records the bounded lifecycle event; it no longer returns
an empty object. The focused native suite remains `18` passed, and an
isolated installed-runtime smoke verified Context injection plus the exact
Stop response. This improves host compatibility but does not create a real
Antigravity proof receipt until the host fires the hook.

The current non-editable runtime is
`runtime-20260810T062941Z-aa7ee6ed`, wheel SHA-256
`258e43f12af9beff7faafb65d414be5959093b9c36f01d2c1e3a4e68ab8769ed`.

## Latest Behavior Contract Freshness Correction (2026-08-14)

The runtime behavior snapshot records the canonical `GLOBAL.md` source path
and its SHA-256. Previously, loading from the runtime data root always marked
that snapshot `stale` because the checkout-level file was not located directly
under the runtime root, even when the recorded source still existed and its
bytes matched. The loader now verifies the recorded source path before
choosing `verified`; a missing or changed source remains `stale`.

The installed runtime is
`runtime-20260810T064856Z-aa7ee6ed`. Its import probe resolves from the
non-editable runtime `site-packages` with `icloud_on_path=[]`, and the live
behavior report returns `status=verified` for SHA-256
`f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29`.
The user-level LLM-WorkMem adapter refresh updated 22 generated entrypoints;
Codex, Claude Code, Gemini, Cursor, Kiro, OpenCode and Trae now expose
`status=verified`. No Ather files were part of this operation.

Regression coverage is six behavior-contract tests and `622 passed` for the
full source suite. Ruff, zsh syntax and `git diff --check` pass. This corrects
the behavior-contract freshness signal only; it does not create real native
host proof for Antigravity, MiniMax, Gemini CLI or Cursor, and it does not
reload launchd or run another supervisor cycle.

Conclusion: the local code package, derived-audit repair, behavior snapshot and
approved local data-owner migration are implemented, and one real supervisor
cycle has supplied truthful runtime evidence. The complete LLM-WorkMem goal is
still not proven: the existing immutable cycle remains degraded, launchd was
intentionally not reloaded, and real per-tool bidirectional proof is still
missing. The clean current audit does not retroactively rewrite that receipt.

## Latest MiniMax and Gemini MCP Bridge Correction (2026-08-14)

MiniMax now has a registered `minimax-mcp` proof integration and Gemini CLI has
a registered `gemini-cli-mcp` proof integration in the tool registry. The MCP
server accepts either proof path only when the installed host configuration
supplies matching `LWM_MCP_TOOL` and `LWM_MCP_INTEGRATION`; ordinary MCP calls,
missing identity, wrong identity, or requests for another tool remain
observation-only. The bridge writes only bounded operation metadata under
`state/receipts/mcp-bridge/` and never copies prompt, transcript, model, or
other user-content fields into proof evidence.

The global installer now calls the same MiniMax installer used by the host
installer, so `install-global` writes MiniMax's shell/MCP files and Gemini's
native hooks/MCP settings while preserving unrelated MCP servers. The actual
user configurations were refreshed locally and contain the matching identity
variables. Isolated installed-runtime MCP smokes produced verified
`mcp-bridge` receipts for both tools; this proves the local bridge contract,
not real MiniMax or Gemini host invocations. No deployment, launchd restart,
second supervisor cycle, raw deletion, or Ather operation occurred.

Verification for this correction: focused MCP/registry/installer tests
`72 passed`, global-install tests `32 passed`, full source suite `625 passed`,
Ruff passed, and the current runtime is
`runtime-20260814T142151Z-aa7ee6ed` with import from non-editable
`site-packages`. The remaining MiniMax gate is an actual host-generated
receipt, and the same rule applies to Gemini; configuration alone must not be
reported as verified capability.

## Latest Host Availability Truth Layer (2026-08-14)

The Tool Registry is now version `5`. Each registered tool exposes a read-only
`host_probe` separate from configuration discovery and capability proof. Its
statuses are `available` (a local executable was found), `app_present` (an app
bundle was found), `not_found`, and `not_applicable`. `hub tools list` and
`hub coverage` expose both `configured` and `host_probe`; read/write capability
status remains receipt-gated and is not promoted by installation or config
presence.

The source suite is now `632 passed`; Ruff and `git diff --check` pass. The
refreshed non-editable runtime is
`runtime-20260814T151438Z-aa7ee6ed`, with imports resolved from runtime
`site-packages` and `icloud_on_path=[]`. Current local host discovery reports
available executables for Codex, Claude Code, OpenCode, Antigravity (`agy`) and
Trae; app presence for VS Code, Kiro, MiniMax and Gemini; and `not_found` for
Cursor. These are availability facts only. The remaining real bidirectional
proof gaps are unchanged, and no deployment, launchd reload, second cycle,
external model call or Ather operation occurred.

## Latest Proof Boundary And Health Scope Hardening (2026-08-15)

`explicit-smoke` is now an observation source even when it has an evidence
file; it cannot enter `verified_read`, `verified_write` or
`verified_bidirectional`. The public JSON Session Bridge also rejects
proof-bearing requests unless they come through the internal trusted-host
adapter path. The shell native hook binds that marker to the bridge process on
the right side of its pipeline, and the Antigravity native adapter uses the
same trusted path.

The health snapshot now reports capability proof across all projects with an
explicit `capabilities_scope=all_projects`, while project-specific checks stay
available through `hub coverage --project-id`. This removes the previous false
contradiction where `coverage` showed verified host receipts but `health`
filtered them out by the runtime root project.

Final source verification is `635 passed`; Ruff and zsh syntax checks pass.
The final local runtime is
`runtime-20260815T013746Z-aa7ee6ed`, importing from non-editable
`site-packages` with `icloud_on_path=[]`. Runtime coverage has 11 registered
tools, 7 verified bidirectional tools (`codex`, `claude-code`, `opencode`,
`shell`, `vscode`, `kiro`, `trae`) and 4 explicitly unverified tools
(`cursor`, `antigravity`, `minimax`, `gemini-cli`). No deployment, launchd
reload, second supervisor cycle, external model call, raw deletion or Ather
operation occurred.

## Latest Antigravity Host Load Check (2026-08-16)

The local `agy agent` command was run without a prompt. Its fresh host log
records `loaded 1 named hooks from 1 hooks.json file(s)`, proving that the
global Antigravity hook configuration is now discovered by the real host.
The command did not execute a model request or a full agent lifecycle, so it
did not create a qualifying read/write receipt. Coverage therefore remains
`partially_supported` with the honest reason that a fresh lifecycle event is
still required. No raw event was deleted, no supervisor cycle or launchd
action occurred, and Ather was not touched.

## Latest Ingest Compatibility Boundary Correction (2026-08-15)

The public `ingest.run(..., auto_promote=True)` compatibility parameter is now
documented and tested as observation-only. It may record withheld legacy
decisions and candidate pages, but it cannot write `wiki/global/`; reviewed
compiler candidates remain the only global-memory write path. This closes the
API-level bypass that was still possible even after the legacy CLI was
disabled.

The focused ingest/promotion/CLI regression passed `46` tests and the full
source suite passed `638`. The runtime was refreshed as
`runtime-20260815T143452Z-aa7ee6ed`; no launchd reload, supervisor cycle,
deployment, raw deletion, or Ather operation occurred.

## Latest Trusted Host Propagation Correction (2026-08-15)

The VS Code-family IDE companion and the OpenCode plugin were sending
registered `ide-extension`/`native-hook` proof requests without propagating
the trusted-host marker to their child `lwm hub bridge` process. The public
bridge correctly rejected those requests, so this was a real adapter wiring
bug rather than a proof-policy failure. The companion now sets
`LWM_HOST_BRIDGE=1` only in its child environment, and the generated and
checked-in OpenCode plugins invoke the bridge through `env LWM_HOST_BRIDGE=1`.
The server-side fail-closed boundary remains unchanged.

The focused companion/OpenCode/bridge regression passed `44` tests; the full
source suite passed `639`; Ruff and diff checks passed. Installed-runtime
smoke verified untrusted rejection and trusted `host-reported` plus
`verified` receipt behavior in an isolated temporary root. Runtime
`runtime-20260815T144851Z-aa7ee6ed` imports from non-editable `site-packages`
with no iCloud path. No launchd reload, supervisor cycle, deployment, raw
deletion or Ather operation occurred.

## Latest Scheduler Single-Writer Guard (2026-08-15)

`lwm schedule` now atomically claims
`state/scheduler-owner.json` inside the canonical runtime data root. Reusing
the same label is idempotent; attempting to register a different label for
the same owner fails closed before a second schedule bundle is written. An
isolated installed-runtime smoke confirmed the first claim, the second-label
rejection, and zero `launchctl` invocation. This prevents future duplicate
writers but does not inspect or unload any already-existing launchd job, so
R2 remains a real-host boundary.

The full source suite passed `640`; scheduler-focused tests passed `20`; Ruff
and diff checks passed. Runtime `runtime-20260815T145926Z-aa7ee6ed` imports
from non-editable `site-packages` with no iCloud path. No launchd reload,
supervisor cycle, deployment, raw deletion or Ather operation occurred.

## Latest Legacy Dream Writer Retirement (2026-08-15)

The local runtime previously contained `bin/lwm-dream.sh`, an independent
writer that ran ingest, health, insights and the retired auto-promotion path.
The materialization flow now backs up that script under
`runtime/backups/legacy-writers/` and atomically replaces it with a
fail-closed stub that exits `2` and points operators to the single
`lwm hub run-supervisor` authority. The existing `com.ethan.lwm.dream.plist`
was not edited or loaded. Read-only `launchctl print` confirms both harvest
and dream services are currently absent from the GUI domain.

The full source suite passed `641`; the retirement regression passed `2`; shell
syntax, Ruff and diff checks passed. Runtime
`runtime-20260815T151054Z-aa7ee6ed` imports from non-editable `site-packages`
with no iCloud path. The old script remains available in the runtime backup;
no raw evidence was deleted and no launchd action or supervisor cycle was run.

## Latest Scheduler Runtime Binding Correction (2026-08-15)

The local audit found that `lwm schedule` preferred the convenience launcher at
`~/.local/bin/lwm`. That launcher normally forwards to the non-editable runtime,
but it also contains a development-only checkout fallback when the runtime is
missing. Generated launchd schedules must not inherit that fallback. The
scheduler now prefers the concrete
`~/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm` path and
does not fall back to the global wrapper; if the concrete runtime is absent,
the generated schedule remains visibly unusable instead of silently importing
checkout code.

The canonical local schedule was rewritten without `--load`. Its
`scheduler-owner.json` claims only `com.ethan.lwm.harvest`, and the plist now
directly invokes the non-editable runtime. Read-only `launchctl print` still
finds neither harvest nor dream loaded, and no raw files changed during the
schedule operation. The full source suite passed `643`; the focused schedule
and runtime tests passed `32`; Ruff and diff checks passed. Runtime
`runtime-20260815T152311Z-aa7ee6ed` imports from non-editable `site-packages`
with `icloud_on_path=[]`. No deployment, launchd load/restart, supervisor
cycle, raw deletion or Ather operation occurred.

## Current Host Availability And Health Recheck (2026-08-16)

The installed runtime recheck was performed without starting a service or
running another supervisor cycle. Non-strict health is `healthy`, with audit
`0`, eval `2/2`, CBMEM healthy, `failed=0`, and `capabilities_scope=all_projects`.
The last successful receipt remains `cycle-10d657108685`; `due=true` is
honestly reported because launchd is unloaded and a new cycle was not
authorized. Strict health therefore remains a separate boundary, not a failed
code test.

The current read-only host probe finds executable hosts for Codex, Claude Code,
OpenCode, Antigravity (`agy`) and Trae; app bundles for VS Code, Kiro, MiniMax
and Gemini; and no Cursor host. Real bidirectional proof remains present for
Codex, Claude Code, OpenCode, shell, VS Code, Kiro and Trae. Antigravity has a
configured native hook but no live proof receipt; Cursor, MiniMax and Gemini
CLI have no qualifying host receipt. No model call was made, no deployment or
launchd action occurred, no second cycle ran, and no raw event was deleted.

## Latest Native Host Contract Completion (2026-08-16)

The Gemini CLI native lifecycle writer now omits the empty `matcher` field for
`SessionStart` and `SessionEnd`. Gemini lifecycle names are exact event names,
so an empty matcher is not a valid substitute for an omitted matcher. The
generated `~/.gemini/settings.json` was rewritten locally and preserves the
existing MCP configuration. The installed runtime command uses Python
isolated mode and the non-editable runtime path.

Cursor now has a code-package native adapter at
`adapters/hooks/cursor_native.py`. The installer merges, rather than replaces,
`~/.cursor/hooks.json` and registers `sessionStart` and `sessionEnd`. The
adapter only consumes workspace/session identifiers, writes lifecycle receipts
through the trusted bridge, returns session-start context, and fails open for
malformed or incomplete host input. An isolated temporary-root smoke proved
the package contract with two receipts; it is not real Cursor host proof.

The current runtime is `runtime-20260816T020548Z-aa7ee6ed`, non-editable, and
imports with `icloud_on_path=[]`. Full source verification is `647 passed`;
Ruff and `git diff --check` pass. Local coverage still truthfully marks Cursor
and Gemini CLI as partial because neither host has produced a real
capture/proof receipt in this authorization. Antigravity and MiniMax retain
the same real-host proof gap. The focused native-host/bridge/installer suite
passed `62` tests in an isolated temporary root; this is code-contract evidence
only and does not promote any host capability. No deployment, launchd reload,
second supervisor cycle, raw deletion, or Ather operation occurred.

The separate strict health check returned `degraded` for the expected reason:
`due=true` while launchd is intentionally unloaded and the last successful
receipt is historical. It did not report an audit, eval, CBMEM or source-stage
failure. The strict result is retained as a boundary signal and was not
overridden by the non-strict health snapshot.

The optional workflow/relationship compiler was also exercised against the
current runtime with `hub analyze --pending`. Its queue was empty and the
result was `status=disabled`, with `analyzed=0`, `deferred=0`, `dead_letter=0`
and `errors=0`. No model call or candidate-state mutation occurred.

The deterministic workflow, cross-project relationship, optional compiler
state-machine, conflict-insight and stable-promotion regression suite passed
`58` tests. These tests prove admission, evidence binding and review gates;
they do not create live multi-project evidence or auto-promote memory.

## Latest Task 9B Execution And Post-Cycle Correction (2026-08-16)

The repository access topology was rechecked before execution. The physical
mutable owner is already the canonical runtime data root at
`~/Library/Application Support/llm-workmem-runtime/llm-workmem`; the checkout
paths are access symlinks and `mutable_ownership_issues()` returns empty. A
second data migration was therefore not repeated: re-running an already
applied ownership migration would add risk without changing the owner.

The owner guard had a real code defect: it rejected every valid checkout link
because it compared the link target to the checkout root instead of the
selected DATA_ROOT. The guard now accepts only exact
`DATA_ROOT/<mutable-entity>` targets and still rejects arbitrary external
owners. A regression test covers both cases.

The one explicitly authorized manual supervisor cycle was then run as
`cycle-d76c20fc721a`. The owner gate passed; ingest processed `18`, accepted
`18`, rejected `5`, and failed `0`; CBMEM was healthy, eval was `2/2`, and the
runtime import was independent. The cycle returned `1` because its audit saw
one schema false positive and one review item, so its immutable status is
`core_status=success_with_warnings`, `overall_status=degraded`. No second
cycle was run.

The post-cycle code audit found and fixed two deterministic issues exposed by
that result: multiline YAML `tags`/`sources` were parsed as empty, and
absolute or repository-relative source references were resolved under
`raw/` incorrectly. Current schema validation is `0` issues. Six genuine
missing historical source references remain in the review queue; they are not
silenced or converted into fake evidence. Current health is therefore
truthfully `degraded`, not healthy.

The full source suite passed `650`; Ruff and `git diff --check` passed. The
runtime was refreshed as non-editable
`runtime-20260816T031038Z-aa7ee6ed` and isolated import resolves from
`site-packages` with no iCloud path. Raw contained `3,423` JSON files before
and after the cycle. After excluding the three identified CBMEM snapshot
refreshes, the remaining `3,420` content hashes are identical; no raw event
was deleted or rewritten. Launchd remains unloaded, no deployment or launchd
action occurred, and Ather was not read or modified.

## Historical Source-Gap Reconciliation (2026-08-16)

The six remaining review items were checked against the current Downloads,
Documents, Desktop, and active Codex/Claude/Trae configuration locations. No
replacement file was found for `user/board`, the three historical Codex files,
or the two historical Trae Unified Brain files. The missing references are
therefore genuine provenance gaps, not unresolved path normalization.

The pages remain visible and the audit remains degraded. We do not remove the
`sources` entries, point them at unrelated current files, or mark them
verified. Any future source restoration must provide the original file or a
human-approved replacement with an explicit historical-source decision.

## Latest Source-Gap Quality Gate (2026-08-16)

The wiki analyzer now emits a structured `SourceGap` for every missing source,
including the page, declared value, resolved path and scope. A gap is `local`
when it resolves inside the LLM-WorkMem root, and `external` when an absolute
path points outside that root. The review queue keeps the compatible
`missing-source` prefix but adds `scope=local|external`; analysis reports show
both counts. This makes the repair action explicit without weakening the
quality gate: all six gaps still count as analysis errors and review items,
so audit remains `FAILED` until the evidence is restored or explicitly
reviewed.

The focused source-gap and audit tests pass, the complete source suite passes
`652`, Ruff passes, and `git diff --check` passes. The live read-only audit
reports `1` local gap and `5` external gaps, with eval `2/2` and CBMEM `1/1`.
No source reference was removed or rewritten, no runtime was refreshed, no
deployment or launchd action occurred, no second supervisor cycle ran, and
Ather was not read or modified.

## Latest Non-Editable Runtime Refresh (2026-08-16)

The source-gap quality-gate fix was materialized into the local runtime as
`runtime-20260816T093217Z-aa7ee6ed`. The installed wheel SHA-256 is
`bc958d29c0606b587664ed863070cf7942efd105daa4f3e65f230405c6454315`, and
the runtime manifest SHA-256 is
`0bec9c16492c93a7137cfd9884e77110f7441a35532a8f6ac988ad4dac1e4c8f`. The
manifest has `editable=false`, imports from runtime `site-packages`, and
reports `icloud_on_path=[]`. An installed-runtime review command now reports
the same six explicit source gaps (`5 external`, `1 local`).

The source suite remains `652 passed`; Ruff, bytecode compilation and
`git diff --check` pass. This was a local runtime refresh only: no deployment,
launchd load/restart, supervisor cycle, raw deletion or Ather operation
occurred.

## Latest Coverage Reason Contract And Runtime Refresh (2026-08-16)

Coverage now includes `status_reason`, derived from proof receipts, capture
freshness, configuration state and the read-only host probe. The installed
runtime reports plain reasons instead of leaving operators to interpret
`configured_unverified`: Cursor is not found, Antigravity and MiniMax have
stale captures, Gemini CLI is waiting for its first lifecycle event, and the
seven verified tools report real read/write proof. The field does not promote
any receipt or change the proof gate.

The change was materialized as non-editable runtime
`runtime-20260816T093953Z-aa7ee6ed`; source verification is `653 passed`, Ruff
passes, and the installed import remains in `site-packages` with no iCloud
path. No deployment, launchd action, supervisor cycle, raw deletion or Ather
operation occurred.
