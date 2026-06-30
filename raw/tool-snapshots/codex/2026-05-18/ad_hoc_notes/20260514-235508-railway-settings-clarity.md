# Memory update request

User要求：部署指导必须明确区分“哪个服务、哪个页面、哪个字段”。

固定答复模板（Railway）：
1) 先写服务名：`@ather/api` 或 `web`
2) 再写位置：`Settings` 或 `Variables`
3) 再写字段名：`Root Directory` / `Build Command` / `Start Command` / `Port`
4) 禁止混写，必须逐项对应。

本次明确结论：
- `Start Command` 与 `Root Directory` 的组合设置在 `@ather/api -> Settings`。
- 不是 `web`。
- 不是 `Variables`。
