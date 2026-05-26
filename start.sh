#!/usr/bin/env bash
# start.sh — launch the BTC Trade Engine FastAPI backend and Next.js WebUI together.
#
# Usage:
#   ./start.sh
#
# Environment overrides:
#   BTE_API_HOST   backend bind host (default: 0.0.0.0)
#   BTE_API_PORT   backend port      (default: 8765)
#   BTE_WEBUI_PORT WebUI port        (default: 3000)
#
# Ctrl+C (SIGINT) or SIGTERM cleanly stops both processes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Export only the env vars start.sh and uvicorn actually consume from .env.
# We deliberately do NOT `source .env`: it contains values like
# `TP_FIBONACCI_LEVELS=[1.618, 2.618, 3.618]` whose unquoted whitespace bash
# would parse as KEY=firstToken followed by spurious commands, aborting the
# script under `set -e`. .env is consumed by Pydantic Settings / python-dotenv
# inside the app, which handles those literal values correctly.
if [[ -f "$REPO_ROOT/.env" ]]; then
  while IFS= read -r line; do
    line="${line%$'\r'}"
    case "$line" in
      BTE_API_DEV_MODE=*|BTE_API_HOST=*|BTE_API_PORT=*|BTE_API_LOG=*|BTE_WEBUI_PORT=*)
        export "${line?}"
        ;;
    esac
  done < "$REPO_ROOT/.env"
fi

BACKEND_HOST="${BTE_API_HOST:-0.0.0.0}"
BACKEND_PORT="${BTE_API_PORT:-8765}"
WEBUI_PORT="${BTE_WEBUI_PORT:-3000}"

# --- pre-flight: refuse to start if either port is already in use ------------

check_port() {
  local port="$1" label="$2" pid=""

  # Prefer `ss` (works without root for current-user sockets and catches both
  # IPv4 and IPv6 listeners); fall back to `lsof` if `ss` is missing.
  if command -v ss >/dev/null 2>&1; then
    pid="$(ss -lntpH "sport = :$port" 2>/dev/null \
      | grep -oE 'pid=[0-9]+' | head -n1 | cut -d= -f2 || true)"
  fi
  if [[ -z "$pid" ]] && command -v lsof >/dev/null 2>&1; then
    pid="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
  fi

  if [[ -n "$pid" ]]; then
    echo "ERROR: port $port ($label) is already in use by PID $pid" >&2
    echo "       refusing to start — stop that process first, or set a different port." >&2
    return 1
  fi
}

check_port "$BACKEND_PORT" backend
check_port "$WEBUI_PORT"   webui

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
  echo "Stopping services..."

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
echo "  (Ctrl+C to stop)"
echo

# Backend (FastAPI via uvicorn); sed -u keeps the prefixed stream unbuffered.
setsid bash -c "
  cd '$REPO_ROOT' || exit 1
  '$PYTHON' -m uvicorn src.api.app:app \
    --host '$BACKEND_HOST' \
    --port '$BACKEND_PORT' 2>&1 \
    | sed -u 's/^/[backend] /'
" &
BACKEND_PID=$!

# Frontend (Next.js dev server)
setsid bash -c "
  cd '$REPO_ROOT/packages/web-ui' || exit 1
  '$NPM' run dev -- --port '$WEBUI_PORT' 2>&1 \
    | sed -u 's/^/[webui] /'
" &
WEBUI_PID=$!

# If either side dies, fall through and let `cleanup` shut the other down.
wait -n 2>/dev/null || true
exit 1
