"""Bootstrap and doctor helpers for scix."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

from .constants import APP_NAME, ROOT_MARKER, TRIVIAL_HIDDEN_NAMES
from .exceptions import ScixError
from .scaffold import copy_template_paths, copy_template_root

DEVELOPER_TEMPLATE_PATHS = [
    ROOT_MARKER,
    ".agents/.gitkeep",
    ".claude/.gitkeep",
    ".codex/.gitkeep",
    Path("repos/.gitkeep"),
    Path("repos/README.md"),
    Path("workspace/.gitkeep"),
    Path("workspace/README.md"),
]
ALLOWED_INITIAL_DIRS = {"xenv"}


def perform_up(
    target_root: Path,
    *,
    assume_yes: bool = False,
    force: bool = False,
    skip_repos: bool = False,
    check: bool = False,
    prompt=input,
) -> list[str]:
    target_root = target_root.resolve()
    _ensure_directory_ready(target_root, assume_yes=assume_yes, force=force, prompt=prompt)
    copy_template_root(target_root)
    return _finalize_workspace(
        target_root,
        skip_repos=skip_repos,
        check=check,
    )


def perform_dev_up(
    target_root: Path,
    *,
    skip_repos: bool = False,
    check: bool = False,
) -> list[str]:
    target_root = target_root.resolve()
    _ensure_developer_checkout(target_root)
    copy_template_paths(target_root, DEVELOPER_TEMPLATE_PATHS)
    return _finalize_workspace(
        target_root,
        skip_repos=skip_repos,
        check=check,
    )


def install_missing_repos(root: Path | None = None) -> list[Path]:
    root = _find_workspace_root(root)
    repo_map = _load_yaml(root / "ai/policy/repos.yaml")
    cloned: list[Path] = []
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        target = root / (spec.get("path") or f"repos/{repo_name}")
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", spec["clone_url"], str(target)], cwd=root)
        cloned.append(target)
    return cloned


def doctor(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10  # leave margin

    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    rule = f"{DIM}{'─' * width}{RESET}"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: list[str]) -> list[str]:
        padded_cmds = [f"  {c}  " for c in cmds]
        box_w = min(max(len(c) for c in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{c.ljust(box_w)}{RESET}│" for c in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    def issue(title: str, text: str | None = None, cmds: list[str] | None = None) -> list[str]:
        lines = [f"{RED}✗{RESET} {BOLD}{title}{RESET}"]
        if text:
            lines += wrap(text, indent=3)
        if cmds:
            lines += command_box(cmds)
        return lines

    notes: list[str] = []

    notes.append(rule)
    notes.append(f"{BOLD}Workspace Doctor Report{RESET}".center(width))
    notes.append(rule)
    notes.append("")

    # Check workspace root marker
    if not (root / ROOT_MARKER).exists():
        notes += issue(
            "Missing workspace marker",
            f"{ROOT_MARKER} not found in {root}",
        )

    # Check skills for YAML frontmatter
    for skill_path in sorted((root / "ai/skills").glob("*/SKILL.md")):
        if not _has_yaml_frontmatter(skill_path):
            notes += issue(
                "Invalid skill file",
                f"{skill_path} missing required YAML frontmatter (---).",
            )

    # Check required CLI tools
    if shutil.which("codex") is None:
        notes += issue(
            "Codex CLI not found",
            _codex_install_message(),
            [
                "sudo apt install npm",
                "npm install -g @openai/codex",
                "codex --help",
            ],
        )

    if shutil.which("claude") is None:
        notes += issue(
            "Claude CLI not found",
            _claude_install_message(),
            [
                "sudo apt install npm",
                "npm install -g @anthropic-ai/claude-code",
                "claude --help",
            ],
        )

    # Check repository clones
    repo_map = _load_yaml(root / "ai/policy/repos.yaml")
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        repo_path = root / (spec.get("path") or f"repos/{repo_name}")
        if not repo_path.exists():
            notes += issue(
                "Missing repo clone",
                f"{repo_name} expected at {repo_path}",
                [f"git clone {spec.get('url', '<repo-url>')} {repo_path}"],
            )

    if not notes:
        notes.append(f"{GREEN}✓{RESET} All checks passed!")

    notes.append(rule)
    return notes


def doctor0(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)
    issues: list[str] = []
    if not (root / ROOT_MARKER).exists():
        issues.append(f"Missing {ROOT_MARKER} in {root}")
    for skill_path in sorted((root / "ai/skills").glob("*/SKILL.md")):
        if not _has_yaml_frontmatter(skill_path):
            issues.append(
                f"Invalid skill file: {skill_path}. Codex requires YAML frontmatter "
                "delimited by ---."
            )
    if shutil.which("codex") is None:
        issues.append(_codex_install_message())
    if shutil.which("claude") is None:
        issues.append(_claude_install_message())
    repo_map = _load_yaml(root / "ai/policy/repos.yaml")
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        repo_path = root / (spec.get("path") or f"repos/{repo_name}")
        if not repo_path.exists():
            issues.append(f"Missing repo clone: {repo_path}")
    return issues


def up_guidance(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10  # leave margin

    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    rule = f"{DIM}{'─' * width}{RESET}"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: list[str]) -> list[str]:
        padded_cmds = [f"  {c}  " for c in cmds]
        box_w = min(max(len(c) for c in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{c.ljust(box_w)}{RESET}│" for c in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    def step(title: str, text: str | None = None, cmds: list[str] | None = None) -> list[str]:
        lines = [f"{GREEN}✓{RESET} {BOLD}{title}{RESET}"]
        if text:
            lines += wrap(text, indent=3)
        if cmds:
            lines += command_box(cmds)
        return lines

    notes: list[str] = []

    notes.append(rule)
    notes.append(f"{BOLD}Workspace Setup Guidance{RESET}".center(width))
    notes.append(rule)
    notes.append("")

    # Step 1: Environment setup
    notes += step(
        "1. Prepare Python environment",
        "Create and activate `xenv/` yourself before installing packages.",
        ["python3 -m venv xenv", "source xenv/bin/activate"],
    )

    # Step 2: Install core packages
    notes += step(
        "2. Install core packages",
        "Recommended environment setup:",
        [
            "pip install --upgrade pip",
            "pip install scix",
            "pip install pydisort pyharp kintera snapy paddle",
        ],
    )

    # Warnings for missing commands
    if shutil.which(APP_NAME) is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}`scix` command not found{RESET}")
        notes += wrap(_virtual_env_message(), indent=3)

    if shutil.which("codex") is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}Codex CLI not detected{RESET}")
        notes += wrap(_codex_install_message(), indent=3)

    if shutil.which("claude") is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}Claude CLI not detected{RESET}")
        notes += wrap(_claude_install_message(), indent=3)

    if _is_ssh_session():
        notes.append(f"{YELLOW}!{RESET} {BOLD}SSH session detected{RESET}")
        notes += wrap(
            "Enable device code authorization in ChatGPT Security Settings.",
            indent=3,
        )
        notes += command_box(["codex login --device-auth"])

    notes.append(rule)
    return notes


def dev_up_guidance(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10  # leave margin

    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    rule = f"{DIM}{'─' * width}{RESET}"

    def wrap(text: str, indent: int = 0) -> list[str]:
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
        )

    def command_box(cmds: list[str]) -> list[str]:
        """
        Render one or more commands inside a CLI-style box.
        Each element of cmds is a separate line.
        """
        padded_cmds = [f"  {c}  " for c in cmds]
        box_w = min(max(len(c) for c in padded_cmds), width - 10)
        top = f"    ┌{'─' * box_w}┐"
        mid_lines = [f"    │{CYAN}{c.ljust(box_w)}{RESET}│" for c in padded_cmds]
        bot = f"    └{'─' * box_w}┘"
        return [top] + mid_lines + [bot]

    def step(title: str, text: str | None = None, cmds: list[str] | None = None) -> list[str]:
        lines = [f"{GREEN}✓{RESET} {BOLD}{title}{RESET}"]
        if text:
            lines += wrap(text, indent=3)
        if cmds:
            lines += command_box(cmds)
        return lines  # no empty line at the end

    notes: list[str] = []

    notes.append(rule)
    notes.append(f"{BOLD}Development Environment Setup{RESET}".center(width))
    notes.append(rule)
    notes.append("")

    notes += step(
        "1. Prepare Python environment",
        "Create and activate `xenv` (or your own virtual environment) before installing packages.",
        [
            "python3 -m venv xenv",
            "source xenv/bin/activate",
        ],
    )

    notes += step(
        "2. Install development dependencies",
        None,
        [
            "pip install -e .",
            "pip install pydisort pyharp kintera snapy paddle",
        ],
    )

    notes += step(
        "3. Install pre-commit hooks",
        None,
        [
            "pip install pre-commit",
            "pre-commit install",
            "pre-commit run --all-files",
        ],
    )

    notes.append(rule)

    # Additional environment hints
    if shutil.which(APP_NAME) is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}`scix` command not found{RESET}")
        notes += wrap(_virtual_env_message(), indent=3)

    if shutil.which("codex") is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}Codex CLI not detected{RESET}")
        notes += wrap(_codex_install_message(), indent=3)

    if shutil.which("claude") is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}Claude CLI not detected{RESET}")
        notes += wrap(_claude_install_message(), indent=3)

    if _is_ssh_session():
        notes.append(f"{YELLOW}!{RESET} {BOLD}SSH session detected{RESET}")
        notes += wrap(
            "Enable device code authorization in ChatGPT Security Settings.",
            indent=3,
        )
        notes += command_box(["codex login --device-auth"])

    return notes


def _ensure_directory_ready(
    target_root: Path,
    *,
    assume_yes: bool,
    force: bool,
    prompt,
) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    entries = [path for path in target_root.iterdir() if path.name not in TRIVIAL_HIDDEN_NAMES]
    blocking_entries = [path for path in entries if path.name not in ALLOWED_INITIAL_DIRS]
    if blocking_entries and not force:
        raise ScixError(
            f"{target_root} is not empty. Use --force only if this directory "
            "should become a scix workspace."
        )

    if assume_yes:
        return

    if blocking_entries and force:
        answer = prompt(
            f"{target_root} is not empty. Type 'yes' to confirm that it "
            "should become your scix workspace: "
        )
    else:
        answer = prompt(
            f"Type 'yes' to confirm that {target_root} should become your scix workspace: "
        )
    if answer.strip().lower() != "yes":
        raise ScixError("Aborted by user")


def _ensure_developer_checkout(target_root: Path) -> None:
    required = [
        target_root / "pyproject.toml",
        target_root / "README.md",
        target_root / "src/scix",
        target_root / "ai/policy/repos.yaml",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ScixError(f"Developer bootstrap expects a cloned scix source repo. Missing: {joined}")


def _finalize_workspace(
    root: Path,
    *,
    skip_repos: bool,
    check: bool,
) -> list[str]:
    changed = [str(path) for path in _sync_workspace(root)]
    if not skip_repos:
        install_missing_repos(root)
        changed.extend(str(path) for path in _sync_workspace(root))
    if check:
        issues = doctor(root)
        if issues:
            raise ScixError("\n".join(issues))
    return changed


def _find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ROOT_MARKER).exists():
            return candidate
    raise ScixError(f"Could not find {ROOT_MARKER} from {current}")


def _load_yaml(path: Path) -> dict:
    try:
        from .generator import load_yaml
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc

    return load_yaml(path)


def _sync_workspace(root: Path, check: bool = False) -> list[Path]:
    try:
        from .generator import sync_workspace
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc

    return sync_workspace(root, check=check)


def _dependency_error(exc: ModuleNotFoundError) -> ScixError:
    if exc.name == "yaml":
        return ScixError(
            "Missing dependency 'PyYAML'. Activate your virtual environment and run "
            "`python -m pip install -e .` (or `python -m pip install PyYAML`)."
        )
    return ScixError(
        f"Missing dependency '{exc.name}'. Activate your virtual environment and install "
        "project dependencies."
    )


def _virtual_env_message() -> str:
    return (
        "`xenv/` virtual environment not found. "
        "Activate `xenv/` or your own virtual environment and "
        "install the package before using scix."
    )


def _codex_install_message() -> str:
    return (
        "Codex is not on PATH. If you use Codex, install Codex CLI, then run `codex login`. "
        "Otherwise, you can 🫣 ignore this message if you only use Claude or other agents."
    )


def _claude_install_message() -> str:
    return (
        "Claude is not on PATH. If you use Claude, install Claude Code, then run "
        "`claude auth login`. Otherwise, you can ignore this message if you only use Codex or "
        "other agents."
    )


def _has_yaml_frontmatter(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    return any(line.strip() == "---" for line in lines[1:])


def _is_ssh_session() -> bool:
    return any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"))


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ScixError(f"Command failed: {' '.join(cmd)}") from exc
