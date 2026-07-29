<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use this llm-workmem as an auxiliary evidence source for this tool.
Native instructions, skills, memory, planning, execution, and verification remain authoritative.

Read order:
0. **On session start**, run `lwm hub context --tool <your-tool-name> /Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem` to get the latest dynamic context (project memory, recent decisions, open questions). This is always fresher than the static files below.
1. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.txt` for compact context (fallback if step 0 is unavailable).
2. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/purpose.md` for scope and guardrails.
3. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/wiki/overview.md` for the current synthesis.
4. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms-full.txt` only when deeper context is needed.
5. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/llms.json` for programmatic page metadata.

Write-back:
- After meaningful work, emit events via `lwm hub record` so the hub stays current.
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwm harvest`, `lwm watch`, or `lwm audit` can consume.
<!-- LLM-WIKI:END -->
