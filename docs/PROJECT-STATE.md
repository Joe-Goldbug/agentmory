# LLM-WorkMem 项目与分支状态

核查日期：2026-10-12。本文是当前仓库整合入口；以后 Git 状态变化时更新这里。

## 唯一项目与主线

项目仓库：https://github.com/EthanLau1/LLM-WorkMem ，私有仓库。
唯一正式整合主线：`main`。当前远端提交 `96ddb95`。
本地根目录仍在 `agent/sync-llm-workmem`，已提交 HEAD 与远端 main 相同，但存在未提交修改。分支名不能代表工作树内容已同步。

## 当前远端分支

| 分支 | HEAD | 相对 main | 定位与处理 |
| --- | --- | --- | --- |
| main | 96ddb95 | 主线 | 双方已整合代码的权威入口 |
| agent/sync-llm-workmem | 96ddb95 | 完全相同 | PR #1 已合并；没有独有提交，属于冗余旧同步分支 |
| feat/web-integration | 345acba | 落后 8，独有 0 | 所有提交已在 main；属于已整合旧功能分支 |
| feat/web-gateway | e99dd23 | 落后 5，独有 2 | 后端与前端未整合开发，需审查两条独有提交 |
| codex/lwm-collaboration-20261012 | af4a3a2 起 | 领先核心检查点及本文更新 | PR #2；临时整合载体，不能当成完整最新项目 |

gateway 独有提交：`2fc2111`（核心、交接、租约、vault、前端），`e99dd23`（Solana、存储、恢复）。提交标题是作者声明，不能替代测试与真实远端验收。
`feat/web-integration` 同时是 gateway 的祖先，不需要再单独合并。

## 尚未整合的本地代码

1. 根目录核心：memory_compiler、structured_candidates、queue_compaction 和三份测试。六份代码/测试与 PR #2 的 af4a3a2 内容逐字节一致；它们已上传协作分支，尚未进入 main。
2. 根目录前端：删除登录入口、App/导航/文案/配额 UI、package 与锁文件、新增前端测试。尚未上传。与 gateway 在 package、锁文件、App、配额 UI、文案、LoginView 六个已跟踪路径重叠。
3. 根目录备份/Web3：backup.py、test_backup.py、backupAdapter、web3/crypto、storage、solana 等未跟踪模块。尚未上传，存在实验性与安全缺口。当前 main 的调用端引用部分缺失文件，需以完整调用链修复，不能只加文件就声明完成。
4. 嵌套目录 `LLM-WorkMem-web-gateway/`：detached HEAD 2fc2111，33 个未提交变更，包含 gateway、认证删除、API、UI、依赖与测试。它早于远端 e99dd23，并且叠加本地修改；不能等同于远端 gateway 分支，也不能删除。
5. README、设计/分析文档、Logo、本机配置、生成物等另行审核。机器状态、凭据、个人记忆、缓存、嵌套仓库不进入代码发布集。

## 统一到 main 的顺序

1. 保全根目录与嵌套副本的未提交代码，制作完整文件清单。
2. 对齐 gateway 两个远端独有提交与嵌套副本修改，确认协作者实际工作基线。其机器上未推送的修改目前未知。
3. 把核心、后端、前端三批差异整合到现有 PR #2，逐文件处理重叠；不再增加长期主线。实验备份/Web3 必须明确标识，禁止模拟成功。
4. 统一 API、入口与依赖，完成干净检出安装、核心测试、网关契约和 Web 构建。只把有证据的能力标为已完成。
5. 通过后合入 main；同步本地工作基线。确认没有独有提交、没有活动工作依赖后，再清理旧分支。

## 当前已验证与未知

- PR #2 核心修改：28 个定向 Python 测试通过，Ruff 与差异检查通过；原本地文件保留。
- 目前没有一个已发布 Git 提交包含根目录全部修改、嵌套副本修改和协作者未推送代码。
- 远端只有 PR #2 开放；PR #1 已合并。协作者尚未推送的代码不能从 GitHub 推断。
- 本文整理分支关系，不代表已完成整合、部署、备份恢复或链上交易。
