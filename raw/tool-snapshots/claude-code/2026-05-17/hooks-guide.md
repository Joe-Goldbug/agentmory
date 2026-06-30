# Claude Code Hooks 完整配置指南

## 什么是 Hooks？

Hooks 是在特定事件发生时自动执行的脚本，让你可以实现确定性自动化行为，而非依赖 LLM 选择执行。

## 完整 Hook 事件列表 (v2.1.100 - 已补齐)

| 事件 | 触发时机 | Matcher 支持 | 当前配置状态 |
|------|----------|--------------|-------------|
| `SessionStart` | 会话开始或恢复时 | `startup`, `resume`, `clear`, `compact` | ✅ 已配置 |
| `SessionEnd` | 会话终止时 | `clear`, `resume`, `logout`, ... | ✅ 已配置 |
| `UserPromptSubmit` | 用户提交 prompt 时 | ❌ 不支持 | ✅ 已配置 |
| `PreToolUse` | 工具调用前（可阻止） | 工具名 (`Bash`, `Edit|Write`) | ✅ 已配置 |
| `PermissionRequest` | 权限对话框出现时 | 工具名 | ✅ 已配置 |
| `PermissionDenied` | 工具调用被拒绝时 | 工具名 | ✅ 已配置 |
| `PostToolUse` | 工具调用成功后 | 工具名 | ✅ 已配置 |
| `PostToolUseFailure` | 工具调用失败后 | 工具名 | ✅ 已配置 |
| `Notification` | Claude Code 发送通知时 | `permission_prompt`, `idle_prompt`, ... | ✅ 已配置 |
| `SubagentStart` | 子代理启动时 | 代理类型 | ✅ 已配置 |
| `SubagentStop` | 子代理完成时 | 代理类型 | ✅ 已配置 |
| `TaskCreated` | 任务创建时 (TaskCreate) | ❌ 不支持 | ✅ 已配置 |
| `TaskCompleted` | 任务完成时 | ❌ 不支持 | ✅ 已配置 |
| `Stop` | Claude 响应结束时 | ❌ 不支持 | ✅ 已配置 |
| `StopFailure` | API 错误导致终止时 | `rate_limit`, `authentication_failed`, ... | ✅ 已配置 |
| `TeammateIdle` | Agent team 成员闲置时 | ❌ 不支持 | 🔄 可选 |
| `InstructionsLoaded` | CLAUDE.md 加载时 | `session_start`, `nested_traversal`, ... | ✅ 已配置 |
| `ConfigChange` | 配置文件变更时 | `user_settings`, `project_settings`, ... | ✅ 已配置 |
| `CwdChanged` | 工作目录改变时 | ❌ 不支持 | ✅ 已配置 |
| `FileChanged` | 监控文件变更时 | 文件名 (`.env`, `.envrc`) | ✅ 已配置 |
| `WorktreeCreate` | Worktree 创建时 | ❌ 不支持 | ✅ 已配置 |
| `WorktreeRemove` | Worktree 移除时 | ❌ 不支持 | ✅ 已配置 |
| `PreCompact` | 上下文压缩前 | `manual`, `auto` | ✅ 已配置 |
| `PostCompact` | 上下文压缩后 | `manual`, `auto` | ✅ 已配置 |
| `Elicitation` | MCP server 请求用户输入时 | MCP server 名 | ✅ 已配置 |
| `ElicitationResult` | 用户响应 MCP elicitation 后 | MCP server 名 | ✅ 已配置 |

## Hook 类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `command` | 执行 shell 命令 | 确定性规则、格式化、日志 |
| `http` | POST 到 HTTP endpoint | 云服务、审计系统 |
| `prompt` | 单次 LLM 评估 | 需判断力的决策 |
| `agent` | 多轮验证+工具访问 | 需检查代码状态的复杂验证 |

## 配置格式

### 基础结构

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write $FILE_PATH"
          }
        ]
      }
    ]
  }
}
```

### 使用 `if` 字段精确过滤 (v2.1.85+)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git *)",
            "command": "echo 'Git command detected'"
          }
        ]
      }
    ]
  }
}
```

### Prompt-based Hook

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains\"}."
          }
        ]
      }
    ]
  }
}
```

### Agent-based Hook

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite.",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### HTTP Hook

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "http",
            "url": "http://localhost:8080/hooks/tool-use",
            "headers": {
              "Authorization": "Bearer $MY_TOKEN"
            },
            "allowedEnvVars": ["MY_TOKEN"]
          }
        ]
      }
    ]
  }
}
```

## 退出码与决策

| 退出码 | 效果 |
|--------|------|
| `0` | 允许继续执行 |
| `2` | 阻止操作，stderr 作为反馈 |
| 其他 | 允许继续，stderr 仅日志记录 |

### JSON 结构化输出

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use rg instead of grep"
  }
}
```

| `permissionDecision` | 效果 |
|----------------------|------|
| `allow` | 跳过交互式权限提示 |
| `deny` | 取消工具调用，发送原因给 Claude |
| `ask` | 正常显示权限提示 |
| `defer` | (仅非交互模式) 保留工具调用供 SDK 处理 |

## 常用配置示例

### 1. 桌面通知

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude needs attention\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

### 2. 自动格式化

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

### 3. 保护敏感文件

```bash
#!/bin/bash
# .claude/hooks/protect-files.sh
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh"
          }
        ]
      }
    ]
  }
}
```

### 4. 压缩后注入上下文

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use Bun, not npm. Run bun test before committing.'"
          }
        ]
      }
    ]
  }
}
```

### 5. 自动批准特定权限

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"PermissionRequest\", \"decision\": {\"behavior\": \"allow\"}}}'"
          }
        ]
      }
    ]
  }
}
```

### 6. 目录切换时加载环境

```json
{
  "hooks": {
    "CwdChanged": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "direnv export bash >> \"$CLAUDE_ENV_FILE\""
          }
        ]
      }
    ]
  }
}
```

### 7. 配置变更审计

```json
{
  "hooks": {
    "ConfigChange": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jq -c '{timestamp: now | todate, source: .source, file: .file_path}' >> ~/claude-config-audit.log"
          }
        ]
      }
    ]
  }
}
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `CLAUDE_PROJECT_DIR` | 项目根目录 |
| `CLAUDE_ENV_FILE` | 环境变量输出文件路径 |
| `FILE_PATH` | (stdin JSON) 文件路径 |

## 配置位置

| 文件 | 范围 | 可共享 |
|------|------|--------|
| `~/.claude/settings.json` | 所有项目 | ❌ 本地 |
| `.claude/settings.json` | 单项目 | ✅ 可提交 |
| `.claude/settings.local.json` | 单项目 | ❌ gitignore |
| Plugin `hooks/hooks.json` | 插件启用时 | ✅ 插件内 |

## 安全相关设置

```json
{
  "allowManagedHooksOnly": true,
  "allowedHttpHookUrls": ["https://hooks.example.com/*", "http://localhost:*"],
  "httpHookAllowedEnvVars": ["MY_TOKEN", "HOOK_SECRET"]
}
```

## 常见问题

### Stop hook 无限循环

检查 `stop_hook_active` 字段：

```bash
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0  # 允许停止
fi
```

### JSON 解析失败

Shell profile 的 `echo` 会污染输出。在 `.zshrc` 中：

```bash
if [[ $- == *i* ]]; then
  echo "Shell ready"
fi
```

### 调试

- `Ctrl+O` 切换 verbose 模式
- `claude --debug` 查看完整执行详情
- `/hooks` 浏览所有配置的 hooks

## 参考链接

- [Hooks Reference](https://code.claude.com/docs/en/hooks.md) - 完整 schema
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide.md) - 使用指南