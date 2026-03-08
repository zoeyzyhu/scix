"""Shared constants for scix."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "scix"
ROOT_MARKER = ".ai-root"
TRIVIAL_HIDDEN_NAMES = {".DS_Store", ".localized"}
REQUIRED_ROOT_PATHS = [
    Path("ai/policy/repos.yaml"),
    Path("ai/policy/workspace.md"),
    Path("ai/policy/rules.md"),
    Path("ai/agents/roles.yaml"),
]
