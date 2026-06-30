# OpenCode 全局配置

这是为OpenCode配置的全局最佳实践方案，让你在任何项目文件夹都能使用统一的智能开发环境。

## 📁 配置结构

```
~/.config/opencode/
├── opencode.json          # 主配置文件
├── tui.json               # TUI界面配置
├── AGENTS.md              # 全局规则和行为准则
├── package.json           # 插件依赖
├── skills/                # 技能库
│   ├── code-review/
│   ├── tdd-workflow/
│   ├── git-release/
│   └── security-check/
├── agents/                # 智能体
│   ├── security-reviewer/
│   ├── doc-writer/
│   └── test-runner/
├── commands/              # 自定义命令
│   ├── test.md
│   ├── review.md
│   ├── analyze.md
│   ├── module.md
│   ├── lint.md
│   ├── update.md
│   ├── todo.md
│   └── quality.md
└── plugins/               # 插件
    └── automation.ts
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ~/.config/opencode
bun install
```

### 2. 配置Provider

运行OpenCode并配置你的AI Provider:

```bash
opencode
```

在OpenCode中运行:
```
/connect
```

选择你的Provider并输入API密钥。

### 3. 使用配置

在任何项目文件夹中启动OpenCode:

```bash
cd /path/to/your/project
opencode
```

全局配置会自动加载。

## 📚 可用功能

### Skills (技能)

在对话中使用 `/skill` 命令加载技能:

- `code-review` - 专业的代码审查工作流
- `tdd-workflow` - TDD测试驱动开发流程
- `git-release` - 创建规范的版本发布
- `security-check` - 安全审计和漏洞扫描

### Agents (智能体)

使用 `@` 提及智能体:

- `@security-reviewer` - 安全审查专家
- `@doc-writer` - 技术文档撰写专家
- `@test-runner` - 测试执行和覆盖率分析专家

### Commands (命令)

使用 `/` 执行自定义命令:

- `/test` - 运行测试并分析失败
- `/review` - 审查代码质量和安全问题
- `/analyze` - 分析项目结构和技术栈
- `/module <name>` - 创建新模块
- `/lint` - 检查代码格式和lint问题
- `/update` - 检查依赖更新
- `/todo` - 查找代码中的TODO和FIXME
- `/quality` - 分析代码复杂度和质量

## 🔐 安全特性

### 分层权限系统

1. **默认模式**: 所有操作需确认
2. **白名单模式**: 预授权安全操作
3. **沙箱模式**: 限制文件访问范围
4. **自动防护**: 防止危险命令执行

### 禁止的操作

- ❌ `rm -rf` 批量删除
- ❌ `git push --force` 强制推送
- ❌ 访问 `.env` 敏感文件
- ❌ 修改全局配置

### 允许的安全操作

- ✅ `git status/diff/log` 查看状态
- ✅ `ls/cat/grep` 文件查看
- ✅ `npm test` 运行测试
- ✅ 编辑源代码文件

## 🎯 最佳实践

### 工作流程

```
探索 → 计划 → 执行 → 验证 → 提交
```

### Plan模式触发条件

以下场景自动进入Plan模式:
- 涉及>2个文件改动
- 架构级变更
- 数据库迁移
- 安全相关修改
- 重构任务

### 上下文管理

- 使用 `@filename` 精准加载文件
- 定期执行 `/compact` 压缩上下文
- 任务切换时执行 `/clear` 清空上下文
- 避免Kitchen Sink Session(一Session多任务)

### TDD工作流

1. 用自然语言描述需求
2. 使用 `@test-runner` 生成测试用例
3. 确认测试用例
4. 实现代码
5. 自动运行测试验证
6. 全部通过后提交

## 📊 配置详解

### 主配置 (opencode.json)

```json
{
  "model": "claude-sonnet-4",          // 主模型
  "small_model": "claude-haiku-4",     // 快速模型
  "default_agent": "build",            // 默认Agent
  "share": "disabled",                 // 禁止分享
  "autoupdate": "notify",              // 更新提醒
  "snapshot": true,                    // 文件变更追踪
  "permission": { ... },               // 权限配置
  "compaction": { ... },               // 上下文压缩
  "mcp": { ... }                       // MCP服务器
}
```

### 权限配置

```json
{
  "permission": {
    "*": "ask",                        // 默认询问
    "bash": {
      "git status*": "allow",          // 允许查看状态
      "git push*": "deny"              // 禁止推送
    },
    "edit": {
      "*.env": "deny",                 // 禁止编辑环境变量
      "src/**": "ask"                  // 源代码需确认
    }
  }
}
```

## 🔧 自定义配置

### 添加新Skill

```bash
mkdir -p ~/.config/opencode/skills/my-skill
```

创建 `SKILL.md`:
```markdown
---name: my-skilldescription: 我的自定义技能license: MIT---
## 技能内容
...
```

### 添加新Agent

在 `~/.config/opencode/agents/my-agent/agent.md`:
```markdown
---description: 我的Agentmode: subagentpermission:
  edit: deny---
Agent指令...
```

### 添加新Command

在 `~/.config/opencode/commands/my-cmd.md`:
```markdown
---description: 我的命令agent: build---
命令模板...
```

### 添加新Plugin

在 `~/.config/opencode/plugins/my-plugin.ts`:
```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ client, $ }) => {
  return {
    "session.idle": async ({ event }) => {
      // 插件逻辑
    }
  }
}
```

## 📝 使用示例

### 示例1: 代码审查

```
/review
```

OpenCode会:
1. 分析代码质量
2. 检查安全问题
3. 识别性能瓶颈
4. 提供改进建议

### 示例2: TDD开发

```
我想添加一个用户登录功能

@test-runner 帮我生成测试用例
```

确认测试后:
```
实现这个功能，确保所有测试通过
```

### 示例3: 安全审计

```
@security-reviewer 审查这个认证模块的安全性
```

### 示例4: 创建模块

```
/module UserService
```

### 示例5: 分析项目

```
/analyze
```

## 🚨 反模式警示

| 反模式 | 后果 | 解决方案 |
|--------|------|---------|
| Kitchen Sink Session | 上下文污染 | 一事一议，做完/clear |
| Infinite Exploration | token耗尽 | 限制搜索范围 |
| Trust-then-Verify Gap | 生产事故 | 未测试代码不提交 |
| Vague Error Reporting | AI瞎猜 | 粘贴完整错误信息 |

## 📈 性能优化

### 上下文管理

- 自动压缩: 上下文>150K自动压缩
- 智能加载: 按需加载文件
- 缓存优化: 避免重复读取

### 模型分层

- **复杂任务**: claude-sonnet-4
- **简单任务**: claude-haiku-4
- **后台任务**: 本地模型

### 成本控制

- 使用 `small_model` 处理轻量任务
- 禁用非必要模型调用
- 监控token使用情况

## 🔍 故障排查

### Skills不显示

1. 检查 `SKILL.md` 是否存在
2. 验证frontmatter格式
3. 确认skill名称唯一

### Commands不工作

1. 检查文件名格式
2. 验证frontmatter配置
3. 查看agent是否存在

### 权限问题

1. 检查 `permission` 配置
2. 验证文件路径匹配
3. 查看权限日志

## 🆘 获取帮助

- 官方文档: https://opencode.ai/docs
- GitHub Issues: https://github.com/anomalyco/opencode/issues
- Discord社区: https://opencode.ai/discord

## 📜 许可证

本配置基于最佳实践整理，遵循MIT许可证。

---

**享受智能开发体验! 🚀**