"""Bootstrap and doctor helpers for scix."""

from __future__ import annotations

import os
import shutil
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
from .generator import find_workspace_root, load_yaml, sync_workspace
from .scaffold import copy_template_root


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
    changed = [str(path) for path in sync_workspace(target_root)]
    if not skip_python:
        ensure_python_bootstrap(target_root)
        install_scix_into_xenv(target_root)
        install_science_packages(target_root)
    if not skip_repos:
        install_missing_repos(target_root)
        changed.extend(str(path) for path in sync_workspace(target_root))
    if check:
        issues = doctor(target_root)
        if issues:
            raise ScixError("\n".join(issues))
    return changed


def install_missing_repos(root: Path | None = None) -> list[Path]:
    root = find_workspace_root(root)
    repo_map = load_yaml(root / "ai/policy/repos.yaml")
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
    root = find_workspace_root(root)
    issues: list[str] = []
    if not (root / ROOT_MARKER).exists():
        issues.append(f"Missing {ROOT_MARKER} in {root}")
    if not (root / "xenv").exists():
        issues.append("Missing xenv/ virtual environment")
    if shutil.which("pyenv") is None and not (Path.home() / ".pyenv/bin/pyenv").exists():
        issues.append("pyenv is not installed or not on PATH")
    if shutil.which("codex") is None:
        issues.append("codex is not on PATH")
    if shutil.which("claude") is None:
        issues.append("claude is not on PATH")
    repo_map = load_yaml(root / "ai/policy/repos.yaml")
    for repo_name, spec in sorted((repo_map.get("repos") or {}).items()):
        repo_path = root / (spec.get("path") or f"repos/{repo_name}")
        if not repo_path.exists():
            issues.append(f"Missing repo clone: {repo_path}")
    return issues


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


def install_scix_into_xenv(root: Path) -> None:
    pip = root / "xenv/bin/pip"
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "pyproject.toml").exists():
        _run([str(pip), "install", "-e", str(source_root)], cwd=root)
    else:
        _run([str(pip), "install", APP_NAME], cwd=root)


def install_science_packages(root: Path) -> None:
    pip = root / "xenv/bin/pip"
    repo_map = load_yaml(root / "ai/policy/repos.yaml")
    packages = [
        spec["pip_package"]
        for spec in (repo_map.get("repos") or {}).values()
        if spec.get("pip_package")
    ]
    _run([str(pip), "install", *packages], cwd=root)


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
    targets: list[tuple[Path, str]]
    if shell == "zsh":
        targets = [(home / ".zprofile", PYENV_PATH_BLOCK), (home / ".zshrc", PYENV_INIT_BLOCK)]
    else:
        targets = [(home / ".bash_profile", PYENV_PATH_BLOCK), (home / ".bashrc", PYENV_INIT_BLOCK)]
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


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise ScixError(f"Command failed: {' '.join(cmd)}") from exc
