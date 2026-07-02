# HARVEST — Snapshot Tool Memory Sources

## When to Run

Use when the user wants the wiki to automatically read working memory or workflow sources from Codex, Claude Code, VSCode, or related tool folders and fold them into the wiki.

## Process

### 1. Refresh sources into raw/

Run `lwm harvest <wiki-root>` from the wiki root. This command snapshots configured tool-memory sources into `raw/tool-snapshots/`, updates the memory-governance page, writes a tool harvest insight, refreshes the knowledge radar, runs `lwm raw sync`, and refreshes the dashboard snapshot.
It also refreshes AI-consumable exports at the repo root (`llms.txt`, `llms-full.txt`, and `llms.json`).

### 2. Inspect missing source slots

Review the harvest output for missing source slots. Missing sources are not automatically fatal; they indicate the user has not provisioned one of the configured tool-memory roots yet.

### 3. Escalate only when needed

If the user wants a schedule, follow up with [references/schedule.md](schedule.md) so the harvest can run on macOS launchd.
