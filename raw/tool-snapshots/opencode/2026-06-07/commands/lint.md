---description: 检查代码格式和lint问题agent: buildmodel: anthropic/claude-haiku-4-20250514---

执行代码质量检查:

1. **格式检查**
   !`[ -f .prettierrc ] && npx prettier --check "src/**/*.{ts,tsx,js,jsx}" || echo "Prettier not configured"`

2. **Lint检查**
   !`[ -f .eslintrc.* ] && npx eslint "src/**/*.{ts,tsx,js,jsx}" || echo "ESLint not configured"`

3. **类型检查**
   !`[ -f tsconfig.json ] && npx tsc --noEmit || echo "TypeScript not configured"`

总结发现的问题并提供修复命令。