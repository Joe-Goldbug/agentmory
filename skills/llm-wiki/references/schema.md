# SCHEMA — Controlled Schema Validation

## When to Run

Use when the user asks to validate wiki page quality, frontmatter consistency, or page-type constraints.

## Command

Run:

`lwiki schema <wiki-root>`

## Output

- Lists missing frontmatter keys.
- Flags pages without YAML frontmatter.
- Flags unknown page types outside the controlled type set.
- Returns non-zero exit code when issues exist.
