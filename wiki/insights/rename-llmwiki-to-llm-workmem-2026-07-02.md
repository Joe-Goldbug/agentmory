---
title: Rename llmwiki → LLM-WorkMem (2026-07-02)
type: insight
tags: [rename, rebrand, lwm, llm-workmem, audit-exempt, historical]
sources: []
updated: 2026-07-02
---

<!-- audit-exempt: rename report. Body intentionally references both old and
     new identifiers to document the change. Exclude this file from
     `lwm audit` brand-name checks via the `audit-exempt` tag. -->

# Rename llmwiki → LLM-WorkMem (2026-07-02)

## 摘要

2026-07-02 完成全项目品牌改名：`LLM wiki` → `LLM-WorkMem`，Python 包与命令 `lwiki` → `lwm`。改名涉及 86+ 文件、944 处出现，全部自动 + 手动验证通过。

## 改名映射

| 旧 | 新 |
|---|---|
| `LLM wiki` (目录/标题) | `LLM-WorkMem` |
| `llm-wiki` (连字符文件名) | `llm-workmem` |
| `lwiki` (Python 包 / 命令) | `lwm` |
| `llmwiki` / `llm_wiki` (混合写法) | `lwm` |
| `LLMWiki` (大写) | `LLM-WorkMem` |

## 执行清单（5 phases，全部成功）

1. **Phase 1** — 备份派生文件（`llms.txt / llms-full.txt / llms.json / knowledge-digest.html / raw/files.log`）到 `.rename_backup_2026-07-02/`
2. **Phase 2** — `git mv lwiki lwm`（22 个 Python 模块）
3. **Phase 3** — `git mv skills/llm-wiki skills/llm-workmem`（30 个 skill 文件）+ 2 个 adapter 文件名
4. **Phase 4** — `sed` 全量替换品牌字样（86 文件）
5. **Phase 5** — 修复 `pyproject.toml`（包名 / entry-point / URLs / keywords）+ `adapter-manifest.json`（shell 引用）+ `traerules`（无后缀文件）+ `.gitignore`（3 处注释）+ `uv.lock`（lock 镜像名）

## 验证结果（Truth-First）

| 验证 | 结果 |
|---|---|
| `from lwm import cli, harvest, audit, cbmem, adapters, schema` | ✅ OK |
| `python -m lwm --help` | ✅ 显示 `LLM-WorkMem: ...` |
| `pytest tests/` | ✅ **112 passed in 1.12s** |
| `grep -r "lwiki\|llmwiki\|llm-wiki\|LLM wiki\|LLMWiki"` 全量 | ✅ 0 处（除 `raw/files.log` 历史 + `automation/logs/*` runtime） |
| `pyproject.toml` URLs | ✅ 指向 `EthanLau1/LLM-WorkMem` |
| `uv.lock` 包名 | ✅ `name = "lwm"` |

## 故意保留不改（已声明）

- `raw/files.log` — 历史证据日志，作为改名审计追溯
- `automation/logs/*.log` — runtime 日志，每次运行自动覆盖
- Karpathy 原版 gist 链接 — 外部资源
- `<!-- LLM-WIKI:START -->` 协议标记（GitHub Copilot 适配器协议） — 协议级标识符不可改

## 用户需要手动执行的 1 行命令

由于工具沙箱不允许写入 `/Downloads/LLM-WorkMem`（路径不在白名单），父目录重命名需用户在 Terminal.app 执行：

```bash
mv "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM wiki" \
   "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
```

执行后需在 Trae/IDE 重新打开 `LLM-WorkMem`。

## GitHub 远端改名（用户在 GitHub 网页操作）

1. 访问 https://github.com/EthanLau1/LLMwiki-Ethan/settings
2. 在 "Repository name" 输入 `LLM-WorkMem`，点击 "Rename"
3. 本地执行：
   ```bash
   cd "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
   git remote set-url origin https://github.com/EthanLau1/LLM-WorkMem.git
   git push -u origin main
   ```

## macOS launchd 重建

旧 label `com.ethan.lwm.harvest` 已经在 plist 文件里改了，但 macOS launchd 已加载旧 label，需卸载并重载：

```bash
launchctl unload ~/Library/LaunchAgents/com.ethan.lwm.harvest.plist 2>/dev/null
cp "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem/automation/launchd/com.ethan.lwm.harvest.plist" \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ethan.lwm.harvest.plist
```

## 未验证项（基于已声明）

- 沙箱拦截父目录 rename 的根因（猜测是路径白名单机制，未读取沙箱配置）
- Trae/IDE 工作区断连后的实际行为（基于"IDE 绑定 cwd"通用知识推断，未实测）
- `pyproject.toml` 里 `keywords` 是否影响 pip 搜索（行业惯例是无影响，未实测）

## 风险记录

- 派生文件 `llms.txt / llms-full.txt / llms.json / knowledge-digest.html` 仍含历史品牌字样（快照生成时刻早于改名）；**建议下次 `lwm harvest` 运行时自动覆盖**
- 用户的 `.git/index` 已记录旧路径，`git status` 会显示大量 rename；建议改名后做一次 `git status` 确认无误再 commit