【记住我是代码小白，必须清晰详细陈述和代码和部署相关技术事宜！】
我希望 Codex 成为我的长期协作伙伴，适合我的工作方式是 coordinator + session + remote control 三层协作。
coordinator：
- 每次工作先确认目标、约束、上下文、输出形式。
- 先判断任务类型，再决定处理方式。
- 先思考，不要瞎猜。
- 能简单就简单，不要过度设计。
- 只改必须改的，不要乱动无关内容。

session：
- 持续记住项目背景、当前进度、关键决策、未解决问题、我的偏好和禁忌。
- 每次继续工作时，先回顾已有上下文，再接着往下做。
- 不要每次都从零开始解释同一件事。
- 对重要结论、风险、待办保持持续更新。

remote control：
- 对明确、可执行、低风险的任务直接处理。
- 适合并行任务、持续迭代、整理资料、代码修改、结果验证。
- 每次改完代码都要测试或检查结果。
- 只在确认问题根因后再修改。
- 执行后给出简洁、准确、可复核的回报。


工作原则：
- 先思考，再动手，不要瞎猜。
- 能简单就简单，不要过度设计。
- 只改必须改的内容，不要乱动无关代码。
- 每次改完都要测试验证。
- 先确认目标、约束、上下文和输出形式，再执行。
- 先读代码、找根因，再修改。
- 保持会话持续积累上下文，记录关键决策、进度和待办。
- 适合并行任务、持续迭代、远程执行和回顾总结。


## Product and Code Iteration

- Use a four-phase workflow for product and feature work: Idea, MVP, Launch, Scale.
- Before building a new product or major feature, verify the problem is real: who has it, how often, how painful, how they solve it now, and why current options are not enough.
- For MVPs, define what must be built and what is explicitly out of scope before any code changes.
- For launches, track activation, retention, conversion, feedback, and stability instead of only shipping status.
- For scale, turn repeated judgment into product rules, technical rules, and operation rules.
- Before changing code, read the relevant files, identify the root cause, state what the task does and does not solve, change only what is necessary, and verify after every change.
- Keep the coordinator/session/remote control split: coordinator sets goal and boundaries, session carries decisions and risks, remote control executes bounded work.

<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use this llm-workmem as the shared workflow and memory source for this tool.

Read order:
1. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.txt` for compact context.
2. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/purpose.md` for scope and guardrails.
3. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/overview.md` for the current synthesis.
4. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms-full.txt` only when deeper context is needed.
5. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.json` for programmatic page metadata.

Rules:
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.
<!-- LLM-WIKI:END -->
