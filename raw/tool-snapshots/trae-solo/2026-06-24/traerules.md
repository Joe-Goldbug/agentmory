# Trae Solo 项目级安全与工作流规范 (.traerules)

> 本文件是 Trae IDE (SOLO 模型) 的项目级宪法，每次会话启动时自动读取。

## 1. 终端安全拦截 (Terminal Safety)

*作为 Builder/Agent，你在执行以下高危操作前，**必须**使用 `AskUserQuestion` 或 `NotifyUser` 向我确认，绝不允许静默执行：*

### 绝对禁止静默执行
- **危险文件操作**: `rm -rf *`, `rm -rf /`, `rm -rf /*`, `rm -rf ~/*`
- **破坏性 Git 操作**: `git push --force`, `git push -f`, `git reset --hard`, `git clean -fdx`
- **系统级配置更改**: 修改 `~/.zshrc`, `~/.bashrc`, `~/.profile`, `~/.ssh/`, `/etc/` 等深层系统文件
- **网络暴露操作**: `ngrok`, `localtunnel`, 或任何将本地服务暴露到公网的命令
- **包管理器全局操作**: `npm install -g`, `pip install --user`, `brew install` 等全局安装

### 安全白名单 (可自动执行)
`chmod`, `bash`, `mkdir`, `cp`, `grep`, `echo`, `tail`, `mv`, `git` (非破坏性), `cat`, `cd`, `node`, `sleep`, `pwd`, `ls`, `find`, `sed`, `sqlite3`, `python3`, `curl`, `ssh` (只读), `launchctl` (status only)

## 2. 知识图谱与记忆 (MCP Memory)

你已全局挂载 `@modelcontextprotocol/server-memory`。

### 自动保存触发点
在以下场景完成后，**必须**调用 Memory MCP 保存上下文：
1. 完成一个大的 Milestone 或 Feature
2. 解决一个复杂的 Bug 并验证通过
3. 发现项目特有的架构决策或环境变量配置
4. 用户明确说"记住这个"或"保存到记忆"

### 背景读取策略
- **新会话启动**: 优先读取知识图谱中的当前项目实体信息
- **进入新目录**: 读取该目录相关的历史决策记录
- **避免重复询问**: 如果知识图谱中已有答案，直接使用，不要再次询问用户

## 3. 任务消耗总结 (Usage Tracking)

**强制要求**: 每次完成任务或结束一个对话循环后，**必须**在回答末尾输出以下格式的统计模块：

```
### 📊 任务消耗统计 (Task Metrics)
- **使用模型 (Model)**: [模型名称]
- **输入词元 (Input Tokens)**: [数量] tokens
- **输出词元 (Output Tokens)**: [数量] tokens
- **预估花费 (Cost)**: [金额] USD
- **响应耗时 (Duration)**: [耗时]s
```

> 如果无法精确计算 token 数量，请给出合理估算。未输出此模块视为任务未闭环。

## 4. 强制执行顺序 (Execution Pipeline)

**禁止一上来就写代码。** 你必须遵循以下 Pipeline：

1. **Think**: 明确你要做什么，遇到模糊地带**必须提问** (`AskUserQuestion`)
2. **Plan**: 在工作区生成包含架构决策的 Markdown 计划（复杂任务 >2 文件改动时强制）
3. **Build**: 开始编写代码
4. **Verify**: 使用终端命令或 Puppeteer/Playwright 测试你写的东西
5. **Reflect**: 如果出错，不要盲目试错，去阅读原始日志并分析根本原因

### 上下文管理策略
- 在会话上下文使用率达到 ~50% 时，主动建议用户执行 `/compact`
- 将子任务拆分到足够小，确保每个子任务在 50% 上下文内完成
- 使用子代理 (Subagent) 进行调查类任务，避免污染主会话上下文
- **一事一议**: 一个 Session 只做一件事，做完后建议 `/clear`

## 5. Obsidian 记忆体桥接 (Obsidian Memory Bridge)

### 核心原则 (源自 Obsidian PKM + Zettelkensen)
- **原子笔记**: 每个笔记只描述一个概念，使用 `[[双向链接]]` 连接到相关笔记
- **标签系统**: 使用 `#memory`, `#workflow`, `#architecture`, `#skill`, `#bug`, `#decision`
- **命名规范**: `YYYY-MM-DD-简短描述.md`
- **知识图谱**: 通过 backlinks 构建概念间的语义网络

### 路径映射 (Obsidian ↔ Trae Solo)
- **Obsidian 入口**: `~/Documents/ObsidianVault/Trae_Memory/`
- **Trae 本地镜像**: `./.memory/obsidian-broadcast/shared/`
- **全局 AI 大脑**: `~/.ai_brain/`

### 同步规则
- **写入源**: Trae Solo (`.memory/obsidian-broadcast/shared/` 目录)
- **Obsidian 镜像**: 通过 Git 同步到 ObsidianVault
- **工作流**: 每次会话结束自动写入记忆 → Obsidian 同步 → 跨设备可用

### 自动触发点
1. 完成 Milestone → 保存架构决策到 Obsidian
2. 解决 Bug → 写入根因分析到 `#bug` 标签笔记
3. 关键决策 → 创建 `#decision` 标签的新笔记
4. 学习新技能 → 创建 `#skill` 标签的原子笔记

## 6. Prompt 缓存优化 (Prompt Caching)

### 场景识别与模板加载
系统自动识别以下场景并加载优化后的缓存模板：

| 场景 | 触发关键词 | 模板来源 |
|------|-----------|---------|
| **代码编写** | `写代码`, `create`, `implement`, `新增功能` | `workflows/PROMPT_CACHE_SYSTEM.md` |
| **Debug 分析** | `Bug`, `报错`, `debug`, `investigate`, `问题` | `workflows/PROMPT_CACHE_SYSTEM.md` |
| **架构设计** | `设计`, `架构`, `review`, `refactor` | `workflows/PROMPT_CACHE_SYSTEM.md` |
| **安全审计** | `安全`, `漏洞`, `security`, `cso` | `workflows/PROMPT_CACHE_SYSTEM.md` |
| **发布部署** | `ship`, `deploy`, `上线`, `release` | `workflows/PROMPT_CACHE_SYSTEM.md` |

### Token 优化策略
1. **固定上下文压缩**: 使用角色标签 `[Architect]` 替代完整描述
2. **模板复用**: 使用 `@template:场景名` 快速加载
3. **增量上下文**: 仅追加新信息，引用历史摘要而非重复

### 效果目标
- 原始 Prompt ~800 tokens → 缓存后 ~350 tokens (**56% 节省**)
- 场景切换时自动重置上下文，避免累积冗余

### 手动调用命令
```
@cache:code-writing  → 加载代码编写缓存模板
@cache:compact       → 压缩当前上下文
@cache:status        → 显示缓存命中率
```

## 7. Git 提交规范

- **每个逻辑变更一个独立 Commit**，不要将不相关的文件改动打包到同一个 Commit
- 使用 Conventional Commits 格式: `type(scope): description`
- 可用类型: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- 提交后自动 `push` 到 `origin/main`

---
**v3.0** | 2026-05-03 | **适用范围**: Trae Solo 所有会话

<!-- LLM-WIKI:START -->
# LLM Wiki Context

Use this llm-wiki as the shared workflow and memory source for this tool.

Read order:
1. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms.txt` for compact context.
2. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/wiki/purpose.md` for scope and guardrails.
3. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/wiki/overview.md` for the current synthesis.
4. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms-full.txt` only when deeper context is needed.
5. `/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki/llms.json` for programmatic page metadata.

Rules:
- Treat `raw/` as source evidence, not polished memory.
- Prefer `wiki/` pages that passed audit over raw snapshots.
- Keep local project facts local unless they should be promoted through review.
- After meaningful work, update or generate evidence that `lwiki harvest`, `lwiki watch`, or `lwiki audit` can consume.
<!-- LLM-WIKI:END -->
