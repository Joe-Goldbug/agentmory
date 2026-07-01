#!/usr/bin/env zsh
# lwiki shell history hook — auto-installed by `lwiki install-shell-hook`.
#
# Behaviour:
# - On every interactive command, append a single JSONL line to
#   $LLM_WIKI_ROOT/raw/shell/<YYYY-MM-DD>.jsonl
# - The line carries: ts (epoch seconds), iso, pwd, duration_ms, exit_code,
#   session_id, command (truncated to 1 KiB).
# - Skips lines that match the sensitive-keyword filter or the trivial-command
#   filter — both are intentionally narrow to keep recall high.
# - Respects the opt-out env var LBM_SHELL_HOOK=0.
#
# This file is sourced at the end of ~/.zshrc inside an LBM-WIKI:SHELL-HOOK
# marker block. Re-running `lwiki install-shell-hook` is idempotent.
# To uninstall: `lwiki uninstall-shell-hook` (or delete the marker block).

# Only act in interactive shells.
[[ -o interactive ]] || return 0 2>/dev/null

# Opt-out. Must be checked on every call because the user can flip it per
# session without re-sourcing the hook.
_lbm_shell_hook_disabled() {
  [[ "${LBM_SHELL_HOOK:-1}" == "0" ]]
}

# Resolve the wiki root once per session, fall back to the canonical location.
_lbm_shell_hook_root() {
  local root="${LLM_WIKI_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/llm-wiki}"
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

# Sensitive command filter — if any token matches, drop the whole line.
# These patterns cover the most common credential-leak vectors without
# being so aggressive that they nuke useful audit context.
_lbm_shell_hook_sensitive() {
  local cmd="$1"
  # Word-boundary match against common secrets
  if [[ "$cmd" =~ (^|[[:space:]])(\-\-?(token|password|passwd|secret|apikey|api[-_]?key|access[-_]?key)= ]] then
    return 0
  fi
  if [[ "$cmd" =~ (^|[[:space:]])(AWS_SECRET|GITHUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|HUGGINGFACE_TOKEN)[[:space:]]*= ]] then
    return 0
  fi
  if [[ "$cmd" =~ (^|[[:space:]])(curl[[:space:]]+.*-[[:space:]]*X[[:space:]]+POST.*-d[[:space:]]+.*(token|password|secret)) ]] then
    return 0
  fi
  if [[ "$cmd" =~ (^|[[:space:]])ssh[[:space:]]+.*@ ]] then
    return 0
  fi
  if [[ "$cmd" =~ (^|[[:space:]])gpg[[:space:]]+(--(decrypt|import|export-secret-keys)|--passphrase) ]] then
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
  local exit_code="$?"
  LBM_LAST_START_MS=""

  local ts iso pwd session_id cmd_escaped
  ts=$(date +%s)
  iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  pwd=$(print -Pn '%~')
  session_id="${LBM_SHELL_SESSION:-$$}"
  # Truncate + escape for JSON. We are conservative: strip control chars,
  # backslash-escape the JSON-mandatory ones, and cap at 1024 chars.
  cmd_escaped="${cmd:0:1024}"
  cmd_escaped="${cmd_escaped//\\/\\\\}"
  cmd_escaped="${cmd_escaped//\"/\\\"}"
  cmd_escaped="${cmd_escaped//	/ }"
  # Remove carriage returns and other control bytes (0x00-0x1F except 0x09 tab handled above).
  cmd_escaped=$(print -r -- "$cmd_escaped" | tr -d '\000-\010\013-\037')

  local line
  line=$(printf '{"ts":%s,"iso":"%s","pwd":"%s","duration_ms":%s,"exit_code":%s,"session":"%s","command":"%s"}' \
    "$ts" "$iso" "$pwd" "$duration_ms" "$exit_code" "$session_id" "$cmd_escaped")

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
