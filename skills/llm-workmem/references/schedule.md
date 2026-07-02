# SCHEDULE — Generate a Harvest Schedule Bundle

## When to Run

Use when the user wants `llm-workmem` to run on a schedule and keep its working memory in sync automatically.

## Process

### 1. Generate the bundle

Run `lwm schedule <wiki-root>` to write a launchd script under `automation/bin/` and a plist under `automation/launchd/`.

The generated job runs at load and every 12 hours after that. It performs a source-drift watch first, then audits the current wiki state. If the machine sleeps or is powered off, launchd resumes on the next load/wake cycle and the next eligible interval.

### 2. Hand off activation

The command only generates files. If the user wants the schedule loaded into macOS launchd immediately, provide the exact `launchctl` command separately.
