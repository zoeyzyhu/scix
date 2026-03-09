- Modify only the primary repo unless the task explicitly requires coordinated edits.
- Read tests, examples, and neighboring code before implementation.
- Implementation work follows `implementer -> tester -> reviewer`.
- Add or update tests when a change affects behavior and automated coverage is feasible.
- Run the relevant test or validation command before finalizing.
- If tests fail, fix the issue and rerun before finalizing.
- If no automated test is feasible, say why and run the closest available validation step.
- Do not duplicate source-of-truth logic across repos.
- Use `paddle` for examples, tutorials, and high-level API patterns.
- If a developer types `/learn`, hand off to `student`. The `student` workflow
  summarizes the durable lesson from the latest conversation, inspects
  `ai/skills/` for an appropriate skill, proposes the skill name/location and
  lesson summary, waits for confirmation before editing, then updates
  `ai/skills/<skill-name>/SKILL.md` and runs `scix sync`.
- Summaries must mention which reference repos were consulted.
- Summaries for implementation work must include the exact validation command and result.
