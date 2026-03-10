"""Bootstrap and doctor helpers for scix."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
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
NVM_VERSION = "v0.40.4"
NVM_INSTALL_URL = f"https://raw.githubusercontent.com/nvm-sh/nvm/{NVM_VERSION}/install.sh"


@dataclass(frozen=True)
class AgentToolState:
    nvm_script: Path
    nvm_default_bin: Path | None
    codex_path: str | None
    claude_path: str | None

    @property
    def node_ready(self) -> bool:
        if self.nvm_default_bin is None:
            return False
        return (self.nvm_default_bin / "node").exists() and (self.nvm_default_bin / "npm").exists()

    @property
    def install_needed(self) -> bool:
        return bool(self.missing_components())

    def missing_components(self) -> list[str]:
        missing: list[str] = []
        if not self.nvm_script.exists():
            missing.append("nvm")
        if not self.node_ready:
            missing.extend(["node", "npm"])
        if self.codex_path is None:
            missing.append("codex")
        if self.claude_path is None:
            missing.append("claude")
        return missing


@dataclass(frozen=True)
class AgentInstallResult:
    install_needed: bool
    attempted: bool


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


def doctor(
    root: Path | None = None,
    *,
    suppress_agent_cli_issues: bool = False,
) -> list[str]:
    root = _find_workspace_root(root)

    width = shutil.get_terminal_size((90, 20)).columns
    width = width - 10  # leave margin

    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
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

    report: list[str] = [
        rule,
        f"{BOLD}Workspace Doctor Report{RESET}".center(width),
        rule,
        "",
    ]
    issue_lines: list[str] = []

    # Check workspace root marker
    if not (root / ROOT_MARKER).exists():
        issue_lines += issue(
            "Missing workspace marker",
            f"{ROOT_MARKER} not found in {root}",
        )

    # Check skills for YAML frontmatter
    for skill_path in sorted((root / "ai/skills").glob("*/SKILL.md")):
        if not _has_yaml_frontmatter(skill_path):
            issue_lines += issue(
                "Invalid skill file",
                f"{skill_path} missing required YAML frontmatter (---).",
            )

    # Check required CLI tools
    if not suppress_agent_cli_issues and not _has_any_agent_cli():
        issue_lines += issue(
            "No agent CLI found",
            _agent_cli_install_message(),
            _agent_install_commands(include_codex=True, include_claude=True),
        )

    # Check repository clones
    repo_map = _load_yaml(root / "ai/policy/repos.yaml")
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        repo_path = root / (spec.get("path") or f"repos/{repo_name}")
        if not repo_path.exists():
            issue_lines += issue(
                "Missing repo clone",
                f"{repo_name} expected at {repo_path}",
                [f"git clone {spec.get('url', '<repo-url>')} {repo_path}"],
            )

    if not issue_lines:
        return []

    report.extend(issue_lines)
    report.append(rule)
    return report


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

    # Warnings for missing commands
    if shutil.which(APP_NAME) is None:
        notes.append(f"{YELLOW}!{RESET} {BOLD}`scix` command not found{RESET}")
        notes += wrap(_virtual_env_message(), indent=3)

    if not _has_any_agent_cli():
        notes.append(f"{YELLOW}!{RESET} {BOLD}No agent CLI detected{RESET}")
        notes += wrap(_agent_cli_install_message(), indent=3)

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
        "1. Install development dependencies",
        None,
        [
            "pip install pydisort pyharp kintera snapy paddle",
        ],
    )

    notes += step(
        "2. Install pre-commit hooks",
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

    if not _has_any_agent_cli():
        notes.append(f"{YELLOW}!{RESET} {BOLD}No agent CLI detected{RESET}")
        notes += wrap(_agent_cli_install_message(), indent=3)

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
    install_result = _ensure_agent_clis()
    if check:
        issues = doctor(root, suppress_agent_cli_issues=install_result.install_needed)
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


def _agent_cli_install_message() -> str:
    return (
        "Neither Codex nor Claude is on PATH. `scix up` (if you are a user) and `scix dev` "
        "(if you are a developer) try to install nvm, "
        "user-local Node.js/npm, Codex, and Claude automatically. If both commands are still "
        "missing, rerun the nvm-based install commands below, open a new shell or source "
        "`~/.nvm/nvm.sh`, then run `codex login` (or `codex login --device-auth` "
        "if you're in an SSH session) or `claude auth login`."
    )


def _has_yaml_frontmatter(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    return any(line.strip() == "---" for line in lines[1:])


def _is_ssh_session() -> bool:
    return any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"))


def _has_any_agent_cli() -> bool:
    return shutil.which("codex") is not None or shutil.which("claude") is not None


def _ensure_agent_clis() -> AgentInstallResult:
    state = _detect_agent_tool_state()
    if not state.install_needed:
        return AgentInstallResult(install_needed=False, attempted=False)

    bash_path = shutil.which("bash")
    curl_path = shutil.which("curl")
    missing_prereqs = [
        name for name, path in (("bash", bash_path), ("curl", curl_path)) if path is None
    ]
    if missing_prereqs:
        _print_agent_install_warning(
            f"Missing prerequisite command(s): {', '.join(sorted(missing_prereqs))}.",
        )
        return AgentInstallResult(install_needed=True, attempted=False)

    print("Installing nvm, user-local Node.js/npm, Codex CLI, and Claude Code CLI...")
    try:
        subprocess.run(
            [bash_path, "-lc", _agent_install_script(state)],
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        _prepend_nvm_default_bin_to_path()
        _print_agent_install_warning(
            f"Automatic install command failed with exit code {exc.returncode}.",
        )
        return AgentInstallResult(install_needed=True, attempted=True)

    _prepend_nvm_default_bin_to_path()
    remaining = _detect_agent_tool_state().missing_components()
    if remaining:
        _print_agent_install_warning(
            f"Automatic install finished, but these commands are still missing: "
            f"{', '.join(remaining)}.",
        )
    return AgentInstallResult(install_needed=True, attempted=True)


def _detect_agent_tool_state() -> AgentToolState:
    nvm_script = _nvm_script_path()
    nvm_default_bin = _prepend_nvm_default_bin_to_path(nvm_script)
    if nvm_default_bin is None:
        nvm_default_bin = _resolve_nvm_default_bin_dir(nvm_script)
    return AgentToolState(
        nvm_script=nvm_script,
        nvm_default_bin=nvm_default_bin,
        codex_path=shutil.which("codex"),
        claude_path=shutil.which("claude"),
    )


def _agent_install_commands(
    *,
    include_codex: bool = False,
    include_claude: bool = False,
) -> list[str]:
    commands = [
        f"curl -o- {NVM_INSTALL_URL} | bash",
        'export NVM_DIR="$HOME/.nvm"',
        '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
        "nvm install --lts",
        "nvm use --lts",
        "nvm alias default lts/*",
    ]
    if include_codex:
        commands.append("npm install -g @openai/codex")
    if include_claude:
        commands.append("npm install -g @anthropic-ai/claude-code")
    return commands


def _agent_install_script(state: AgentToolState) -> str:
    lines = []
    if not state.nvm_script.exists():
        lines.append(f"curl -o- {shlex.quote(NVM_INSTALL_URL)} | bash")
    lines.append(f"export NVM_DIR={shlex.quote(str(state.nvm_script.parent))}")
    lines.append('[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"')
    if not state.node_ready:
        lines.extend(
            [
                "nvm install --lts",
                "nvm use --lts",
                "nvm alias default lts/*",
            ]
        )
    if state.codex_path is None:
        lines.append("npm install -g @openai/codex")
    if state.claude_path is None:
        lines.append("npm install -g @anthropic-ai/claude-code")
    return "\n".join(lines)


def _print_agent_install_warning(reason: str) -> None:
    print("")
    print(
        "Warning: scix could not finish installing nvm, user-local Node.js/npm, Codex CLI, "
        "and Claude Code CLI automatically."
    )
    print(f"Reason: {reason}")
    print("Run these commands manually:")
    for command in _agent_install_commands(include_codex=True, include_claude=True):
        print(f"  {command}")
    print("If the commands are still missing afterwards, open a new shell or run:")
    print('  export NVM_DIR="$HOME/.nvm"')
    print('  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"')


def _nvm_script_path() -> Path:
    configured = os.environ.get("NVM_DIR")
    if configured:
        return Path(configured).expanduser() / "nvm.sh"
    return Path.home() / ".nvm" / "nvm.sh"


def _prepend_nvm_default_bin_to_path(nvm_script: Path | None = None) -> Path | None:
    bin_dir = _resolve_nvm_default_bin_dir(nvm_script)
    if bin_dir is None:
        return None
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    bin_str = str(bin_dir)
    if bin_str not in path_parts:
        os.environ["PATH"] = f"{bin_str}{os.pathsep}{current_path}" if current_path else bin_str
    return bin_dir


def _resolve_nvm_default_bin_dir(nvm_script: Path | None = None) -> Path | None:
    nvm_script = nvm_script or _nvm_script_path()
    bash_path = shutil.which("bash")
    if bash_path is None or not nvm_script.exists():
        return None
    command = "\n".join(
        [
            f"export NVM_DIR={shlex.quote(str(nvm_script.parent))}",
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"',
            "nvm which default",
        ]
    )
    result = subprocess.run(
        [bash_path, "-lc", command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    node_path = result.stdout.strip()
    if not node_path or node_path == "N/A":
        return None
    resolved = Path(node_path).expanduser()
    if resolved.name != "node":
        return None
    return resolved.parent


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ScixError(f"Command failed: {' '.join(cmd)}") from exc
