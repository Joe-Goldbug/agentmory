v1

## User Profile

The user wants Codex to behave like a long-term collaborator that verifies the real target first, thinks before acting, keeps scope tight, and proves outcomes with concrete checks. They care about correctness over speed when the task could touch the wrong repo, branch, service, page, quota model, or user flow.

They repeatedly steer toward audit-first execution: inspect current code/config first, distinguish real breakage from assumption drift, and explain blast radius clearly. For product or quota-sensitive work, they want planning before implementation. In UX work, they often care about the full reading/conversion sequence rather than isolated text edits. For tooling and memory systems, they prefer automation, shared memory, and tool-readable outputs over manual note-taking.

Environment signal in memory: macOS with `zsh`, file-based memory under `/Users/ethan/.codex/memories`, frequent work in iCloud-backed repos, and a cross-Mac Codex sync boundary limited to account settings plus iCloud Drive shared state files. [ad-hoc note]

## User preferences

- Follow the standing rule: "先思考不要瞎猜、能简单就简单不要过度设计、只改必须改的不要乱动代码、每次改完代码就测试检验。"
- Do not let a merely plausible path advance; verify premise, target state, and success criteria before planning or execution. [ad-hoc note]
- In code/debug work, read the real path first, prove the failure, make the smallest fix, and close with build/test or equivalent evidence.
- For deploy or target-sensitive debugging, verify repo/remote, branch, head commit, service/env, and exact page/field before advising or changing anything. [ad-hoc note]
- Structure deploy/debug answers as `platform settings / variables / code changes / verification`, with exact target, location, change, and proof signal; do not mix `Settings` and `Variables`. [ad-hoc note]
- If the user scopes out a verification surface such as "API 暂时不需检测，略过", continue with code/file/log evidence instead of insisting on live probes.
- If the user asks for planning first, especially around quota, pricing, or product-impact changes, model budget and limits before proposing code changes.
- When a change could be local-only versus app-wide, report blast radius explicitly instead of giving one mixed answer.
- For guest-result or activation pages, treat the whole reading order as the task; login CTA belongs last when the user says "游客测试结果，登录一定是最后最下面展示的内容".
- For workflow/tooling memory systems, default to scheduled, source-driven automation plus tool-readable adapters, not manual note placement.
- For cross-Mac Codex consistency, use only account-level settings (`Custom Instructions` and `Memory`) plus iCloud Drive shared state files unless explicitly asked for another sync path. [ad-hoc note]

## General Tips

- `phase2_workspace_diff.md` is the first routing file for Phase 2 consolidation; treat its adds/deletes as authoritative.
- Read every extension `instructions.md` before using extension content. Current `extensions/ad_hoc/instructions.md` requires consolidating all notes and tagging summary-derived content with `[ad-hoc note]`. [ad-hoc note]
- Cross-project debug order is `source mismatch -> build -> startup -> runtime env -> business logic`. [ad-hoc note]
- In iCloud-backed repos, early failures are often cache/build-metadata write problems or mixed build artifacts rather than app logic; check write targets and dev/prod artifact separation before assuming the code is broken.
- Current reusable workflow skills live in `skills/product-code-iteration-loop/SKILL.md`, `skills/strict-bugfix-review-loop/SKILL.md`, and `skills/truth-first-execution-checks/SKILL.md`.
- In current Ather memory, start with the runtime/security audit block for `.next-dev`, `Cannot find module './522.js'`, runtime sentinel, and hosting-only cost framing; start with the auth-routing block for `returnTo`, mock-only versus app-wide blast radius, and `/profile` growth limits.

## What's in Memory

### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather

#### 2026-06-16

- Guest assessment completion page reorder so login is last: assessment page, guest result flow, 游客测试结果，登录一定是最后最下面展示的内容, ResultPortraitPreview, 登录开启更多功能 →
  - desc: Search this first in `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather` when the task is about guest result-page hierarchy, conversion ordering, or whether login should appear near the top or only at the bottom.
  - learnings: the validated flow was result -> preview -> confirmation/reflection -> what login unlocks -> CTA last; treat this as a sequence redesign, not a text tweak.

#### 2026-06-15

- Ather runtime/security audit and hosting-only cost framing: 不需要计算LLM，只需要计算部署托管, .next-dev, Cannot find module './522.js', runtime-sentinel, DevController
  - desc: Search this first in `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather` when the task touches hosting-only estimates, Next.js dev/runtime failures, or whether sentinel/dev endpoints are intentional versus risky.
  - learnings: separate LLM from hosting cost, isolate `next dev` artifacts with `.next-dev`, prefer terminal verification over browser-only localhost checks, and keep the unfinished audit state explicit.

### /Users/ethan/.codex/memories

#### 2026-06-11

- Cross-project truth-first execution, deploy targeting, and cross-Mac Codex sync: truth-first, git remote -v, Railway, Settings, Variables, iCloud Drive, Custom Instructions [ad-hoc note]
  - desc: Search this first for planning/execution rules, deploy-target verification, Railway field-path answers, or Codex cross-Mac setup in `cwd=/Users/ethan/.codex/memories`. [ad-hoc note]
  - learnings: verify premise and target before acting, answer deploy work as `service/page/field=value/proof`, and keep Codex sync limited to account settings plus iCloud state files. [ad-hoc note]

### Older Memory Topics

#### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather

- Ather local auth-routing fix and quota-aware profile planning: returnTo, /chat, /login, baseline_completed, MOCK_DB, Upstash, Resend, /profile
  - desc: Use for `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Ather` when the task touches login-to-chat routing, local mock verification, blast radius reporting, quota-aware profile/chat growth, or `/profile` as the long-lived persona home.

#### /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem

- llm-workmem personal knowledge body, multi-tool harvest, and shell/web startup: llm-workmem, --profile personal, harvest, watch, adapters, install-global, Kiro, shell, 127.0.0.1:8765
  - desc: Use for `cwd=/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem` when the task is to build the user's central knowledge body, harvest tool memories, expose adapters back to tools, or explain shell vs web vs background roles.

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
