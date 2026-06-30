# Claude Code 规则

## 红线（不商量）
- 不删文件，不先确认不删
- 不暴露密钥，环境变量注入用占位符
- 不读 .env / *.key / settings.local.json

## 工作原则
- 先思考，再动手 — 理解目标和上下文再做
- 能简单就简单 — 只改必须改的，不预防性重构
- 改完要验证 — 跑一下，不对就改

## gstack Skills（可选工具）
见 `/Users/ethan/CLAUDE.md` 清单。按需调用，无需把关。

## Bug 修复
该排查排查，该修复修复，不限制输出格式。

## 禁止
- `git push --force` / `git reset --hard` / `git clean -f`
- 修改系统配置 / 全局安装包 / 改 CI 配置
- 删云资源 / 清 Docker / 改防火墙
