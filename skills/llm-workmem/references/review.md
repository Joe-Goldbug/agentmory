# REVIEW — Deterministic Review Queue

## When to Run

Use when the user asks for unresolved quality items, contradictions, or a queue of fixes.

## Command

Run:

`lwm review <wiki-root> [--write]`

## What it includes

- Broken links
- Missing sources
- Orphan pages
- Duplicate slugs
- Schema issues

When `--write` is enabled, a dated queue page is created in `wiki/review/`.
