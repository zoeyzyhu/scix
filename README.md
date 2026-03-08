# scix

`scix` creates a science-oriented workspace that is ready for both Codex CLI and
Claude Code. You install `scix` once, run `scix up` inside a new empty folder,
and it builds the workspace for you.

## What scix does

`scix` sets up:

- a shared AI policy system for Codex and Claude
- a `repos/` folder for cloned reference repositories
- a `workspace/` folder for your own scripts, models, experiments and notes
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

This quick start is for a brand new working folder. If you cloned the `scix`
source repository, skip to [Developers / Contributors](#developers--contributors)
instead.

Create a brand new empty folder, then move into it:

```bash
mkdir my-scix-work
cd my-scix-work
```

Install `scix`:

```bash
python3 -m pip install --user scix
```

Run the setup command:

```bash
python3 -m scix up
```

`scix` will ask you to confirm that:

- the current directory should become your `scix` workspace
- this directory is where you want to do your `scix` work

If the folder is not empty, `scix up` stops by default. That is intentional.

If the short `scix` command already works in your shell, `scix up` is the same
thing as `python3 -m scix up`.

## If `scix` says "command not found"

This usually means Python installed the `scix` command into your user scripts
directory, but that directory is not on your shell `PATH` yet.

Two safe fixes:

1. Keep using the module form:

```bash
python3 -m scix up
```

2. Or add the user scripts directory to your shell path on Ubuntu or Debian:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

After `scix up` runs, it also tries to add your user-level Python scripts
directory to your shell startup file automatically. Open a new terminal after
setup if the short `scix` command still does not appear right away.

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

## Install Codex CLI if needed

If `codex` is missing on Ubuntu or Debian, install it with:

```bash
sudo apt install npm
sudo npm install -g @openai/codex
```

`sudo` means the command uses administrator permission. Your machine may ask for
your password.

## Log into Codex

Open a Terminal in your `scix` workspace and run:

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

## Log into Claude

Open a Terminal in your `scix` workspace and run:

```bash
claude auth login
```

If you use a long-lived token flow:

```bash
claude setup-token
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

If the short `scix` command is still missing in your current shell, every
command above also works in module form:

```bash
python3 -m scix sync
python3 -m scix doctor
python3 -m scix install-repos
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
./scripts/dev-up.sh
```

`./scripts/dev-up.sh` is the contributor bootstrap for a cloned source repo. It
keeps the existing source files in place, creates any missing workspace files,
creates `xenv/`, installs `scix` in editable mode with developer dependencies,
installs the science packages, clones missing reference repos, installs Git
hooks, and regenerates the generated Codex and Claude files.

It also handles a fresh-clone case where the system Python does not have
project dependencies such as `PyYAML`. In that situation, `./scripts/dev-up.sh`
bootstraps `xenv/` first and then re-enters the normal contributor flow from
inside `xenv/`.

Before you change shared agent behavior, read
[`docs/AI_FOLDER_GUIDE.md`](/Users/zoey/Documents/Playground/docs/AI_FOLDER_GUIDE.md).
That guide explains what the repo-root `ai/` folder controls, how it maps to
generated agent files, which files are safe to edit, and the main reliability
and safety risks.

After that, activate the environment:

```bash
source xenv/bin/activate
```

If you want to install the Git hooks yourself again later, run:

```bash
xenv/bin/pre-commit install
```

`--skip-python` is intended for later reruns after `xenv/` already exists. Do
not use it for the first contributor bootstrap on a fresh clone.

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
- keep hooks portable and auditable, and never place secrets in prompt files or
  scripts
- prefer narrow prompt and routing changes over large rewrites

The contributor path is separate on purpose:

- end users should still create a fresh folder and run `python3 -m scix up`
- contributors should clone the repo and run `./scripts/dev-up.sh`
