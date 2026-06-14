#!/usr/bin/env bash
# stop-test.sh — gracefully stop the ephemeral test instance on :3000
#
# Behavior:
#   1. Finds the `next dev -p 3000` process from THIS checkout
#   2. Sends SIGTERM
#   3. Waits 5s for graceful shutdown
#   4. If still running, sends SIGKILL

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the next dev process bound to :3000 from THIS checkout
get_test_pid() {
  local test_pid=""

  # Try ss first (more reliable)
  if command -v ss >/dev/null 2>&1; then
    test_pid=$(ss -tlnp 2>/dev/null | grep ":3000 " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || echo "")
  else
    test_pid=$(lsof -t -i :3000 2>/dev/null | head -1 || echo "")
  fi

  if [[ -z "$test_pid" ]]; then
    return 1
  fi

  # Verify it's from this checkout
  local cwd=""
  if [[ -r /proc/$test_pid/cwd ]]; then
    cwd=$(realpath /proc/$test_pid/cwd 2>/dev/null || echo "")
  fi

  local repo_real
  repo_real=$(realpath "$REPO_ROOT" 2>/dev/null || echo "$REPO_ROOT")

  if [[ "$cwd" != "$repo_real" ]] && [[ "$cwd" != "$repo_real/packages/web-ui" ]]; then
    # Foreign process
    return 1
  fi

  echo "$test_pid"
  return 0
}

echo "[stop-test] looking for ephemeral test instance on :3000..."

test_pid=$(get_test_pid || echo "")

if [[ -z "$test_pid" ]]; then
  echo "[stop-test] no test instance found on :3000"
  exit 0
fi

echo "[stop-test] found PID $test_pid, sending SIGTERM..."
if ! kill -TERM "$test_pid" 2>/dev/null; then
  echo "${YELLOW}[stop-test] PID $test_pid already gone${NC}"
  exit 0
fi

# Wait for graceful shutdown
echo "[stop-test] waiting for graceful shutdown (5s timeout)..."
timeout=5
elapsed=0

while [[ $elapsed -lt $timeout ]]; do
  if ! kill -0 "$test_pid" 2>/dev/null; then
    echo "${GREEN}[stop-test] ✓ PID $test_pid exited gracefully${NC}"
    exit 0
  fi

  sleep 0.5
  elapsed=$((elapsed + 1))
done

# Still running, force kill
echo "${YELLOW}[stop-test] ⚠ PID $test_pid still running, sending SIGKILL...${NC}"
if kill -9 "$test_pid" 2>/dev/null; then
  sleep 0.5
  if ! kill -0 "$test_pid" 2>/dev/null; then
    echo "${GREEN}[stop-test] ✓ PID $test_pid killed${NC}"
  else
    echo "${RED}[stop-test] ✗ PID $test_pid still alive after SIGKILL${NC}"
    exit 1
  fi
else
  echo "${YELLOW}[stop-test] PID $test_pid already gone${NC}"
fi

echo
echo "${GREEN}✓ Test instance stopped${NC}"
exit 0
