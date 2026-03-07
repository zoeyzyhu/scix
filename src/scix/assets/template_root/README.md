# scix Workspace

This folder was created by `scix`.

It is a working directory for science and engineering work that can be used
with both Codex CLI and Claude Code.

## First steps

1. Activate the local environment:

```bash
source xenv/bin/activate
```

2. Log into Codex if needed:

```bash
codex login
```

3. Log into Claude if needed:

```bash
claude auth login
```

4. Regenerate the tool files if you change anything under `ai/`:

```bash
scix sync
```

## Key folders

- `ai/`: the canonical rules, repo map, skills, hooks, and templates
- `repos/`: cloned reference repositories
- `workspace/`: your own notes, notebooks, and rough work
- `xenv/`: the local Python environment for this workspace

## Open this folder in VS Code

If VS Code is installed:

```bash
code .
```

If that command is missing, open VS Code and run the Command Palette command:

`Shell Command: Install 'code' command in PATH`
