# Trae Solo 项目级安全与工作流规范

> 会话启动时自动读取。与 CLAUDE.md 互补：本文件负责安全边界和执行纪律，CLAUDE.md 负责行为规则。

## 1. 终端安全拦截

**以下高危操作必须确认，禁止静默执行：**

- `rm -rf` / 删除文件
- `git push --force` / `git reset --hard` / `git clean -fdx`
- 修改 `~/.zshrc`, `~/.ssh/`, `/etc/` 等系统文件
- 全局安装 (`npm i -g`, `pip install --user`, `brew install`)
- 暴露本地服务到公网 (ngrok, localtunnel)

**安全白名单（自动执行）：** `chmod`, `bash`, `mkdir`, `cp`, `grep`, `echo`, `tail`, `mv`, `git` (非破坏性), `cat`, `cd`, `node`, `python3`, `curl`, `ls`, `find`, `sed`, `sqlite3`

## 2. 执行 Pipeline

**禁止一上来就写代码。必须按顺序：**

1. **Think** — 明确目标，模糊则提问
2. **Plan** — >2 文件改动时写 Plan
3. **Build** — 最小修改，不碰无关代码
4. **Verify** — 必须验证，不通过不回传
5. **Reflect** — 出错时读日志找根因，不盲试

## 3. 上下文管理

- 上下文 ~50% 时建议 `/compact`
- 一事一议，一个 Session 只做一件事
- 子任务拆分到足够小，确保在 50% 上下文内完成
- 调查类任务用 Subagent，不污染主会话

---

**v4.0** | 2026-05-13 | 精简版
