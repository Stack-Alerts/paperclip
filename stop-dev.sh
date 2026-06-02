#!/usr/bin/env bash
# stop-dev.sh — gracefully stop the supervised web UI service (:3010)
#
# Behavior:
#   1. Stops btc-dev-server.service via systemctl --user
#   2. If it doesn't go inactive within 5s, force-kill the next-server PID

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "[stop-dev] stopping btc-dev-server.service..."

# Stop the service
if systemctl --user stop btc-dev-server.service 2>/dev/null; then
  echo "[stop-dev] systemctl --user stop → OK"
else
  echo "${YELLOW}[stop-dev] systemctl --user stop → FAILED${NC}"
  # Continue anyway, in case process is already gone
fi

# Wait for service to be inactive
echo "[stop-dev] waiting for graceful shutdown (5s timeout)..."
timeout=5
elapsed=0

while [[ $elapsed -lt $timeout ]]; do
  state=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "inactive")

  if [[ "$state" == "inactive" ]]; then
    echo "${GREEN}[stop-dev] ✓ service inactive${NC}"
    exit 0
  fi

  sleep 0.5
  elapsed=$((elapsed + 1))
done

echo "${YELLOW}[stop-dev] ⚠ service still active after 5s, force-killing...${NC}"

# Get the service's main PID
service_pid=$(systemctl --user show -p MainPID --value btc-dev-server.service 2>/dev/null || echo "")

if [[ -n "$service_pid" ]] && [[ "$service_pid" != "0" ]]; then
  echo "[stop-dev] SIGKILL PID $service_pid"
  if kill -9 "$service_pid" 2>/dev/null; then
    sleep 1
    if ! kill -0 "$service_pid" 2>/dev/null; then
      echo "${GREEN}[stop-dev] ✓ PID $service_pid killed${NC}"
    else
      echo "${RED}[stop-dev] ✗ PID $service_pid still alive after SIGKILL${NC}"
      exit 1
    fi
  else
    echo "${YELLOW}[stop-dev] PID $service_pid already gone${NC}"
  fi
fi

echo
echo "${GREEN}✓ Dev server stopped${NC}"
exit 0
