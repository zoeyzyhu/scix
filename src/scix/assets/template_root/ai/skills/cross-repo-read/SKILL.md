---
name: cross-repo-read
description: Read neighboring repositories before making a scoped change in the primary repo.
---

# Cross Repo Read

Use this skill when a task spans more than one repository.

## Workflow

1. Identify the primary repo to modify.
2. Identify the secondary repos to read.
3. Read tests and examples in each relevant repo.
4. Summarize interface assumptions before editing.

## Guardrails

- Avoid coordinated multi-repo edits unless the user explicitly requests them.
- Report mismatches between repos before broad refactors.
