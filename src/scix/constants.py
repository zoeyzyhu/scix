"""Shared constants for scix."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "scix"
DEFAULT_PYTHON = "3.11"
ROOT_MARKER = ".ai-root"
TRIVIAL_HIDDEN_NAMES = {".DS_Store", ".localized"}
REQUIRED_ROOT_PATHS = [
    Path("ai/policy/repos.yaml"),
    Path("ai/policy/workspace.md"),
    Path("ai/policy/rules.md"),
    Path("ai/agents/roles.yaml"),
]

PYENV_PATH_BLOCK = """# >>> scix pyenv path >>>
export PYENV_ROOT="$HOME/.pyenv"
if [ -d "$PYENV_ROOT/bin" ]; then
  export PATH="$PYENV_ROOT/bin:$PATH"
fi
# <<< scix pyenv path <<<
"""

PYENV_INIT_BLOCK = """# >>> scix pyenv init >>>
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi
# <<< scix pyenv init <<<
"""
