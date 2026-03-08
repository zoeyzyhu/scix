# scix Workspace

This folder was created by `scix`.

It is a working directory for science and engineering work that can be used
with both Codex CLI and Claude Code.

## First steps

Activate the local environment:

```bash
source xenv/bin/activate
```

If the short `scix` command is missing in this shell, open a new terminal or
run your shell startup file, then try again:

```bash
source ~/.bashrc
```

or:

```bash
source ~/.zshrc
```

All `scix` commands also work in module form:

```bash
python3 -m scix sync
python3 -m scix doctor
python3 -m scix install-repos
```

## Codex

If `codex` is missing on Ubuntu or Debian, install it with:

```bash
sudo apt install npm
sudo npm install -g @openai/codex
```

Then log in:

```bash
codex login
```

If you are in an SSH terminal, first enable device code authorization in
ChatGPT Security Settings. Then use:

```bash
codex login --device-auth
```

If your installed Codex version expects a flag-style login command instead of
`codex login`, check `codex --help` and use the login form shown there.

## Claude

If `claude` is installed, log in with:

```bash
claude auth login
```

Or use the token flow:

```bash
claude setup-token
```

## Regenerate tool files

If you change anything under `ai/`, regenerate the tool files with:

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
