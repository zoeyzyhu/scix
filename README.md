<h4 align="center">
  <img src="https://raw.githubusercontent.com/zoeyzyhu/scix/main/docs/img/scix_image.png" alt="SciX" width="360" style="display: block; margin: 0 auto">
</h4>

<p align="center">
  <i>Planetary atmosphere research, organized for fast science and reliable AI collaboration.</i>
</p>

<p align="center">
  <a href="https://github.com/zoeyzyhu/scix/actions/workflows/ci.yml">
    <img alt="GitHub Workflow Status"
      src="https://img.shields.io/github/actions/workflow/status/zoeyzyhu/scix/ci.yml?branch=main&style=flat-square&logo=github">
  </a>
  <a href="https://github.com/zoeyzyhu/scix/releases">
    <img alt="GitHub release"
      src="https://img.shields.io/github/v/release/zoeyzyhu/scix?style=flat-square&logo=github">
  </a>
  <a href="https://github.com/zoeyzyhu/scix/issues">
    <img alt="GitHub issues"
      src="https://img.shields.io/github/issues/zoeyzyhu/scix?style=flat-square&logo=git">
  </a>
  <a href="https://github.com/zoeyzyhu/scix/blob/main/pyproject.toml">
    <img alt="macOS and Linux"
      src="https://img.shields.io/badge/OS-macOS%20%7C%20Linux-F28C28?style=flat-square">
  </a>
</p>

<p align="center">
  <strong>scix</strong> builds a reproducible dual-agent workspace for planetary-atmosphere research, so scientists and developers can focus on science instead of setup, and collaborate with AI agents that understand the shared context and tools of the stack.
</p>

<p align="center">
  <a href="#introduction">Introduction</a> &nbsp;&bull;&nbsp;
  <a href="#agent-cli-setup">Agent CLI Setup</a> &nbsp;&bull;&nbsp;
  <a href="#quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
  <a href="#workflow">Workflow</a> &nbsp;&bull;&nbsp;
  <a href="#contributing">Contributing</a>
</p>

<br/>

## Introduction

`scix` is the workspace layer for the planetary-atmosphere modeling stack. It assembles domain libraries into one working environment with shared AI policies and skills, so you have both the tools and the agent context to do your science faster, and collaborate with AI agents more effectively.

It is designed to work alongside:

- [pydisort](https://github.com/zoeyzyhu/pydisort) for DISORT-based radiative transfer workflows
- [kintera](https://github.com/chengcli/kintera) for thermodynamics, equation of state, and chemistry
- [pyharp](https://github.com/chengcli/pyharp) for radiation infrastructure and opacity handling
- [snapy](https://github.com/chengcli/snapy) for atmospheric dynamics and coupled workflow composition
- [paddle](https://github.com/elijah-mullens/paddle) for higher-level examples, tutorials, and exploratory modeling patterns

With `scix`, a fresh workspace gives you:

- a `repos/` directory for the reference scientific packages
- a `workspace/` directory for your own scripts, models, and outputs
- generated `AGENTS.md`, `CLAUDE.md`, skills, hooks, and editor/tool configs
- one setup path for both research users (`scix up`) and contributors (`scix dev`)

You can also turn `/workspace` or any folder in `repos/` into a git managed directory:
- just `cd` into the folder and run `git init`
- `scix` will ignore these directories in its own git version control so it does not interfere with `scix`'s workspace management

## Requirements

- macOS or Linux
- Python `>= 3.9`

## Quick Start

For a new research workspace:

```bash
mkdir my-scix-work
cd my-scix-work
python3 -m venv xenv
source xenv/bin/activate
pip install --upgrade pip
pip install scix
scix up
```

If the short `scix` command is not on `PATH` in the current shell yet, run:

```bash
python -m scix up
```

For contributor setup, see the [Contributing](#contributing) section below.

`scix up` will:

1. create the workspace files and folders
2. clone the reference repositories into `repos/`
3. generate Codex and Claude config, policy, and skills
4. try to install missing `nvm`, user-local Node.js/npm, Codex CLI, and Claude
   Code

The commands you will use most often are:

| Command | Use it when |
| --- | --- |
| `scix --help` | You want to see the list of available commands and options. |
| `scix up` | You are creating or refreshing a research workspace in the current directory. |
| `scix doctor` | You want a quick health check on the current workspace. |
| `scix sync` | You changed the AI canon and need to regenerate Codex/Claude outputs. |
| `scix install-repos` | One or more reference repositories are missing and need to be cloned again. |
| `scix dev` | You are working on the `scix` source repository itself. |

Whenever you return to the workspace, reactivate the local environment:

```bash
source xenv/bin/activate
```

## Agent CLI Setup

`scix up` and `scix dev` try to install missing `nvm`, user-local Node.js/npm, Codex CLI, and Claude Code automatically.

If that automatic step fails, run this fallback sequence exactly:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
nvm alias default lts/*
npm install -g @openai/codex
npm install -g @anthropic-ai/claude-code
```

If `codex` or `claude` is still unavailable, start a new shell or load your shell profile with:

```bash
source ~/.bashrc
# or if you use zsh (Mac default):
source ~/.zshrc
```

Official references:

- [Codex CLI Setup](https://developers.openai.com/codex/cli/)
- [Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)

### Authenticate Codex

```bash
codex login
```

Alternative auth flows:

```bash
codex login --device-auth
printenv OPENAI_API_KEY | codex login --with-api-key
```

If your installed Codex CLI uses a different login syntax, check:

```bash
codex --help
```

### Authenticate Claude

```bash
claude auth login
```

If you use a token-based flow:

```bash
claude setup-token
```

## Workflow

### Terminal Workflow

From the workspace root:

```bash
source xenv/bin/activate
codex
```

or:

```bash
source xenv/bin/activate
claude
```

### Workspace Layout

- `repos/`: cloned reference repositories such as `pydisort`, `kintera`, `pyharp`, `snapy`, and `paddle`
- `workspace/`: your own analyses, experiments, prototypes, and notes
- `xenv/`: your manually created local Python environment
- `ai/`: the shared AI canon that generates Codex and Claude files

## Contributing

If you are developing `scix` itself, clone the source repository instead of starting from `pip install scix`:

```bash
git clone https://github.com/zoeyzyhu/scix.git
cd scix
python3 -m venv xenv
source xenv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
scix dev
```

`scix dev` bootstraps a contributor checkout in place. It keeps the existing source tree, creates any missing workspace files, optionally clones missing reference repositories, regenerates generated Codex and Claude files, and tries to install missing agent CLIs if needed.

Before changing shared agent behavior, read [`docs/AI_FOLDER_GUIDE.md`](docs/AI_FOLDER_GUIDE.md). That guide explains whatthe repo-root `ai/` folder controls, how it maps to generated agent files, and which files are safe to edit.

Install contributor hooks with:

```bash
pre-commit install
```

Run the main contributor checks with:

```bash
pre-commit run --all-files
pytest
python -m build
scix sync --check
```

When you change the AI canon:

- edit the repo-root `ai/` files, not generated files under `.codex/`, `.claude/`, `.agents/`, or repo overlays
- run `scix sync` after each logical change so generated files and the packaged template stay aligned
- inspect both the generated agent diff and the template diff before you commit
- keep hooks portable and auditable, and never place secrets in prompts or scripts
- follow the `implementer -> tester -> reviewer` workflow
