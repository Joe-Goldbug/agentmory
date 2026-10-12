# LLM-WorkMem collaboration checkpoint — 2026-10-12

Base revision: `96ddb9522257e1b1f3710bf66243b7f75bc18213`.
This branch shares the verified local core changes for backend coordination.
It is a draft integration checkpoint, not a release or deployment claim.

## Included changes

- `lwm/structured_candidates.py`: ignore generic transport observations and transport-only tags; retain previously recorded counterevidence through regeneration and analysis seeding.
- `lwm/queue_compaction.py`: retire redundant automatic queue plans with persisted recovery mappings; preserve human-reviewed records and source evidence.
- `lwm/memory_compiler.py`: deterministic evidence projection, explicit byte-based admission estimates, bounded queue priority with aging, and order-insensitive evidence comparison.
- Three focused test files cover queue compaction, compiler behavior and counterevidence preservation.

No gateway endpoint or request/response schema is changed by this checkpoint.
Do not copy machine-local queue/state files between developers. Queue compaction is reached by analysis seeding and changes pending machine-local plans; review this behavior before running a real cycle.

## Coordination with backend work

Remote `main` and `agent/sync-llm-workmem` were both at the base revision during this check. `feat/web-gateway` was at `e99dd233ccc00c8b9bd5320553f563708f31a539` and `feat/web-integration` at `345acba016319d60c045e7f971e634123acce58b`.
The gateway feature branch has two unique commits and is five commits behind this base. Review individual commits before integration; it overlaps current core, gateway, frontend and documentation paths. Avoid merging the whole branch into a dirty checkout.

Use this Draft PR as the shared review point: record backend endpoint/schema changes and their owning branch in the PR before merging. This checkpoint does not prove that unpublished collaborator work has been inspected.

## Local work still outside this commit

- Frontend direct-entry changes remove the login UI while backend auth handlers remain. The intended single-machine/auth boundary needs one shared decision.
- Backup and Web3 files are local experimental prototypes. Browser storage currently uses sessionStorage; generated remote URIs and transaction identifiers do not prove upload or chain confirmation.
- Current base Web build references backup/Web3 modules absent from its committed tree. Gateway backup handling similarly references an absent backup module. This draft does not fix those existing base omissions; do not treat a local dirty-tree build as clean-clone proof.
- Gateway authorization, safe bounded archive extraction/restore, wallet signature verification, real-mode mock separation and API/documentation alignment remain open.
- Host configuration contains credential-shaped values. Rotate potentially exposed credentials and review history separately. No host config, personal memory, runtime state, cache or nested worktree is added in this commit.
- README/design edits, logos and unrelated local tool changes are not part of the verified core checkpoint.

## Verification

Focused source tests: 28 passed. Focused Ruff: passed. Candidate-tree validation is recorded in the Draft PR description. No remote backup, wallet, chain transaction or production deployment is claimed.
