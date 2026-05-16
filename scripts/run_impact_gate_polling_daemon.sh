#!/bin/bash
# Wrapper script for Impact Gate polling daemon
# Can be called from GitHub Actions, systemd, or manual orchestration
# Sets up environment and delegates to the Python daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment if running locally (not in CI)
if [ -z "$PAPERCLIP_API_URL" ]; then
    if [ -f "$REPO_ROOT/.env" ]; then
        set -a
        source "$REPO_ROOT/.env"
        set +a
    fi
fi

# Validate required environment variables
for var in PAPERCLIP_API_URL PAPERCLIP_API_KEY PAPERCLIP_BOARD_API_KEY PAPERCLIP_COMPANY_ID; do
    if [ -z "${!var}" ]; then
        echo "Error: $var not set" >&2
        exit 1
    fi
done

# Set Python path
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH}"

# Run daemon with provided arguments
exec python3 "$SCRIPT_DIR/impact_gate_polling_daemon.py" "$@"
