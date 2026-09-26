#!/usr/bin/env bash
# Materialize the LWM-WorkMem runtime as a self-contained install.
#
# Spec: docs/superpowers/specs/2026-07-31-llm-workmem-unified-behavior-memory-interface.md
#       -> Implementation Changes / 8. Runtime and data ownership
#
# Builds a wheel from the current source, installs it *non-editable* into
# ``$RUNTIME_BASE/app/venv/`` so the installed ``lwm`` module never imports
# code from the iCloud checkout. Then writes a manifest with the source
# revision and per-file SHA-256 hashes for migration rollback.

set -euo pipefail

# launchd and IDE hosts do not guarantee an interactive shell PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [[ "$SCRIPT_DIR" == "$SCRIPT_PATH" ]]; then
  SCRIPT_DIR="."
fi
SCRIPT_DIR="$(cd "$SCRIPT_DIR" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_BASE="${RUNTIME_BASE:-$HOME/Library/Application Support/llm-workmem-runtime}"
APP_DIR="$RUNTIME_BASE/app"
VENV_DIR="$APP_DIR/venv"
STAGING_DIR="$APP_DIR/.staging"
WHEEL_DIR="$APP_DIR/.wheels"
RUNTIME_ID_FILE="$RUNTIME_BASE/runtime-id"
MANIFEST="$APP_DIR/runtime-manifest.json"
BACKUP_DIR="$APP_DIR/backups"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"

echo "== Materialize LWM-WorkMem runtime =="
echo "Source : $ROOT_DIR"
echo "Runtime: $RUNTIME_BASE"
echo "Python : $PYTHON_BIN"
echo

if [[ ! -d "$ROOT_DIR" ]] || [[ ! -f "$ROOT_DIR/pyproject.toml" ]]; then
  echo "ERROR: source root must contain pyproject.toml: $ROOT_DIR" >&2
  exit 2
fi

# 1. Build a wheel from the source tree, or consume an already audited local
# wheel when the build environment is intentionally offline.
WHEEL_FILE="${LWM_WHEEL_FILE:-}"
if [[ -n "$WHEEL_FILE" ]]; then
  if [[ ! -f "$WHEEL_FILE" ]]; then
    echo "ERROR: LWM_WHEEL_FILE does not exist: $WHEEL_FILE" >&2
    exit 2
  fi
  AUDITED_WHEEL="$WHEEL_FILE"
  WHEEL_NAME="$(basename "$AUDITED_WHEEL")"
  WHEEL_TARGET="$WHEEL_DIR/$WHEEL_NAME"
  mkdir -p "$WHEEL_DIR"
  AUDITED_WHEEL_ABS="$(cd "$(dirname "$AUDITED_WHEEL")" && pwd)/$WHEEL_NAME"
  if [[ "$AUDITED_WHEEL_ABS" != "$WHEEL_TARGET" ]]; then
    cp "$AUDITED_WHEEL_ABS" "$WHEEL_TARGET"
  fi
  WHEEL_FILE="$WHEEL_TARGET"
  echo ">> using audited wheel: $AUDITED_WHEEL"
  echo ">> archived wheel: $WHEEL_FILE"
else
  rm -rf "$WHEEL_DIR"
  mkdir -p "$WHEEL_DIR"
  echo ">> building wheel"
  if command -v uv >/dev/null 2>&1; then
    ( cd "$ROOT_DIR" && uv build --wheel --out-dir "$WHEEL_DIR" >/dev/null )
  else
    ( cd "$ROOT_DIR" && "$PYTHON_BIN" -m pip wheel --no-deps --no-build-isolation -w "$WHEEL_DIR" . >/dev/null )
  fi
  WHEEL_FILE="$(ls -1 "$WHEEL_DIR"/*.whl | head -n1)"
fi
if [[ -z "$WHEEL_FILE" ]]; then
  echo "ERROR: wheel build produced no output" >&2
  exit 3
fi

# 2. Stage a fresh venv and install the wheel non-editable.
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
echo ">> creating fresh venv"
"$PYTHON_BIN" -m venv "$STAGING_DIR/venv"
echo ">> installing wheel and declared dependencies"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$STAGING_DIR/venv/bin/python" "$WHEEL_FILE"
else
  "$STAGING_DIR/venv/bin/python" -m pip install --quiet "$WHEEL_FILE"
fi

# 3. Sanity check: import must not bring iCloud on sys.path.
echo ">> import probe"
PROBE_JSON="$("$STAGING_DIR/venv/bin/python" -I -c '
import json, lwm, sys
print(json.dumps({
    "module": lwm.__file__,
    "icloud_on_path": [p for p in sys.path if "Mobile Documents" in p],
}))
')"
if echo "$PROBE_JSON" | grep -q "Mobile Documents"; then
  echo "ERROR: runtime still imports iCloud: $PROBE_JSON" >&2
  exit 4
fi
echo "$PROBE_JSON" | sed 's/^/   /'

# 4. Atomic swap into the real app/ directory.
mkdir -p "$RUNTIME_BASE"
if [[ -d "$APP_DIR/venv" ]]; then
  mkdir -p "$BACKUP_DIR"
mv "$APP_DIR/venv" "$BACKUP_DIR/venv-$(date -u +%Y%m%dT%H%M%SZ)"
fi
mv "$STAGING_DIR/venv" "$APP_DIR/venv"
rm -rf "$STAGING_DIR"

# Console scripts generated inside the staging directory keep its absolute
# shebang. Reinstall the already-built local wheel from the final venv so
# ``bin/lwm`` points at the runtime path that will actually be retained.
echo ">> rebinding console scripts to final venv"
"$APP_DIR/venv/bin/python" -m pip install --quiet --no-deps --force-reinstall "$WHEEL_FILE"

# The pre-swap probe proves the staged environment; this probe proves the
# retained environment and is the one recorded in the runtime manifest.
echo ">> final import probe"
PROBE_JSON="$("$APP_DIR/venv/bin/python" -I -c '
import json, lwm, sys
print(json.dumps({
    "module": lwm.__file__,
    "icloud_on_path": [p for p in sys.path if "Mobile Documents" in p],
}))
')"
if echo "$PROBE_JSON" | grep -q "Mobile Documents"; then
  echo "ERROR: final runtime still imports iCloud: $PROBE_JSON" >&2
  exit 5
fi

# 5. Compute SHA-256 manifest and source revision.
SOURCE_REV="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
SOURCE_DIRTY="$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null | shasum -a 256 | awk '{print $1}' || echo unknown)"
RUNTIME_ID="runtime-$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%s' "$SOURCE_REV" | head -c 8)"

# 6. Capture per-file SHA-256 for the canonical code set.
MANIFEST_HASHES="$(cd "$ROOT_DIR" && {
  find lwm adapters -type f -name '*.py' -print0 2>/dev/null
  find mcp -type f -name '*.py' -print0 2>/dev/null
  find lwm adapters -type f -name '*.toml' -print0 2>/dev/null
  find lwm adapters -type f -name '*.json' -print0 2>/dev/null
} | sort -z | xargs -0 shasum -a 256 | awk '{print $1"  "$2}')"

printf '%s\n' "$MANIFEST_HASHES" | "$PYTHON_BIN" "$ROOT_DIR/scripts/write-runtime-manifest.py" \
  --output "$MANIFEST" \
  --runtime-id "$RUNTIME_ID" \
  --source-revision "$SOURCE_REV" \
  --source-dirty-hash "$SOURCE_DIRTY" \
  --source-root "$ROOT_DIR" \
  --runtime-root "$APP_DIR" \
  --python "$(command -v "$PYTHON_BIN" || echo unknown)" \
  --wheel "$(basename "$WHEEL_FILE")" \
  --import-probe "$PROBE_JSON"

echo "$RUNTIME_ID" > "$RUNTIME_ID_FILE"
echo
echo "OK: runtime_id=$RUNTIME_ID"
echo "OK: manifest=$MANIFEST"
echo "OK: rollback_versions=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name 'venv-*' 2>/dev/null | wc -l | tr -d ' ')"
echo "OK: lwm=$(echo "$PROBE_JSON" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["module"])')"

# Keep the historical dream LaunchAgent rollback-safe but unable to create a
# second writer if an old plist is ever loaded again. This changes only the
# local runtime script; it does not load, unload, or edit launchd plists.
if [[ "${LWM_RETIRE_LEGACY_DREAM_WRITER:-1}" == "1" ]]; then
  "$ROOT_DIR/scripts/retire-legacy-dream-writer.sh" "$RUNTIME_BASE"
fi
