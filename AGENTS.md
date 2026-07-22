<!-- LLM-WIKI:START -->
# LLM-WorkMem Context

Use this repository as the shared workflow and memory source for this project.

On session start, run:

`lwm hub context --tool <your-tool-name> --project "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem" "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"`

If the command is unavailable, read `llms.txt`. Read `wiki/purpose.md` and
`wiki/overview.md` only when more context is needed. Treat `raw/` as evidence,
not polished memory.

After meaningful work, write back a sanitized event with `lwm hub record` so
other IDE and shell agents can reuse the result.
<!-- LLM-WIKI:END -->
