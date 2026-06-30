---
inclusion: always
---

# AI 产品与代码迭代方法论

> 适用于新产品、新功能、产品方向调整、重大用户流程变更、超出小修复的投入。
> 不强制用于：明确 Bug 修复、小 UI 调整、已知技术重构、依赖/配置修复、纯测试/验证工作。

---

## 一、人机协作模型

**人决定**：目标、边界、优先级、验收标准

**AI 帮助**：
- 验证假设
- 拆解工作
- 执行有界任务
- 测试和验证结果
- 总结状态
- 暴露风险和下一步行动

一次只做一个明确任务。每个任务完成后更新：进度、风险、决策、下一步。

---

## 二、四阶段迭代工作流

### Phase 1: Idea — 证明问题真实

在开始任何新产品/功能/重大改动前回答：

1. 谁有这个问题？
2. 多频繁发生？
3. 多痛苦？
4. 用户现在怎么解决？
5. 为什么现有方案不够好？

默认角色：**怀疑论产品顾问**。不默认同意，挑战弱假设，识别伪需求，对比竞品和替代品，定义最小验证行动。

Reusable Prompt:

```text
You are now acting as a skeptical product advisor. Do not agree with me by default.

My idea is: [product/feature]
Target users are: [users]

Find:
1. The 5 most likely reasons this idea may not work
2. Which parts may be fake demand
3. Which competitors or substitutes already solve this
4. The 3 key assumptions I must validate first
5. The smallest validation action, without recommending code first
```

### Phase 2: MVP — 最小核心循环

目标：让真实用户完成一个核心动作。

实施前定义：
```text
Must build in this version:
- [core feature 1]
- [core feature 2]

Explicitly not building in this version:
- [future feature]
- [distracting feature]
```

**Feature admission rule**: 只有当至少 X 个真实用户明确说"没这个功能完成不了核心价值"时才加功能。

**工程规则**: 不一次建大系统。拆成小改动，每个改动有明确目的、有限范围、有验证步骤。

### Phase 3: Launch — 证明稳定使用

上线 ≠ "能访问了"。需要跟踪：

| 指标 | 含义 |
|------|------|
| Activation | 用户是否完成首次核心动作 |
| Retention D7 | 7 天后是否回来 |
| Retention D30 | 30 天后是否回来 |
| Conversion | 是否付费/提交信息/邀请/完成目标动作 |
| Feedback | 用户卡在哪里 |
| Stability | 错误率、加载速度、登录、部署健康 |

Reusable Prompt:

```text
Please design first-version launch metrics for this product.

Product: [description]
Core user action: [most important user step]

Give me:
1. Activation metric
2. 7-day retention metric
3. 30-day retention metric
4. Which numbers may be vanity metrics
5. Which numbers I should review every week
6. If the numbers are bad, whether I should first inspect product, positioning, or channel
```

### Phase 4: Scale — 判断变规则

把重复判断系统化：

- **产品规则**：做什么、不做什么
- **技术规则**：代码怎么改、怎么测、怎么部署
- **运营规则**：反馈怎么收集、问题怎么排序、下版本怎么定优先级

---

## 三、Standing Rules（项目级检查清单）

每个项目都应维护：

1. 项目简报：目标用户、核心问题、产品边界、第一版范围
2. 改代码前：说明这个任务解决什么、不解决什么
3. 写代码前：读相关文件、定位根因、再动手
4. 只改必须改的，不碰无关代码
5. 每次代码改动后：跑测试/构建/静态检查/明确的手动验证
6. 每个功能问：属于核心循环还是锦上添花？
7. 每周回顾：完成的工作、阻塞、风险、指标、需要人工决策的点
8. 上线前：安全/环境/部署/认证/数据/可靠性检查，不只依赖"本地能跑"

---

## 四、协调分工模型

| 角色 | 职责 |
|------|------|
| Coordinator（人） | 设定目标、边界、优先级、验收标准 |
| Session（上下文） | 承载决策、当前状态、风险、未解决问题 |
| Remote Control（AI） | 执行明确的、有界的、可验证的任务 |
