#!/usr/bin/env bash
# stop-backend.sh — gracefully stop the backend API service (:8765)
#
# Behavior:
#   1. Stops btc-dev-backend.service via systemctl --user
#   2. If it doesn't go inactive within 5s, force-kill the process
#   3. Handles manual uvicorn processes that might hold :8765

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Get main PID of a systemd service
get_service_pid() {
  local service=$1
  systemctl --user show -p MainPID --value "$service" 2>/dev/null || echo ""
}

echo "[stop-backend] stopping btc-dev-backend.service..."

# Stop the service
if systemctl --user stop btc-dev-backend.service 2>/dev/null; then
  echo "[stop-backend] systemctl --user stop → OK"
else
  echo "${YELLOW}[stop-backend] systemctl --user stop → FAILED${NC}"
  # Continue anyway, in case process is already gone
fi

# Wait for service to be inactive
echo "[stop-backend] waiting for graceful shutdown (5s timeout)..."
timeout=5
elapsed=0

while [[ $elapsed -lt $timeout ]]; do
  state=$(systemctl --user is-active btc-dev-backend.service 2>/dev/null || echo "inactive")

  if [[ "$state" == "inactive" ]]; then
    echo "${GREEN}[stop-backend] ✓ service inactive${NC}"
    exit 0
  fi

  sleep 0.5
  elapsed=$((elapsed + 1))
done

echo "${YELLOW}[stop-backend] ⚠ service still active after 5s, force-killing...${NC}"

# Get the service's main PID
service_pid=$(get_service_pid btc-dev-backend.service)

if [[ -n "$service_pid" ]] && [[ "$service_pid" != "0" ]]; then
  echo "[stop-backend] SIGKILL PID $service_pid (service cgroup)"
  if kill -9 "$service_pid" 2>/dev/null; then
    sleep 1
    if ! kill -0 "$service_pid" 2>/dev/null; then
      echo "${GREEN}[stop-backend] ✓ PID $service_pid killed${NC}"
    else
      echo "${RED}[stop-backend] ✗ PID $service_pid still alive after SIGKILL${NC}"
      exit 1
    fi
  else
    echo "${YELLOW}[stop-backend] PID $service_pid already gone${NC}"
  fi
fi

# Also check for any stray uvicorn holding :8765
port_holder=$(get_port_holder 8765)

if [[ -n "$port_holder" ]]; then
  echo "${YELLOW}[stop-backend] ⚠ unmanaged process still holds :8765 (PID $port_holder), killing...${NC}"
  if kill -9 "$port_holder" 2>/dev/null; then
    sleep 1
    echo "${GREEN}[stop-backend] ✓ PID $port_holder killed${NC}"
  else
    echo "${RED}[stop-backend] ✗ failed to kill PID $port_holder${NC}"
    exit 1
  fi
fi

echo
echo "${GREEN}✓ Backend stopped${NC}"
exit 0
