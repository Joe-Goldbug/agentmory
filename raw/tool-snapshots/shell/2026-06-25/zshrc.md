


# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/ethan/.lmstudio/bin"
# End of LM Studio CLI section

export PATH="/opt/homebrew/opt/node@18/bin:$PATH"


export PATH="$HOME/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"


# bun completions
[ -s "/Users/ethan/.bun/_bun" ] && source "/Users/ethan/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# 钉死 Claude Code 官方 CLI 路径 — 拦截任何 wrapper/launcher/IDE 注入
export CLAUDE_OFFICIAL_BIN="/Users/ethan/.local/bin/claude"
unalias claude 2>/dev/null
unalias claude-m3 2>/dev/null
claude() { "$CLAUDE_OFFICIAL_BIN" --bare "$@"; }
alias claude-m3="ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic ANTHROPIC_API_KEY=$MINIMAX_API_KEY $CLAUDE_OFFICIAL_BIN --model MiniMax-M3"

# 统一记忆体系统别名
[ -f "/Users/ethan/.unified_memory_aliases" ] && source "/Users/ethan/.unified_memory_aliases"
export CLAUDE_CONFIG_DIR="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config"

# === API Keys（仅 MiniMax，DeepSeek 已彻底移除）===
export MINIMAX_API_KEY="sk-cp-Vur2RO_jN2A2YmIfmYeqjERqa5W8ek014Hb_CK5doglhTSl6f9S5AxSmREfRfe5sURzJtniE5129yqvo8bPnZwMGco8pQH2W7GrDa2sowJ17MxdvAYEu5B8"

# 唯一 API 端点：MiniMax
export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export ANTHROPIC_API_KEY="$MINIMAX_API_KEY"
export ANTHROPIC_MODEL="MiniMax-M3"

# 启动 Claude Code（直接走 MiniMax 端点）

# 守卫：拦截任何尝试把 BASE_URL 切成 DeepSeek 的命令
_deepseek_guard() {
  if [[ "$ANTHROPIC_BASE_URL" == *"deepseek"* ]]; then
    echo "❌ DeepSeek 已禁用，强制恢复为 MiniMax"
    export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
    export ANTHROPIC_API_KEY="$MINIMAX_API_KEY"
  fi
}
precmd_functions+=(_deepseek_guard)


# LLM-WIKI:START
# LLM Wiki shell context
if [ -f '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/adapters/llm-wiki-shell-context.sh' ]; then
  source '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/adapters/llm-wiki-shell-context.sh'
fi
# LLM-WIKI:END
