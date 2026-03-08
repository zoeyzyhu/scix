<!-- AUTO-GENERATED FILE. EDIT ai/policy/* OR ai/agents/roles.yaml INSTEAD. -->
# Repo Policy: paddle

This file is generated for Codex.

## This Repo Owns
- examples
- tutorials
- high_level_python_api
- pedagogical_patterns

## Inspect This Repo First When
- user-facing examples
- tutorial and notebook design
- simple reference implementations
- high-level API ergonomics

## Notes
- Use paddle for examples and tutorial style, not as the low-level numerical source of truth.

## Guardrails
- Modify this repo only when it is the primary repo for the task.
- Read neighboring tests and examples before making changes.
- For behavior changes, add or update tests when feasible, run the relevant validation command, and explain if no automated test was possible.
- Summaries must include the exact validation command and result.
- Report cross-repo compatibility risks in your summary.
