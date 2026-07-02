---
title: "Debug No-Guess: 写代码前必须 curl/ssh 验证线上真实状态"
type: insight
tags: [insight, debug-failure, workflow, no-guess, truth-first]
sources: ["project:iDream-2026-07-02-waterfall"]
updated: 2026-07-02
---

# Debug No-Guess Rule

## 摘要
生产环境 debug 时，**不允许**只读本地镜像就把根因方案写完。
每条关键事实（端点、文件、配置、权限、流量路由）在动代码前**先 curl/ssh 验证**。

## 案例
**iDream 瀑布流 bug**（2026-07-02）：用户报告 PC 用户主页和 /explore 瀑布流空。

错误流程（约 90 分钟）：
1. 读 8 个本地代码文件，把 `admin/api/controllers/` 没有 `actionExplore` 当成线上 bug。
2. 写完整套"方案 A：补三个 controller action + 适配 PC 前端 + 改 endpoint 路径"。
3. 才 ssh 上去测试，发现：
   - `api.idream.fans` 的 nginx root 是 `admin/frontend/web/`（**frontend 命名空间**），不是 `admin/api/web/`。
   - `FeedController::actionExplore` 在 frontend 里**存在**，返回的是 JSON 401 而非 404。
   - 同 token 在 `mapi.idream.fans/users/get-user-home`（api 命名空间）能拿到完整瀑布流数据。
4. 真实根因是 frontend `UserController::init()` 第 45-53 行多一步 DB 校验，删 9 行就修好。

正确流程（应该 15 分钟内完成）：
1. 先 curl 4 个端点（用户报告里的 URL）拿到线上真实响应。
2. 看 nginx 域名 → root 映射，确认走的是 frontend 还是 api。
3. 对比同一个 token 在 frontend 和 api 的响应差异。
4. 看到 frontend 多一步 `Users::findOne(...token...)`，直接定位。
5. 改 9 行，验证瀑布流有数据。

## 规则

### Hard Rule
- 任何"线上是否存在 X" / "线上走的是 Y 路径" / "线上配置是 Z"的判断 → **必须先 curl/ssh 取真实证据**才能进方案。
- 推断可以写进 thinking 辅助推理，但**不能进入方案结论**。

### Verify-Before-Design
设计阶段只输出"证据清单 + 假设链"。
- 拿到 curl 真实响应、日志片段、nginx 配置后**再动笔写修复方案**。
- 如果验证后发现假设错了，**废弃方案**重起，**不在旧方案上打补丁**。

### Minimal Diff
- 修一个 bug 只改必须的代码。
- 多文件改动前先回答："这些文件是不是同一个根因？"——不是就别一起改。
- 不为"代码美观"或"防止未来复发"做大改。

### Verification Is Work
- 每改一个文件 = 给出对应的验证命令。
- 验证通过才能标记 todo 完成；拿不到可信证据时，明说"未验证"。

## 不要做的事

- 不要把"我推断这里有问题"当成"这里有问题"写进方案。
- 不要基于本地镜像就开始"补 action / 改 endpoint / 重写配置"。
- 不要在同一段调试里同一个 expect/curl 命令连续失败 2 次还不换思路。
- 不要在方案顶部用流畅的话掩盖"我没验证"。

## 相关项目

- iDream 瀑布流 bug：见 history 段（管理员 Ethan）
- 其他 debug 失败模式待补充

## See Also

- [[workflow-policy]]
- [[memory-policy]]
- [[architecture-policy]]
