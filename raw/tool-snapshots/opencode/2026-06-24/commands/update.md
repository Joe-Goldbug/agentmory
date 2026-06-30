---description: 更新项目依赖agent: build---

检查并更新项目依赖:

1. **检查过时依赖**
   !`[ -f package.json ] && npx npm-check-updates || echo "No package.json"`

2. **安全审计**
   !`[ -f package.json ] && npm audit || echo "No package.json"`

3. **建议更新**
   分析依赖版本和安全问题，提供更新建议。

注意: 不会自动执行更新操作，只提供建议。