# ANALYZE — Inspect Graph Health

Use `lwm analyze <wiki-root>` to inspect the wiki graph before or after larger changes.

## When to Run

- The user wants to understand how pages connect across projects, concepts, and decisions.
- You need a quick read on hubs, orphans, broken links, duplicate slugs, or missing raw sources.
- You want a deterministic preflight before a larger ingest, rewrite, or schema change.

## Process

1. Run `lwm analyze <wiki-root>` from outside or inside the wiki root.
2. Read the report and separate:
   - **Broken links** and **missing sources** as hard issues.
   - **Orphans** and **connected components** as structural signals.
   - **Hubs** as likely anchors for synthesis.
3. If the user asked for persistence, rerun with `--write` to save a snapshot into `wiki/insights/`.
4. Use the result to guide the next step:
   - Link missing pages.
   - Consolidate duplicate slugs.
   - Promote repeated themes into `pattern` or `principle` pages.

## Output

The command prints a markdown report with:

- Page counts
- Hubs
- Orphans
- Broken links
- Missing sources
- Duplicate slugs
- Connected components

