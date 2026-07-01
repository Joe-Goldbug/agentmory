---
title: Memory Governance
type: concept
tags: [concept, memory, governance, workflow]
sources: []
updated: 2026-07-01
---

# Memory Governance

This page defines the working memory lifecycle for the llm-wiki-first setup.

## Memory Layers

- **Working**: the current task and the active thread.
- **Session**: decisions and context that should survive the current conversation.
- **Project**: reusable project-level facts, constraints, and playbooks.
- **Global**: stable operating rules, preferences, and cross-project principles.

## Promotion Rules

- Promote only durable working style and workflow rules.
- Keep project facts and ephemeral fixes out of the global layer.
- Prefer explicit links and dated snapshots over implicit memory.
- Re-run harvest before promoting anything into durable pages.

## Tool Sources

- [[codex]]
- [[claude-code]]
- [[cursor]]
- [[opencode]]
- [[trae-solo]]
- [[github-copilot]]
- [[vscode]]
- [[kiro]]
- [[antigravity]]
- [[minimax]]
- [[shell]]

## See Also

- [[purpose]]
- [[overview]]
- [[workflow-policy]]
- [[memory-policy]]
