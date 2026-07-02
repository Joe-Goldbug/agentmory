# Task Group: Cross-project truth-first execution, deploy targeting, and cross-Mac Codex sync

scope: Cross-project operating rules for target verification before planning/execution, deploy/debug answer structure, exact Railway field scoping, and the approved cross-Mac sync model for Codex.
applies_to: cwd=/Users/ethan/.codex/memories; reuse_rule=safe across repos when the task involves planning, execution, push/deploy guidance, target-sensitive debugging, or Codex cross-Mac setup; revalidate repo/platform-specific facts at execution time

## Task 1: Enforce truth-first planning and execution before acting, outcome success

### rollout_summary_files

- extensions/ad_hoc/notes/20260607-0002-hard-rule-planning-execution.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260607-0002-hard-rule-planning-execution.md, updated_at=2026-06-07, repeat confirmation that plausible is not enough)
- extensions/ad_hoc/notes/20260607-0001-enforce-truth-during-planning-execution.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260607-0001-enforce-truth-during-planning-execution.md, updated_at=2026-06-07, planning/execution extension of the hard rule)
- extensions/ad_hoc/notes/20260606-2045-enforce-truth-correctness.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260606-2045-enforce-truth-correctness.md, updated_at=2026-06-06, authoritative extension note for anti-guessing and source-of-truth-first behavior)

### keywords

- truth-first, anti-guessing, source-of-truth, verify premise, target state, success criteria, planning, execution, hard failure, plausible is not enough

## Task 2: Verify repo/branch/service target before deploy guidance, outcome success

### rollout_summary_files

- extensions/ad_hoc/notes/20260515-003020-universal-verification-workflow.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260515-003020-universal-verification-workflow.md, updated_at=2026-05-15, generalized the deploy checks beyond Railway)
- extensions/ad_hoc/notes/20260515-002650-deploy-guardrails-enforce.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260515-002650-deploy-guardrails-enforce.md, updated_at=2026-05-15, fixed deploy output contract and debug order)
- extensions/ad_hoc/notes/20260515-001400-railway-source-verification-first.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260515-001400-railway-source-verification-first.md, updated_at=2026-05-15, source-repo mismatch incident and corrected deploy order)
- extensions/ad_hoc/notes/20260514-235508-railway-settings-clarity.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260514-235508-railway-settings-clarity.md, updated_at=2026-05-14, exact Railway service/page/field mapping)

### keywords

- Railway, Source Repo, branch, target commit, git remote -v, service name, Settings, Variables, Root Directory, Build Command, Start Command, Port, source mismatch, build, startup, runtime env, business logic

## Task 3: Keep cross-Mac Codex sync limited to account settings plus iCloud Drive state, outcome success

### rollout_summary_files

- extensions/ad_hoc/notes/20260611-icloud-account-only-sync-rule.md (cwd=/Users/ethan/.codex/memories, rollout_path=/Users/ethan/.codex/memories/extensions/ad_hoc/notes/20260611-icloud-account-only-sync-rule.md, updated_at=2026-06-11, current cross-Mac sync rule)

### keywords

- cross-Mac, Codex sync, Custom Instructions, Memory, iCloud Drive, shared state files, account-level settings, do not propose other sync mechanisms

## User preferences

- when planning or executing work, the standing correction is: do not let a merely plausible path advance; verify premise, target state, and success criteria before acting [Task 1]
- when a task involves deploy or target-sensitive debugging, the user wants repo/remote, branch, head commit, service/env, and code path verified before advice or changes are proposed [Task 2]
- when giving platform guidance, the user wants exact layering and exact location: service name first, then page (`Settings` or `Variables`), then field name, then verification signal; do not mix them [Task 2]
- for cross-Mac Codex consistency, default to account-level settings (`Custom Instructions` and `Memory`) plus iCloud Drive shared state files; do not propose other sync mechanisms unless explicitly asked [Task 3]

## Reusable knowledge

- Treat lying, guessing, and pushing wrong actions as hard failures; when evidence is weak or contradictory, stop and verify before planning or execution [Task 1]
- The fixed cross-project debug order is `source mismatch -> build -> startup -> runtime env -> business logic`; do not jump into business logic before earlier layers are cleared [Task 2]
- For deploy/push work, report `git remote -v`, current branch, and head commit before high-impact steps, then structure the answer as `platform settings / variables / code changes / verification` with target, exact location, change, and proof signal [Task 2]
- Railway-specific field truth preserved from the incident: `Start Command` plus `Root Directory` belongs under `@ather/api -> Settings`; it is not `web`, and it is not `Variables` [Task 2]
- The verified mismatch pattern from the incident was "patched repo != Railway source repo"; one cited example was Railway deploying `EthanLau1/Ather` while fixes had been pushed to `Joe-Goldbug/ather-cyberpunk-self-discovery`, which then surfaced as `Script not found "railway:build:api"` on stale branch state [Task 2]
- Cross-Mac shared truth for Codex should be treated as the same account behavior plus the same iCloud working-state files, not extra ad hoc sync layers [Task 3]
- Related skill: skills/truth-first-execution-checks/SKILL.md

## Failures and how to do differently

- Symptom: a plan sounds reasonable but would produce the wrong result. Cause: premise, target state, or success criteria were assumed instead of verified. Fix: stop before execution and correct the plan first; plausible is not enough [Task 1]
- Symptom: pushed fixes do not affect the deployed service. Cause: source repo or connected branch mismatch. Fix: verify the actual platform source repo, connected branch, and target commit before build/start/env guidance or push/deploy actions [Task 2]
- Symptom: deployment instructions are confusing or wrong. Cause: service/page/field paths were mixed together. Fix: answer in `service -> page -> field=value -> verification signal` form and keep `Settings` fields separate from `Variables` [Task 2]
- Symptom: cross-Mac setup advice drifts into unsupported sync mechanisms. Cause: the approved sync boundary was not respected. Fix: stay within account-level settings plus iCloud Drive shared state files unless the user explicitly asks for alternatives [Task 3]

# Task Group: Ather local auth-routing fix and quota-aware profile planning

scope: Ather repo memory for proving local login/chat routing bugs before patching, validating mock-only versus app-wide blast radius, and planning quota-aware profile/chat growth before product changes.
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather; reuse_rule=safe for Ather auth-routing, local mock verification, and hosting/quota planning in this checkout; treat capacity figures as planning estimates unless revalidated against current pricing and repo state

## Task 1: Verify and fix local email login -> chat return flow, outcome success

### rollout_summary_files

- rollout_summaries/2026-04-23T05-25-26-fC2W-ather_local_login_fix_and_capacity_planning.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather, rollout_path=/Users/ethan/.codex/sessions/2026/04/23/rollout-2026-04-23T13-25-26-019db8cc-daad-7633-87d5-17e03896cbd6.jsonl, updated_at=2026-06-09T15:09:35+00:00, thread_id=019db8cc-daad-7633-87d5-17e03896cbd6, verified route-preserving login fix plus local mock matcher repairs)

### keywords

- login redirect, returnTo, /chat, /login, baseline_completed, MOCK_DB, MOCK_REDIS, ATHER_LOCAL_MOCK_LLM, validateToken, conversation ownership, safeReturnTo, build:web, tsc --noEmit

## Task 2: Capacity planning / free-tier economics / profile-page product shape, outcome partial

### rollout_summary_files

- rollout_summaries/2026-04-23T05-25-26-fC2W-ather_local_login_fix_and_capacity_planning.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather, rollout_path=/Users/ethan/.codex/sessions/2026/04/23/rollout-2026-04-23T13-25-26-019db8cc-daad-7633-87d5-17e03896cbd6.jsonl, updated_at=2026-06-09T15:09:35+00:00, thread_id=019db8cc-daad-7633-87d5-17e03896cbd6, quota planning and product-shape estimate for profile/chat growth)

### keywords

- Upstash, Resend, Railway, Neon, Vercel, quota planning, free-tier, DAU, profile page, evidence events, micro-sandbox, chat pricing, profitability, /profile

## User preferences

- when the user said "验证上述是真 bug，才执行计划修改-然后执行修复-验证" -> prove the bug first, then make the smallest fix, then validate it [Task 1]
- when the user said "我从来没说 API 坏了！我只说要换 API！" -> treat the issue as route/login-flow and local-test behavior, not as a broad API failure [Task 1]
- when the user later asked whether the change was local-only or global -> report blast radius explicitly as local mock-only vs app-wide runtime vs build/tooling, not one mixed answer [Task 1]
- when the user said "必须先计划，这样子修改我部署的线上使用量，多少用户多少量多少天就超额度？？先计划这个！" -> do capacity planning before any code or product change [Task 2]
- when the user said the business must be "商业平衡甚至盈利和让用户满意" -> optimize for both user satisfaction and profit, not just tech correctness [Task 2]
- when the user asked whether Ather had a "个人用户展示页面" beyond just test results -> treat `/profile` as the long-term persona home, not a one-off report [Task 2]

## Reusable knowledge

- In Ather, the validated login-to-chat fix is route-preserving: carry `returnTo=%2Fchat` from `/chat` into `/login`, then honor it only through a safe local-path allowlist [Task 1]
- Safe fallback matters: if `baseline_completed` is false, login should still follow the normal assessment-entry flow instead of forcing chat [Task 1]
- The local mock verification bundle that proved the flow end-to-end was `MOCK_DB=1 + MOCK_REDIS=1 + ATHER_LOCAL_MOCK_LLM=1`; with that bundle, `send-code` auto-logs in and the same cookie can be reused across `/auth/me`, `/assessment/complete`, `/chat/history`, and `/chat/send` [Task 1]
- `chat/send`, `getDialogueState`, and `getHistory` remain gated by baseline completion unless local mock mode is enabled, so "logged in but cannot use chat" can be a baseline gate issue, not a front-end routing bug [Task 1]
- The final verified flow was `send-code -> auth/me -> assessment/complete -> auth/me baseline=true -> chat/history -> chat/send`, and `chat/send` returned a mock reply with `dialogue_state.total_turns=1` [Task 1]
- Ather should not make every chat turn or practice test a full image recomputation; the better pattern is to write evidence every time and absorb it into the current profile with weights, confidence, and per-source limits [Task 2]
- The product split that emerged is: baseline and first report as free acquisition, then a limited short debrief chat for free, and longer/frequent chat or deeper reports as paid or heavily rate-limited [Task 2]
- A reasonable first safety band under free quotas was estimated as roughly 100-150 DAU, with 3 chat turns per free user per session/day and limited practice updates; beyond that, Redis, email, backend, and model costs need active control [Task 2]
- The current `/profile` page should evolve into the long-lived user personality home: baseline vector vs current vector, chat influence, micro-sandbox influence, diary influence, evidence timeline, confidence, and correction history [Task 2]

## Failures and how to do differently

- Symptom: `send-code` looked successful but `/auth/me` returned `401`. Cause: the mock DB regex did not flatten whitespace, so the validate-token SQL missed the inserted token. Fix: adapt the mock matcher in `apps/api/src/common/pool.ts`, not production auth [Task 1]
- Symptom: auth succeeded but `/chat/send` returned `500` with evidence ownership errors. Cause: the mock conversation matcher did not match the real insert shape. Fix: distinguish the two `INSERT INTO conversations` forms rather than changing production chat ownership logic [Task 1]
- Symptom: `build:api` failed on duplicated `* 2.ts` files. Cause: copied files in `packages/core/src` were included by TypeScript. Fix: exclude `**/* 2.ts` from core tsconfig [Task 1]
- Symptom: later planning turns lost live repo access with `Operation not permitted`. Cause: the quota model could not be recomputed from the worktree at that point. Fix: use public pricing pages plus previously verified architecture notes, and label the result as a planning estimate rather than live accounting [Task 2]
- Symptom: product planning reaches for a paywall too early. Cause: cost pressure gets solved before the user experiences the core value loop. Fix: preserve `test -> result -> save -> short debrief` before locking persistent chat or deeper profile updates behind payment [Task 2]

# Task Group: llm-workmem automated knowledge body, adapters, and local startup workflow

scope: Durable memory for turning `llm-workmem` into the user's central automated knowledge body, harvesting multiple tool ecosystems, feeding adapters back into those tools, and explaining local shell/web usage.
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem; reuse_rule=safe for llm-workmem work in this repo family and related local-tooling discussions, but revalidate exact source paths and install targets before rerunning automation

## Task 1: Build personal knowledge-body base, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-06T05-13-43-4xVW-lwm_personal_knowledge_body_and_multi_tool_adapters.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem, rollout_path=/Users/ethan/.codex/sessions/2026/05/06/rollout-2026-05-06T13-13-43-019dfbb4-cd6c-7ce3-8b37-14a8c559976c.jsonl, updated_at=2026-06-06T17:16:29+00:00, thread_id=019dfbb4-cd6c-7ce3-8b37-14a8c559976c, personal knowledge-body base plus local serve/analysis validation)

### keywords

- llm-workmem, 建立我自己知识体, --profile personal, lwm analyze, wiki/insights, graph-health, hubs, orphans, duplicate slugs, UV_CACHE_DIR, UV_PROJECT_ENVIRONMENT

## Task 2: Harvest and re-export all tool memories, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-06T05-13-43-4xVW-lwm_personal_knowledge_body_and_multi_tool_adapters.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem, rollout_path=/Users/ethan/.codex/sessions/2026/05/06/rollout-2026-05-06T13-13-43-019dfbb4-cd6c-7ce3-8b37-14a8c559976c.jsonl, updated_at=2026-06-06T17:16:29+00:00, thread_id=019dfbb4-cd6c-7ce3-8b37-14a8c559976c, harvest/watch/export/adapters/install-global/attach loop exercised end-to-end)

### keywords

- harvest, watch, export, adapters, attach, install-global, llms.txt, llms-full.txt, llms.json, Kiro, shell, Codex, Claude Code, VSCode, Trae, Copilot, sources list, raw/tool-snapshots

## Task 3: Validate the new local web and shell workflow, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-06T05-13-43-4xVW-lwm_personal_knowledge_body_and_multi_tool_adapters.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem, rollout_path=/Users/ethan/.codex/sessions/2026/05/06/rollout-2026-05-06T13-13-43-019dfbb4-cd6c-7ce3-8b37-14a8c559976c.jsonl, updated_at=2026-06-06T17:16:29+00:00, thread_id=019dfbb4-cd6c-7ce3-8b37-14a8c559976c, shell-vs-web startup clarification and local server verification)

### keywords

- shell 还是网页, lwm serve, 127.0.0.1:8765, 501 Unsupported method ('HEAD'), curl -I, lsof -nP -iTCP:8765 -sTCP:LISTEN, launchd

## User preferences

- when the user repeatedly said the goal was to "根据我项目我文档咨询我想法来建立我自己知识体" and to make it "自动化处理我项目和想法所有关系的内在联系和洞察" -> for similar work, default to a knowledge-body / cross-project relationship model instead of a plain notes app [Task 1]
- when the user asked "启动 llm wiki 必须在后台吗？shell 还是网页？" -> proactively explain shell vs web vs background responsibilities [Task 1][Task 3]
- when the user explicitly asked to "自动收集 codex Claude trae kiro vscode 我本地所有 ide 和 shell 的工作流和记忆体，融合起来，然后又能让各自 IDE 和 shell 能读取这里利用起来使它们 IDE 和 shell 更优质" -> design for a bidirectional hub, not a one-way archive [Task 2]
- when the user asked "我的好东西如果在 llm wiki 为什么不让工作工具来读取" -> expose direct tool-readable adapters, not just human docs [Task 2]
- when the user asked for the work to be done, they said "根据上述做出来做到我目标效果，仔细审核-计划-执行" -> do a careful audit/plan/execute sequence before changing code [Task 1][Task 2]

## Reusable knowledge

- `uv run` in this repository works with `UV_CACHE_DIR=/private/tmp/uv-cache` and `UV_PROJECT_ENVIRONMENT=/private/tmp/uv-venv` when the default cache/venv paths are blocked by permissions [Task 1]
- `pytest -q` and `ruff check .` both pass when run in the temp environment; use those exact env vars for repeatable verification [Task 1]
- `lwm analyze` inspects hubs, orphans, broken links, missing sources, duplicate slugs, and connected components, and can write reports into `wiki/insights/` [Task 1]
- The new `personal` profile creates a project/decision/pattern/conflict/question/principle/preference-oriented structure that matches the user's "知识体" framing [Task 1]
- The repository now has a `lwm watch` flow that harvests active tool-memory sources into `raw/tool-snapshots/`, refreshes the wiki, writes `llms.txt`, `llms-full.txt`, and `llms.json`, and then audits the result [Task 2]
- `lwm sources list` reports configured tool-memory source groups and marks each path as found or missing, including Kiro and shell [Task 2]
- `lwm adapters` writes adapter files under `adapters/`, `lwm attach <project>` installs project-level entrypoints, and `lwm install-global <root>` writes global entrypoints such as `~/.codex/AGENTS.md`, `~/CLAUDE.md`, `~/.traerules`, `~/.kiro/steering/llm-workmem.md`, `~/.zshrc`, and `~/.config/lwm/context.json` [Task 2]
- `lwm serve` provides the local web UI on port 8765; shell is the command/control plane, the browser is the display plane, and background is only needed for automated `watch/harvest/audit` scheduling [Task 3]
- Related skill: skills/product-code-iteration-loop/SKILL.md

## Failures and how to do differently

- Symptom: test runs fail in the default environment. Cause: `uv` tries to create `.venv` inside the iCloud-synced repo and cache writes hit blocked paths. Fix: redirect cache and venv to `/private/tmp` before concluding the code is broken [Task 1]
- Symptom: fresh `watch` or `schedule` runs fail audit immediately. Cause: generated runner files or base policy/entity pages are missing. Fix: keep generated runners inside the repo and seed the init tree with the required bridge pages first [Task 1]
- Symptom: generated launcher files trip `ruff`. Cause: the generation path needs explicit lint suppression for import ordering. Fix: add `# ruff: noqa: E402` to the generated launcher files rather than distorting the main logic [Task 1]
- Symptom: adapter generation fails or produces bad shell glue. Cause: quoting or shell formatting mistakes. Fix: simplify script generation and retest before writing repo files [Task 2]
- Symptom: the system only archives data and does not improve the tools. Cause: the reverse-read path was omitted. Fix: always think in pairs: `harvest + adapter/install` [Task 2]
- Symptom: local startup looks broken because `curl -I` returns `501 Unsupported method ('HEAD')`. Cause: the server does not support HEAD. Fix: verify with GET or `lsof -nP -iTCP:8765 -sTCP:LISTEN` instead [Task 3]

# Task Group: Sentinel WebUI audit and debug-plan cleanup

scope: Sentinel repo memory for verifying that the local WebUI matches README claims, correcting stale launch/build wiring, and applying checklist-driven monorepo cleanup without broad refactors.
applies_to: cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel; reuse_rule=safe for Sentinel local WebUI, CLI UI launcher, and monorepo config cleanup tasks in this checkout; verify current dist path and workspace wiring before reusing

## Task 1: Audit and fix Sentinel WebUI usability + structure, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-21T08-03-49-2yML-sentinel_webui_audit_and_debug_plan_cleanup.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel, rollout_path=/Users/ethan/.codex/sessions/2026/05/21/rollout-2026-05-21T16-03-49-019e498f-ed7f-7d90-a2aa-b48098677317.jsonl, updated_at=2026-05-30T07:11:23+00:00, thread_id=019e498f-ed7f-7d90-a2aa-b48098677317, README-path audit plus current-dist launch verification)

### keywords

- sentinel-ui, webui, ui.ts, dist, demo fallback, SSE buffer, reports/sentinel-latest.json, bun packages/cli/src/index.ts ui, /private/tmp/sentinel-ui-dist

## Task 2: Apply the debug-plan cleanup and verify it without broad refactoring, outcome success

### rollout_summary_files

- rollout_summaries/2026-05-21T08-03-49-2yML-sentinel_webui_audit_and_debug_plan_cleanup.md (cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel, rollout_path=/Users/ethan/.codex/sessions/2026/05/21/rollout-2026-05-21T16-03-49-019e498f-ed7f-7d90-a2aa-b48098677317.jsonl, updated_at=2026-05-30T07:11:23+00:00, thread_id=019e498f-ed7f-7d90-a2aa-b48098677317, checklist-driven monorepo cleanup and verification)

### keywords

- packages/skills, packages/providers/src/skills/prompts, dist entrypoints, tsconfig references, build scripts, lint scripts, tsBuildInfoFile, iCloud EPERM, typecheck, test, lint

## User preferences

- when the user says the WebUI should be usable and "达到 readme 的准确，检查，确保我能够使用做到" -> verify actual end-to-end usability against README claims, not just code presence [Task 1]
- when the user says "先不动手" during the audit pass -> begin with inspection and evidence before edits when requested [Task 1]
- when the user later asks for a "debug plan，然后按照 plan 准确 debug（不改框架，不动无关其他）" -> keep fixes tightly scoped to the identified plan and avoid unrelated refactors [Task 1][Task 2]
- when the user supplies a concrete "发现清单 & 修复计划" and then asks to "验证" -> implement in checklist order and pair each fix with rerun validation [Task 2]

## Reusable knowledge

- The accepted local WebUI command is `bun packages/cli/src/index.ts ui` [Task 1]
- The launcher should serve from `sentinel-ui/dist`; stale `/private/tmp/sentinel-ui-dist` precedence was the concrete failure mode to avoid [Task 1]
- The no-key demo path is valid when `.sentinel/llm.yml` is absent and should still write `reports/sentinel-latest.md` and `reports/sentinel-latest.json` in the target project [Task 1]
- `GET /api/bootstrap`, `GET /api/projects`, and `POST /api/projects/current/run` are the useful smoke bundle for proving the WebUI works as a product path rather than just as an HTTP server [Task 1]
- `packages/skills` was a fake/empty workspace package and the useful prompt markdown belongs under `packages/providers/src/skills/prompts/` [Task 2]
- Root `tsconfig.json` should reference `./sentinel-ui`, package entrypoints should target `dist/index.js` and `dist/index.d.ts`, and `sentinel-ui` should keep `@sentinel/core` as a workspace dependency so contracts stay aligned [Task 2]
- `sentinel-ui` needs its `tsBuildInfoFile` outside the iCloud tree, under `/private/tmp/...`, to avoid EPERM on build metadata writes [Task 2]

## Failures and how to do differently

- Symptom: the UI opens but does not really work. Cause: inert buttons, stubbed APIs, or silent mock fallbacks hide the failure. Fix: classify "looks alive but does nothing" as a usability defect and run an actual smoke flow with report writeback [Task 1]
- Symptom: the wrong UI appears even though the current source looks correct. Cause: the launcher prefers a stale temp build. Fix: verify the effective UI root and remove stale build precedence unless it is deliberately refreshed [Task 1]
- Symptom: file moves or build steps fail in the iCloud-backed checkout. Cause: write targets like build metadata land inside restricted synced directories. Fix: move build-info outputs to `/private/tmp` and keep package cleanup scoped [Task 2]
- Symptom: cleanup introduces a follow-up compile error. Cause: a dependent type import was pruned along with an export. Fix: after entrypoint cleanup, immediately re-run typecheck and inspect dependent imports such as `FixOption` in `packages/cli/src/run.ts` [Task 2]
