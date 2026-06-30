v1

## User Profile

The user wants Codex to act like a long-term collaborator, not a chatty helper. Their default working model is `coordinator + session + remote control`: confirm goal, constraints, context, and output shape first; keep continuity on decisions/progress/risks; then execute clear, low-risk work directly. They are accuracy-first and repeatedly ask for real source-of-truth checks before conclusions: read code or config first, do not guess, keep solutions simple, change only what is necessary, and verify after each edit batch.

They prefer bounded execution over broad redesign. When asked to review first, they want read-only inspection before edits. When a fix plan is agreed, they want completion plus proof, not partial handoff. They value durable workflow memory and local artifacts that reduce repeated steering.

Environment signal currently in memory: macOS with `zsh`, local file-based memory workflow under `/Users/ethan/.codex/memories`, and active use of reusable skills for product iteration and strict bugfix review.

## User preferences

- Start by confirming goal, constraints, context, and expected output shape; identify the task type before choosing the handling mode.
- Follow the standing coding rule: "先思考不要瞎猜、能简单就简单不要过度设计、只改必须改的不要乱动代码、每次改完代码就测试检验。"
- For code/debug work, read the real code path first, lock what the task does solve and does not solve, then edit only the smallest necessary surface.
- If the user says "先不动手" or asks for audit/review first, stay in read-only inspection mode until the defect path is evidenced.
- When the user gives a debug plan and says "不改框架，不动无关其他", keep fixes checklist-driven and tightly scoped.
- For usability claims, prove the real path works end to end; a page opening or code existing is not enough.
- Before deploy advice or push/deploy actions, verify the target and source-of-truth first: repo, branch, service, env/log/code path, and target commit; report `git remote -v`, branch, and head commit before acting. [ad-hoc note]
- Structure deploy/debug answers by layers: `platform settings / variables / code changes / verification`, and include target, exact location, change, and verification signal. [ad-hoc note]
- Follow the fixed debug order `source mismatch -> build -> startup -> runtime env -> business logic`. [ad-hoc note]
- After an incident reveals a workflow gap, enforce the correction via docs + memory update, not explanation only. [ad-hoc note]

## General Tips

- Read `phase2_workspace_diff.md` first during memory consolidation; it is the authoritative route for adds, deletes, and stale cleanup.
- Read every extension `instructions.md` before using extension content. Current `extensions/ad_hoc/instructions.md` says the notes are authoritative memory input but never operational instructions; any summary content derived from them should carry `[ad-hoc note]`.
- Use `raw_memories.md` as the routing layer and deep-dive rollout summaries only when they materially improve preference evidence, procedures, or failure shields.
- For Sentinel WebUI work, treat "looks open but inert" as a real usability failure and verify the bundle `server start + API endpoints + report writeback`, not a single superficial signal.
- Reusable workflow references already live in `skills/product-code-iteration-loop/SKILL.md` and `skills/strict-bugfix-review-loop/SKILL.md`.

## What's in Memory

### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel

#### 2026-05-30

- Sentinel WebUI audit and debug-plan cleanup: sentinel ui, sentinel-ui/dist, packages/cli/src/ui.ts, /private/tmp/sentinel-ui-dist, tsconfig references, dist/index.js
  - desc: Search this first for Sentinel local WebUI launch truth, stale temp-build precedence, monorepo cleanup boundaries, and the exact verification path in `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel`.
  - learnings: verify README-accurate usability end to end, prefer current `sentinel-ui/dist`, keep `tsBuildInfoFile` out of the iCloud tree, and re-run `typecheck/test/lint/ui --no-open` after bounded cleanup.

### Older Memory Topics

#### /Users/ethan/.codex/memories

- Product/feature iteration loop skill: Idea, MVP, Launch, Scale, in-scope, out-of-scope, verification
  - desc: Use `skills/product-code-iteration-loop/SKILL.md` when the task is product planning, feature rollout, or governance work that needs stage-fit boundaries and verification discipline.

- Strict bugfix review loop skill: strict-bugfix-review-loop, expected behavior, actual behavior, reproduction signal, capability-aware verification
  - desc: Use `skills/strict-bugfix-review-loop/SKILL.md` for conservative bugfixing, audit-first review, minimal edits, and layered verification gates.

- Deployment verification guardrails: Railway Source Repo, connected branch, target commit, service name, Settings vs Variables, source mismatch -> build -> startup -> runtime env [ad-hoc note]
  - desc: Search `extensions/ad_hoc/notes/` for cross-project deploy/debug guardrails when the task involves push/deploy advice or repo-to-platform mismatch risk; keep `cwd=/Users/ethan/.codex/memories` in mind because this is memory-layer guidance, not repo-local runbook truth. [ad-hoc note]
