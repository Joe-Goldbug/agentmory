# Task Group: Sentinel WebUI audit, monorepo cleanup, and usability verification

scope: Auditing whether Sentinel's local WebUI really works by the README path, fixing only the proven launch/build/config defects, and verifying the UI and monorepo wiring end to end.
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel; reuse_rule=safe inside the Sentinel checkout for WebUI launch/debug-plan cleanup work, but actual workspace paths, temp build artifacts, and Bun/TypeScript results should be revalidated on the current machine

## Task 1: Audit and fix Sentinel WebUI usability and launch path, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-21T08-03-49-2yML-sentinel_webui_audit_and_debug_plan_cleanup.md (cwd=/Users/ethan/Documents/Codex/2026-05-21/files-mentioned-by-the-user-project, rollout_path=/Users/ethan/.codex/sessions/2026/05/21/rollout-2026-05-21T16-03-49-019e498f-ed7f-7d90-a2aa-b48098677317.jsonl, updated_at=2026-05-30T07:11:23+00:00, thread_id=019e498f-ed7f-7d90-a2aa-b48098677317, WebUI smoke path, stale temp-build diagnosis, and README-accurate local usage verification)

### keywords

- sentinel ui, sentinel-ui/dist, packages/cli/src/ui.ts, pickUiRoot, /private/tmp/sentinel-ui-dist, README path, reports/sentinel-latest.md, reports/sentinel-latest.json, SSE buffer, inert buttons

## Task 2: Apply the debug-plan cleanup without broad refactoring, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-21T08-03-49-2yML-sentinel_webui_audit_and_debug_plan_cleanup.md (cwd=/Users/ethan/Documents/Codex/2026-05-21/files-mentioned-by-the-user-project, rollout_path=/Users/ethan/.codex/sessions/2026/05/21/rollout-2026-05-21T16-03-49-019e498f-ed7f-7d90-a2aa-b48098677317.jsonl, updated_at=2026-05-30T07:11:23+00:00, thread_id=019e498f-ed7f-7d90-a2aa-b48098677317, fake workspace removal, dist entrypoint alignment, root build/lint script cleanup, and post-fix verification)

### keywords

- packages/skills, packages/providers/src/skills/prompts, tsconfig references, package.json workspaces, dist/index.js, dist/index.d.ts, sentinel-ui tsBuildInfoFile, /private/tmp, bun run typecheck, bun run test, bun run lint

## User preferences

- when auditing usability, the user asked for the tool to reach README accuracy and to "确保我能够使用做到" -> default to browser/server smoke plus report-writeback proof, not code inspection only [Task 1]
- when the user said "先不动手", start in read-only review mode and gather evidence before edits [Task 1]
- when the user asked for a "debug plan，然后按照 plan 准确 debug（不改框架，不动无关其他）", keep fixes checklist-driven and tightly scoped to the proven defect path [Task 1][Task 2]
- when the user asked to validate and then fix, pair every bounded edit batch with re-run verification instead of handing back a patch without proof [Task 1][Task 2]

## Reusable knowledge

- `sentinel ui` is the local WebUI entry, and the launcher should serve the current UI from `sentinel-ui/dist` rather than stale temp output [Task 1]
- The no-key demo path is valid when `.sentinel/llm.yml` is absent and should still write `reports/sentinel-latest.md` and `reports/sentinel-latest.json` into the target project [Task 1]
- The working smoke bundle for this path is not just "server starts": check `GET /api/bootstrap`, `GET /api/projects`, `POST /api/projects/current/run`, then confirm report writeback in the temp project [Task 1]
- Root monorepo truth after cleanup: `sentinel-ui` stays in root workspaces and root `tsconfig.json` references, workspace package entrypoints point to `dist/index.js` plus `dist/index.d.ts`, and the useful prompt markdown moved under `packages/providers/src/skills/prompts/` after removing the fake `packages/skills` package [Task 2]
- `sentinel-ui` build metadata should stay outside the iCloud-synced tree by writing `tsBuildInfoFile` under `/private/tmp/...`; this avoids environment-specific EPERM failures during `tsc -b` [Task 2]
- Verified checks for this cleanup were `bun run typecheck`, `bun run test`, `bun run lint`, and `bun packages/cli/src/index.ts ui --no-open --port 45124` [Task 2]
- Related skill: skills/strict-bugfix-review-loop/SKILL.md

## Failures and how to do differently

- Symptom: the UI opens but "doesn't really work". Cause: inert buttons, stubbed APIs, or silent mock fallbacks can make the page look alive while the product path is broken. Fix: classify this as a usability defect and verify the real run/report flow, not only the shell page load [Task 1]
- Symptom: the wrong UI appears even after fixes. Cause: launcher precedence favored stale `/private/tmp/sentinel-ui-dist`. Fix: make the launcher prefer the current `sentinel-ui/dist` unless temp output was deliberately refreshed [Task 1]
- Symptom: `tsc -b` fails in this repo even though code is fine. Cause: TypeScript build metadata writes inside iCloud-backed directories. Fix: move `tsBuildInfoFile` to `/private/tmp` and keep front-end references minimal and explicit [Task 2]
- Symptom: a cleanup patch causes a follow-up compile error after removing exports or packages. Cause: adjacent packages still depend on the removed type/import path. Fix: after pruning entrypoints or re-exports, immediately audit dependent imports and rerun typecheck before broader validation [Task 2]
