<!-- LLM-WIKI:START -->
# LLM Wiki Context

Use this llm-wiki as the shared workflow and memory source for this tool.

Read order:
1. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms.txt` for compact context.
2. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/wiki/purpose.md` for scope and guardrails.
3. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/wiki/overview.md` for the current synthesis.
4. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms-full.txt` only when deeper context is needed.
5. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms.json` for programmatic page metadata.

Rules:
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwiki harvest`, `lwiki watch`, or `lwiki audit` can consume.
<!-- LLM-WIKI:END -->
