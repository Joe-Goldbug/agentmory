#!/usr/bin/env bash
# Retire the historical dream writer without deleting its rollback copy.
#
# The old script was an independent ingest/health/insights/promotion writer.
# Keep the old bytes in a runtime backup, then replace the executable with a
# fail-closed stub so an old LaunchAgent cannot silently create a second writer.

set -euo pipefail

RUNTIME_BASE="${1:-${RUNTIME_BASE:-$HOME/Library/Application Support/llm-workmem-runtime}}"
DREAM_PATH="$RUNTIME_BASE/bin/lwm-dream.sh"
BACKUP_DIR="$RUNTIME_BASE/backups/legacy-writers"
RETIRE_MARKER="LLM-WORKMEM-RETIRED-DREAM-WRITER"

mkdir -p "$BACKUP_DIR" "$(dirname "$DREAM_PATH")"

if [[ -f "$DREAM_PATH" ]] && grep -q "$RETIRE_MARKER" "$DREAM_PATH"; then
  printf '%s\n' "legacy dream writer already retired: $DREAM_PATH"
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_PATH="$BACKUP_DIR/lwm-dream.sh.$STAMP.bak"
if [[ -f "$DREAM_PATH" ]]; then
  cp -p "$DREAM_PATH" "$BACKUP_PATH"
  printf '%s\n' "backup: $BACKUP_PATH"
fi

TEMP_PATH="$DREAM_PATH.tmp.$$"
trap 'rm -f "$TEMP_PATH"' EXIT
cat > "$TEMP_PATH" <<'EOF'
#!/bin/sh
# LLM-WORKMEM-RETIRED-DREAM-WRITER
#
# This compatibility entrypoint is intentionally fail-closed. The single
# authoritative writer is the installed `lwm hub run-supervisor` schedule.

set -eu
printf '%s\n' "lwm-dream.sh is retired; use the single lwm hub run-supervisor writer" >&2
exit 2
EOF
chmod 0755 "$TEMP_PATH"
mv "$TEMP_PATH" "$DREAM_PATH"
trap - EXIT
printf '%s\n' "retired: $DREAM_PATH"
