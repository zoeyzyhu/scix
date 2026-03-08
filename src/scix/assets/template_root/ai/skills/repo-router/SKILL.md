---
name: repo-router
description: Decide which repo owns a concept and which sibling repos should only be consulted.
---

# Repo Router

Use this skill when you need to decide which repo owns a concept or should be
modified first.

## Workflow

1. Read `ai/policy/repos.yaml`.
2. Pick the primary repo that owns the requested behavior.
3. List reference repos that should be inspected before changes.
4. State any cross-repo compatibility risks.

## Rules

- Prefer the declared source-of-truth repo over copied logic in another repo.
- Use `paddle` for examples and tutorial style.
