# scix

`scix` creates a science-oriented workspace that works with both Codex CLI and
Claude Code.

## Table of Contents
- [What scix does](#what-scix-does)
- [Who this is for](#who-this-is-for)
- [Before you begin](#before-you-begin)
- [Quick start](#quick-start)
- [What `scix up` will do](#what-scix-up-will-do)
- [Activate the local Python environment](#activate-the-local-python-environment)
- [Install Codex CLI if needed](#install-codex-cli-if-needed)
- [Log into Codex](#log-into-codex)
- [Log into Claude](#log-into-claude)
- [Use VS Code](#use-vs-code)
- [Start Codex or Claude inside VS Code](#start-codex-or-claude-inside-vs-code)
- [Important folders](#important-folders)
- [Helpful commands](#helpful-commands)
- [Developers / Contributors](#developers--contributors)

## What scix does

`scix` sets up:

- a shared AI policy system for Codex and Claude
- a `repos/` folder for cloned reference repositories
- a `workspace/` folder for your own scripts, models, experiments, and notes
- generated `AGENTS.md`, `CLAUDE.md`, skills, hooks, and tool configs

`scix` does not create Python environments for you. You create `xenv/`
yourself, activate it, install packages into it, and then run `scix up`.

## Who this is for

This README assumes:

- you are new to AI tools
- you are new to the Terminal
- you are new to VS Code

## Before you begin

You need:

- a macOS or Linux machine
- a GitHub account
- a Python version `>= 3.9`
- Codex CLI installed if you want to use Codex
- Claude Code installed if you want to use Claude

If you need a newer Python, Python 3.11 is the recommended version.

If you are using macOS and have never opened the Terminal:

1. Press `Command + Space`.
2. Type `Terminal`.
3. Press `Return`.

## Quick start

This quick start is for a brand new working folder. If you cloned the `scix`
source repository, skip to [Developers / Contributors](#developers--contributors)
instead.

Create a brand new empty folder, then move into it:

```bash
mkdir my-scix-work
cd my-scix-work
```

Check your Python version:

```bash
python3 --version
```

Create and activate `xenv/`:

```bash
python3 -m venv xenv
source xenv/bin/activate
```

Upgrade pip and install `scix` plus the reference packages:

```bash
python -m pip install --upgrade pip
python -m pip install scix
python -m pip install pydisort pyharp kintera snapy paddle
```

Run the workspace setup command:

```bash
scix up
```

`scix` will ask you to confirm that:

- the current directory should become your `scix` workspace
- this directory is where you want to do your `scix` work

If the folder is not empty, `scix up` stops by default. A pre-existing `xenv/`
directory is fine.

If the short `scix` command does not work in this shell, make sure `xenv/` is
activated and run:

```bash
python -m scix up
```

## What `scix up` will do

It will:

1. create the `scix` workspace files
2. clone the five reference repositories into `repos/`
3. generate Codex and Claude config files

## Activate the local Python environment

Whenever you return to this workspace, activate the environment again:

```bash
source xenv/bin/activate
```

When it is active, Python and pip commands use the local environment inside
this workspace.

## If you use Codex

If `codex` is missing on Ubuntu or Debian, install it with:

```bash
sudo apt install npm
npm install -g @openai/codex
```

`sudo` means the command uses administrator permission. Your machine may ask for
your password.

Alternatively, you can follow the instructions from the Codex CLI setup guide: https://developers.openai.com/codex/cli/

Once installed, open a Terminal in your `scix` workspace and run:

```bash
codex login
```

If you are using an API key instead of the normal login flow:

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

If you are in an SSH terminal, first enable device code authorization in
ChatGPT Security Settings. Then use:

```bash
codex login --device-auth
```

Some Codex CLI versions use a flag-style login command instead of the
subcommand form. If `codex login` is rejected on your installed version, check
`codex --help` and use the login form shown there.

## If you use Claude

If `claude` is missing and you already have Node.js 18+ and npm, install
Claude Code CLI with:

```bash
npm install -g @anthropic-ai/claude-code
```

Alternative installation methods are documented in the official Claude Code CLI guide: https://code.claude.com/docs/en/quickstart

Once installed, open a Terminal in your `scix` workspace and run:

```bash
claude auth login
```

If you use a long-lived token flow:

```bash
claude setup-token
```

## If you use VS Code

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

From the VS Code terminal:

```bash
codex
```

or:

```bash
claude
```

If you prefer to work from the editor UI instead of the terminal, you can also
install these VS Code extensions and use them from the Extensions view or
editor sidebar:

- `Claude Code for VS Code` by Anthropic
- `Codex - OpenAI's coding agent` by OpenAI


## Important folders

- `repos/`: cloned reference repos such as `kintera` and `pydisort`
- `workspace/`: your own experiments, notes, notebooks, and rough work
- `xenv/`: your manually created local Python environment
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

## Developers / Contributors

If you want to work on `scix` itself, do not start from `pip install scix`.
Clone the source repository instead:

```bash
git clone https://github.com/zoeyzyhu/scix.git
cd scix
python3 --version
python3 -m venv xenv
source xenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
python -m pip install pydisort pyharp kintera snapy paddle
scix dev
```

`scix dev` is the contributor bootstrap for a cloned source repo. It
keeps the existing source files in place, creates any missing workspace files,
optionally clones missing reference repos, and regenerates the generated Codex
and Claude files. It does not create `xenv/` or install packages for you.

Before you change shared agent behavior, read
[`docs/AI_FOLDER_GUIDE.md`](docs/AI_FOLDER_GUIDE.md). That guide explains what
the repo-root `ai/` folder controls, how it maps to generated agent files,
which files are safe to edit, and the main reliability and safety risks.

Install Git hooks with:

```bash
xenv/bin/pre-commit install
```

To run all contributor checks locally:

```bash
xenv/bin/pre-commit run --all-files
pytest
python -m build
scix sync --check
```

When you change the AI canon, keep these rules in mind:

- edit the repo-root `ai/` files, not generated files under `.codex/`,
  `.claude/`, `.agents/`, or repo overlays
- run `scix sync` after each logical change; in the source repo it also refreshes
  `src/scix/assets/template_root/ai/` for packaged installs
- inspect both the generated agent diff and the packaged template diff before
  you commit
- implementation work now follows an explicit implementer -> tester -> reviewer
  workflow
- keep hooks portable and auditable, and never place secrets in prompt files or
  scripts
- prefer narrow prompt and routing changes over large rewrites

The contributor path is separate on purpose:

- end users should still create a fresh folder, create `xenv/`, install
  packages, and run `scix up`
- contributors should clone the repo, create `xenv/`, install `.[dev]`, and run
  `scix dev`
