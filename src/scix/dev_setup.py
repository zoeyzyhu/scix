"""Contributor bootstrap entry point for cloned scix source checkouts."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bootstrap import dev_up_guidance, perform_dev_up
from .exceptions import CheckFailedError, ScixError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev-up")
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
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        changes = perform_dev_up(
            Path.cwd(),
            skip_repos=args.skip_repos,
            check=args.check,
        )
    except CheckFailedError as exc:
        print(str(exc))
        return 1
    except ScixError as exc:
        print(str(exc))
        return 1

    print(f"\nscix developer bootstrap completed with {len(changes)} changed paths")
    print("\n\nNext steps:")
    for note in dev_up_guidance(Path.cwd()):
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
