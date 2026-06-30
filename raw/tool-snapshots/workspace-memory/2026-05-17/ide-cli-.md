# IDE/CLI 统一记忆体集成指南

> **版本**: v2.1-链接型
> **日期**: 2026-04-21
> **状态**: ✅ 使用中

---

## 快速入口

- 架构：[[AI-Hub-架构.md]]
- 记忆规则：[[MASTER-记忆体.md]]
- 工作流：[[MASTER-工作流.md]]

## 快速参考

| 工具 | 配置方式 | 配置文件 |
|------|---------|---------|
| Claude Code | 原生 Hook | `~/Documents/claude-code-config/config/settings.json` |
| VSCode | 包装脚本 | `wrappers/vscode-launcher.sh` |
| Trae | 包装脚本 | `wrappers/trae-launcher.sh` |
| Cursor | 包装脚本 | `wrappers/cursor-launcher.sh` |
| OpenCode | 原生 Hook | `~/.opencode/config.json` |

## 核心脚本位置

```
~/Documents/ObsidianVault/
├── broadcast_to_hub.sh              # 广播到只读 Hub
├── promote_to_obsidian.sh           # 经验晋升审核
├── unified-memory-recovery.sh       # 多工具记忆回收
├── ide-adapter.sh                   # 自动创建包装脚本
└── wrappers/                       # 各工具包装脚本
```

## Claude Code Hook

`~/Documents/claude-code-config/config/settings.json` 中的 SessionEnd Hook 已配置：

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/Documents/ObsidianVault/unified-memory-recovery.sh\" claude-code",
            "description": "回收 Claude Code 记忆体到 Obsidian Inbox"
          }
        ]
      }
    ]
  }
}
```

## 包装脚本使用

```bash
# VSCode
bash ~/Documents/ObsidianVault/wrappers/vscode-launcher.sh

# Trae
bash ~/Documents/ObsidianVault/wrappers/trae-launcher.sh

# Cursor
bash ~/Documents/ObsidianVault/wrappers/cursor-launcher.sh

# 创建别名
alias code='bash ~/Documents/ObsidianVault/wrappers/vscode-launcher.sh'
```

## 自动配置

```bash
# 创建所有包装脚本
bash ~/Documents/ObsidianVault/ide-adapter.sh --wrap-all

# 测试回收
bash ~/Documents/ObsidianVault/unified-memory-recovery.sh claude-code
```
