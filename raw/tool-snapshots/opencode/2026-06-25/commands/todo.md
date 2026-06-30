---description: 查找代码中的TODO和FIXMEagent: explore---

搜索代码中的待办事项:

!`grep -rn "TODO\|FIXME\|XXX\|HACK" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" src/ 2>/dev/null || echo "No TODOs found"`

总结并按优先级分类这些待办事项。