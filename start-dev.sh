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

# Early branch gate: detect non-main branch and offer to switch before touching systemd.
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
  echo ""
  echo "⚠️  You are on branch: $CURRENT_BRANCH"
  echo "   start-dev.sh requires the main branch (btc-dev-server.service enforces this)."
  echo ""
  echo "Options:"
  echo "  [s] switch to main and start the dev server"
  echo "  [t] use ./start-test.sh instead (ephemeral :3000, no branch restriction)"
  echo "  [c] cancel"
  echo ""
  if [[ -t 0 ]]; then
    read -r -p "Action? [s/t/c]: " action
  else
    echo "Non-interactive: defaulting to [c] cancel." >&2
    action="c"
  fi
  case "${action,,}" in
    s)
      echo "[start-dev] switching to main..."
      DIRTY=$(git status --porcelain 2>/dev/null | grep -c '^.' || true)
      if [[ "$DIRTY" -gt 0 ]]; then
        echo "[start-dev] stashing $DIRTY uncommitted change(s)..."
        git stash push -m "start-dev auto-stash before switching to main" --include-untracked 2>&1 || {
          echo "ERROR: git stash failed; commit or discard changes before switching." >&2
          exit 1
        }
      fi
      git checkout main 2>&1 || { echo "ERROR: git checkout main failed." >&2; exit 1; }
      git pull --ff-only origin main 2>&1 || { echo "ERROR: git pull --ff-only origin main failed." >&2; exit 1; }
      CURRENT_BRANCH="main"
      echo "[start-dev] now on main — continuing..."
      ;;
    t)
      echo "[start-dev] use: ./start-test.sh"
      echo "            (runs on :3000, auto-switches to main, no systemd branch gate)"
      exit 0
      ;;
    *)
      echo "[start-dev] cancelled."
      exit 1
      ;;
  esac
fi

WATCH=0
KILL_EXISTING=0
REUSE_EXISTING=0
CANCEL_ON_CONFLICT=0
for arg in "$@"; do
  case "$arg" in
    --watch) WATCH=1 ;;
    --kill-existing) KILL_EXISTING=1 ;;
    --reuse-existing) REUSE_EXISTING=1 ;;
    --cancel-on-conflict) CANCEL_ON_CONFLICT=1 ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-dev.sh [--watch] [--kill-existing] [--reuse-existing] [--cancel-on-conflict]" >&2
      exit 1
      ;;
  esac
done

# Port conflict detection and handling (defense-in-depth for unmanaged processes)
check_port_in_use() {
  # Must return 0 even when no listener is found: under `set -euo pipefail`,
  # the inner grep returns non-zero on no match, which would silently abort
  # any caller using `$(check_port_in_use ...)`. BTCAAAAA-32422 forensics.
  local port=$1
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || true)
  else
    pid=$(lsof -t -i :"$port" 2>/dev/null | grep -v '^$' | head -1 || true)
  fi
  echo "$pid"
}

get_service_pid() {
  systemctl --user show -p MainPID --value btc-dev-server.service 2>/dev/null || echo ""
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
  echo "⚠️  Port :$port is already in use by unmanaged process"
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
    echo "[port-conflict] --reuse-existing: exiting without restarting service"
    exit 0
  elif [[ $CANCEL_ON_CONFLICT -eq 1 ]]; then
    echo "[port-conflict] --cancel-on-conflict: canceling startup"
    exit 1
  else
    echo "Choose action:"
    echo "  [k] kill PID $pid and restart service"
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

# Check if btc-dev-server.service exists
UNIT_CHECK=$(systemctl --user list-unit-files 2>/dev/null || true)
if ! echo "$UNIT_CHECK" | grep -q btc-dev-server.service; then
  echo "ERROR: btc-dev-server.service not found in systemd user units" >&2
  echo "       Run 'deploy/systemd/install-dev-server.sh' to register the unit" >&2
  exit 1
fi

# Check current status
SERVICE_STATE=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "unknown")

# Defense-in-depth: check if port :3010 is held by a foreign process
TARGET_PORT=3010
PID_ON_PORT=$(check_port_in_use "$TARGET_PORT")
SERVICE_PID=$(get_service_pid)

if [[ -n "$PID_ON_PORT" ]] && [[ "$PID_ON_PORT" != "$SERVICE_PID" ]]; then
  # Foreign process is holding the port
  handle_port_conflict "$TARGET_PORT" "$PID_ON_PORT"
fi

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
