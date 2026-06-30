---description: 运行测试并分析失败agent: buildmodel: anthropic/claude-haiku-4-20250514---

运行完整的测试套件并生成覆盖率报告:

!`npm test -- --coverage 2>&1 || true`

分析失败的测试用例，提供修复建议。如果所有测试通过，总结测试结果和覆盖率情况。