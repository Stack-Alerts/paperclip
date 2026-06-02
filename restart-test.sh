#!/usr/bin/env bash
# restart-test.sh — restart ephemeral test instance on :3000
#
# Usage:
#   ./restart-test.sh                   # Standard restart
#   ./restart-test.sh --clean            # Also rm -rf packages/web-ui/.next
#   ./restart-test.sh --branch <name>   # Switch to <name> then restart
#   ./restart-test.sh --clean --branch <name>
#
# Behavior:
#   1. Optionally clean .next cache
#   2. Stop the test instance
#   3. Detect hangs on :3000
#   4. Call ./start-test.sh to start fresh (which handles branch-gate)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
CLEAN=0
BRANCH=""
prev_arg=""
for arg in "$@"; do
  if [[ "$prev_arg" == "--branch" ]]; then
    BRANCH="$arg"
    prev_arg=""
    continue
  fi
  case "$arg" in
    --clean)
      CLEAN=1
      ;;
    --branch)
      prev_arg="--branch"
      ;;
    --branch=*)
      BRANCH="${arg#--branch=}"
      ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./restart-test.sh [--clean] [--branch <name>]" >&2
      exit 1
      ;;
  esac
done

# Get process holding a given port
get_port_holder() {
  local port=$1
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || true)
  else
    pid=$(lsof -t -i :"$port" 2>/dev/null | head -1 || true)
  fi
  echo "$pid"
}

echo "[restart-test] ★ restarting ephemeral test instance..."
echo

# Step 0: Optional cleanup
if [[ $CLEAN -eq 1 ]]; then
  echo "[restart-test] cleaning .next cache..."
  rm -rf "$REPO_ROOT/packages/web-ui/.next" 2>/dev/null || true
  echo "[restart-test] cache cleaned"
  echo
fi

# Step 1: Stop the test instance
echo "[restart-test] stopping current test instance..."
"$REPO_ROOT/stop-test.sh" 2>&1 | sed 's/^/  /'

# Step 2: Verify port is free
echo "[restart-test] verifying port :3000 is free..."
local port_holder
port_holder=$(get_port_holder 3000)
if [[ -n "$port_holder" ]]; then
  echo "${YELLOW}[restart-test] ⚠ port :3000 still in use, force-killing PID $port_holder...${NC}"
  if kill -9 "$port_holder" 2>/dev/null; then
    sleep 1
  fi
fi

echo

# Step 3: Start test instance with optional branch switch
echo "[restart-test] starting fresh test instance..."
local start_test_args=""
if [[ -n "$BRANCH" ]]; then
  start_test_args="--branch $BRANCH"
fi

# Run start-test.sh with automatic conflict handling
if "$REPO_ROOT/start-test.sh" $start_test_args --kill-existing --cancel-on-conflict 2>&1 | sed 's/^/  /'; then
  # start-test.sh execs into npm, so we only get here if something failed
  echo
  echo "${RED}✗ Test instance failed to start${NC}"
  exit 1
else
  exit_code=$?
  if [[ $exit_code -eq 0 ]]; then
    # This shouldn't happen since start-test.sh execs, but just in case
    echo
    echo "${GREEN}✓ Test instance restarted successfully${NC}"
    exit 0
  else
    # start-test.sh exited with error
    echo
    echo "${RED}✗ Test instance failed to start (exit code $exit_code)${NC}"
    exit 1
  fi
fi
