<!-- AUTO-GENERATED FILE. EDIT ai/policy/* OR ai/agents/roles.yaml INSTEAD. -->
# Repo Policy: pydisort

This file is generated for Claude.

## This Repo Owns
- disort
- radiative_transfer_solver
- quadrature
- boundary_conditions

## Inspect This Repo First When
- DISORT numerics
- RT boundary handling
- solver benchmark behavior

## Notes
- Treat pydisort as the source of truth for DISORT semantics.

## Guardrails
- Modify this repo only when it is the primary repo for the task.
- Read neighboring tests and examples before making changes.
- For behavior changes, add or update tests when feasible, run the relevant validation command, and explain if no automated test was possible.
- Summaries must include the exact validation command and result.
- Report cross-repo compatibility risks in your summary.
