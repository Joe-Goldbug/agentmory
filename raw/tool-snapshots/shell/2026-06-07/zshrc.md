
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

# 统一记忆体系统别名
[ -f "/Users/ethan/.unified_memory_aliases" ] && source "/Users/ethan/.unified_memory_aliases"
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_API_KEY=sk-ac9da5a220e745ddb8e29f6ec0868a42
export ANTHROPIC_MODEL=deepseek-v4-flash
export CLAUDE_CONFIG_DIR="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config"
alias claude="/Users/ethan/.local/bin/claude --model deepseek-v4-flash --agent pragmatic"
alias claude-pro="/Users/ethan/.local/bin/claude --model deepseek-v4-pro"
alias claude-flash="/Users/ethan/.local/bin/claude --model deepseek-v4-flash"
alias claude-fast="/Users/ethan/.local/bin/claude --model deepseek-v4-flash --agent pragmatic"

claude-use() {
  local model="$1"
  case "$model" in
    flash|pro)
      eval "alias claude=\"/Users/ethan/.local/bin/claude --model deepseek-v4-$model\""
      echo "✅ 已切换到 deepseek-v4-$model，直接 claude 启动即可"
      ;;
    *)
      echo "可用模型: flash, pro"
      echo "示例: claude-use flash"
      ;;
  esac
}

# ---------- 底部状态栏：当前 Claude 模型 ----------
_claude_prompt_model() {
  local alias_cmd=$(alias claude 2>/dev/null)
  case "$alias_cmd" in
    *deepseek-v4-pro*)    echo "%F{cyan}🧠 Pro%f" ;;
    *deepseek-v4-flash*)  echo "%F{green}⚡ Flash%f" ;;
    *)                    echo "%F{red}❌ 未配置%f" ;;
  esac
}

precmd() {
  RPROMPT='$(_claude_prompt_model)'
}

export OPENAI_API_KEY="sk-cp-jclNwARwXON--NvNdhN8wznnOP-qVnawFdqFwsdzk9AZ7_fU6Z-X8MwnJYG61Onlc-HojWFRbA_hljWQZ0oBduuqmcG5HSWOT4pl1Ka4KAuw8nzcW-kKj_4"
export CODEX_NO_TOOLS=1

# Codex CLI MiniMax 完整配置
export CODEX_NO_TOOLS=1

# Codex 命令别名 - 禁用所有可能导致 function calling 问题的选项
alias codex-minimax='CODEX_NO_TOOLS=1 codex -p m27 exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -c "features.unified_exec=true" -c "sanitizer.disable_tool_use=true"'
alias codex-fix="source ~/.zshrc && cd \"/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Codex Cli\" && CODEX_NO_TOOLS=1 codex -p m27 exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -c \"features.unified_exec=true\" -c \"sanitizer.disable_tool_use=true\""

# Prefer Node 20 for Next.js 16
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"

# Sentinel LLM API Key (MiniMax)
export MINIMAX_API_KEY="sk-cp-Vur2RO_jN2A2YmIfmYeqjERqa5W8ek014Hb_CK5doglhTSl6f9S5AxSmREfRfe5sURzJtniE5129yqvo8bPnZwMGco8pQH2W7GrDa2sowJ17MxdvAYEu5B8"

<!-- LLM-WIKI:START -->
# LLM Wiki shell context
if [ -f '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/adapters/llm-wiki-shell-context.sh' ]; then
  source '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/adapters/llm-wiki-shell-context.sh'
fi
<!-- LLM-WIKI:END -->
