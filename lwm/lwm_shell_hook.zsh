#!/usr/bin/env zsh
# lwm shell history hook — auto-installed by `lwm install-shell-hook`.
#
# Behaviour:
# - On every interactive command, append a single JSONL line to
#   $LWM_ROOT/raw/shell/<YYYY-MM-DD>.jsonl
# - The line carries: ts (epoch seconds), iso, pwd, duration_ms, exit_code,
#   session_id, command (truncated to 1 KiB).
# - Skips lines that match the sensitive-keyword filter or the trivial-command
#   filter — both are intentionally narrow to keep recall high.
# - Respects the opt-out env var LWM_SHELL_HOOK=0 (legacy LBM_SHELL_HOOK is
#   also accepted).
#
# This file is sourced at the end of ~/.zshrc inside an LBM-WIKI:SHELL-HOOK
# marker block. Re-running `lwm install-shell-hook` is idempotent.
# To uninstall: `lwm uninstall-shell-hook` (or delete the marker block).

# Only act in interactive shells.
[[ -o interactive ]] || return 0 2>/dev/null

# Opt-out. Must be checked on every call because the user can flip it per
# session without re-sourcing the hook.
_lbm_shell_hook_disabled() {
  [[ "${LWM_ANALYSIS_JOB:-0}" == "1" || "${LWM_SHELL_HOOK:-${LBM_SHELL_HOOK:-1}}" == "0" ]]
}

# Explicit launch wrapper. Context is an actual initial agent input, never
# a discarded preexec return or an override of native instructions/settings.
# Usage: lwm-agent codex|claude|opencode|agy "initial request" [native options]
lwm-agent() {
  local host="$1" request="$2"
  (( $# >= 2 )) || { print -u2 'usage: lwm-agent <host> <request> [native options]'; return 2; }
  shift 2
  case "$host" in codex|claude|opencode|agy) ;; *) return 2 ;; esac
  if _lbm_shell_hook_disabled; then
    case "$host" in
      codex|claude) command "$host" "$@" "$request" ;;
      opencode) command opencode "$@" --prompt "$request" ;;
      agy) command agy "$@" --prompt-interactive "$request" ;;
    esac
    return $?
  fi
  local root="$(_lbm_shell_hook_root)" context input
  context=$(LWM_LAUNCH_PROJECT="$PWD" LWM_LAUNCH_HOST="$host" python3 -c '
import json,os
print(json.dumps({"phase":"context","tool":{"agy":"antigravity","claude":"claude-code"}.get(os.environ["LWM_LAUNCH_HOST"],os.environ["LWM_LAUNCH_HOST"]),"project_path":os.environ["LWM_LAUNCH_PROJECT"]}))' |
    "${LWM_BIN:-lwm}" hub bridge --root "$root" --output markdown 2>/dev/null) || context=""
  input="$request"
  if [[ -n "$context" ]]; then
    input=$'Shared LLM-WorkMem evidence only. Native safety, instructions, skills and verification remain authoritative.\n'"$context"$'\n\nUser request:\n'"$request"
  fi
  case "$host" in
    codex|claude) command "$host" "$@" "$input" ;;
    opencode) command opencode "$@" --prompt "$input" ;;
    agy) command agy "$@" --prompt-interactive "$input" ;;
  esac
}

# Resolve the wiki root once per session, fall back to the canonical location.
_lbm_shell_hook_root() {
  local root="${LWM_ROOT:-$HOME/Library/Application Support/llm-workmem-runtime/llm-workmem}"
  if [[ ! -d "$root" ]]; then
    # Best-effort discovery: walk up to find a wiki marker.
    local dir="$PWD"
    while [[ "$dir" != "/" ]]; do
      if [[ -f "$dir/wiki/index.md" && -f "$dir/wiki/log.md" ]]; then
        root="$dir"
        break
      fi
      dir="${dir:h}"
    done
  fi
  print -r -- "$root"
}

# Emit only host lifecycle metadata. Command text remains in the separate,
# filtered shell-history observer below and is never passed to this bridge.
_lbm_shell_hook_lifecycle() {
  local phase="$1"
  local host_event="$2"
  _lbm_shell_hook_disabled && return 0

  local root
  root="$(_lbm_shell_hook_root)"
  [[ -z "$root" ]] && return 0

  local lwm_bin="${LWM_BIN:-lwm}"
  if [[ "$lwm_bin" == */* ]]; then
    [[ -x "$lwm_bin" ]] || return 0
  else
    command -v "$lwm_bin" >/dev/null 2>&1 || return 0
  fi
  command -v python3 >/dev/null 2>&1 || return 0

  local session_id="${LBM_SHELL_SESSION:-shell-$$}"
  LWM_HOST_BRIDGE=1 \
  LBM_BRIDGE_PHASE="$phase" \
  LBM_BRIDGE_EVENT="$host_event" \
  LBM_BRIDGE_ROOT="$root" \
  LBM_BRIDGE_PROJECT="$PWD" \
  LBM_BRIDGE_SESSION="$session_id" \
    python3 -c 'import json,os; print(json.dumps({
      "phase": os.environ["LBM_BRIDGE_PHASE"],
      "tool": "shell",
      "project_path": os.environ["LBM_BRIDGE_PROJECT"],
      "session_id": os.environ["LBM_BRIDGE_SESSION"],
      "source": "native-hook",
      "host_proof": {
        "integration": "shell-hook",
        "event": os.environ["LBM_BRIDGE_EVENT"],
        "session_id": os.environ["LBM_BRIDGE_SESSION"]
      }
    }, ensure_ascii=False))' \
    | LWM_HOST_BRIDGE=1 "$lwm_bin" hub bridge --root "$root" >/dev/null 2>&1 || true
}

_lbm_shell_hook_session_exit() {
  [[ "${LBM_SHELL_LIFECYCLE_STARTED:-0}" == "1" ]] || return 0
  LBM_SHELL_LIFECYCLE_STARTED=0
  _lbm_shell_hook_lifecycle stop shell_session_end
}

# Sensitive command filter — if any token matches, drop the whole line.
# These patterns cover the most common credential-leak vectors without
# being so aggressive that they nuke useful audit context.
_lbm_shell_hook_sensitive() {
  local cmd="$1"
  local secret_option='(^|[[:space:]])--?(token|password|passwd|secret|apikey|api[-_]?key|access[-_]?key)='
  local secret_env='(^|[[:space:]])(AWS_SECRET|GITHUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|HUGGINGFACE_TOKEN)[[:space:]]*='
  local secret_post='(^|[[:space:]])curl[[:space:]]+.*-[[:space:]]*X[[:space:]]+POST.*-d[[:space:]]+.*(token|password|secret)'
  local ssh_remote='(^|[[:space:]])ssh[[:space:]]+.*@'
  local gpg_secret='(^|[[:space:]])gpg[[:space:]]+(--(decrypt|import|export-secret-keys)|--passphrase)'
  # Word-boundary match against common secrets
  if [[ "$cmd" =~ "$secret_option" ]]; then
    return 0
  fi
  if [[ "$cmd" =~ "$secret_env" ]]; then
    return 0
  fi
  if [[ "$cmd" =~ "$secret_post" ]]; then
    return 0
  fi
  if [[ "$cmd" =~ "$ssh_remote" ]]; then
    return 0
  fi
  if [[ "$cmd" =~ "$gpg_secret" ]]; then
    return 0
  fi
  return 1
}

# Trivial command filter — if the command is a single token from this list,
# skip. Multi-token commands (e.g. `ls -la`, `cd ~/code`) still go through.
_lbm_shell_hook_trivial() {
  local first="${1%% *}"
  case "$first" in
    ls|cd|pwd|exit|clear|history)
      return 0 ;;
  esac
  return 1
}

_lbm_shell_hook_preexec() {
  # $1 contains the command about to run. zsh's preexec passes it positionally.
  LBM_LAST_CMD="$1"
  LBM_LAST_START_MS="${EPOCHREALTIME:-$(date +%s)}"
}

_lbm_shell_hook_precmd() {
  # zsh exposes the previous command's status through `$?` at precmd entry.
  # Capture it before any guard, test, or command substitution changes it.
  local exit_code="$?"
  _lbm_shell_hook_disabled && return 0
  [[ -z "${LBM_LAST_CMD:-}" ]] && return 0

  local cmd="$LBM_LAST_CMD"
  LBM_LAST_CMD=""

  # Filters
  _lbm_shell_hook_trivial "$cmd" && return 0
  _lbm_shell_hook_sensitive "$cmd" && {
    LBM_LAST_CMD_FILTERED="sensitive"
    return 0
  }

  local root
  root="$(_lbm_shell_hook_root)"
  [[ -z "$root" ]] && return 0

  local raw_dir="$root/raw/shell"
  if [[ ! -d "$raw_dir" ]]; then
    command mkdir -p "$raw_dir" 2>/dev/null || return 0
  fi

  local date_part
  date_part="${LBM_TODAY:-$(date +%Y-%m-%d)}"
  local file="$raw_dir/${date_part}.jsonl"

  local now_ms="${EPOCHREALTIME:-$(date +%s)}"
  local duration_ms
  if [[ -n "${LBM_LAST_START_MS:-}" ]]; then
    # $EPOCHREALTIME is a float string with a decimal; arithmetic handles it.
    duration_ms=$(awk -v s="$LBM_LAST_START_MS" -v e="$now_ms" 'BEGIN{printf "%d", (e-s)*1000}')
  else
    duration_ms="0"
  fi
  LBM_LAST_START_MS=""

  local ts iso pwd pwd_escaped session_id session_escaped cmd_escaped
  ts=$(date +%s)
  iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  pwd=$(print -Pn '%~')
  session_id="${LBM_SHELL_SESSION:-$$}"
  # Escape every string field for JSON. We are conservative: strip control
  # chars, backslash-escape the JSON-mandatory ones, and cap commands at 1 KiB.
  pwd_escaped="${pwd//\\/\\\\}"
  pwd_escaped="${pwd_escaped//\"/\\\"}"
  pwd_escaped="${pwd_escaped//	/ }"
  pwd_escaped=$(print -r -- "$pwd_escaped" | tr -d '\000-\010\013-\037')
  session_escaped="${session_id//\\/\\\\}"
  session_escaped="${session_escaped//\"/\\\"}"
  session_escaped="${session_escaped//	/ }"
  session_escaped=$(print -r -- "$session_escaped" | tr -d '\000-\010\013-\037')
  cmd_escaped="${cmd:0:1024}"
  cmd_escaped="${cmd_escaped//\\/\\\\}"
  cmd_escaped="${cmd_escaped//\"/\\\"}"
  cmd_escaped="${cmd_escaped//	/ }"
  # Remove carriage returns and other control bytes (0x00-0x1F except 0x09 tab handled above).
  cmd_escaped=$(print -r -- "$cmd_escaped" | tr -d '\000-\010\013-\037')

  local line
  line=$(printf '{"ts":%s,"iso":"%s","pwd":"%s","duration_ms":%s,"exit_code":%s,"session":"%s","command":"%s"}' \
    "$ts" "$iso" "$pwd_escaped" "$duration_ms" "$exit_code" "$session_escaped" "$cmd_escaped")

  # Append, best-effort. Use a per-date lock to avoid two preexec racing.
  local lock="$raw_dir/.${date_part}.lock"
  if command mkdir "$lock" 2>/dev/null; then
    print -r -- "$line" >> "$file" 2>/dev/null
    command rmdir "$lock" 2>/dev/null
  fi
}

# Register the hooks. add-zsh-hook is a no-op for re-registration of the same
# function name, so this is safe to re-source.
autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec _lbm_shell_hook_preexec 2>/dev/null
add-zsh-hook precmd  _lbm_shell_hook_precmd  2>/dev/null
add-zsh-hook zshexit _lbm_shell_hook_session_exit 2>/dev/null

# Source-time is the native shell session start. Keep the guard unexported so
# a child shell gets its own lifecycle proof instead of inheriting the parent.
if [[ "${LBM_SHELL_LIFECYCLE_STARTED:-0}" != "1" ]] && ! _lbm_shell_hook_disabled; then
  LBM_SHELL_LIFECYCLE_STARTED=1
  _lbm_shell_hook_lifecycle start shell_session_start
fi
