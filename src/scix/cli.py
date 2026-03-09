"""Command-line interface for scix."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bootstrap import (
    dev_up_guidance,
    doctor,
    install_missing_repos,
    perform_dev_up,
    perform_up,
    up_guidance,
)
from .exceptions import CheckFailedError, ScixError
from .generator import find_workspace_root, sync_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scix")
    subparsers = parser.add_subparsers(dest="command", required=True)

    up_parser = subparsers.add_parser(
        "up",
        help="Create or update a scix workspace in the current directory",
    )
    up_parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation")
    up_parser.add_argument("--force", action="store_true", help="Allow a non-empty directory")
    up_parser.add_argument(
        "--skip-repos",
        action="store_true",
        help="Skip cloning reference repositories",
    )
    up_parser.add_argument(
        "--check",
        action="store_true",
        help="Run doctor at the end and fail on issues",
    )
    up_parser.set_defaults(func=cmd_up)

    dev_parser = subparsers.add_parser(
        "dev",
        help="Bootstrap a cloned scix source checkout for contributors",
    )
    dev_parser.add_argument(
        "--skip-repos",
        action="store_true",
        help="Skip cloning reference repositories",
    )
    dev_parser.add_argument(
        "--check",
        action="store_true",
        help="Run doctor at the end and fail on issues",
    )
    dev_parser.set_defaults(func=cmd_dev)

    sync_parser = subparsers.add_parser(
        "sync",
        help="Regenerate agent files and refresh the packaged AI template when present",
    )
    sync_parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of rewriting stale files",
    )
    sync_parser.set_defaults(func=cmd_sync)

    repo_parser = subparsers.add_parser(
        "install-repos",
        help="Clone missing reference repositories",
    )
    repo_parser.set_defaults(func=cmd_install_repos)

    doctor_parser = subparsers.add_parser("doctor", help="Validate the current scix workspace")
    doctor_parser.set_defaults(func=cmd_doctor)

    return parser


def cmd_up(args: argparse.Namespace) -> int:
    root = Path.cwd()
    changes = perform_up(
        root,
        assume_yes=args.yes,
        force=args.force,
        skip_repos=args.skip_repos,
        check=args.check,
    )
    print(f"\n scix up completed with {len(changes)} changed paths")
    print("\n\nNext steps:")
    for note in up_guidance(root):
        print(f"- {note}")
    return 0


def cmd_dev(args: argparse.Namespace) -> int:
    root = Path.cwd()
    changes = perform_dev_up(
        root,
        skip_repos=args.skip_repos,
        check=args.check,
    )
    print(f"\nscix developer bootstrap completed with {len(changes)} changed paths")
    print("\n\nNext steps:")
    for note in dev_up_guidance(root):
        print(f"- {note}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    changed = sync_workspace(find_workspace_root(), check=args.check)
    if args.check:
        print("scix sync --check passed")
    else:
        print(f"scix sync updated {len(changed)} paths")
    return 0


def cmd_install_repos(args: argparse.Namespace) -> int:
    cloned = install_missing_repos(find_workspace_root())
    print(f"Installed {len(cloned)} repositories")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report = doctor(find_workspace_root())
    if report:
        for line in report:
            print(line)
        return 1
    print("scix doctor passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CheckFailedError as exc:
        print(str(exc))
        return 1
    except ScixError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
