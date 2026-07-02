#!/bin/zsh
set -euo pipefail
# After migration (2026-06-30), the runtime symlinks point back at the repo.
# We cd into the repo so `lwm` finds its pyproject and `raw/` correctly.
cd '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem'
/usr/bin/python3 '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/automation/bin/run-harvest.py'
