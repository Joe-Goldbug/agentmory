# COMPILE — Raw to Summary Compilation

## When to Run

Use when the user wants deterministic conversion of `raw/` sources into wiki pages.

## Command

Run:

`lwm compile <wiki-root>`

## Behavior

- Scans `raw/` tracked files (except `tool-snapshots/`).
- Creates or updates `wiki/summaries/source-*.md`.
- Stores `source_sha256` in frontmatter for change detection.
- Updates `wiki/index.md` and appends to `wiki/log.md`.
