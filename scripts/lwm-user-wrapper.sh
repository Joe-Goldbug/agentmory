#!/bin/sh
# Stable user-facing entrypoint for /Users/ethan/bin/lwm.
#
# The editable .venv script can fail to import the package when the repo lives
# under iCloud paths with spaces. This wrapper runs from the repo root so the
# source tree is always importable.

set -eu

ROOT="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
cd "$ROOT"
exec env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$ROOT/.venv/bin/python" -m lwm.cli "$@"
