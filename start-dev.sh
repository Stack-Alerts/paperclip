#!/usr/bin/env bash
# start-dev.sh — canonical launcher for supervised development server on :3010
#
# Behavior:
#   1. Code-safety gate: refuses to start unless every local change is
#      committed AND pushed to GitHub (protects un-submitted work before
#      we sync/switch to origin/main).
#   2. Syncs the working tree to the latest origin/main.
#   3. Always restarts btc-dev-server.service so `next dev` recompiles the
#      newest origin/main (an already-running server is restarted too).
#   4. Waits for HTTP 200 on http://localhost:3010/
#   5. Prints the canonical URL
#   6. By default exits after readiness; --watch to tail journalctl
#
# Usage:
#   ./start-dev.sh                  # Start/verify, then exit
#   ./start-dev.sh --watch          # Start/verify, then tail logs
#
# All branch gating, main-branch enforcement, and health surveillance
# are inherited from btc-dev-server.service (see AGENTS.md).
#
# NOTE (BTCAAAAA-38800): btc-devserver-autosync.timer keeps the served
# worktree on origin/main automatically (checks every 60s after any merge),
# so running this script after each merge is no longer required — it remains
# the manual/recovery entry point.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ─── Code-safety gate (BTCAAAAA-38724) ───────────────────────────────────
# The dev server always compiles the latest origin/main. To avoid losing
# un-submitted local work when we sync/switch to main, refuse to start until
# everything is committed AND pushed to GitHub.
echo "[start-dev] verifying all local work is submitted to GitHub..."
if ! git fetch --quiet origin 2>/dev/null; then
  echo "ERROR: git fetch origin failed — check network/remote before starting." >&2
  exit 1
fi

DIRTY_COUNT=$(git status --porcelain 2>/dev/null | grep -c '^.' || true)
if [[ "$DIRTY_COUNT" -gt 0 ]]; then
  echo "" >&2
  echo "✗ Refusing to start: $DIRTY_COUNT uncommitted change(s) present." >&2
  echo "  Commit and push them before starting the dev server (code safety)." >&2
  echo "  Uncommitted paths:" >&2
  git status --porcelain 2>/dev/null | sed 's/^/    /' >&2
  exit 1
fi

# Committed-but-unpushed work on the current branch.
GATE_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GATE_UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo "")
if [[ -n "$GATE_UPSTREAM" ]]; then
  UNPUSHED=$(git rev-list "$GATE_UPSTREAM"..HEAD --count 2>/dev/null || echo "0")
  if [[ "$UNPUSHED" -gt 0 ]]; then
    echo "" >&2
    echo "✗ Refusing to start: $UNPUSHED commit(s) on '$GATE_BRANCH' are not pushed to $GATE_UPSTREAM." >&2
    echo "  Push them before starting the dev server (code safety):" >&2
    echo "    git push" >&2
    exit 1
  fi
elif [[ "$GATE_BRANCH" != "main" && "$GATE_BRANCH" != "master" ]]; then
  # No upstream tracking branch — verify HEAD is at least contained in origin/main.
  if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
    echo "" >&2
    echo "✗ Refusing to start: branch '$GATE_BRANCH' has no upstream and its commits are not on origin/main." >&2
    echo "  Push your branch to GitHub before starting (code safety):" >&2
    echo "    git push -u origin $GATE_BRANCH" >&2
    exit 1
  fi
fi
echo "[start-dev] ✓ all local work is committed and pushed"

# Early branch gate: detect non-main branch and offer branch-aware recovery.
# BTCAAAAA-39034: probe which options are actually viable (main held elsewhere?
# backend already alive? dirty tree?) instead of forcing a single "switch to main"
# path that fails silently when another worktree already has main checked out.
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
  echo ""
  echo "⚠️  You are on branch: $CURRENT_BRANCH"
  echo "   start-dev.sh prefers the main branch (btc-dev-server.service enforces this)."
  echo ""

  # ─── Diagnostics: which options are actually viable? (BTCAAAAA-39034) ──
  # 1. Is 'main' checked out in another worktree?
  MAIN_HELD_BY=""
  MAIN_HELD_SHA=""
  _wt_path=""
  while IFS= read -r line; do
    case "$line" in
      worktree*) _wt_path="${line#worktree }" ;;
      branch*)
        _br="${line#branch }"
        if [[ "$_br" == "refs/heads/main" ]]; then
          MAIN_HELD_BY="$_wt_path"
          MAIN_HELD_SHA=$(git -C "$_wt_path" rev-parse --short HEAD 2>/dev/null || echo "unknown")
        fi
        ;;
    esac
  done < <(git worktree list --porcelain)

  # 2. Is the supervised backend already responding on :8765?
  BACKEND_ALIVE=0
  if curl -sf -m 2 http://localhost:8765/health >/dev/null 2>&1; then
    BACKEND_ALIVE=1
  fi

  # 3. Is this worktree dirty?
  DIRTY=$(git status --porcelain 2>/dev/null | grep -c '^.' || true)
  if [[ "$DIRTY" -gt 0 ]]; then
    echo "⚠️  Worktree has $DIRTY uncommitted change(s):"
    git status --porcelain 2>/dev/null | sed 's/^/    /'
    echo ""
  fi

  echo "Detected state:"
  if [[ -n "$MAIN_HELD_BY" ]]; then
    echo "  ✗ 'main' is checked out in another worktree: $MAIN_HELD_BY ($MAIN_HELD_SHA)"
    echo "       → cannot 'git checkout main' here"
  else
    echo "  ✓ 'main' is not held elsewhere — checkout is possible"
  fi
  if [[ "$BACKEND_ALIVE" -eq 1 ]]; then
    echo "  ✓ supervised backend on :8765 is responding"
  else
    echo "  ✗ supervised backend on :8765 is NOT responding"
  fi
  echo ""

  # ─── Build the menu: only show options that are actually viable ────────
  OPTIONS=()
  OPT_DEFAULT_LETTER="c"

  # [s] run uvicorn from the other main worktree (only when main is held elsewhere)
  if [[ -n "$MAIN_HELD_BY" ]]; then
    OPTIONS+=("s")
  fi

  # [m] git checkout main (only when main is NOT held elsewhere)
  if [[ -z "$MAIN_HELD_BY" ]]; then
    OPTIONS+=("m")
    OPT_DEFAULT_LETTER="m"
  fi

  # [b] run uvicorn directly here (always; bypasses branch gate)
  OPTIONS+=("b")
  # If main is held elsewhere, prefer [s] as default
  if [[ "$OPT_DEFAULT_LETTER" == "c" && -n "$MAIN_HELD_BY" ]]; then
    OPT_DEFAULT_LETTER="s"
  fi

  # [i] isolated test instance (always; frontend only — :8765 still required)
  OPTIONS+=("i")

  # [t] ephemeral :3000 (always; no branch restriction)
  OPTIONS+=("t")

  # [c] cancel (always)
  OPTIONS+=("c")

  echo "Options:"
  for opt in "${OPTIONS[@]}"; do
    case "$opt" in
      s) printf "  [s] run uvicorn from %s (uses the existing main checkout)\n" "$MAIN_HELD_BY" ;;
      m) echo "  [m] git checkout main and start the dev server" ;;
      b) echo "  [b] run uvicorn directly here on $CURRENT_BRANCH (bypasses the branch gate)" ;;
      i) echo "  [i] use ./start-test-iso.sh for an isolated instance of $CURRENT_BRANCH (frontend only; UI still hits :8765)" ;;
      t) echo "  [t] use ./start-test.sh instead (ephemeral :3000, no branch restriction)" ;;
      c) echo "  [c] cancel" ;;
    esac
  done
  echo ""

  if [[ -t 0 ]]; then
    _opt_str=$(IFS=/; echo "${OPTIONS[*]}")
    read -r -p "Action? [${_opt_str}] (default: $OPT_DEFAULT_LETTER): " action
    [[ -z "$action" ]] && action="$OPT_DEFAULT_LETTER"
  else
    echo "Non-interactive: defaulting to [c] cancel." >&2
    action="c"
  fi
  case "${action,,}" in
    s)
      # Run uvicorn from the other main worktree.
      if [[ -z "$MAIN_HELD_BY" ]]; then
        echo "ERROR: option 's' is only valid when 'main' is checked out in another worktree." >&2
        exit 1
      fi
      echo "[start-dev] starting uvicorn from $MAIN_HELD_BY ($MAIN_HELD_SHA)..."
      _uv_log="$MAIN_HELD_BY/.btc-uvicorn.log"
      (
        cd "$MAIN_HELD_BY" || { echo "ERROR: cannot cd to $MAIN_HELD_BY" >&2; exit 1; }
        if [[ ! -x ./venv/bin/python ]]; then
          echo "ERROR: $MAIN_HELD_BY/venv/bin/python not executable — worktree may need bootstrap." >&2
          exit 1
        fi
        setsid nohup ./venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8765 \
          >>"$_uv_log" 2>&1 &
        echo $! >"$MAIN_HELD_BY/.btc-uvicorn.pid"
      ) || exit 1
      # Wait for /health to respond.
      _ready=0
      for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
        if curl -sf -m 2 http://localhost:8765/health >/dev/null 2>&1; then
          echo "[start-dev] ✓ uvicorn is up on :8765 (log: $_uv_log)"
          _ready=1
          break
        fi
        sleep 1
      done
      if [[ "$_ready" -ne 1 ]]; then
        echo "ERROR: uvicorn did not respond on :8765 within 15s. See $_uv_log" >&2
        exit 1
      fi
      echo "[start-dev] supervised web UI on :3010 should now connect to the backend."
      ;;
    m)
      # git checkout main — only offered when main is not held elsewhere.
      echo "[start-dev] switching to main..."
      git worktree prune 2>/dev/null || true
      if [[ "$DIRTY" -gt 0 ]]; then
        echo "[start-dev] stashing $DIRTY uncommitted change(s)..."
        git stash push -m "start-dev auto-stash before switching to main" --include-untracked 2>&1 || {
          echo "ERROR: git stash failed; commit or discard changes before switching." >&2
          exit 1
        }
      fi
      git checkout main 2>&1 || { echo "ERROR: git checkout main failed." >&2; exit 1; }
      git pull --ff-only origin main 2>&1 || { echo "ERROR: git pull --ff-only origin main failed." >&2; exit 1; }
      CURRENT_BRANCH="main"
      echo "[start-dev] now on main — continuing..."
      ;;
    b)
      # Run uvicorn directly here, bypassing the btc-dev-backend.service gate.
      # WARNING: the systemd unit won't restart this if it dies — operator owns the lifecycle.
      echo "[start-dev] starting uvicorn directly here on $CURRENT_BRANCH (bypasses branch gate)..."
      _uv_log="$REPO_ROOT/.btc-uvicorn-direct.log"
      _uv_pid="$REPO_ROOT/.btc-uvicorn-direct.pid"
      if [[ ! -x ./venv/bin/python ]]; then
        echo "ERROR: ./venv/bin/python not executable — worktree may need bootstrap." >&2
        exit 1
      fi
      setsid nohup ./venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8765 \
        >>"$_uv_log" 2>&1 &
      echo $! >"$_uv_pid"
      _ready=0
      for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
        if curl -sf -m 2 http://localhost:8765/health >/dev/null 2>&1; then
          echo "[start-dev] ✓ uvicorn is up on :8765 (pid in $_uv_pid, log: $_uv_log)"
          _ready=1
          break
        fi
        sleep 1
      done
      if [[ "$_ready" -ne 1 ]]; then
        echo "ERROR: uvicorn did not respond on :8765 within 15s. See $_uv_log" >&2
        exit 1
      fi
      echo "[start-dev] NOTE: btc-dev-backend.service is inactive; this uvicorn has no auto-restart."
      echo "[start-dev] supervised web UI on :3010 should now connect to the backend."
      ;;
    i)
      echo "[start-dev] use: ./start-test-iso.sh $CURRENT_BRANCH"
      echo "            (worktree-per-instance on a :40XX port, frontend only — UI still hits :8765)"
      exit 0
      ;;
    t)
      echo "[start-dev] use: ./start-test.sh"
      echo "            (runs on :3000, auto-switches to main, no systemd branch gate)"
      exit 0
      ;;
    c|*)
      echo "[start-dev] cancelled."
      exit 1
      ;;
  esac
fi

# ─── Always compile the latest origin/main (BTCAAAAA-38724) ───────────────
# Fast-forward the working tree to origin/main so `next dev` recompiles the
# newest merged code. Safe: the code-safety gate above guaranteed a clean,
# fully-pushed tree, so a fast-forward can never clobber local work.
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
  echo "[start-dev] syncing $CURRENT_BRANCH to latest origin/main..."
  if ! git pull --ff-only origin main 2>&1; then
    echo "ERROR: git pull --ff-only origin main failed." >&2
    exit 1
  fi
fi

WATCH=0
KILL_EXISTING=0
REUSE_EXISTING=0
CANCEL_ON_CONFLICT=0
for arg in "$@"; do
  case "$arg" in
    --watch) WATCH=1 ;;
    --kill-existing) KILL_EXISTING=1 ;;
    --reuse-existing) REUSE_EXISTING=1 ;;
    --cancel-on-conflict) CANCEL_ON_CONFLICT=1 ;;
    *)
      echo "ERROR: unknown flag: $arg" >&2
      echo "Usage: ./start-dev.sh [--watch] [--kill-existing] [--reuse-existing] [--cancel-on-conflict]" >&2
      exit 1
      ;;
  esac
done

# Port conflict detection and handling (defense-in-depth for unmanaged processes)
check_port_in_use() {
  # Must return 0 even when no listener is found: under `set -euo pipefail`,
  # the inner grep returns non-zero on no match, which would silently abort
  # any caller using `$(check_port_in_use ...)`. BTCAAAAA-32422 forensics.
  local port=$1
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || true)
  else
    pid=$(lsof -t -i :"$port" 2>/dev/null | grep -v '^$' | head -1 || true)
  fi
  echo "$pid"
}

get_service_pid() {
  systemctl --user show -p MainPID --value btc-dev-server.service 2>/dev/null || echo ""
}

handle_port_conflict() {
  local port=$1
  local pid=$2

  local cmd_line
  cmd_line=$(ps -o args= -p "$pid" 2>/dev/null || echo "unknown")
  local etime
  etime=$(ps -o etime= -p "$pid" 2>/dev/null || echo "unknown")

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠️  Port :$port is already in use by unmanaged process"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "PID:     $pid"
  echo "Command: $cmd_line"
  echo "Time:    $etime"
  echo

  if [[ $KILL_EXISTING -eq 1 ]]; then
    echo "[port-conflict] --kill-existing: terminating PID $pid..."
    kill -TERM "$pid" 2>/dev/null || true

    local wait_count=0
    while [[ $(check_port_in_use "$port") != "" ]] && [[ $wait_count -lt 50 ]]; do
      sleep 0.1
      wait_count=$((wait_count + 1))
    done

    if [[ $(check_port_in_use "$port") == "" ]]; then
      echo "[port-conflict] port :$port is now free"
      return 0
    else
      echo "ERROR: port :$port still in use after killing PID $pid" >&2
      exit 1
    fi
  elif [[ $REUSE_EXISTING -eq 1 ]]; then
    echo "[port-conflict] --reuse-existing: exiting without restarting service"
    exit 0
  elif [[ $CANCEL_ON_CONFLICT -eq 1 ]]; then
    echo "[port-conflict] --cancel-on-conflict: canceling startup"
    exit 1
  else
    echo "Choose action:"
    echo "  [k] kill PID $pid and restart service"
    echo "  [r] reuse existing server on :$port"
    echo "  [c] cancel startup"
    echo
    read -p "Action? [k/r/c]: " -r action

    case "$action" in
      k|K)
        echo "[port-conflict] killing PID $pid..."
        kill -TERM "$pid" 2>/dev/null || true

        local wait_count=0
        while [[ $(check_port_in_use "$port") != "" ]] && [[ $wait_count -lt 50 ]]; do
          sleep 0.1
          wait_count=$((wait_count + 1))
        done

        if [[ $(check_port_in_use "$port") == "" ]]; then
          echo "[port-conflict] port :$port is now free"
          return 0
        else
          echo "ERROR: port :$port still in use after killing PID $pid" >&2
          exit 1
        fi
        ;;
      r|R)
        echo "[port-conflict] reusing existing server on :$port"
        echo "[port-conflict] browse http://localhost:$port"
        exit 0
        ;;
      c|C)
        echo "[port-conflict] canceling"
        exit 1
        ;;
      *)
        echo "ERROR: invalid action '$action'" >&2
        exit 1
        ;;
    esac
  fi
}

# Check if btc-dev-server.service exists
UNIT_CHECK=$(systemctl --user list-unit-files 2>/dev/null || true)
if ! echo "$UNIT_CHECK" | grep -q btc-dev-server.service; then
  echo "ERROR: btc-dev-server.service not found in systemd user units" >&2
  echo "       Run 'deploy/systemd/install-dev-server.sh' to register the unit" >&2
  exit 1
fi

# Check current status
SERVICE_STATE=$(systemctl --user is-active btc-dev-server.service 2>/dev/null || echo "unknown")

# Defense-in-depth: check if port :3010 is held by a foreign process
TARGET_PORT=3010
PID_ON_PORT=$(check_port_in_use "$TARGET_PORT")
SERVICE_PID=$(get_service_pid)

if [[ -n "$PID_ON_PORT" ]] && [[ "$PID_ON_PORT" != "$SERVICE_PID" ]]; then
  # Foreign process is holding the port
  handle_port_conflict "$TARGET_PORT" "$PID_ON_PORT"
fi

# Always restart (BTCAAAAA-38724): restarting re-runs the service's
# ExecStartPre (which fast-forwards HEAD to origin/main) and bounces
# `next dev` so it recompiles the newest code. Restarting an already-active
# server is exactly what guarantees "always compile the latest main".
echo "[start-dev] restarting btc-dev-server.service to compile latest origin/main (was: $SERVICE_STATE)..."
if ! systemctl --user restart btc-dev-server.service 2>/dev/null; then
  echo "ERROR: failed to restart btc-dev-server.service" >&2
  systemctl --user status btc-dev-server.service 2>&1 | head -20 >&2
  exit 1
fi
sleep 1

# Wait for HTTP 200 on :3010
echo "[start-dev] waiting for http://localhost:3010/ to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
  ATTEMPT=$((ATTEMPT + 1))

  # Try IPv4
  if curl -s -4 -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:3010/" 2>/dev/null | grep -q 200; then
    echo "[start-dev] ✓ ready on :3010"
    echo
    echo "Local: http://localhost:3010"
    echo
    break
  fi

  # Try IPv6
  if curl -s -6 -o /dev/null -w '%{http_code}' -m 3 "http://[::1]:3010/" 2>/dev/null | grep -q 200; then
    echo "[start-dev] ✓ ready on :3010"
    echo
    echo "Local: http://localhost:3010"
    echo
    break
  fi

  if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "ERROR: :3010 did not respond with HTTP 200 after $MAX_ATTEMPTS attempts" >&2
    echo "       Check service logs: journalctl --user -fu btc-dev-server.service" >&2
    systemctl --user status btc-dev-server.service 2>&1 | head -10 >&2
    exit 1
  fi

  echo "[start-dev] attempt $ATTEMPT/$MAX_ATTEMPTS (waiting 1s)..."
  sleep 1
done

# If --watch, tail the journal
if [[ $WATCH -eq 1 ]]; then
  echo "[start-dev] --watch enabled; tailing journalctl (Ctrl+C to detach)..."
  echo
  journalctl --user -fu btc-dev-server.service
fi

exit 0
