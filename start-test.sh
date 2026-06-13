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
#   ./start-test.sh --force         # Stop supervised service, then spawn test on :3000
#   ./start-test.sh --restart       # Kill existing :3000, pull latest main, restart fresh
#   ./start-test.sh --stop          # Kill existing :3000 and exit (no new server started)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGINAL_REPO_ROOT="$REPO_ROOT"
CREATED_TEMP_WORKTREE=0
TEMP_WORKTREE=""
cd "$REPO_ROOT"

BRANCH_OVERRIDE=""
FORCE_MODE=0
KILL_EXISTING=0
REUSE_EXISTING=0
CANCEL_ON_CONFLICT=0
RESTART_MODE=0
STOP_MODE=0
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
    --restart)
      RESTART_MODE=1
      KILL_EXISTING=1
      ;;
    --stop)
      STOP_MODE=1
      KILL_EXISTING=1
      ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-test.sh [--branch <name>] [--force] [--kill-existing] [--reuse-existing] [--cancel-on-conflict] [--restart] [--stop]" >&2
      exit 1
      ;;
  esac
done

# Branch handling: explicit --branch overrides; otherwise auto-switch to main.
CURRENT_BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

if [[ -n "$BRANCH_OVERRIDE" ]]; then
  echo "[test-instance] switching to branch $BRANCH_OVERRIDE..."
  git -C "$REPO_ROOT" fetch --quiet origin "$BRANCH_OVERRIDE" 2>/dev/null || true
  if ! git -C "$REPO_ROOT" switch "$BRANCH_OVERRIDE" 2>/dev/null; then
    if ! git -C "$REPO_ROOT" switch --detach "origin/$BRANCH_OVERRIDE" 2>/dev/null; then
      echo "ERROR: cannot switch to '$BRANCH_OVERRIDE'" >&2
      exit 1
    fi
  fi
elif [[ "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
  echo "[test-instance] on branch '$CURRENT_BRANCH' — resolving main for test server..."

  # Prune stale worktree references first (handles the case where /tmp/... was deleted but
  # git still tracks the reference, causing "already used by worktree" false positives).
  git -C "$REPO_ROOT" worktree prune 2>/dev/null || true

  # Check if main is actively checked out in another worktree (not just a stale ref).
  MAIN_WORKTREE=$(git -C "$REPO_ROOT" worktree list --porcelain 2>/dev/null | \
    awk '/^worktree /{wt=$2} /^branch refs\/heads\/main$/{print wt; exit}' || true)

  if [[ -n "$MAIN_WORKTREE" && "$MAIN_WORKTREE" != "$REPO_ROOT" ]]; then
    # main is actively checked out in another worktree — use it directly.
    # This avoids any stashing and works even when agents are using main.
    echo "[test-instance] main is checked out in worktree at: $MAIN_WORKTREE"
    echo "[test-instance] using existing worktree (no stash or branch switch needed)..."
    REPO_ROOT="$MAIN_WORKTREE"
  else
    DIRTY=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | grep -c '^.' || true)
    if [[ "$DIRTY" -gt 0 ]]; then
      echo "[test-instance] stashing $DIRTY uncommitted change(s) before switch..."
      git -C "$REPO_ROOT" stash push -m "start-test auto-stash before switching to main" --include-untracked 2>&1 || {
        echo "ERROR: git stash failed; commit or discard changes before running start-test.sh." >&2
        exit 1
      }
    fi
    if git -C "$REPO_ROOT" checkout main 2>/dev/null; then
      git -C "$REPO_ROOT" pull --ff-only origin main 2>&1 || true
      echo "[test-instance] switched to main — starting test server..."
    else
      # main checkout still failed (actively used by another worktree) — create a temp worktree.
      TEMP_WORKTREE="/tmp/user-test-main-$$"
      echo "[test-instance] main branch is in use; creating temporary worktree at $TEMP_WORKTREE..."
      git -C "$REPO_ROOT" fetch --quiet origin main 2>/dev/null || true
      git -C "$REPO_ROOT" worktree add "$TEMP_WORKTREE" main 2>&1 || {
        echo "ERROR: failed to create worktree for main at $TEMP_WORKTREE" >&2
        exit 1
      }
      CREATED_TEMP_WORKTREE=1
      REPO_ROOT="$TEMP_WORKTREE"
      echo "[test-instance] using temporary worktree — starting test server..."
    fi
  fi
fi

# --restart: pull latest main before starting so the user sees the newest build.
# REPO_ROOT is already resolved to wherever main lives (own worktree, existing worktree,
# or temp worktree) so this pull always targets the right directory.
if [[ $RESTART_MODE -eq 1 ]]; then
  echo "[test-instance] --restart: pulling latest origin/main..."
  git -C "$REPO_ROOT" fetch --quiet origin main 2>/dev/null || true
  if git -C "$REPO_ROOT" pull --ff-only origin main 2>&1; then
    echo "[test-instance] pull complete — restarting with latest main..."
  else
    echo "[test-instance] WARNING: pull --ff-only failed (local divergence?); starting with current code." >&2
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

# --stop: kill any process on :3000 and exit without starting a new server.
if [[ $STOP_MODE -eq 1 ]]; then
  _stop_pid=$(check_port_in_use 3000)
  if [[ -n "$_stop_pid" ]]; then
    echo "[test-instance] --stop: terminating PID $_stop_pid on :3000..."
    kill -TERM "$_stop_pid" 2>/dev/null || true
    _wait=0
    while [[ $(check_port_in_use 3000) != "" ]] && [[ $_wait -lt 50 ]]; do
      sleep 0.1
      _wait=$((_wait + 1))
    done
    if [[ $(check_port_in_use 3000) == "" ]]; then
      echo "[test-instance] test server stopped."
    else
      echo "ERROR: process on :3000 did not exit after SIGTERM" >&2
      exit 1
    fi
  else
    echo "[test-instance] no test server running on :3000."
  fi
  exit 0
fi

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
  if [[ "${CREATED_TEMP_WORKTREE:-0}" -eq 1 && -n "${TEMP_WORKTREE:-}" ]]; then
    echo "[test-instance] cleaning up temporary worktree at $TEMP_WORKTREE..."
    git -C "$ORIGINAL_REPO_ROOT" worktree remove --force "$TEMP_WORKTREE" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

# Launch test instance
# BTE_BRANCH_GATE_OK=1 tells gate-main-branch.sh (the predev hook) that we've
# already done branch verification here — skip the npm-level gate.
echo "[test-instance] spawning next dev on :3000..."
echo
cd "$REPO_ROOT/packages/web-ui"
exec env BTE_BRANCH_GATE_OK=1 "$NPM" run dev -- --port 3000
