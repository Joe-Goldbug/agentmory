# Meta_Workflow: The Standard Operating Procedure (统一工作流)

> 这是全局唯一的标准执行链路，适用于所有 Mac IDE (Trae, Cursor, VSCode) 和 CLI (Claude Code, Terminal 等)。

## The 5-Step Loop (标准五步闭环)

1. **探索 (Explore)**
   - 限制范围：不要进行漫无目的的全盘搜索。
   - 工具：使用 `grep`, `search`, `find` 快速定位核心文件。
   - 输出：获取足够的上下文，了解当前项目状态。

2. **计划 (Plan)**
   - 深度推理：使用全英文（如 `<thinking>` 标签）进行逻辑拆解。
   - 输出：生成一个结构化的执行清单（Todo List）。对于复杂任务（>2个文件改动），必须先制定 Plan。

3. **执行 (Execute)**
   - 自动操作：修改代码、创建文件、安装依赖。
   - 规则：严格遵守项目现有代码风格和架构规范。

4. **验证 (Verify)** [⭐ 核心不可跳过的一步]
   - 强制动作：执行测试命令、启动本地服务或检查语法。
   - 规则：如果验证失败，自动回滚或修正，直至通过。绝对不能提交未经验证的代码。

5. **提交/记录 (Commit & Remember)**
   - 代码提交：如果测试通过，进行标准化的 Git Commit。
   - 记忆更新：将本次任务的关键上下文、踩过的坑更新至 `02_Global_Memory.md`。
