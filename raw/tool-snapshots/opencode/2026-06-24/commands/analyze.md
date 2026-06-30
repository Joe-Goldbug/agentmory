---description: 分析项目结构和技术栈agent: explore---

分析当前项目:

1. **项目结构**
   !`find . -type f -name "*.json" -o -name "*.yaml" -o -name "*.yml" | head -20`
   
2. **技术栈识别**
   !`[ -f package.json ] && cat package.json || echo "No package.json"`
   
3. **依赖分析**
   !`[ -f package.json ] && npm list --depth=0 2>&1 | head -30 || echo "No npm dependencies"`

总结项目的技术栈、主要功能和架构特点。