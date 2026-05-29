#!/usr/bin/env bash
# start-test.sh — ephemeral test instance on :3000
#
# ⚠️  THIS IS A TEST INSTANCE
#
# Spawns its own `next dev -p 3000` (does NOT register with systemd).
# For production-like testing or supervised operation, use ./start-dev.sh on :3010.
#
# Usage:
#   ./start-test.sh                 # Spawn test on :3000
#   ./start-test.sh --branch <name> # Spawn test on <name>, not main

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

BRANCH_OVERRIDE=""
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
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-test.sh [--branch <name>]" >&2
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

# Kill any existing orphan next dev processes in this repo's web-ui directory
# Note: We don't pre-kill orphan next processes here because:
# 1. We can't distinguish between a "supervised by systemd" process and an orphan
# 2. If there's a conflict, Next.js will error (that's fine)
# 3. start-dev.sh (supervised) and start-test.sh (ephemeral) use different ports anyway

# Print the test instance notice
echo
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ⚠️  THIS IS A TEST INSTANCE on :3000                  ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ For supervised, production-like testing, use:              ║"
echo "║   ./start-dev.sh          (port :3010, systemd-managed)    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Resolve interpreters and env
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found in PATH" >&2
  exit 1
fi

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
