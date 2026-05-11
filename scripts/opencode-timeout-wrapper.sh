#!/usr/bin/env bash
# Timeout wrapper for opencode CLI.
#
# Installs a timeout around 'opencode run' so that if the model API
# silently hangs (e.g. free-tier rate-limit), the process is killed
# after the configured duration.
#
# Usage (via Paperclip adapterConfig.command):
#   command: "/path/to/opencode-timeout-wrapper.sh"
#
# The wrapper reads the timeout from:
#   1. $PAPERCLIP_OPENCODE_TIMEOUT_SEC  (env var, default 1800 = 30 min)
#   2. Falls back to 1800
#
# It then runs: timeout $TIMEOUT_SEC opencode "$@"

set -euo pipefail

TIMEOUT_SEC="${PAPERCLIP_OPENCODE_TIMEOUT_SEC:-1800}"
OPENCODE_BIN="${PAPERCLIP_OPENCODE_BIN:-opencode}"

# Only wrap the 'run' subcommand; pass everything else through directly
if [ "${1:-}" = "run" ]; then
    exec timeout "$TIMEOUT_SEC" "$OPENCODE_BIN" "$@"
else
    exec "$OPENCODE_BIN" "$@"
fi
