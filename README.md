# scix

`scix` creates a science-oriented workspace that is ready for both Codex CLI and
Claude Code. You install `scix` once, run `scix up` inside a new empty folder,
and it builds the workspace for you.

## What scix does

`scix` sets up:

- a shared AI policy system for Codex and Claude
- a `repos/` folder for cloned reference repositories
- a `workspace/` folder for your own experiments and notes
- a local Python environment named `xenv/`
- generated `AGENTS.md`, `CLAUDE.md`, skills, hooks, and tool configs

## Who this is for

This README assumes:

- you are new to AI tools
- you are new to the Terminal
- you are new to VS Code

## Before you begin

You need:

- a macOS or Linux machine
- a GitHub account
- a PyPI-accessible Python install that can run `pip install scix`
- Codex CLI installed if you want to use Codex
- Claude Code installed if you want to use Claude

If you are using macOS and have never opened the Terminal:

1. Press `Command + Space`.
2. Type `Terminal`.
3. Press `Return`.

## Quick start

Create a brand new empty folder, then move into it:

```bash
mkdir my-scix-work
cd my-scix-work
```

Install `scix`:

```bash
pip install scix
```

Run the setup command:

```bash
scix up
```

`scix` will ask you to confirm that:

- the current directory should become your `scix` workspace
- this directory is where you want to do your `scix` work

If the folder is not empty, `scix up` stops by default. That is intentional.

## What `scix up` will do

It will:

1. create the `scix` workspace files
2. install `pyenv` if needed
3. install Python `3.11`
4. create a local environment named `xenv/`
5. install `scix` and the five science packages into `xenv/`
6. clone the five reference repositories into `repos/`
7. generate Codex and Claude config files

## Activate the local Python environment

After setup finishes, activate the environment with:

```bash
source xenv/bin/activate
```

When it is active, your Terminal prompt usually changes. From then on, Python
and pip commands use the local environment inside this workspace.

## Log into Codex

Open a Terminal in your `scix` workspace and run:

```bash
codex login
```

If you are using an API key instead of the normal login flow:

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

To check whether you are already logged in:

```bash
codex login status
```

## Log into Claude

Open a Terminal in your `scix` workspace and run:

```bash
claude auth login
```

If you use a long-lived token flow:

```bash
claude setup-token
```

To check whether you are already logged in:

```bash
claude auth status
```

## Use VS Code

If Visual Studio Code is installed, open it and choose:

1. `File`
2. `Open Folder...`
3. Select your `scix` workspace folder

Then open the built-in terminal in VS Code:

1. `Terminal`
2. `New Terminal`

Activate `xenv` there too:

```bash
source xenv/bin/activate
```

If the `code` command does not work in the Terminal, open VS Code and run:

1. `Command Palette`
2. Type `Shell Command: Install 'code' command in PATH`
3. Press `Return`

After that, you can open the current folder from Terminal with:

```bash
code .
```

## Start Codex or Claude inside VS Code

From the VS Code terminal:

```bash
codex
```

or:

```bash
claude
```

## Important folders

- `repos/`: cloned reference repos such as `kintera` and `pydisort`
- `workspace/`: your own experiments, notes, notebooks, and rough work
- `xenv/`: the local Python environment for this workspace
- `ai/`: the shared rules and templates that generate Codex and Claude files

## Helpful commands

Regenerate all Codex and Claude files:

```bash
scix sync
```

Check whether the workspace is healthy:

```bash
scix doctor
```

Clone any missing reference repositories again:

```bash
scix install-repos
```

## Notes for source-repo developers

This GitHub repository is the source of truth for the `scix` package. End users
normally do not clone it. They install from PyPI and run `scix up`.
