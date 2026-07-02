# WATCH — Source Drift Gate

## When to Run

Use when the wiki should check whether configured source folders changed and only refresh when there is real drift.

## Process

### 1. Check source fingerprints

Run `lwm watch <wiki-root>` to compare the configured tool-memory sources against the last saved watch state.

### 2. Refresh only when needed

If the source state changed, `lwm watch` runs the normal harvest refresh path, which snapshots sources, compiles summaries, updates analysis, and refreshes the dashboard.

### 3. Audit after refresh

The watch command finishes by running the unified audit gate so the current state is still checked for graph, schema, review, and optional eval health.
