# Maintaining `/ai`

This document is for contributors who change the shared agent behavior in the `scix` source repository.

## What `/ai` is

The repo-root `ai/` directory is the canonical source for shared agent behavior. It defines how Codex and Claude should reason about this workspace, route tasks across repos, load reusable skills, and apply shell hooks.

In practice, an "AI agent" in this repo is not just a model name. It is the combination of:

- prompt and policy text
- tool access and tool restrictions
- repo-routing rules
- reusable skills
- subagent or role definitions
- hook scripts that run before or after tool actions
- generated tool-specific wrapper files

Changing `ai/` changes behavior, not just documentation.

## The mechanisms in `scix`

The main layers are:

- `ai/policy/*.md`
  - Shared workspace purpose, rules, and common command guidance.
  - These feed the generated root `AGENTS.md` and `CLAUDE.md`.
- `ai/policy/repos.yaml`
  - The repo map.
  - This tells agents which repo owns which domain, when to inspect a repo, and which package or clone URL goes with it.
- `ai/agents/roles.yaml`
  - Canonical role definitions.
  - These generate `.codex/agents/*.toml` and `.claude/agents/*.md`.
  - This includes the `implementer`, `tester`, and `reviewer` collaboration flow for implementation work, plus specialized roles such as `student` for lesson capture.
- `ai/skills/*/SKILL.md`
  - Reusable local instructions for focused workflows.
  - These are mirrored into `.agents/skills/` and `.claude/skills/`.
- `ai/hooks/*.sh`
  - Executable shell hooks.
  - These are called by tool integrations such as Claude settings.
- `ai/generated/repos/*`
  - Generated repo-local overlays.
  - These become `AGENTS.md` and `CLAUDE.md` inside cloned repos when present.

The generator lives in `src/scix/generator.py`. `scix sync` is the command that turns the canonical sources into generated files.

## The packaging wrinkle

There are two mirrored sets of workspace-facing inputs in the source tree:

- repo-root `ai/`
- repo-root `README.md` and shipped `docs/` files
- `src/scix/assets/template_root/ai/`
- `src/scix/assets/template_root/README.md` and shipped `docs/` files

The repo-root copy is what contributors work against locally. The packaged template copy is what end users get when they run `pip install scix` and then `scix up`.

When you run `scix sync` from the source repo, it mirrors the editable inputs from repo root into `src/scix/assets/template_root/` automatically. That includes the canonical `ai/` tree plus the curated workspace docs that ship with new workspaces. This keeps packaged installs aligned with the source tree without manual copying.

The exception is generated output under `ai/generated/repos/*`. Fresh workspaces do not need those files baked into the package because `scix sync` recreates them.

There is a regression test for this on purpose.

## Safe change workflow

When you want to change agent behavior:

1. Decide which layer you actually need to change.
   - Routing issue: edit `ai/policy/repos.yaml`.
   - Shared instruction issue: edit `ai/policy/*.md`.
   - Specialized workflow issue: edit `ai/skills/*/SKILL.md`.
   - Tool-role issue: edit `ai/agents/roles.yaml`.
   - Runtime shell behavior issue: edit `ai/hooks/*.sh`.
2. Edit the repo-root `ai/` files first.
3. Regenerate generated files and refresh the packaged AI template:

```bash
scix sync
```

4. Inspect the diff. In a source checkout, you should usually see both:

- generated agent file updates
- `src/scix/assets/template_root/` updates for mirrored `ai/`, `README.md`, and shipped docs

5. Run contributor checks:

```bash
pre-commit run --all-files
pytest
python -m build
scix sync --check
```

6. Sanity-check the actual agent behavior if the change is behavioral, not just structural.

Implementation changes should also preserve the expected agent handoff:

- `implementer` makes the change
- `tester` adds or updates tests when feasible and runs the relevant command
- `reviewer` checks correctness, regression risk, and whether testing evidence is present

For lesson capture, the expected flow is:

- the user starts a message with `203 /learn` in the main conversation
- the main agent routes that request to `student`
- `student` proposes the lesson title, skill folder, and summary first
- only after developer confirmation does `student` edit `ai/skills/*/SKILL.md` and run `scix sync`

`/learn` by itself is not reliable because some clients reject unknown slash commands before the agent sees them. Use the literal prefix `203 /learn` instead. It only activates the workflow when it appears at the start of the message; quoted or explanatory mentions should not trigger it.

## What not to edit directly

Do not hand-edit generated files unless you are debugging the generator:

- `AGENTS.md`
- `CLAUDE.md`
- `.codex/config.toml`
- `.codex/agents/*`
- `.claude/settings.json`
- `.claude/agents/*`
- `.agents/skills/*`
- `.claude/skills/*`
- `ai/generated/repos/*`
- repo-local overlay files inside `repos/*`

If you change a generated file directly, `scix sync` will overwrite it.

## Important cautions

### 1. Prompt changes have code-like blast radius

An instruction tweak can redirect edits, change tool usage, or make the agent too aggressive. Treat prompt and policy edits with the same care as code.

### 2. Skills must stay structurally valid

Codex expects `SKILL.md` files to begin with YAML frontmatter delimited by `---`. If that is missing or malformed, the skill will silently stop loading in practice except for runtime warnings.

### 3. Hooks are executable code

Anything under `ai/hooks/` can block commands or mutate behavior at runtime. Keep hooks:

- portable across macOS and Linux
- small and easy to audit
- deterministic and idempotent
- explicit about failures

Avoid hidden network calls, interactive prompts, or machine-specific paths.

### 4. Repo routing errors can damage the wrong repo

Changes in `repos.yaml` affect which repo the agent treats as authoritative. Keep `owns` and `consult_when` precise. Ambiguous routing is one of the easiest ways to cause cross-repo mistakes.

### 5. Never put secrets into prompts, hooks, or examples

Do not hardcode tokens, credentials, internal endpoints, or private paths in any `ai/` content. Remember that this material gets copied into generated files and may end up in user workspaces.

### 6. Keep tool-specific behavior intentional

Codex and Claude do not read exactly the same files. `scix` smooths over that with generated wrappers, but the tools still differ. If a change relies on a tool-specific behavior, document that assumption in the PR.

### 7. Prefer small, testable edits

Large prompt rewrites are hard to review. Prefer narrow changes with a clear expected behavior change and a short rationale.

## Review checklist for `/ai` changes

Before merging, check:

- Did I edit the right layer?
- Did I run `scix sync` after editing `ai/`?
- Did `scix sync` update `src/scix/assets/template_root/ai/` the way I expected?
- Did I inspect the generated diff instead of editing generated files by hand?
- Did I run `xenv/bin/pre-commit run --all-files`, `pytest`, and `python -m build`?
- If behavior changed, did I manually verify the change with Codex or Claude?

## Additional contributor notes

- If `pre-commit` rewrites generated files and `scix sync --check` then fails, the generator likely needs to be updated to emit the normalized output.
- If a change is intended only for source-repo contributors and not for packaged end users, document that explicitly in the PR and explain why the
  packaged template should remain unchanged.
- When in doubt, prefer clearer and shorter instructions over broader and more "powerful" prompts. Over-specification often makes agents less reliable, not more.
