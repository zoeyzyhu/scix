<!-- AUTO-GENERATED FILE. EDIT ai/policy/* OR ai/agents/roles.yaml INSTEAD. -->
# AGENTS.md

This file is generated for Codex.

## Workspace Purpose
This workspace contains multiple interdependent repositories. For every task,
identify the primary repo to modify, the reference repos to read, and the
cross-repo compatibility risks before making changes.

## Hard Rules
- Modify only the primary repo unless the task explicitly requires coordinated edits.
- Read tests, examples, and neighboring code before implementation.
- Do not duplicate source-of-truth logic across repos.
- Use `paddle` for examples, tutorials, and high-level API patterns.
- Summaries must mention which reference repos were consulted.

## Repo Routing
- `kintera` at `repos/kintera` owns: thermodynamics, eos, chemistry, thermal_state
  consult when: temperature calculations
  consult when: heat capacity work
  consult when: adiabats and state functions
  consult when: equilibrium chemistry
- `paddle` at `repos/paddle` owns: examples, tutorials, high_level_python_api, pedagogical_patterns
  consult when: user-facing examples
  consult when: tutorial and notebook design
  consult when: simple reference implementations
  consult when: high-level API ergonomics
- `pydisort` at `repos/pydisort` owns: disort, radiative_transfer_solver, quadrature, boundary_conditions
  consult when: DISORT numerics
  consult when: RT boundary handling
  consult when: solver benchmark behavior
- `pyharp` at `repos/pyharp` owns: rt_kernels, performance_rt, rt_infrastructure
  consult when: optimized radiative-transfer kernels
  consult when: performance-sensitive RT implementation
- `snapy` at `repos/snapy` owns: climate_model, orchestration, coupled_workflows
  consult when: model integration
  consult when: workflow composition
  consult when: high-level simulation logic

## Common Commands
- `pytest`: preferred default test entry point when a repo already uses pytest.
- `python -m pip install -e .`: preferred editable install pattern for local Python repos.
- `python -m build`: package build check for `scix`.
- When a repo has its own documented commands, prefer that repo's README or test config.

## Shared Skills
- `cross-repo-read`
- `disort`
- `paddle-examples`
- `repo-router`
- `thermodynamics`
- `tutorial-style`
