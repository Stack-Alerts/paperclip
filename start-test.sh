#!/usr/bin/env bash
# start-test.sh — ephemeral test instance on :3000
#
# ⚠️  THIS IS A TEST INSTANCE
#
# Spawns its own `next dev -p 3000` (does NOT register with systemd).
# For production-like testing or supervised operation, use ./start-dev.sh on :3010.
#
# If btc-dev-server.service is running, detects the per-project lock conflict
# up-front and guides the operator to either use :3010 or use --force to stop
# the supervised service temporarily.
#
# Usage:
#   ./start-test.sh                 # Spawn test on :3000 (or fail if :3010 is supervised)
#   ./start-test.sh --branch <name> # Spawn test on <name>, not main
#   ./start-test.sh --force          # Stop supervised service, then spawn test on :3000

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

BRANCH_OVERRIDE=""
FORCE_MODE=0
prev_arg=""
for arg in "$@"; do
  if [[ "$prev_arg" == "--branch" ]]; then
    BRANCH_OVERRIDE="$arg"
    prev_arg=""
    continue
  fi
  case "$arg" in
    --branch)
      prev_arg="--branch"
      ;;
    --branch=*)
      BRANCH_OVERRIDE="${arg#--branch=}"
      ;;
    --force)
      FORCE_MODE=1
      ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-test.sh [--branch <name>] [--force]" >&2
      exit 1
      ;;
  esac
done

# If --branch specified, switch to it
if [[ -n "$BRANCH_OVERRIDE" ]]; then
  echo "[test-instance] switching to branch $BRANCH_OVERRIDE..."
  git -C "$REPO_ROOT" fetch --quiet origin "$BRANCH_OVERRIDE" 2>/dev/null || true
  if ! git -C "$REPO_ROOT" switch "$BRANCH_OVERRIDE" 2>/dev/null; then
    if ! git -C "$REPO_ROOT" switch --detach "origin/$BRANCH_OVERRIDE" 2>/dev/null; then
      echo "ERROR: cannot switch to '$BRANCH_OVERRIDE'" >&2
      exit 1
    fi
  fi
fi

# Resolve npm
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found in PATH" >&2
  exit 1
fi
NPM="$(command -v npm)"

# Detect if supervised dev server is already running on :3010
SUPERVISED_STATUS=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "inactive")

if [[ "$SUPERVISED_STATUS" == "active" ]]; then
  if [[ $FORCE_MODE -eq 0 ]]; then
    # Mode A: Refuse and guide operator
    PID=$(systemctl --user show -p MainPID --value btc-dev-server.service 2>/dev/null || echo "unknown")
    echo
    echo "[start-test] ✗ supervised dev server already serving the same code on :3010 (PID $PID)."
    echo "            Browse http://localhost:3010 directly, OR re-run with --force to stop"
    echo "            the supervised service and bind :3000 ephemerally."
    echo
    echo "ERROR: refusing to start; supervised server holds the per-project lock."
    exit 1
  else
    # Mode B: Stop supervised service and continue
    echo "[start-test] --force mode: stopping btc-dev-server.service to free the per-project lock..."
    if systemctl --user stop btc-dev-server.service 2>/dev/null; then
      echo "[start-test] systemctl --user stop btc-dev-server.service → OK"
      sleep 1
    else
      echo "ERROR: failed to stop btc-dev-server.service" >&2
      systemctl --user status btc-dev-server.service 2>&1 | head -10 >&2
      exit 1
    fi
  fi
fi

# Print the test instance notice
echo
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ⚠️  THIS IS A TEST INSTANCE on :3000                  ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ For supervised, production-like testing, use:              ║"
echo "║   ./start-dev.sh          (port :3010, systemd-managed)    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Load env for NEXT_PUBLIC_* vars
if [[ -f "$REPO_ROOT/.env" ]]; then
  while IFS= read -r line; do
    line="${line%$'\r'}"
    case "$line" in
      BTE_API_HOST=*|BTE_API_PORT=*|BTE_API_DEV_MODE=*)
        export "${line?}"
        ;;
    esac
  done < "$REPO_ROOT/.env"
fi

BACKEND_HOST="${BTE_API_HOST:-0.0.0.0}"
BACKEND_PORT="${BTE_API_PORT:-8765}"
BACKEND_PUBLIC_HOST="${BTE_API_PUBLIC_HOST:-${BACKEND_HOST}}"
if [[ "$BACKEND_PUBLIC_HOST" == "0.0.0.0" || -z "$BACKEND_PUBLIC_HOST" ]]; then
  BACKEND_PUBLIC_HOST="localhost"
fi
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${BACKEND_PUBLIC_HOST}:${BACKEND_PORT}}"
export NEXT_PUBLIC_BRIDGE_WS_URL="${NEXT_PUBLIC_BRIDGE_WS_URL:-ws://${BACKEND_PUBLIC_HOST}:${BACKEND_PORT}}"

# Cleanup on exit
cleanup() {
  trap - INT TERM EXIT
  # The process group management is handled by npm/node naturally
  # Just exit gracefully
}
trap cleanup INT TERM EXIT

# Launch test instance
echo "[test-instance] spawning next dev on :3000..."
echo
cd "$REPO_ROOT/packages/web-ui"
exec "$NPM" run dev -- --port 3000
