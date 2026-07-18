# LLM-WorkMem V2 Implementation Plan

**Date:** 2026-07-18
**Design:** `docs/superpowers/specs/2026-07-18-llm-workmem-v2-control-plane-design.md`

## Objective

Make LLM-WorkMem a truthful local control plane for shared workflow memory:

1. a supervisor wakes every 15 minutes and runs the 12-hour due cycle;
2. every cycle leaves a verifiable receipt, even when no work is due;
3. event quality reports distinguish accepted, duplicate, privacy-blocked, invalid,
   and failed records;
4. projects and tools have explicit registries and real read/write receipts;
5. Retain, Recall, Reflect and project `STATE.md` become one deterministic chain;
6. CBMEM is connected as a direct project code-memory service, not as a repeated
   Markdown snapshot source;
7. strict health fails when the chain is stale, incomplete, or unverified.

## Execution Rules

- Use TDD for behavior changes: add a failing focused test, implement the smallest
  change, run the focused test, then run the full suite.
- Preserve unrelated dirty files.
- Do not declare an IDE connected from a config file alone. A capability is active
  only after a receipt proves its read/write path.
- Do not invent hooks for tools that expose no verified hook/API. Such tools are
  recorded as manual/unsupported with an explicit reason.

## Tasks

### A. Runtime truth and health

- Add cycle receipt/state helpers and supervisor execution.
- Make health report schedule due state, last successful cycle, receipt age, and
  rejection breakdown.
- Treat an idle launchd job with successful history as loaded, but still fail when
  the last successful cycle is past the SLO.
- Change the generated LaunchAgent to a 15-minute supervisor interval while the
  supervisor enforces the 12-hour full cycle.

Tests: cycle state round-trip, due/not-due behavior, stale-cycle strict health,
launchd plist interval and idempotent schedule generation.

### B. Event truth and memory chain

- Classify ingest outcomes separately: accepted, duplicate, privacy blocked,
  invalid schema, and processing failure.
- Expose counters by reason and stop calling all rejected records privacy.
- Add deterministic Retain and Recall APIs over the existing filesystem index.
- Add Reflect output and per-project `STATE.md` generation with provenance.

Tests: one test per classification, dedup does not inflate privacy rate, retain /
recall / reflect round-trip, project state provenance.

### C. Project and tool control plane

- Add project registry records with canonical path, project id, status, and CBMEM
  association.
- Add capability registry and read/write receipts. Static adapter files are only
  declarations; health uses receipts as proof.
- Add session/checkpoint/close helpers and tool-aware context assembly.

Tests: canonical project identity, receipt freshness, unsupported capability status,
context is project-scoped and includes global policy.

### D. CBMEM and tool surfaces

- Make CBMEM direct bridge consume project registry and query/index/status through
  the installed binary.
- Keep the old `lwm-sources.json` snapshot path as migration-only and remove it from
  the default runner path.
- Add CLI/MCP surfaces for session, receipt, health, retain, recall, and project
  state.
- Keep Claude Code, Codex, OpenCode, shell, and VS Code on verified paths; record
  Kiro/Trae/Antigravity/MiniMax status from actual probes, not assumptions.

Tests: CBMEM unavailable/available behavior, MCP schema, CLI smoke tests, no
snapshot indexing in the default cycle.

### E. Installation and acceptance

- Generate and install runtime bundle from a stable copied runtime, not an iCloud
  source import.
- Bootstrap the LaunchAgent, kickstart one supervisor run, and inspect launchctl
  print output.
- Run full tests, lint, audit, strict health, and real adapter probes.
- Write a final verification report with the exact receipts and unsupported-tool
  limitations.

Acceptance: AC-01 through AC-16 in the V2 design document, with no claim of
complete cross-IDE automation unless a real read/write receipt exists.
