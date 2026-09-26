<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/GLOBAL.md` as the shared personal behavior contract for this tool.
Project memory, handoffs, Recall and review candidates are auxiliary evidence; native platform safety rules, instructions, skills, memory, planning, execution and verification remain authoritative.
Canonical personal behavior contract: `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/GLOBAL.md` (version=1 sha256=f73d3a026fa3a213b763698b09cc1e698baa5aaa4e086f52b329ec722b18a29e status=verified).
Use the startup context command above to refresh this hash before relying on it.

Read order:
0. **On session start**, run `printf '%s' "$PWD" | python3 -c 'import json,sys; print(json.dumps({'"'"'phase'"'"':'"'"'context'"'"','"'"'tool'"'"':"claude-code",'"'"'project_path'"'"':sys.stdin.read()}))' | lwm hub bridge --output markdown --root '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem'` to get the latest dynamic context (project memory, recent decisions, open questions). This is always fresher than the static files below.
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

Structured write-back for completed work:
- Record only bounded decisions, changes, verifications, risks, or open questions; do not paste a transcript or raw prompt.
- For cross-tool continuation, submit a bounded handoff with:
  `lwm hub bridge-stop --tool claude-code --project "$PWD" --task-id "$LWM_TASK_ID" --handoff-json '{"task_id":"...","objective":"...","current_state":"...","changes":["..."],"verifications":["..."],"risks":[],"open_questions":[],"next_action":"..."}' --root '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem'`
- A handoff is evidence for the next tool, not a replacement for native instructions, skills, planning, execution, or verification.
<!-- LLM-WIKI:END -->
