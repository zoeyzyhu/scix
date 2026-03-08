"""Bootstrap and doctor helpers for scix."""

from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

from .constants import (
    APP_NAME,
    DEFAULT_PYTHON,
    PYENV_INIT_BLOCK,
    PYENV_PATH_BLOCK,
    ROOT_MARKER,
    TRIVIAL_HIDDEN_NAMES,
)
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


def perform_up(
    target_root: Path,
    *,
    assume_yes: bool = False,
    force: bool = False,
    skip_python: bool = False,
    skip_repos: bool = False,
    check: bool = False,
    prompt=input,
) -> list[str]:
    target_root = target_root.resolve()
    _ensure_directory_ready(target_root, assume_yes=assume_yes, force=force, prompt=prompt)
    copy_template_root(target_root)
    return _finalize_workspace(
        target_root,
        skip_python=skip_python,
        skip_repos=skip_repos,
        check=check,
    )


def perform_dev_up(
    target_root: Path,
    *,
    skip_python: bool = False,
    skip_repos: bool = False,
    check: bool = False,
) -> list[str]:
    target_root = target_root.resolve()
    _ensure_developer_checkout(target_root)
    copy_template_paths(target_root, DEVELOPER_TEMPLATE_PATHS)
    return _finalize_workspace(
        target_root,
        skip_python=skip_python,
        skip_repos=skip_repos,
        check=check,
        install_dev_package=True,
        install_hooks=True,
    )


def bootstrap_dev_python(target_root: Path) -> None:
    """Create ``xenv/`` and install contributor dependencies without requiring PyYAML."""

    target_root = target_root.resolve()
    _ensure_developer_checkout(target_root)
    copy_template_paths(target_root, DEVELOPER_TEMPLATE_PATHS)
    ensure_python_bootstrap(target_root)
    install_scix_into_xenv(
        target_root,
        package_root=target_root,
        editable=True,
        include_dev=True,
    )
    _run_in_xenv(
        target_root,
        [
            "-c",
            (
                "from pathlib import Path; "
                "from scix.bootstrap import install_pre_commit_hooks, install_science_packages; "
                "root = Path.cwd(); "
                "install_science_packages(root); "
                "install_pre_commit_hooks(root)"
            ),
        ],
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
    issues: list[str] = []
    if not (root / ROOT_MARKER).exists():
        issues.append(f"Missing {ROOT_MARKER} in {root}")
    if not (root / "xenv").exists():
        issues.append("Missing xenv/ virtual environment")
    if shutil.which("pyenv") is None and not (Path.home() / ".pyenv/bin/pyenv").exists():
        issues.append("pyenv is not installed or not on PATH")
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
    notes: list[str] = []
    if (root / "xenv").exists():
        notes.append("Activate the workspace Python with: source xenv/bin/activate")
    else:
        notes.append(
            "Python bootstrap was skipped, so `xenv/` does not exist yet. "
            "Run `scix up` again without `--skip-python` when you want a local environment."
        )
    if shutil.which(APP_NAME) is None:
        notes.append(
            "If the `scix` command is missing in a new shell, run "
            f"`source {_primary_shell_rc_path()}` or open a new terminal. "
            "You can always run `python3 -m scix ...`."
        )
    if shutil.which("codex") is None:
        notes.append(_codex_install_message())
    if shutil.which("claude") is None:
        notes.append(_claude_install_message())
    if _is_ssh_session():
        notes.append(
            "SSH session detected. In ChatGPT Security Settings, enable device "
            "code authorization, then run `codex login --device-auth`."
        )
    return notes


def dev_up_guidance(root: Path | None = None) -> list[str]:
    root = _find_workspace_root(root)
    notes: list[str] = []
    if (root / "xenv").exists():
        notes.append("Activate the workspace Python with: source xenv/bin/activate")
    else:
        notes.append(
            "Python bootstrap was skipped, so `xenv/` does not exist yet. "
            "Run `./scripts/dev-up.sh` again without `--skip-python` when you want "
            "the contributor environment."
        )
    if shutil.which(APP_NAME) is None:
        notes.append(
            "If the `scix` command is missing in a new shell, run "
            f"`source {_primary_shell_rc_path()}` or open a new terminal. "
            "You can always run `python3 -m scix ...`."
        )
    if shutil.which("codex") is None:
        notes.append(_codex_install_message())
    if shutil.which("claude") is None:
        notes.append(_claude_install_message())
    if _is_ssh_session():
        notes.append(
            "SSH session detected. In ChatGPT Security Settings, enable device "
            "code authorization, then run `codex login --device-auth`."
        )
    if (root / "xenv").exists():
        notes.append("Install Git hooks with: xenv/bin/pre-commit install")
        notes.append("Run all contributor checks with: xenv/bin/pre-commit run --all-files")
    return notes


def ensure_python_bootstrap(root: Path) -> None:
    system = sys.platform
    if not (system.startswith("darwin") or system.startswith("linux")):
        raise ScixError("scix supports only macOS and Linux in v1")
    ensure_pyenv_installed()
    update_shell_startup_files()
    pyenv = resolve_pyenv_binary()
    _run([str(pyenv), "install", "-s", DEFAULT_PYTHON], cwd=root)
    (root / ".python-version").write_text(DEFAULT_PYTHON + "\n", encoding="utf-8")
    if not (root / "xenv").exists():
        _run(
            [str(pyenv), "exec", "python", "-m", "venv", str(root / "xenv")],
            cwd=root,
            env=_pyenv_env(root),
        )
    _run(
        [
            str(root / "xenv/bin/python"),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        cwd=root,
    )


def install_scix_into_xenv(
    root: Path,
    *,
    package_root: Path | None = None,
    editable: bool = False,
    include_dev: bool = False,
) -> None:
    pip = root / "xenv/bin/pip"
    source_root = package_root or Path(__file__).resolve().parents[2]
    if editable:
        requirement = "."
        if include_dev:
            requirement = ".[dev]"
        _run([str(pip), "install", "-e", requirement], cwd=source_root)
    elif (source_root / "pyproject.toml").exists():
        _run([str(pip), "install", "-e", str(source_root)], cwd=root)
    else:
        _run([str(pip), "install", APP_NAME], cwd=root)


def install_science_packages(root: Path) -> None:
    pip = root / "xenv/bin/pip"
    repo_map = _load_yaml(root / "ai/policy/repos.yaml")
    packages = [
        spec["pip_package"]
        for spec in (repo_map.get("repos") or {}).values()
        if spec.get("pip_package")
    ]
    _run([str(pip), "install", *packages], cwd=root)


def install_pre_commit_hooks(root: Path) -> None:
    pre_commit = root / "xenv/bin/pre-commit"
    if not pre_commit.exists():
        raise ScixError("pre-commit is not installed in xenv/.")
    _run([str(pre_commit), "install"], cwd=root)


def ensure_pyenv_installed() -> None:
    if shutil.which("pyenv") or (Path.home() / ".pyenv/bin/pyenv").exists():
        return
    if sys.platform.startswith("darwin"):
        if shutil.which("brew"):
            _run(["brew", "install", "pyenv"])
            return
        _run(["bash", "-lc", "curl https://pyenv.run | bash"])
        return

    package_manager = _detect_package_manager()
    if package_manager == "apt-get":
        _run(
            [
                "sudo",
                "apt-get",
                "update",
            ]
        )
        _run(
            [
                "sudo",
                "apt-get",
                "install",
                "-y",
                "build-essential",
                "curl",
                "git",
                "libbz2-dev",
                "libffi-dev",
                "liblzma-dev",
                "libncursesw5-dev",
                "libreadline-dev",
                "libsqlite3-dev",
                "libssl-dev",
                "tk-dev",
                "xz-utils",
                "zlib1g-dev",
            ]
        )
    elif package_manager in {"dnf", "yum"}:
        _run(
            [
                "sudo",
                package_manager,
                "install",
                "-y",
                "gcc",
                "make",
                "patch",
                "zlib-devel",
                "bzip2",
                "bzip2-devel",
                "readline-devel",
                "sqlite",
                "sqlite-devel",
                "openssl-devel",
                "tk-devel",
                "libffi-devel",
                "xz-devel",
                "git",
                "curl",
            ]
        )
    else:
        raise ScixError(
            "Could not find a supported Linux package manager. "
            "Install pyenv manually and rerun scix up."
        )
    _run(["bash", "-lc", "curl https://pyenv.run | bash"])


def resolve_pyenv_binary() -> Path:
    path = shutil.which("pyenv")
    if path:
        return Path(path)
    fallback = Path.home() / ".pyenv/bin/pyenv"
    if fallback.exists():
        return fallback
    raise ScixError("pyenv was not found after installation")


def update_shell_startup_files() -> None:
    shell = Path(os.environ.get("SHELL", "")).name
    home = Path.home()
    user_base_block = _render_user_base_path_block()
    targets: list[tuple[Path, str]]
    if shell == "zsh":
        targets = [
            (home / ".zprofile", user_base_block),
            (home / ".zprofile", PYENV_PATH_BLOCK),
            (home / ".zshrc", user_base_block),
            (home / ".zshrc", PYENV_PATH_BLOCK),
            (home / ".zshrc", PYENV_INIT_BLOCK),
        ]
    else:
        targets = [
            (home / ".bash_profile", user_base_block),
            (home / ".bash_profile", PYENV_PATH_BLOCK),
            (home / ".bashrc", user_base_block),
            (home / ".bashrc", PYENV_PATH_BLOCK),
            (home / ".bashrc", PYENV_INIT_BLOCK),
        ]
    for path, block in targets:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if block.strip() in existing:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        path.write_text(existing + prefix + block, encoding="utf-8")


def _ensure_directory_ready(
    target_root: Path,
    *,
    assume_yes: bool,
    force: bool,
    prompt,
) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    entries = [path for path in target_root.iterdir() if path.name not in TRIVIAL_HIDDEN_NAMES]
    if entries and not force:
        raise ScixError(
            f"{target_root} is not empty. Use --force only if this directory "
            "should become a scix workspace."
        )

    if assume_yes:
        return

    if entries and force:
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


def _detect_package_manager() -> str | None:
    for candidate in ("apt-get", "dnf", "yum"):
        if shutil.which(candidate):
            return candidate
    return None


def _pyenv_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    pyenv_root = str(Path.home() / ".pyenv")
    env["PYENV_ROOT"] = pyenv_root
    env["PATH"] = f"{pyenv_root}/bin:{env.get('PATH', '')}"
    env["PYENV_VERSION"] = DEFAULT_PYTHON
    env["PWD"] = str(root)
    return env


def _finalize_workspace(
    root: Path,
    *,
    skip_python: bool,
    skip_repos: bool,
    check: bool,
    install_dev_package: bool = False,
    install_hooks: bool = False,
) -> list[str]:
    changed = [str(path) for path in _sync_workspace(root)]
    if not skip_python:
        ensure_python_bootstrap(root)
        if install_dev_package:
            install_scix_into_xenv(
                root,
                package_root=root,
                editable=True,
                include_dev=True,
            )
        else:
            install_scix_into_xenv(root)
        install_science_packages(root)
        if install_hooks:
            install_pre_commit_hooks(root)
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
    from .generator import load_yaml

    return load_yaml(path)


def _sync_workspace(root: Path, check: bool = False) -> list[Path]:
    from .generator import sync_workspace

    return sync_workspace(root, check=check)


def _run_in_xenv(root: Path, args: list[str]) -> None:
    python = root / "xenv/bin/python"
    if not python.exists():
        raise ScixError(f"Missing xenv Python at {python}")
    _run([str(python), *args], cwd=root)


def _codex_install_message() -> str:
    if sys.platform.startswith("linux"):
        return (
            "codex is not on PATH. On Ubuntu or Debian, run `sudo apt install npm` "
            "and then `sudo npm install -g @openai/codex`."
        )
    return "codex is not on PATH. Install Codex CLI with `npm install -g @openai/codex`."


def _claude_install_message() -> str:
    return "claude is not on PATH. Install Claude Code, then run `claude auth login`."


def _has_yaml_frontmatter(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    return any(line.strip() == "---" for line in lines[1:])


def _is_ssh_session() -> bool:
    return any(os.environ.get(name) for name in ("SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"))


def _primary_shell_rc_path() -> str:
    shell = Path(os.environ.get("SHELL", "")).name
    if shell == "zsh":
        return "~/.zshrc"
    return "~/.bashrc"


def _render_user_base_path_block() -> str:
    user_base_bin = Path(site.getuserbase()) / "bin"
    return (
        "# >>> scix user base bin >>>\n"
        f'SCIX_USER_BASE_BIN="{user_base_bin}"\n'
        'if [ -d "$SCIX_USER_BASE_BIN" ]; then\n'
        '  case ":$PATH:" in\n'
        '    *":$SCIX_USER_BASE_BIN:"*) ;;\n'
        '    *) export PATH="$SCIX_USER_BASE_BIN:$PATH" ;;\n'
        "  esac\n"
        "fi\n"
        "unset SCIX_USER_BASE_BIN\n"
        "# <<< scix user base bin <<<\n"
    )


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise ScixError(f"Command failed: {' '.join(cmd)}") from exc
