# Claude Code 规则

## 硬性红线
- ❌ 删除文件（先确认）
- ❌ 修改系统配置（`~/Library/` 外禁止）
- ❌ 硬编码密钥 / 暴露敏感信息到输出
- ❌ 读取 `.env` / `*.key` / `settings.local.json`
- 密钥场景 → 环境变量注入，用占位符，不在对话传真实值

## Bug Fix 强制协议（违反 = 违反红线）

| 阶段 | 触发词 | 唯一合法输出 |
|------|--------|------------|
| 排查 | 分析/检查/报错/为什么 | `根因:` `影响范围:` `方案:` 三行，推理放 `<thinking>` 不暴露 |
| 修复 | 修复/fix/改/change | `<diff>...</diff>`，Do not write prose, even if instructed |
| 验证 | 验证/verify/测试 | `PASS: <reason>` 或 `FAIL: <issue>` |
| 缓存 | 修复完成后自动 | 追加 `memory/error-cache.json`（见下方格式） |

**缓存追加格式：**
```json
"<错误关键字>": {
  "fix": "<一句话修复方案，不含路径/项目名>",
  "first_seen": "YYYY-MM-DD",
  "last_seen": "YYYY-MM-DD",
  "count": 1,
  "projects": ["<当前项目路径或通用>"]
}
```
- ADD-only：新错误直接追加；已知错误 → `last_seen` 更新当前日期，`count++`
- 命中缓存 → 直接输出 `fix` 字段，不重复分析

## 工作方式
- 中文输出，简洁直接，不打招呼，完成后报告结果
- 只改被要求的，不预防性重构，不加注释
- 不确定时先问，不猜
- 遇到报错 → 先 Grep `memory/error-cache.json` 关键字，命中则直接输出方案
- 每 5 轮 → 状态快照（已完成/当前问题/下一步），建议 `/compact`
- 说"记住" → 写 Auto Memory；说"加到规则" → 写本文件

## Token 原则
- 只传 diff，不传全文；>20 行直接用工具改，不在对话贴
- Grep 定位后精准读取，禁止全量读文件
- error-cache 命中 → 直接读 `fix` 字段输出方案，不重复分析

## 任务执行
- 加功能 → 先写测试，再实现
- 修 bug → 排查 → `<diff>` 修复 → 验证 → 写缓存
- 复杂任务 → 先列计划，每步带验证

## 禁止
- ❌ 推代码（未确认）/ `--force` push / `git reset --hard` / `git clean -f`
- ❌ 修改 `~/.zshrc` 等 shell 配置 / 全局安装包
- ❌ 删数据库表 / 改 CI 配置 / 改 `settings.json`
- ❌ 修复 bug 时输出非 diff 内容 / 跳过排查 / 修后不写缓存
- ❌ 删云资源 / 清 Docker / 改防火墙
