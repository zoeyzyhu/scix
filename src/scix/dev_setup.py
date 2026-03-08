"""Contributor bootstrap entry point for cloned scix source checkouts."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .exceptions import CheckFailedError, ScixError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev-up")
    parser.add_argument(
        "--skip-python",
        action="store_true",
        help="Skip pyenv, xenv, editable install, and pre-commit setup",
    )
    parser.add_argument(
        "--skip-repos",
        action="store_true",
        help="Skip cloning reference repositories",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run doctor at the end and fail on issues",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv_list)
    root = Path.cwd()

    try:
        if not _python_has_yaml():
            if _xenv_has_scix(root):
                _reexec_in_xenv(root, argv_list)
            if args.skip_python:
                raise ScixError(
                    "System Python is missing PyYAML and xenv/ is not ready yet. "
                    "Run `./scripts/dev-up.sh` once without `--skip-python` first."
                )
            from .bootstrap import bootstrap_dev_python

            bootstrap_dev_python(root)
            forwarded = list(argv_list)
            if "--skip-python" not in forwarded:
                forwarded.append("--skip-python")
            _reexec_in_xenv(root, forwarded)

        from .bootstrap import dev_up_guidance, perform_dev_up

        changes = perform_dev_up(
            root,
            skip_python=args.skip_python,
            skip_repos=args.skip_repos,
            check=args.check,
        )
    except CheckFailedError as exc:
        print(str(exc))
        return 1
    except ScixError as exc:
        print(str(exc))
        return 1

    print(f"scix developer bootstrap completed with {len(changes)} changed paths")
    print("Next steps:")
    for note in dev_up_guidance(root):
        print(f"- {note}")
    return 0


def _python_has_yaml() -> bool:
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _xenv_has_scix(root: Path) -> bool:
    python = root / "xenv/bin/python"
    if not python.exists():
        return False
    result = subprocess.run(
        [str(python), "-c", "import scix.dev_setup"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _reexec_in_xenv(root: Path, argv: list[str]) -> None:
    python = root / "xenv/bin/python"
    os.execv(str(python), [str(python), "-m", "scix.dev_setup", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
