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

## Direct pointers (high-signal concepts to consult on demand)

- When designing, auditing, or reasoning about an LLM system prompt — read `[[portable-llm-system-prompt]]` (cross-IDE design patterns, distilled from the 2026-07-01 Claude Fable 5 leak).
- When in doubt about the global rules — read `[[tooling-policy]]`, `[[memory-policy]]`, `[[architecture-policy]]`.
<!-- LLM-WIKI:END -->
