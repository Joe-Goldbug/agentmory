# Trae Solo v5.1 - 增强版主配置

> Personal AI Development Config Vault
> 参考 Claude Code 规则精简 | MemPalace + Obsidian 双记忆驱动 | 层级记忆 + Reflection Loop

---

## 核心规则文件

| 文件 | 作用 |
|------|------|
| `user_rules/rule-global.md` | 全局硬性规则 + Bug Fix Protocol |
| `.traerules` | 项目级安全 + 工作流宪法 |
| `user_rules/rules/` | 细分规则 (workflow, memory, communication) |
| `memory/HIERARCHICAL_MEMORY_SYSTEM.md` | 层级记忆系统 (v1.0) |

---

## 工作流 Pipeline (v7 Stage)

```
Think → Plan → Build → Verify → Reflect → Commit
```

**执行原则:**
- 复杂任务 (>2 文件) → 先 Plan
- Bug → 排查 → diff → 验证 → 缓存
- 每 5 轮 → 状态快照，建议 `/compact`

### 🔄 Reflection Loop (新增)

**强制执行点**:
1. **任务完成后** (无论成功/失败)
2. **上下文超过 50%** 时
3. **用户要求** (`reflect`)

**Reflect 输出格式**:
```
### 🔄 反思总结
- **做得好的**: [成功点]
- **需要改进的**: [失败点]
- **学到的新知识**: [新发现]
- **下次如何做得更好**: [优化建议]
```

---

## 硬性红线

- ❌ 删除文件（先确认）
- ❌ 修改系统配置（`~/Library/` 外禁止）
- ❌ 硬编码密钥 / 读取敏感文件 (`.env`, `*.key`)
- ❌ 未确认推代码 / `--force` push
- ❌ 删系统文件 / 改 CI 配置

---

## Bug Fix 强制协议

| 阶段 | 输出格式 |
|------|----------|
| **排查** | `根因:` `影响范围:` `方案:` 三行 |
| **修复** | `<diff>...</diff>`，禁止 prose |
| **验证** | `PASS:` 或 `FAIL:` |
| **缓存** | 修复后追加 `memory/error-cache.json` |

---

## Token 效率原则

- 只传 diff，不传全文；>20 行用工具改
- Grep 定位后精准读取，禁止全量读
- error-cache 命中 → 直接返回方案

---

## 层级记忆系统 (Hierarchical Memory)

### 四层架构

| 层级 | TTL | 用途 |
|------|-----|------|
| **Working** | 1h | 当前任务上下文 |
| **Session** | 24h | 会话决策和进度 |
| **Project** | 30d | 项目级知识 |
| **Global** | ∞ | 个人偏好和跨项目知识 |

### 自动流转规则

```
Working (1h) → Session (24h) → Project (30d) → Global (∞)
```

### 检索优先级

```
1. Working (90% 匹配) → 直接使用
2. Session (70% 匹配) → 验证后使用
3. Project (50% 匹配) → 深度匹配后使用
4. Global (30% 匹配) → 基础规则匹配
```

---

## Prompt 缓存 (v2.0)

场景识别自动加载优化模板:

| 场景 | 触发关键词 | Token 节省 |
|------|-----------|-----------|
| 代码编写 | `写代码`, `create`, `implement` | ~85-92% |
| Debug 分析 | `Bug`, `debug`, `报错` | ~82-88% |
| 架构设计 | `设计`, `架构`, `review` | ~83-90% |
| 安全审计 | `安全`, `漏洞`, `cso` | ~85-93% |
| 发布部署 | `ship`, `deploy`, `release` | ~80-88% |

---

## Model Routing (v1.0)

### 任务 → 模型映射

| 任务类型 | 推荐模型 | 理由 |
|---------|---------|------|
| **简单编辑** | Claude 3.5 Haiku | 极速、低成本 |
| **代码编写** | Claude 3.5 Sonnet | 平衡质量与速度 |
| **复杂架构** | DeepSeek-R1 | 深度推理能力 |
| **日常问答** | DeepSeek-V3 | 高性价比 |
| **安全审计** | GPT-4o | 综合推理最强 |

### 切换规则

- 单次修改 < 5 行 → 使用 Haiku
- 跨文件重构 → 使用 Sonnet
- 解决未知的复杂 Bug → 使用 DeepSeek-R1
- 快速解释代码 → 使用 Haiku/V3

---

## 禁止清单

- ❌ `git reset --hard` / `git clean -fdx`
- ❌ 修改 shell 配置 / 全局安装包
- ❌ 删数据库 / 删云资源 / 清 Docker

---

**v5.1** | 2026-05-03 | **新增**: Reflection Loop + Model Routing + 层级记忆