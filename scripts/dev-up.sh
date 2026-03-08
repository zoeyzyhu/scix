#!/usr/bin/env bash
set -euo pipefail

echo "./scripts/dev-up.sh is deprecated; use 'scix dev' instead." >&2
exec scix dev "$@"
