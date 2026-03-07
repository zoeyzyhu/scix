#!/usr/bin/env bash
set -euo pipefail

payload="$(cat || true)"

if printf '%s' "$payload" | grep -Eq 'rm -rf /|git reset --hard|git checkout --'; then
  echo "scix pre_tool_guard: blocked dangerous command pattern" >&2
  exit 2
fi

exit 0
