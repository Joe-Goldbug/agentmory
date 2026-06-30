# ⚡ Claude Code 快速参考

## 🎯 当前模型和环境

- **当前模型**：Claude Opus 4.6 / Sonnet 4.6 / Haiku 4.5
- **CLI 版本**：Claude Code v2.1.114
- **平台**：macOS (Darwin)
- **Shell**：zsh

## 🔑 核心快捷键和命令

### 常用 Slash 命令
```
/help              获取帮助信息
/fast              切换快速模式
/commit            使用 commit skill
/review-pr         代码审查 skill
/loop 5m prompt    5分钟循环执行
```

### 键盘快捷键优化
见 `keybindings-help` skill 文档

## 🛠️ 工具选择决策树

```
我需要做什么？
│
├─ 搜索文件 → Glob
├─ 搜索内容 → Grep
├─ 读取文件 → Read
├─ 修改文件 → Edit（先 Read）
├─ 创建文件 → Write（仅新文件）
├─ 系统命令 → Bash
├─ 复杂搜索 → Agent (Explore)
├─ 多步骤任务 → Agent (general-purpose)
└─ 规划实现 → EnterPlanMode
```

## 📋 任务列表使用

```bash
# 查看任务
TaskList                    # 列出所有任务

# 创建任务
TaskCreate subject="..." description="..."

# 更新任务
TaskUpdate taskId="1" status="in_progress"
TaskUpdate taskId="1" status="completed"
```

## 💾 记忆文件结构

```
~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/claude-code-config/memory/
├── MEMORY.md              ← 主文件（≤200行）
├── skills.md              ← 自定义 Skills 清单
├── patterns.md            ← 工作流最佳实践
├── quick-reference.md     ← 本文件
├── context-optimization.md ← Token 优化策略
├── token-efficiency.md    ← Diff 传输与压缩
└── error-cache.json      ← Bug 模式缓存（ADD-only）
```

## 🎯 5分钟快速开始模板

```markdown
# 任务名称

## 需求
- 简洁的需求列表

## 执行步骤
1. 用 Glob 定位文件
2. 用 Grep 搜索特定模式
3. 用 Read 理解代码
4. 用 Edit 修改
5. 验证修改

## 成功标准
- 清晰的验收条件
```

## 🚀 常见快速命令

### 代码相关
```bash
# 快速定位问题代码
Glob "**/*.js" --pattern "*error*"
Grep "function.*Error" --type js

# 修改和验证
Read /path/to/file
Edit old_string="..." new_string="..."

# 测试
Bash "npm test"
```

### Git 相关
```bash
# 查看状态
Bash "git status"
Bash "git log --oneline -5"

# 使用 /commit skill
/commit -m "Your message"
```

### 内存管理
```bash
# 更新记忆
Edit /path/to/memory/file old="..." new="..."

# 创建新记忆文件
Write /path/to/memory/file content="..."
```

## 📊 效率检查清单

完成任务前自问：

- [ ] 使用了最合适的工具？
- [ ] 是否有可以并行化的操作？
- [ ] 文件是否需要完整读取，还是部分就够？
- [ ] 搜索结果是否太多，需要 head_limit？
- [ ] 这个学习点是否应该保存到记忆？
- [ ] 是否意外引入了安全漏洞？

## 🔐 安全检查点

- ❌ 不要用 `--no-verify` 跳过 git 钩子
- ❌ 不要在代码中硬编码凭证
- ❌ 不要用 `rm -rf` 等破坏性命令（确认后执行）
- ❌ 不要 force push（除非确实需要）
- ✅ 检查命令注入风险
- ✅ 验证环境变量设置

## 🆘 常见问题

### Q: 如何触发特定 Skill？
A: 在提示中使用自然语言或用 `/skill-name` 命令

### Q: 内存文件太满了怎么办？
A: MEMORY.md ≤200行，详细内容放专题文件，用 link 连接

### Q: 如何确保 Skill 被正确触发？
A: Skill description 要包含具体触发词，要说 WHAT & WHEN

### Q: 什么时候用 Agent？
A: 简单搜索用 Glob/Grep；复杂多步骤才用 Agent

### Q: 如何优化上下文消耗？
A: 使用三层信息架构，大文件分段读，搜索结果限制行数

---

## 📚 相关资源链接

- [官方 Skills 课程](https://anthropic.skilljar.com/introduction-to-agent-skills)
- [GitHub 完整指南](https://gist.github.com/joyrexus/ff71917b4fc0a2cbc84974212da34a4a)
- [Claude API 文档](https://docs.anthropic.com)

---

**最后更新**：2026-04-04
**配置版本**：v1.1
**优化目标**：最大化效率，最小化上下文消耗

