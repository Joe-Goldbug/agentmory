
# Kiro CLI pre block. Keep at the top of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.pre.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.pre.zsh"


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
# 强制用新版 claude 二进制，不走旧 launcher alias
unalias claude 2>/dev/null
export CLAUDE_CONFIG_DIR="/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config"

# === API Keys ===
export MINIMAX_API_KEY="sk-cp-Vur2RO_jN2A2YmIfmYeqjERqa5W8ek014Hb_CK5doglhTSl6f9S5AxSmREfRfe5sURzJtniE5129yqvo8bPnZwMGco8pQH2W7GrDa2sowJ17MxdvAYEu5B8"

# 默认端点（MiniMax）
export ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
export ANTHROPIC_API_KEY="$MINIMAX_API_KEY"
claude() { /Users/ethan/.local/bin/claude "$@"; }
# 硬覆盖别名
alias claude-m3="ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic ANTHROPIC_API_KEY=$MINIMAX_API_KEY /Users/ethan/.local/bin/claude --model MiniMax-M3"
# 注意: 你系统中 `claude` 实际指向 wrappers/claude-code-launcher.sh,
# 那个启动器不会传 --model。需要直接用 /Users/ethan/.local/bin/claude。

export CODEX_NO_TOOLS=1

# Codex 命令别名 - 禁用所有可能导致 function calling 问题的选项
alias codex-minimax='CODEX_NO_TOOLS=1 codex -p m27 exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -c "features.unified_exec=true" -c "sanitizer.disable_tool_use=true"'
alias codex-fix="source ~/.zshrc && cd \"/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Codex Cli\" && CODEX_NO_TOOLS=1 codex -p m27 exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -c \"features.unified_exec=true\" -c \"sanitizer.disable_tool_use=true\""

# Prefer Node 20 for Next.js 16
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"

# Added by MiniMax Code
export PATH="/Users/ethan/.mavis/bin:$PATH"


# Kiro CLI post block. Keep at the bottom of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.post.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.post.zsh"

<!-- LLM-WIKI:START -->
# LLM-WorkMem shell context
if [ -f '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/adapters/llm-workmem-shell-context.sh' ]; then
  source '/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/adapters/llm-workmem-shell-context.sh'
fi
<!-- LLM-WIKI:END -->
