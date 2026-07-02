<!-- mavis:builtin-agent-md-stub v2 -->
<!--
This file is the user overlay for the built-in agent's system prompt.

Anything you write below the marker line is APPENDED to the agent's
built-in system prompt at runtime. Use it for project-specific tweaks,
personal preferences, or extra instructions — keep it short.

The base system prompt itself ships inside the Mavis package and is
not editable from this file. PERSONA.md for built-in agents is also
read from the package and ignored here.

Delete the marker line above (or replace it with your own content) to
start customising. As long as the marker is present and no other
meaningful content follows, this file is treated as empty.
-->

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
