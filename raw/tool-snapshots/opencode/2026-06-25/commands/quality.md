---description: 分析代码复杂度和质量指标agent: plan---

执行代码质量分析:

1. **代码统计**
   !`find src -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) 2>/dev/null | xargs wc -l | tail -1`

2. **函数复杂度**
   !`[ -f .eslintrc.* ] && npx eslint "src/**/*.{ts,tsx}" --rule 'complexity: ["error", 10]' || echo "ESLint not available"`

3. **代码重复**
   !`npx jscpd src --min-lines 5 --reporters console 2>&1 || echo "jscpd not installed"`

4. **依赖关系**
   !`[ -f package.json ] && npx depcheck || echo "No package.json"`

生成代码质量报告和改进建议。