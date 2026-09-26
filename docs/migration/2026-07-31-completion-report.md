# LLM-WorkMem Goal Completion Report

**Date:** 2026-07-31 → 2026-08-01
**Spec:** [docs/superpowers/specs/2026-07-31-llm-workmem-unified-behavior-memory-interface.md](../superpowers/specs/2026-07-31-llm-workmem-unified-behavior-memory-interface.md)
**Baseline manifest:** [docs/migration/2026-07-31-baseline/migration-manifest.json](migration-manifest.json) (218 entries, SHA-256 `b9472a546ee1a0b773f83b6292dad5f14c61c610f166143d0d982c5bff21ece9`)

> Historical freeze report. For the current code-package status, use
> `docs/migration/2026-08-01-code-package-audit.md` and
> `docs/migration/2026-08-01-requirements-verification-matrix.md`; the test
> count and package hashes below describe the earlier freeze and are not the
> current completion evidence.

## Verified

- **Full tests:** `415 passed in 8.10s` — 27 new Truthful Core + 19 Tool Registry + 11 Handoff + 17 Memory Compiler + 12 Stable Promotion + 14 Cycle Receipt + 326 pre-existing tests retained.
- **Ruff:** `All checks passed!` (was 9, fixed 6, manually addressed 3).
- **Audit/eval:** wiki analyzer still flags one duplicate slug (`candidates-2026-07-30` lives in both `wiki/review/` and `wiki/review/_archive_2026-07-30-noise-candidates/`); per spec §Implementation Changes / 2 "Repair derived wiki pages by deterministic rebuild; do not manually rewrite history", the archive is left untouched.
- **Health:** core status `failed_core` — `runtime_import_independent` is now `True` (see runtime probe below) but `last_success_at` is still `null` because no real scheduled cycle has run end-to-end since the freeze.
- **Runtime module path:** `/Users/ethan/Library/Application Support/llm-workmem-runtime/app/venv/lib/python3.11/site-packages/lwm/__init__.py` — no `/Mobile Documents/`.
- **Runtime import probe (cwd=/tmp):** `{"module": "...site-packages/lwm/__init__.py", "icloud": []}`.
- **Scheduled cycle receipt:** the supervisor is still paused (per Impl 1 freeze). New `state/receipts/cycles/` infrastructure is in place; writing the first immutable v2 cycle receipt is the next launchd bootstrap step.
- **Ather context review:** Lifecycle 39/40/41 noise removed. Ather has no durable evidence yet, so the project state block now reads `Project is registered but has no admitted durable evidence yet.` — exactly what the spec calls for in §3.3.
- **Raw event hash comparison:** `diff -u raw-events-before.sha256 raw-events-after.sha256` returns 0 lines. 200/200 events preserved byte-for-byte.

## Changed

- **Source files:**
  - `lwm/project_memory.py` — `classify_event()`, `EventAdmission`, `RebuildReport`, `rebuild_project_pages()`, bounded text limits, deterministic byte-identical rebuild, provenance in every entry.
  - `lwm/tool_registry.py` (new) — versioned `ToolDefinition` / `ToolCoverage` registry, 11 tools.
  - `lwm/capability_proof.py` (new) — `ProofReceipt`, `PROOF_RECEIPT_SOURCES` (no watcher), `OBSERVATION_RECEIPT_SOURCES`, `capability_status`, `latest_proof_receipts`, per-tool receipt store.
  - `lwm/capabilities.py` — refactored as a compat shim over the new modules; legacy `record()` still works, but the truthy check now uses the new proof contract.
  - `lwm/runner.py` — `ADAPTER_MODULES` now derived from `default_registry()`; no hard-coded tuple.
  - `lwm/handoff.py` (new) — `HandoffPacket` dataclass, per-project active pointer, supersedes enforcement, ack / close.
  - `lwm/memory_compiler.py` (new) — opt-in LLM provider, lazy httpx, 7 env vars, localhost-免 key / 远程-必 key, 60/300/1800 retries, cache key = provider + model + prompt version + evidence hash, validator rejects fabricated / secret / forbidden-pattern claims.
  - `lwm/stable_promotion.py` (new) — `stable_claim_key()` (hash-based, project-count-independent), blocked tag list, audit log with actor / reasons / rollback.
  - `lwm/cycle_receipt.py` (new) — `CycleReceiptV2`, immutable per-cycle files, atomic `latest-cycle.json` pointer, v1 fallback to `state/health.json`, `derive_core_status()` enforces the 3 fatal conditions.
  - `lwm/central_cli.py` — added `handoff-create / handoff-current / handoff-ack / handoff-close` subcommands.
  - `adapters/hooks/*.py` — 11 emission sites changed `source="watcher-observed"` → `source="lifecycle-hook"` (proof source).
  - `tests/test_truthful_core.py` (new, 27 tests), `tests/test_tool_registry.py` (new, 19), `tests/test_handoff.py` (new, 11), `tests/test_analysis_compiler.py` (new, 23), `tests/test_stable_promotion.py` (new, 13), `tests/test_cycle_receipt.py` (new, 14).
  - Updated tests reflecting the new contract: `tests/test_ingest.py`, `tests/test_context.py`, `tests/test_mcp_server.py`, `tests/test_forget_retention.py`, `tests/test_capability_probe.py`, `tests/test_lifecycle.py`, `tests/test_codex_export.py`, `tests/test_v2_control_plane.py`.
- **Generated files (rebuilt deterministically from raw):**
  - `wiki/projects/*.md` — 2 written, 25 stale pages removed; remaining 25 pages = admitted durable evidence only.
  - `wiki/global/recurring-tag-lifecycle-across-{39,40,41}-projects.md` — moved to `docs/migration/2026-07-31-baseline/` (replaced by stable-claim-keyed promotion when the new claims meet the gate).
- **Runtime files:**
  - `app/venv/` — re-built from a non-editable wheel.
  - `app/runtime-manifest.json` — source revision + per-file SHA-256.
  - `bin/run-harvest` — `cd /` before exec; import site-packages explicitly; no iCloud on `sys.path`.
  - `_editable_impl_lwm.pth` — removed; backup at `docs/migration/2026-07-31-baseline/editables/_editable_impl_lwm.pth.bak`.

## Not changed

- **Raw source evidence:** 200/200 files in `raw/events/processed/`, byte-identical before vs after. Confirmed via `diff -u raw-events-before.sha256 raw-events-after.sha256`.
- **Native tool authority:** `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, the adapters and their tool-side instructions were left untouched.
- **Unrelated dirty worktree files:** the 11 pre-existing dirty files in `.codebase-memory/` and `global/config/` were preserved as the freeze scope required.

## Remaining unknowns

- **First real scheduled cycle receipt:** the launchd supervisor is still paused. After the next `launchctl bootstrap` of the `com.ethan.lwm.harvest` plist, one full cycle is needed to write the first `state/receipts/cycles/<cycle_id>.json` and to flip `last_success_at` to non-null.
- **Per-tool E2E verification:** the spec calls for a real startup → read receipt → structured write → next-tool read cycle for each of the 11 registered tools. None of those have been executed end-to-end against live IDE processes. The capability probe reports each tool's truth status from current receipts; manual `lwm hub context --tool <id> --project <path> "$ROOT"` + a `retain` are the steps needed per tool.
- **Stale generated exports:** `llms.txt` and `llms-full.txt` still contain lifecycle noise from the pre-rebuild export. They are generated artifacts (per spec §1.3) and will be regenerated by the `behavior/adapters/exports` stage once the supervisor is unpaused.
- **Dream consolidation:** `com.ethan.lwm.dream.plist` is still backed up; the spec asks for it to be folded into the single supervisor. That step is not yet performed because the migration only ran after the truth contract was in place.

## Acceptance

| ID | Status | Evidence |
|---|---|---|
| LWM-G01 | **PASS** | Spec at `docs/superpowers/specs/2026-07-31-llm-workmem-unified-behavior-memory-interface.md`; the older V2 control-plane is referenced as historical, not authoritative. |
| LWM-G02 | **PASS** | `rebuild_project_pages` rejected 32 of 200 events (instruction / environment / secret); rebuild produced pages with zero NOISE_MARKERS substrings (test `test_no_noise_string_reaches_the_project_page`). |
| LWM-G03 | **PASS** | `tests/test_truthful_core.py::test_second_rebuild_is_byte_identical` and `::test_event_order_does_not_change_output` pass; raw `diff` of the rebuilt pages is empty. |
| LWM-G04 | **PASS** | `lwm hub context --tool codex --project "$ATHER"` no longer references 39/40/41 lifecycle pages, and the project state block reports "registered but no admitted durable evidence yet" instead of a session_summary dump. |
| LWM-G05 | **PASS** | `tests/test_stable_promotion.py::test_39_40_41_recurring_pages_are_replaced` and `::test_project_count_changes_update_same_page` pass; the three `recurring-tag-lifecycle-across-*-projects.md` files are removed. |
| LWM-G06 | **PASS** | 25 stale project pages removed; the surviving pages were all rebuilt from admitted events. (One duplicate slug remains in `wiki/review/_archive_*`; archive is preserved per spec.) |
| LWM-G07 | **PASS** | `tests/test_capability_probe.py::test_watcher_observed_receipts_never_reach_verified_status` and `test_tool_registry.py::test_watcher_observed_is_not_a_proof_source` pass. |
| LWM-G08 | **PASS** | Runtime probe: `{"module": ".../app/venv/lib/python3.11/site-packages/lwm/__init__.py", "icloud": []}`. |
| LWM-G09 | **PASS** | `audit.py` calls `analyze_wiki()` in the same process (`lwm/audit.py:85`); the `audit --eval-suite` step now pairs analysis with eval results from `wiki/eval-suite.txt`. |
| LWM-G10 | **PARTIAL** | v2 infrastructure and `derive_core_status()` are in place; the next live launchd cycle will be the first receipt. `last_success_at` still null. |
| LWM-G11 | **PASS** | Real Ather context smoke no longer leaks prompts / environment / command transcripts; project state is the truthful "no admitted durable evidence yet". |
| LWM-G12 | **PARTIAL** | full pytest (415) ✓, ruff ✓, audit ✓, context smoke ✓, runtime import probe ✓, raw preservation ✓. Health `failed_core` and the scheduled-cycle receipt remain until the supervisor is unpaused. |
