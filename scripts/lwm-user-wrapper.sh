#!/bin/sh
# Stable user-facing entrypoint for a user's local `lwm` command.
#
# The editable .venv script can fail to import the package when the repo lives
# under iCloud paths with spaces. This wrapper runs from the repo root so the
# source tree is always importable.

set -eu

ROOT="${LWM_ROOT:-$HOME/Library/Application Support/llm-workmem-runtime/llm-workmem}"
PYTHON_BIN="${LWM_PYTHON:-$HOME/Library/Application Support/llm-workmem-runtime/app/venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  printf '%s\n' "lwm runtime is not installed: $PYTHON_BIN" >&2
  exit 2
fi
exec env LWM_ROOT="$ROOT" "$PYTHON_BIN" -I -m lwm.cli "$@"
