# LLM-WorkMem Global Contract

LLM-WorkMem is a shared, source-backed evidence layer for local IDEs and shell. Native tool instructions, skills, memory, session state, planning, execution, and verification remain authoritative.

## One workflow

`sync -> truth -> execute -> verify -> write back`

- Read the current project context before acting.
- Separate verified facts, inference, assumptions, and unknowns.
- Execute one bounded task with the smallest necessary change.
- Verify with tests, build, logs, runtime behavior, or a direct check.
- Write back only durable cross-tool evidence: decisions, meaningful changes, verification, risks, preferences, and open loops.

## One memory boundary

- `wiki/purpose.md`: what belongs in long-term memory.
- `wiki/overview.md`: current system synthesis and automation status.
- `wiki/projects/<project_id>.md`: one project page containing meaningful status, decisions, bugfixes, verifications, and open questions.
- `wiki/global/`: audited cross-project rules and principles.
- `raw/events/`: sanitized append-only evidence; lifecycle receipts are not durable knowledge by themselves.
- `raw/tool-snapshots/` and `raw/cbmem-snapshots/`: current source evidence, not polished memory.

## Promotion rule

Keep temporary observations, empty lifecycle events, unchanged snapshots, full conversations, and unverified guesses out of durable Wiki pages. Promote only reusable, source-backed, high-signal knowledge through review.

## Runtime and Git boundary

Runtime state, receipts, logs, caches, absolute local paths, and launchd state are rebuilt locally and are not the long-term truth source. Git synchronizes code, tests, adapters, `GLOBAL.md`, durable Wiki pages, and reviewed project knowledge.

## Cross-tool handoff

Every IDE and shell may read the same LLM-WorkMem evidence and write sanitized events through `lwm hub record`. The active tool still decides the answer and owns its native workflow.
