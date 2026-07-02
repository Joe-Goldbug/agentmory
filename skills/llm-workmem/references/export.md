# EXPORT — AI-Consumable Wiki Exports

## When to Run

Use when another agent or local tool needs a portable view of the wiki without reading the whole tree page by page.

## Process

### 1. Write exports

Run `lwm export <wiki-root>` to write three repo-root artifacts:

- `llms.txt`
- `llms-full.txt`
- `llms.json`

### 2. Use cases

- `llms.txt` gives a compact index and purpose-oriented summary.
- `llms-full.txt` concatenates the full wiki pages in a stable, agent-friendly form.
- `llms.json` exposes structured page metadata for tooling and downstream agents.
