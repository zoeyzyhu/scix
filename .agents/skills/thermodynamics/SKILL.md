---
name: thermodynamics
description: Route thermodynamics and EOS work through the kintera source-of-truth repo.
---

# Thermodynamics

Use this skill when a task involves thermodynamics, EOS, chemistry kernels, or
thermal-state calculations.

## Routing

- Inspect `repos/kintera` first.
- Use repo tests and validation cases before changing formulas.

## Guardrails

- Do not reimplement thermodynamic logic outside the source-of-truth repo unless
  the user explicitly requests duplication.
