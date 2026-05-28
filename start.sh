#!/usr/bin/env bash
# start.sh — launch the BTC Trade Engine FastAPI backend and Next.js WebUI together.
#
# Usage:
#   ./start.sh [--refuse-unhealthy] [--branch <name>] [--skip-branch-gate]
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
#   BTE_SKIP_BRANCH_GATE  if 1, bypass the main-branch enforcement (debug only).
#
# Branch-gate (BTCAAAAA-30590):
#   By default start.sh refuses to launch unless HEAD is origin/main and ff-clean,
#   or `--branch <name>` is explicitly passed. This eliminates the recurring
#   "dev server boots on a stale fix branch and 503s" cycle. If the working tree
#   has modifications under src/, start.sh, or packages/web-ui/src/, the gate
#   refuses; the operator must commit/stash/discard or pass an override.
#
# Ctrl+C (SIGINT) or SIGTERM cleanly stops both processes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Parse flags (supports --branch <name>, --branch=name, --skip-branch-gate,
# --refuse-unhealthy)
REFUSE_UNHEALTHY="${BTE_REFUSE_UNHEALTHY:-0}"
BRANCH_OVERRIDE=""
SKIP_BRANCH_GATE="${BTE_SKIP_BRANCH_GATE:-0}"
prev_arg=""
for arg in "$@"; do
  if [[ "$prev_arg" == "--branch" ]]; then
    BRANCH_OVERRIDE="$arg"
    prev_arg=""
    continue
  fi
  case "$arg" in
    --refuse-unhealthy)
      REFUSE_UNHEALTHY=1
      ;;
    --branch)
      prev_arg="--branch"
      ;;
    --branch=*)
      BRANCH_OVERRIDE="${arg#--branch=}"
      ;;
    --skip-branch-gate)
      SKIP_BRANCH_GATE=1
      ;;
  esac
done

# --- branch-gate: refuse to run on stale code (BTCAAAAA-30590) ---------------
#
# The recurring "Dev Server Offline / API error" cycle traces back to dev
# servers being launched from whichever feature branch the shared worktree
# happened to be on. Code merged to origin/main never reached the running
# process. The gate below makes it structurally impossible to launch on a
# branch other than origin/main without an explicit override.
#
# Behaviour:
#   --branch <name>        — switch to <name> first (no ff-clean check).
#   --skip-branch-gate     — print warning and continue on whatever is checked out.
#   (default)              — fetch origin/main, refuse if load-bearing files are
#                            dirty, else switch the worktree to origin/main
#                            (using `--detach` when another worktree owns the
#                            local main branch) and ff-pull.

if [[ "$SKIP_BRANCH_GATE" == "1" ]]; then
  echo "[branch-gate] skipped via --skip-branch-gate / BTE_SKIP_BRANCH_GATE=1" >&2
elif command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if [[ -n "$BRANCH_OVERRIDE" ]]; then
    echo "[branch-gate] --branch override: switching to $BRANCH_OVERRIDE"
    git -C "$REPO_ROOT" fetch --quiet origin "$BRANCH_OVERRIDE" 2>/dev/null || true
    if ! git -C "$REPO_ROOT" switch "$BRANCH_OVERRIDE" 2>/dev/null; then
      # Branch may exist only on origin, or be in use by another worktree.
      if ! git -C "$REPO_ROOT" switch --detach "origin/$BRANCH_OVERRIDE" 2>/dev/null; then
        echo "ERROR: cannot switch to '$BRANCH_OVERRIDE' (no such branch?)" >&2
        exit 1
      fi
    fi
  else
    # Default path: enforce main.
    echo "[branch-gate] enforcing branch = origin/main"
    git -C "$REPO_ROOT" fetch --quiet origin main || {
      echo "WARNING: 'git fetch origin main' failed; continuing with cached refs" >&2
    }

    # Refuse if load-bearing files are modified. We tolerate dirt outside these
    # paths (e.g. impact-gate JSON snapshots, ad-hoc test scripts) because the
    # board has explicitly OK'd "warn-and-continue on tracked dirt that isn't
    # load-bearing" — see acceptance criteria on BTCAAAAA-30590.
    LOAD_BEARING_DIRT=""
    if ! git -C "$REPO_ROOT" diff --quiet -- src/ start.sh packages/web-ui/src/ 2>/dev/null; then
      LOAD_BEARING_DIRT="unstaged"
    fi
    if ! git -C "$REPO_ROOT" diff --quiet --cached -- src/ start.sh packages/web-ui/src/ 2>/dev/null; then
      LOAD_BEARING_DIRT="${LOAD_BEARING_DIRT:+$LOAD_BEARING_DIRT,}staged"
    fi
    if [[ -n "$LOAD_BEARING_DIRT" ]]; then
      echo "ERROR: working tree has $LOAD_BEARING_DIRT modifications under" >&2
      echo "       src/, start.sh, or packages/web-ui/src/." >&2
      echo "       commit / stash / discard them, then re-run, or pass" >&2
      echo "       --branch <name> / --skip-branch-gate to override." >&2
      git -C "$REPO_ROOT" status --short -- src/ start.sh packages/web-ui/src/ >&2 || true
      exit 1
    fi

    current_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo)"
    main_sha="$(git -C "$REPO_ROOT" rev-parse origin/main 2>/dev/null || echo)"
    current_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"

    if [[ -z "$main_sha" ]]; then
      echo "ERROR: cannot resolve origin/main; aborting." >&2
      echo "       run 'git fetch origin main' manually and retry." >&2
      exit 1
    fi

    if [[ "$current_sha" != "$main_sha" ]]; then
      echo "[branch-gate] current = $current_branch ($current_sha); switching to origin/main ($main_sha)"
      # Prefer switching to the local 'main' branch and fast-forwarding it.
      # Fall back to detached HEAD on origin/main if another worktree owns 'main'.
      if git -C "$REPO_ROOT" switch main 2>/dev/null; then
        if ! git -C "$REPO_ROOT" merge --ff-only "$main_sha" 2>/dev/null; then
          echo "ERROR: local 'main' is not ff-clean with origin/main; aborting." >&2
          echo "       resolve the divergence (rebase / hard-reset) and re-run." >&2
          exit 1
        fi
      else
        echo "[branch-gate] another worktree holds 'main'; using detached HEAD"
        if ! git -C "$REPO_ROOT" switch --detach "$main_sha" 2>/dev/null; then
          echo "ERROR: cannot detach to origin/main ($main_sha)" >&2
          exit 1
        fi
      fi
    else
      echo "[branch-gate] already on origin/main ($main_sha)"
    fi
  fi
else
  echo "[branch-gate] not a git working tree; skipping" >&2
fi

# Compute the running SHA + branch so the banner, /health, and screenshots can
# cross-reference what's actually running.
if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  RUNNING_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  RUNNING_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"
else
  RUNNING_SHA="unknown"
  RUNNING_BRANCH="unknown"
fi
export BTE_RUNNING_SHA="$RUNNING_SHA"
export BTE_RUNNING_BRANCH="$RUNNING_BRANCH"

# Export only the launcher/server-bind env vars start.sh and uvicorn need
# from .env. We deliberately do NOT `source .env`: it contains values like
# `TP_FIBONACCI_LEVELS=[1.618, 2.618, 3.618]` whose unquoted whitespace bash
# would parse as KEY=firstToken followed by spurious commands, aborting the
# script under `set -e`.
#
# DB config (POSTGRES_*) is loaded inside the Python process by
# `src/optimizer_v3/database/settings.py::DatabaseSettings` (pydantic-settings),
# which reads `.env` directly — see BTCAAAAA-30576. Adding a new POSTGRES_*
# to `.env` no longer requires touching this allowlist.
#
# POSTGRES_* are still exported below as a best-effort safety net so legacy
# shell-outs (psql/pg_dump invocations) inherit the same values. New DB env
# vars should be added to `DatabaseSettings` (pydantic); the bash allowlist
# is no longer authoritative.
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

kill_orphan_next_processes() {
  local webui_dir="$1"
  local killed=()

  # Find all 'npm run dev' and 'next-server' processes.
  # We check both to catch the npm parent and any node/next-server children.
  # This matches the process tree: npm -> node -> next-server
  local pids
  # Combine results from two searches (npm dev processes and next-server)
  pids=$(
    (pgrep -f 'npm.*run dev' 2>/dev/null || true; \
     pgrep -f 'next-server' 2>/dev/null || true) | sort -u
  )

  [[ -z "$pids" ]] && return 0

  # For each candidate, check if its cwd matches the webui directory
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue

    # Read the symlink /proc/<pid>/cwd to get the process's working directory
    local proc_cwd
    proc_cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)

    # Resolve webui_dir to an absolute path for comparison
    local abs_webui_dir
    abs_webui_dir=$(readlink -f "$webui_dir" 2>/dev/null || echo "$webui_dir")

    # Match on realpath
    if [[ "$proc_cwd" == "$abs_webui_dir" ]]; then
      # This orphan is in the right directory; get uptime info for logging
      local start_time
      start_time=$(ps -o lstart= -p "$pid" 2>/dev/null | xargs || echo "unknown")

      # Kill the process group (like kill_unhealthy_service does)
      local pgid
      pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | xargs || echo "")

      if [[ -n "$pgid" && "$pgid" != "-" ]]; then
        kill -TERM "-$pgid" 2>/dev/null || true
      else
        kill -TERM "$pid" 2>/dev/null || true
      fi

      # Wait up to 5s for graceful exit
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done

      # Still alive; escalate to -KILL
      if [[ -n "$pgid" && "$pgid" != "-" ]]; then
        kill -KILL "-$pgid" 2>/dev/null || true
      else
        kill -KILL "$pid" 2>/dev/null || true
      fi

      # Wait for it to vanish
      for _ in 1 2 3; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done

      killed+=("$pid")
    fi
  done <<< "$pids"

  # Log what was killed
  if [[ ${#killed[@]} -gt 0 ]]; then
    echo "[webui] killed orphan next dev processes: ${killed[*]}"
    return 0
  fi

  return 0
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

# --- redis preflight (BTCAAAAA-30663) -----------------------------------------
#
# The backend pub/sub layer requires Redis. If redis-cli ping fails, attempt to
# start redis-server as a sidecar. If that also fails, refuse to boot the backend
# with a named error — a silent start without Redis is worse than no start.
REDIS_PORT="${BTE_REDIS_PORT:-6379}"
REDIS_HOST="${BTE_REDIS_HOST:-127.0.0.1}"

check_redis() {
  redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --no-auth-warning ping 2>/dev/null | grep -q PONG
}

if ! check_redis; then
  echo "[redis-preflight] localhost:${REDIS_PORT} is not reachable — attempting sidecar start"
  if command -v redis-server >/dev/null 2>&1; then
    redis-server --daemonize yes --port "$REDIS_PORT" --loglevel warning 2>/dev/null || true
    sleep 1
    if check_redis; then
      echo "[redis-preflight] sidecar redis-server started on :${REDIS_PORT}"
    else
      echo "ERROR: Redis is not reachable on ${REDIS_HOST}:${REDIS_PORT} and sidecar start failed." >&2
      echo "       Install and start Redis before running start.sh:" >&2
      echo "         sudo apt-get install redis-server && sudo systemctl start redis-server" >&2
      exit 1
    fi
  else
    echo "ERROR: redis-cli/redis-server not found. Redis is required by the backend." >&2
    echo "         sudo apt-get install redis-server && sudo systemctl start redis-server" >&2
    exit 1
  fi
else
  echo "[redis-preflight] Redis OK on ${REDIS_HOST}:${REDIS_PORT}"
fi

# Track PIDs of services that existed before this script ran
EXISTING_PIDS=()

check_or_skip "$BACKEND_PORT" backend || exit 1

# Pre-kill orphan 'next dev' processes whose cwd matches the webui directory
# (BTCAAAAA-30626: Next.js refuses to start a second dev instance globally per
# project, regardless of port). This must run before check_or_skip so we clear
# the lock before the port check fails.
if [[ "$REFUSE_UNHEALTHY" != "1" ]]; then
  kill_orphan_next_processes "$REPO_ROOT/packages/web-ui" || exit 1
fi

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
echo "  commit:  $RUNNING_SHA ($RUNNING_BRANCH)"
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
