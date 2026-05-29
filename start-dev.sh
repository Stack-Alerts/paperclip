#!/usr/bin/env bash
# start-dev.sh — canonical launcher for supervised development server on :3010
#
# Behavior:
#   1. Ensures btc-dev-server.service is active
#   2. If inactive/failed, restarts it via systemctl --user
#   3. Waits for HTTP 200 on http://localhost:3010/
#   4. Prints the canonical URL
#   5. By default exits after readiness; --watch to tail journalctl
#
# Usage:
#   ./start-dev.sh                  # Start/verify, then exit
#   ./start-dev.sh --watch          # Start/verify, then tail logs
#
# All branch gating, main-branch enforcement, and health surveillance
# are inherited from btc-dev-server.service (see AGENTS.md).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

WATCH=0
for arg in "$@"; do
  case "$arg" in
    --watch) WATCH=1 ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-dev.sh [--watch]" >&2
      exit 1
      ;;
  esac
done

# Check if btc-dev-server.service exists
UNIT_CHECK=$(systemctl --user list-unit-files 2>/dev/null || true)
if ! echo "$UNIT_CHECK" | grep -q btc-dev-server.service; then
  echo "ERROR: btc-dev-server.service not found in systemd user units" >&2
  echo "       Run 'deploy/systemd/install-dev-server.sh' to register the unit" >&2
  exit 1
fi

# Check current status
SERVICE_STATE=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "unknown")

if [[ "$SERVICE_STATE" != "active" ]]; then
  echo "[start-dev] btc-dev-server.service is $SERVICE_STATE — restarting..."
  if ! systemctl --user restart btc-dev-server.service 2>/dev/null; then
    echo "ERROR: failed to restart btc-dev-server.service" >&2
    systemctl --user status btc-dev-server.service 2>&1 | head -20 >&2
    exit 1
  fi
  sleep 1
fi

# Wait for HTTP 200 on :3010
echo "[start-dev] waiting for http://localhost:3010/ to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
  ATTEMPT=$((ATTEMPT + 1))

  # Try IPv4
  if curl -s -4 -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:3010/" 2>/dev/null | grep -q 200; then
    echo "[start-dev] ✓ ready on :3010"
    echo
    echo "Local: http://localhost:3010"
    echo
    break
  fi

  # Try IPv6
  if curl -s -6 -o /dev/null -w '%{http_code}' -m 3 "http://[::1]:3010/" 2>/dev/null | grep -q 200; then
    echo "[start-dev] ✓ ready on :3010"
    echo
    echo "Local: http://localhost:3010"
    echo
    break
  fi

  if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "ERROR: :3010 did not respond with HTTP 200 after $MAX_ATTEMPTS attempts" >&2
    echo "       Check service logs: journalctl --user -fu btc-dev-server.service" >&2
    systemctl --user status btc-dev-server.service 2>&1 | head -10 >&2
    exit 1
  fi

  echo "[start-dev] attempt $ATTEMPT/$MAX_ATTEMPTS (waiting 1s)..."
  sleep 1
done

# If --watch, tail the journal
if [[ $WATCH -eq 1 ]]; then
  echo "[start-dev] --watch enabled; tailing journalctl (Ctrl+C to detach)..."
  echo
  journalctl --user -fu btc-dev-server.service
fi

exit 0
