v1

## User Profile

The user wants Codex to behave like a long-term collaborator: verify the real target first, think before acting, keep scope tight, and prove outcomes with concrete checks. They care about correctness over speed when the two conflict, especially for deploy/debug/product decisions that could touch the wrong repo, branch, service, or quota model.

They repeatedly push for audit-first execution: inspect current code or config before editing, distinguish real breakage from assumption drift, and explain blast radius clearly. For product or quota-sensitive work, they want planning before implementation. For tooling/memory systems, they prefer automation, shared memory, and tool-readable outputs over manual note-taking.

Environment signal in memory: macOS with `zsh`, file-based memory under `/Users/ethan/.codex/memories`, frequent work in iCloud-backed repos, and a cross-Mac Codex sync boundary limited to account settings plus iCloud Drive shared state files. [ad-hoc note]

## User preferences

- Follow the standing rule: "先思考不要瞎猜、能简单就简单不要过度设计、只改必须改的不要乱动代码、每次改完代码就测试检验。"
- In code/debug work, read the real path first, prove the failure, then make the smallest fix and close with build/test or equivalent evidence.
- Do not let a merely plausible path advance; verify premise, target state, and success criteria before planning or execution. [ad-hoc note]
- For deploy or target-sensitive debugging, verify repo/remote, branch, head commit, service/env, and exact page/field before advising or changing anything. [ad-hoc note]
- Structure deploy/debug answers as `platform settings / variables / code changes / verification`, with exact target, location, change, and proof signal; do not mix `Settings` and `Variables`. [ad-hoc note]
- If the user scopes out a verification surface such as "API 暂时不需检测，略过", continue with code/file/log evidence instead of insisting on live probes.
- If the user asks for planning first, especially around quota, pricing, or product-impact changes, model budget and limits before proposing code changes.
- When a change could be local-only versus app-wide, report blast radius explicitly instead of giving one mixed answer.
- For workflow/tooling memory systems, default to scheduled, source-driven automation plus tool-readable adapters, not manual note placement.
- For cross-Mac Codex consistency, use only account-level settings (`Custom Instructions` and `Memory`) plus iCloud Drive shared state files unless explicitly asked for another sync path. [ad-hoc note]

## General Tips

- `phase2_workspace_diff.md` is the first routing file for Phase 2 consolidation; treat its adds/deletes as authoritative.
- Read every extension `instructions.md` before using extension content. Current `extensions/ad_hoc/instructions.md` requires consolidating all notes and tagging summary-derived content with `[ad-hoc note]`. [ad-hoc note]
- Cross-project debug order is `source mismatch -> build -> startup -> runtime env -> business logic`. [ad-hoc note]
- In iCloud-backed repos, early failures are often cache/build-metadata write problems rather than app logic; check write targets before assuming the code is broken.
- Current reusable workflow skills live in `skills/product-code-iteration-loop/SKILL.md`, `skills/strict-bugfix-review-loop/SKILL.md`, and `skills/truth-first-execution-checks/SKILL.md`.
- In current Ather memory, start with the local auth-routing/quota-planning block for `returnTo`, mock-only versus app-wide blast radius, and `/profile` growth limits.

## What's in Memory

### /Users/ethan/.codex/memories

#### 2026-06-11

- Cross-project truth-first execution, deploy targeting, and cross-Mac Codex sync: truth-first, git remote -v, Railway, Settings, Variables, iCloud Drive, Custom Instructions [ad-hoc note]
  - desc: Search this first for planning/execution rules, deploy-target verification, Railway field-path answers, or Codex cross-Mac setup in `cwd=/Users/ethan/.codex/memories`. [ad-hoc note]
  - learnings: verify premise and target before acting, answer deploy work as `service/page/field=value/proof`, and keep Codex sync limited to account settings plus iCloud state files. [ad-hoc note]

### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather

#### 2026-06-09

- Ather local auth-routing fix and quota-aware profile planning: returnTo, /chat, /login, baseline_completed, MOCK_DB, Upstash, Resend, /profile
  - desc: Search this first in `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather` when the task touches login-to-chat routing, local mock verification, blast radius reporting, or quota-aware profile/chat growth.
  - learnings: preserve `returnTo=%2Fchat` only through a safe local-path allowlist, validate local auth/chat with the mock bundle, and do quota math before changing profile/chat behavior.

### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem

#### 2026-06-06

- llm-workmem personal knowledge body, multi-tool harvest, and shell/web startup: llm-workmem, --profile personal, harvest, watch, adapters, install-global, Kiro, shell, 127.0.0.1:8765
  - desc: Search this first in `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem` when the task is to build the user's central knowledge body, harvest tool memories, expose adapters back to tools, or explain shell vs web vs background roles.
  - learnings: use `/private/tmp` for `uv` cache/venv in this repo, think in pairs `harvest + adapter/install`, and verify local serve with GET or `lsof` because HEAD returns 501.

### Older Memory Topics

#### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel

- Sentinel WebUI audit and debug-plan cleanup: sentinel-ui, bun packages/cli/src/index.ts ui, dist, packages/skills, tsBuildInfoFile, reports/sentinel-latest.json
  - desc: Use for `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Sentinel` when verifying the local WebUI against README claims, fixing stale UI launch/build wiring, or applying checklist-driven monorepo cleanup without a framework rewrite.

#### /Users/ethan/.codex/memories

- Truth-first execution checks skill: truth-first-execution-checks, source mismatch, git remote -v, service -> page -> field=value -> verification signal [ad-hoc note]
  - desc: Use `skills/truth-first-execution-checks/SKILL.md` when deploy/debug/push work risks acting on the wrong repo, branch, service, environment, or plan. [ad-hoc note]

- Strict bugfix review loop skill: strict-bugfix-review-loop, expected behavior, actual behavior, reproduction signal, layered verification
  - desc: Use `skills/strict-bugfix-review-loop/SKILL.md` for audit-first bugfixing, minimal edit scope, and capability-aware checks.

- Product/feature iteration loop skill: Idea, MVP, Launch, Scale, in-scope, out-of-scope, verification
  - desc: Use `skills/product-code-iteration-loop/SKILL.md` for product planning or feature iteration that needs explicit scope boundaries and verification discipline.
