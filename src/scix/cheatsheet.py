"""Curated workflow cheat-sheet content shared by the CLI and docs."""

from __future__ import annotations

import shutil
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowSet:
    title: str
    note: str
    commands: tuple[str, ...]


WORKFLOW_SETS: tuple[WorkflowSet, ...] = (
    WorkflowSet(
        title="scix CLI help",
        note="Use this command to see available scix commands and options.",
        commands=("scix --help",),
    ),
    WorkflowSet(
        title="Start a new research workspace",
        note="Use this in a fresh working directory when you want a new scix workspace.",
        commands=(
            "mkdir my-scix-work",
            "cd my-scix-work",
            "python3 -m venv xenv",
            "source xenv/bin/activate",
            "pip install --upgrade pip",
            "pip install scix paddle",
            "scix up",
        ),
    ),
    WorkflowSet(
        title="Contributor setup for the scix repo",
        note="Use this when you are developing scix itself from a source checkout.",
        commands=(
            "git clone https://github.com/zoeyzyhu/scix.git",
            "cd scix",
            "python3 -m venv xenv",
            "source xenv/bin/activate",
            "pip install --upgrade pip",
            "pip install -e .[dev]",
            "scix dev",
        ),
    ),
    WorkflowSet(
        title="Agent CLI fallback setup",
        note="Use this if scix could not finish installing nvm, Codex CLI, or Claude Code.",
        commands=(
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash",
            'export NVM_DIR="$HOME/.nvm"',
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
            "nvm install --lts",
            "nvm use --lts",
            "nvm alias default lts/*",
            "npm install -g @openai/codex",
            "npm install -g @anthropic-ai/claude-code",
        ),
    ),
    WorkflowSet(
        title="Authenticate Codex",
        note="Use ONE of these commands when Codex CLI is installed but not logged in yet.",
        commands=(
            "codex login",
            "codex login --device-auth",
            "printenv OPENAI_API_KEY | codex login --with-api-key",
            "codex --help",
        ),
    ),
    WorkflowSet(
        title="Authenticate Claude",
        note="Use ONE of these commands when Claude Code is installed but not authenticated yet.",
        commands=(
            "claude auth login",
            "claude setup-token",
        ),
    ),
    WorkflowSet(
        title="Terminal workflow",
        note=(
            "Use ONE of these from the workspace root to reactivate the environment "
            "and start an agent session."
        ),
        commands=(
            "source xenv/bin/activate",
            "codex",
            "",
            "source xenv/bin/activate",
            "claude",
        ),
    ),
    WorkflowSet(
        title="Contributor workflow",
        note=(
            "Use these after setup and before pushing code changes to run pre-commit hooks, "
            "tests, and sync checks."
        ),
        commands=("pre-commit run --all-files", "pytest", "scix sync --check", "scix sync"),
    ),
)


def render_cheat_sheet_text() -> str:
    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10  # leave margin

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: tuple[str, ...]) -> list[str]:
        padded_cmds = [f"  {command}  " for command in cmds]
        box_w = min(max(len(command) for command in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{command.ljust(box_w)}{RESET}│" for command in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    lines = []
    for index, workflow in enumerate(WORKFLOW_SETS):
        lines.append(f"{BOLD}{workflow.title}{RESET}")
        lines.extend(wrap(workflow.note, indent=2))
        lines.append("")
        lines.extend(command_box(workflow.commands))
        if index != len(WORKFLOW_SETS) - 1:
            lines.append("")
            lines.append("")
    return "\n".join(lines) + "\n"


def render_cheat_sheet_markdown() -> str:
    lines = ["<!-- BEGIN scix cheat sheet -->"]
    for workflow in WORKFLOW_SETS:
        lines.extend(
            [
                f"### {workflow.title}",
                "",
                workflow.note,
                "",
                "```bash",
                *workflow.commands,
                "```",
                "",
            ]
        )
    lines.append("<!-- END scix cheat sheet -->")
    return "\n".join(lines)
