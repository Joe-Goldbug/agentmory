# AUDIT — Unified Quality Gate

## When to Run

Use when the user wants a single pass/fail gate before trusting the wiki state.

## Command

Run:

`lwm audit <wiki-root> [--eval-suite wiki/eval-suite.txt --eval-mode thesis]`

## What it checks

- Analyze errors (broken links, duplicate slugs, missing sources)
- Schema issues (frontmatter/type constraints)
- Review queue items (unresolved quality items)
- Optional eval pass ratio

Exit code is non-zero when any gate fails.
