<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use LLM-WorkMem as auxiliary shared evidence for this project. Native client
instructions, safety, skills, memory and verification remain authoritative.

Reuse context already injected by the current session hook or native project
instructions. Only if it is absent, run once:

`lwm hub context --tool <your-tool-name> --project "$PWD" "$HOME/Library/Application Support/llm-workmem-runtime/llm-workmem"`

If the command is unavailable, read `llms.txt`. Read `wiki/purpose.md` and
`wiki/overview.md` only when more context is needed. Treat `raw/` as evidence,
not polished memory.

After meaningful work, preserve observed changes, verification results and
unresolved risks in the native completion/handoff. Native lifecycle hooks
capture bounded results. If that host has no result hook, use `lwm hub
bridge-stop` with a unique task ID and structured handoff. Never equate a
request, configured adapter or transport receipt with accomplished work.
<!-- LLM-WIKI:END -->
