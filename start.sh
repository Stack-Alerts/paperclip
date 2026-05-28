#!/usr/bin/env bash
# start.sh — launch the BTC Trade Engine FastAPI backend and Next.js WebUI together.
#
# Usage:
#   ./start.sh [--refuse-unhealthy]
#
# Environment overrides:
#   BTE_API_HOST          backend bind host (default: 0.0.0.0)
#   BTE_API_PORT          backend port      (default: 8765)
#   BTE_WEBUI_PORT        WebUI port        (default: 3000)
#   BTE_REFUSE_UNHEALTHY  if 1, preserve old behaviour (refuse instead of kill)
#   BTE_API_DEV_MODE      if 1, accept loopback WebSocket handshakes WITHOUT a JWT
#                         (dev-only — the WebUI cannot mint browser-side tokens).
#                         REST endpoints already short-circuit auth under this flag.
#                         Non-loopback origins are NEVER auto-trusted.
#                         NEVER set this in production.
#
# Ctrl+C (SIGINT) or SIGTERM cleanly stops both processes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Parse flags
REFUSE_UNHEALTHY="${BTE_REFUSE_UNHEALTHY:-0}"
for arg in "$@"; do
  case "$arg" in
    --refuse-unhealthy)
      REFUSE_UNHEALTHY=1
      ;;
  esac
done

# Export only the env vars start.sh, uvicorn, and the strategy-builder DB code
# actually consume from .env. We deliberately do NOT `source .env`: it contains
# values like `TP_FIBONACCI_LEVELS=[1.618, 2.618, 3.618]` whose unquoted
# whitespace bash would parse as KEY=firstToken followed by spurious commands,
# aborting the script under `set -e`. Pydantic-settings-backed config loads
# .env directly; but `src/optimizer_v3/database/database_manager.py` reads
# POSTGRES_* via raw os.getenv (BTCAAAAA-30562), so those must be exported
# here too, otherwise /strategy-builder/strategies returns 503.
if [[ -f "$REPO_ROOT/.env" ]]; then
  while IFS= read -r line; do
    line="${line%$'\r'}"
    case "$line" in
      BTE_API_DEV_MODE=*|BTE_API_HOST=*|BTE_API_PORT=*|BTE_API_LOG=*|BTE_WEBUI_PORT=*|\
      POSTGRES_HOST=*|POSTGRES_PORT=*|POSTGRES_DB=*|POSTGRES_USER=*|POSTGRES_PASSWORD=*|POSTGRES_SCHEMA=*)
        export "${line?}"
        ;;
    esac
  done < "$REPO_ROOT/.env"
fi

BACKEND_HOST="${BTE_API_HOST:-0.0.0.0}"
BACKEND_PORT="${BTE_API_PORT:-8765}"
WEBUI_PORT="${BTE_WEBUI_PORT:-3000}"

# --- resolve client-facing backend URL for frontend ---------------------------
# Backend bind host (0.0.0.0) isn't a valid client URL; default the client-facing
# host to localhost. Next.js inlines NEXT_PUBLIC_* env vars at the dev-server's
# process start, so these must be exported before the webui launch.
BACKEND_PUBLIC_HOST="${BTE_API_PUBLIC_HOST:-${BACKEND_HOST}}"
if [[ "$BACKEND_PUBLIC_HOST" == "0.0.0.0" || -z "$BACKEND_PUBLIC_HOST" ]]; then
  BACKEND_PUBLIC_HOST="localhost"
fi
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${BACKEND_PUBLIC_HOST}:${BACKEND_PORT}}"
export NEXT_PUBLIC_BRIDGE_WS_URL="${NEXT_PUBLIC_BRIDGE_WS_URL:-ws://${BACKEND_PUBLIC_HOST}:${BACKEND_PORT}}"

# --- pre-flight: check ports and probe health if in use ----------------------

get_port_pid() {
  local port="$1" pid=""

  # Prefer `ss` (works without root for current-user sockets and catches both
  # IPv4 and IPv6 listeners); fall back to `lsof` if `ss` is missing.
  if command -v ss >/dev/null 2>&1; then
    pid="$(ss -lntpH "sport = :$port" 2>/dev/null \
      | grep -oE 'pid=[0-9]+' | head -n1 | cut -d= -f2 || true)"
  fi
  if [[ -z "$pid" ]] && command -v lsof >/dev/null 2>&1; then
    pid="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
  fi

  echo "$pid"
}

probe_health() {
  local port="$1" label="$2"
  # Check if the service is accepting connections (any HTTP response).
  # Try IPv4, then IPv6; return 0 if either succeeds.
  # Timeout 5s per attempt to allow for cold-start compilation spikes.

  # Try IPv4
  curl -s -4 -o /dev/null -m 5 "http://127.0.0.1:$port/" 2>/dev/null && return 0

  # Try IPv6
  curl -s -6 -o /dev/null -m 5 "http://[::1]:$port/" 2>/dev/null && return 0

  # First attempt failed; sleep 1s and retry (catches mid-compile transients)
  sleep 1

  # Retry IPv4
  curl -s -4 -o /dev/null -m 5 "http://127.0.0.1:$port/" 2>/dev/null && return 0

  # Retry IPv6
  curl -s -6 -o /dev/null -m 5 "http://[::1]:$port/" 2>/dev/null && return 0

  return 1
}

kill_unhealthy_service() {
  local port="$1" label="$2" pid="$3"
  echo "port $port ($label) is in use by PID $pid but health probe failed — killing and restarting"

  # Get the process group ID (pgid) of the PID
  local pgid
  pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | xargs || echo "")

  if [[ -n "$pgid" && "$pgid" != "-" ]]; then
    # PID is a pgid leader; kill the whole group
    kill -TERM "-$pgid" 2>/dev/null || true
  else
    # Not a group leader; kill the PID directly
    kill -TERM "$pid" 2>/dev/null || true
  fi

  # Wait up to 5s for graceful exit
  for _ in 1 2 3 4 5; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1
  done

  # Still alive; escalate to -KILL
  if [[ -n "$pgid" && "$pgid" != "-" ]]; then
    kill -KILL "-$pgid" 2>/dev/null || true
  else
    kill -KILL "$pid" 2>/dev/null || true
  fi

  # Wait up to 3s for the process to vanish
  for _ in 1 2 3; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done

  # Re-check the port is free (busy-wait up to 8s)
  for i in {1..8}; do
    local new_pid
    new_pid="$(get_port_pid "$port")"
    if [[ -z "$new_pid" ]]; then
      echo "port $port ($label) is now free — restarting service"
      return 0
    fi
    sleep 1
  done

  # Port still busy after 8s
  echo "ERROR: port $port ($label) still in use after killing PID $pid" >&2
  echo "       (possibly a different process now owns the port)." >&2
  return 1
}

check_or_skip() {
  local port="$1" label="$2" pid=""

  pid="$(get_port_pid "$port")"

  if [[ -z "$pid" ]]; then
    # Port is free, service will be started later
    return 0
  fi

  # Port is in use; probe health
  if probe_health "$port" "$label"; then
    echo "$label already up on :$port (pid $pid) — skipping launch"
    # Mark this as "already running" (by appending to EXISTING_PIDS)
    EXISTING_PIDS+=("$label:$pid")
    return 0
  fi

  # Port in use but unhealthy
  if [[ "$REFUSE_UNHEALTHY" == "1" ]]; then
    # Old behaviour: refuse
    echo "ERROR: port $port ($label) is already in use by PID $pid" >&2
    echo "       and the service appears unhealthy (health probe failed)." >&2
    echo "       refusing to start — stop that process first, or set a different port." >&2
    return 1
  fi

  # New behaviour: kill and restart
  if kill_unhealthy_service "$port" "$label" "$pid"; then
    # Port is now free; fall through to normal launch
    return 0
  fi

  # Kill failed; refuse
  return 1
}

# Track PIDs of services that existed before this script ran
EXISTING_PIDS=()

check_or_skip "$BACKEND_PORT" backend || exit 1
check_or_skip "$WEBUI_PORT"   webui   || exit 1

# --- resolve interpreters ----------------------------------------------------

if [[ -x "$REPO_ROOT/venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "ERROR: no python interpreter found (looked for venv/bin/python and python3)" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found in PATH" >&2
  exit 1
fi
NPM="$(command -v npm)"

# --- child process bookkeeping ----------------------------------------------
#
# Each service is launched via `setsid` so it gets its own process group
# (pgid == leader pid). On shutdown we signal the whole group with
# `kill -- -<pgid>`, which reaches grandchildren (npm -> node -> next-server)
# that would otherwise survive being orphaned to init.

BACKEND_PID=""
WEBUI_PID=""

kill_group() {
  local pid="$1" signal="$2"
  [[ -z "$pid" ]] && return 0
  kill "$signal" "-$pid" 2>/dev/null || true
}

cleanup() {
  trap - INT TERM EXIT
  echo
  echo "Stopping services (only those started by this invocation)..."

  # Only kill services this invocation started, not pre-existing ones
  kill_group "$BACKEND_PID" -TERM
  kill_group "$WEBUI_PID"   -TERM

  # allow up to 5s for graceful shutdown, then escalate
  for _ in 1 2 3 4 5; do
    local alive=0
    for pid in "$BACKEND_PID" "$WEBUI_PID"; do
      [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && alive=1
    done
    [[ $alive -eq 0 ]] && break
    sleep 1
  done

  kill_group "$BACKEND_PID" -KILL
  kill_group "$WEBUI_PID"   -KILL

  wait 2>/dev/null || true
  echo "Stopped."
}
trap cleanup INT TERM EXIT

# --- launch ------------------------------------------------------------------

echo "Starting BTC Trade Engine..."
echo "  Backend: http://localhost:${BACKEND_PORT}"
echo "  WebUI:   http://localhost:${WEBUI_PORT}"
echo "  api url: $NEXT_PUBLIC_API_URL"
echo "  ws url:  $NEXT_PUBLIC_BRIDGE_WS_URL"
echo "  (Ctrl+C to stop)"
echo

# Backend (FastAPI via uvicorn); sed -u keeps the prefixed stream unbuffered.
BACKEND_EXISTING=0
for existing in "${EXISTING_PIDS[@]}"; do
  if [[ "$existing" == backend:* ]]; then
    BACKEND_EXISTING=1
    break
  fi
done

if [[ $BACKEND_EXISTING -eq 0 ]]; then
  setsid bash -c "
    cd '$REPO_ROOT' || exit 1
    '$PYTHON' -m uvicorn src.api.app:app \
      --host '$BACKEND_HOST' \
      --port '$BACKEND_PORT' 2>&1 \
      | sed -u 's/^/[backend] /'
  " &
  BACKEND_PID=$!
fi

# Frontend (Next.js dev server)
WEBUI_EXISTING=0
for existing in "${EXISTING_PIDS[@]}"; do
  if [[ "$existing" == webui:* ]]; then
    WEBUI_EXISTING=1
    break
  fi
done

if [[ $WEBUI_EXISTING -eq 0 ]]; then
  setsid bash -c "
    cd '$REPO_ROOT/packages/web-ui' || exit 1
    '$NPM' run dev -- --port '$WEBUI_PORT' 2>&1 \
      | sed -u 's/^/[webui] /'
  " &
  WEBUI_PID=$!
fi

# Print summary
echo "Status:"
if [[ -n "$BACKEND_PID" ]]; then
  echo "  backend: started PID $BACKEND_PID"
elif [[ $BACKEND_EXISTING -eq 1 ]]; then
  # Extract PID from EXISTING_PIDS
  for existing in "${EXISTING_PIDS[@]}"; do
    if [[ "$existing" == backend:* ]]; then
      echo "  backend: already up PID ${existing#backend:}"
      break
    fi
  done
fi

if [[ -n "$WEBUI_PID" ]]; then
  echo "  webui: started PID $WEBUI_PID"
elif [[ $WEBUI_EXISTING -eq 1 ]]; then
  # Extract PID from EXISTING_PIDS
  for existing in "${EXISTING_PIDS[@]}"; do
    if [[ "$existing" == webui:* ]]; then
      echo "  webui: already up PID ${existing#webui:}"
      break
    fi
  done
fi

echo

# If neither service was started, exit immediately (both were already running)
if [[ -z "$BACKEND_PID" && -z "$WEBUI_PID" ]]; then
  echo "Both services already up. Exiting (nothing to supervise)."
  exit 0
fi

# If either side dies, fall through and let `cleanup` shut the other down.
wait -n 2>/dev/null || true
exit 1
