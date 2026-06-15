#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT_PATH="$SCRIPT_DIR/codex_usage_limits.py"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_PATH" "$@"
fi

exec python "$SCRIPT_PATH" "$@"
