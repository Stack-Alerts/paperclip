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
KILL_EXISTING=0
REUSE_EXISTING=0
CANCEL_ON_CONFLICT=0
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
    --kill-existing)
      KILL_EXISTING=1
      ;;
    --reuse-existing)
      REUSE_EXISTING=1
      ;;
    --cancel-on-conflict)
      CANCEL_ON_CONFLICT=1
      ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-test.sh [--branch <name>] [--force] [--kill-existing] [--reuse-existing] [--cancel-on-conflict]" >&2
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

# Port conflict detection and handling
check_port_in_use() {
  local port=$1
  # Use ss to check for listening process (more reliable than lsof)
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1
  else
    # Fallback to lsof if ss is not available
    lsof -t -i :"$port" 2>/dev/null | grep -v '^$' | head -1
  fi
}

handle_port_conflict() {
  local port=$1
  local pid=$2

  local cmd_line
  cmd_line=$(ps -o args= -p "$pid" 2>/dev/null || echo "unknown")
  local etime
  etime=$(ps -o etime= -p "$pid" 2>/dev/null || echo "unknown")

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠️  Port :$port is already in use"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "PID:     $pid"
  echo "Command: $cmd_line"
  echo "Time:    $etime"
  echo

  if [[ $KILL_EXISTING -eq 1 ]]; then
    echo "[port-conflict] --kill-existing: terminating PID $pid..."
    kill -TERM "$pid" 2>/dev/null || true

    local wait_count=0
    while [[ $(check_port_in_use "$port") != "" ]] && [[ $wait_count -lt 50 ]]; do
      sleep 0.1
      wait_count=$((wait_count + 1))
    done

    if [[ $(check_port_in_use "$port") == "" ]]; then
      echo "[port-conflict] port :$port is now free"
      return 0
    else
      echo "ERROR: port :$port still in use after killing PID $pid" >&2
      exit 1
    fi
  elif [[ $REUSE_EXISTING -eq 1 ]]; then
    echo "[port-conflict] --reuse-existing: exiting without starting new server"
    exit 0
  elif [[ $CANCEL_ON_CONFLICT -eq 1 ]]; then
    echo "[port-conflict] --cancel-on-conflict: canceling startup"
    exit 1
  else
    echo "Choose action:"
    echo "  [k] kill PID $pid and start fresh"
    echo "  [r] reuse existing server on :$port"
    echo "  [c] cancel startup"
    echo
    read -p "Action? [k/r/c]: " -r action

    case "$action" in
      k|K)
        echo "[port-conflict] killing PID $pid..."
        kill -TERM "$pid" 2>/dev/null || true

        local wait_count=0
        while [[ $(check_port_in_use "$port") != "" ]] && [[ $wait_count -lt 50 ]]; do
          sleep 0.1
          wait_count=$((wait_count + 1))
        done

        if [[ $(check_port_in_use "$port") == "" ]]; then
          echo "[port-conflict] port :$port is now free"
          return 0
        else
          echo "ERROR: port :$port still in use after killing PID $pid" >&2
          exit 1
        fi
        ;;
      r|R)
        echo "[port-conflict] reusing existing server on :$port"
        echo "[port-conflict] browse http://localhost:$port"
        exit 0
        ;;
      c|C)
        echo "[port-conflict] canceling"
        exit 1
        ;;
      *)
        echo "ERROR: invalid action '$action'" >&2
        exit 1
        ;;
    esac
  fi
}

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

# Check if port :3000 is already in use by a foreign process
TARGET_PORT=3000
PID_ON_PORT=$(check_port_in_use "$TARGET_PORT")
if [[ -n "$PID_ON_PORT" ]]; then
  handle_port_conflict "$TARGET_PORT" "$PID_ON_PORT"
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
