#!/usr/bin/env bash
# restart-dev.sh — restart supervised dev server with hang detection
#
# Usage:
#   ./restart-dev.sh              # Standard restart
#   ./restart-dev.sh --clean      # Also rm -rf packages/web-ui/.next/dev
#
# Behavior:
#   1. Optionally clean .next cache
#   2. Stop the dev server
#   3. Detect hangs on :3010 (port bound but no HTTP response)
#   4. Start btc-dev-server.service
#   5. Poll for HTTP 200 on :3010 (timeout 30s)

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
for arg in "$@"; do
  case "$arg" in
    --clean)
      CLEAN=1
      ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./restart-dev.sh [--clean]" >&2
      exit 1
      ;;
  esac
done

# Detect if a hang is in progress (port bound but service unresponsive)
detect_hang() {
  local port=$1
  timeout=2
  local probe_threshold=3
  local consecutive_failures=0

  # Is the port bound?
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || true)
  else
    pid=$(lsof -t -i :"$port" 2>/dev/null | head -1 || true)
  fi

  if [[ -z "$pid" ]]; then
    # Port is free, no hang
    return 1
  fi

  # Port is bound. Try HTTP probes.
  for i in {1..3}; do
    if curl -s -4 -o /dev/null -w '%{http_code}' -m "$timeout" "http://127.0.0.1:$port/" 2>/dev/null | grep -q 200; then
      # Service is responding, no hang
      return 1
    fi

    # Also try IPv6
    if curl -s -6 -o /dev/null -w '%{http_code}' -m "$timeout" "http://[::1]:$port/" 2>/dev/null | grep -q 200; then
      # Service is responding, no hang
      return 1
    fi

    consecutive_failures=$((consecutive_failures + 1))
  done

  # 3 consecutive probe failures with port bound = hang detected
  if [[ $consecutive_failures -ge $probe_threshold ]]; then
    echo "Hang detected on :$port (PID $pid unresponsive)"
    return 0
  fi

  return 1
}

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

echo "[restart-dev] ★ restarting supervised dev server..."
echo

# Step 0: Optional cleanup
if [[ $CLEAN -eq 1 ]]; then
  echo "[restart-dev] cleaning .next/dev cache..."
  rm -rf "$REPO_ROOT/packages/web-ui/.next/dev" 2>/dev/null || true
  echo "[restart-dev] cache cleaned"
  echo
fi

# Step 1: Stop the service (gracefully)
echo "[restart-dev] stopping current instance..."
"$REPO_ROOT/stop-dev.sh" 2>&1 | sed 's/^/  /'

# Step 2: Detect if there's a hang
echo "[restart-dev] checking for hangs..."
if detect_hang 3010; then
  echo "${YELLOW}[restart-dev] ⚠ hang detected, force-killing...${NC}"
  hung_pid=$(get_port_holder 3010)
  if [[ -n "$hung_pid" ]]; then
    kill -9 "$hung_pid" 2>/dev/null || true
    sleep 1
  fi
else
  echo "[restart-dev] no hang detected"
fi

echo

# Step 3: Verify port is free
port_holder=$(get_port_holder 3010)
if [[ -n "$port_holder" ]]; then
  echo "${RED}[restart-dev] ✗ port :3010 still in use by PID $port_holder${NC}"
  exit 1
fi

# Step 4: Start the service
echo "[restart-dev] starting btc-dev-server.service..."
if ! systemctl --user start btc-dev-server.service 2>/dev/null; then
  echo "${RED}[restart-dev] ✗ failed to start service${NC}"
  systemctl --user status btc-dev-server.service 2>&1 | head -20 | sed 's/^/  /'
  exit 1
fi

sleep 1

# Step 5: Poll for readiness
echo "[restart-dev] waiting for HTTP 200 on :3010..."
max_attempts=30
attempt=0

while [[ $attempt -lt $max_attempts ]]; do
  attempt=$((attempt + 1))

  # Try IPv4
  if curl -s -4 -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:3010/" 2>/dev/null | grep -q 200; then
    echo "[restart-dev] attempt $attempt/$max_attempts → ${GREEN}✓ ready${NC}"
    echo
    echo "${GREEN}✓ Dev server restarted successfully${NC}"
    exit 0
  fi

  # Try IPv6
  if curl -s -6 -o /dev/null -w '%{http_code}' -m 3 "http://[::1]:3010/" 2>/dev/null | grep -q 200; then
    echo "[restart-dev] attempt $attempt/$max_attempts → ${GREEN}✓ ready${NC}"
    echo
    echo "${GREEN}✓ Dev server restarted successfully${NC}"
    exit 0
  fi

  if [[ $attempt -eq $max_attempts ]]; then
    echo "[restart-dev] attempt $attempt/$max_attempts → ${RED}✗ TIMEOUT${NC}"
    echo
    echo "${RED}✗ Dev server did not become ready in 30s${NC}"
    echo
    echo "Service status:"
    systemctl --user status btc-dev-server.service 2>&1 | head -20 | sed 's/^/  /'
    exit 1
  fi

  echo "[restart-dev] attempt $attempt/$max_attempts (waiting 1s)..."
  sleep 1
done
