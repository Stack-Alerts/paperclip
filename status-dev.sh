#!/usr/bin/env bash
# status-dev.sh — health check for all dev/test services
#
# Prints state of three services:
#   1. Backend API (:8765) — btc-dev-backend.service
#   2. Supervised web UI (:3010) — btc-dev-server.service
#   3. Ephemeral test web UI (:3000) — ephemeral next dev process
#
# For each: HTTP probe (timeout 2s), PID, uptime, git branch+SHA (backend only).
# Exits 0 if all healthy, non-zero if any service is degraded.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall health
OVERALL_HEALTH=0

# Probe a service with HTTP GET, timeout 2s
http_probe() {
  local port=$1
  local path="${2:-/}"
  local timeout=2

  # Try IPv4 first, then IPv6
  if curl -s -4 -o /dev/null -w '%{http_code}' -m "$timeout" "http://127.0.0.1:$port$path" 2>/dev/null | grep -q 200; then
    return 0
  fi

  if curl -s -6 -o /dev/null -w '%{http_code}' -m "$timeout" "http://[::1]:$port$path" 2>/dev/null | grep -q 200; then
    return 0
  fi

  return 1
}

# Get process uptime in human-readable format
get_uptime() {
  local pid=$1
  if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
    echo "N/A"
    return
  fi

  local etime
  etime=$(ps -o etime= -p "$pid" 2>/dev/null || echo "N/A")
  echo "$etime"
}

# Check backend service (:8765)
check_backend() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Backend API (:8765) — btc-dev-backend.service"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local service_state
  service_state=$(systemctl --user is-active btc-dev-backend.service 2>/dev/null || echo "unknown")

  local service_pid
  service_pid=$(systemctl --user show -p MainPID --value btc-dev-backend.service 2>/dev/null || echo "")

  echo "Service state: $service_state"

  if [[ -z "$service_pid" || "$service_pid" == "0" ]]; then
    echo "Service PID:   [not running]"
    echo "Uptime:        N/A"
    echo "HTTP probe:    ${RED}✗ FAIL${NC} (service not running)"
    OVERALL_HEALTH=1
    return 1
  fi

  echo "Service PID:   $service_pid"
  echo "Uptime:        $(get_uptime "$service_pid")"

  # HTTP probe
  if http_probe 8765 /health; then
    echo "HTTP probe:    ${GREEN}✓ OK${NC}"
  else
    echo "HTTP probe:    ${RED}✗ FAIL${NC} (no response in 2s)"
    OVERALL_HEALTH=1
    return 1
  fi

  # Backend reports SHA in /health
  local sha
  sha=$(curl -s -m 2 "http://127.0.0.1:8765/health" 2>/dev/null | grep -o '"sha":"[^"]*' | cut -d'"' -f4 || echo "unknown")
  echo "Backend SHA:   $sha"

  echo
  return 0
}

# Check supervised web UI (:3010)
check_dev_server() {
  echo "Supervised Web UI (:3010) — btc-dev-server.service"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local service_state
  service_state=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "unknown")

  local service_pid
  service_pid=$(systemctl --user show -p MainPID --value btc-dev-server.service 2>/dev/null || echo "")

  echo "Service state: $service_state"

  if [[ -z "$service_pid" || "$service_pid" == "0" ]]; then
    echo "Service PID:   [not running]"
    echo "Uptime:        N/A"
    echo "HTTP probe:    ${YELLOW}⚠ WARNING${NC} (service not running)"
    return 1
  fi

  echo "Service PID:   $service_pid"
  echo "Uptime:        $(get_uptime "$service_pid")"

  # HTTP probe
  if http_probe 3010; then
    echo "HTTP probe:    ${GREEN}✓ OK${NC}"
  else
    echo "HTTP probe:    ${RED}✗ FAIL${NC} (no response in 2s)"
    OVERALL_HEALTH=1
    return 1
  fi

  echo
  return 0
}

# Check ephemeral test instance (:3000)
check_test_instance() {
  echo "Ephemeral Test Web UI (:3000) — next dev process"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Find the next dev process bound to :3000 from this checkout
  local test_pid=""

  # Try ss first (more reliable)
  if command -v ss >/dev/null 2>&1; then
    test_pid=$(ss -tlnp 2>/dev/null | grep ":3000 " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || echo "")
  else
    test_pid=$(lsof -t -i :3000 2>/dev/null | head -1 || echo "")
  fi

  if [[ -z "$test_pid" ]]; then
    echo "Process PID:   [not running]"
    echo "Uptime:        N/A"
    echo "HTTP probe:    ${YELLOW}⚠ WARNING${NC} (not running)"
    return 1
  fi

  # Verify it's actually from this checkout
  local cwd=""
  if [[ -r /proc/$test_pid/cwd ]]; then
    cwd=$(realpath /proc/$test_pid/cwd 2>/dev/null || echo "")
  fi

  local repo_real
  repo_real=$(realpath "$REPO_ROOT" 2>/dev/null || echo "$REPO_ROOT")

  if [[ "$cwd" != "$repo_real" ]] && [[ "$cwd" != "$repo_real/packages/web-ui" ]]; then
    echo "Process PID:   $test_pid (from different repo: $cwd)"
    echo "Uptime:        $(get_uptime "$test_pid")"
    echo "HTTP probe:    ${YELLOW}⚠ WARNING${NC} (foreign process on :3000)"
    return 1
  fi

  echo "Process PID:   $test_pid"
  echo "Uptime:        $(get_uptime "$test_pid")"

  # HTTP probe
  if http_probe 3000; then
    echo "HTTP probe:    ${GREEN}✓ OK${NC}"
  else
    echo "HTTP probe:    ${RED}✗ FAIL${NC} (no response in 2s)"
    OVERALL_HEALTH=1
    return 1
  fi

  echo
  return 0
}

# Check git state
check_git_state() {
  echo "Git State"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local head_sha
  head_sha=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
  local head_branch
  head_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

  local main_sha
  main_sha=$(git rev-parse origin/main 2>/dev/null || echo "unknown")

  echo "HEAD branch:   $head_branch"
  echo "HEAD SHA:      $head_sha"
  echo "origin/main:   $main_sha"

  if [[ "$head_sha" != "$main_sha" ]]; then
    echo "Status:        ${YELLOW}⚠ DRIFT${NC} (HEAD != origin/main)"
  else
    echo "Status:        ${GREEN}✓ OK${NC} (in sync with origin/main)"
  fi

  echo
}

# Main flow
echo
check_backend
check_dev_server
check_test_instance
check_git_state

if [[ $OVERALL_HEALTH -eq 0 ]]; then
  echo "${GREEN}✓ All services healthy${NC}"
  exit 0
else
  echo "${RED}✗ One or more services degraded${NC}"
  exit 1
fi
