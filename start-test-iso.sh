#!/usr/bin/env bash
# start-test-iso.sh — worktree-per-instance launcher (BTCAAAAA-38277 / plan BTCAAAAA-38260)
#
# Spawns each test/dev instance in its own git worktree under ~/btc-test-worktrees/
# with a deterministic per-branch port in 4000-4999. Coexists with btc-dev-server
# on :3010 — never binds :3000 or :3010 itself.
#
# Usage:
#   ./start-test-iso.sh                         # start instance for main
#   ./start-test-iso.sh <branch>                # start instance for branch
#   ./start-test-iso.sh <branch>@<sha>          # start instance detached at sha
#   ./start-test-iso.sh --no-pull <branch>      # skip git fetch
#   ./start-test-iso.sh --list
#   ./start-test-iso.sh --status <branch>
#   ./start-test-iso.sh --stop <branch>
#   ./start-test-iso.sh --restart <branch>
#   ./start-test-iso.sh --nuke <branch>
#   ./start-test-iso.sh --logs <branch>
#   ./start-test-iso.sh --doctor
#
# Port-conflict resolution (passed through to next dev startup):
#   --kill-existing | --reuse-existing | --cancel-on-conflict

set -euo pipefail

# ----------------------------------------------------------------------------
# Paths and constants
# ----------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIMARY_REPO_ROOT="$REPO_ROOT"

WORKTREE_ROOT="${BTC_TEST_WORKTREES:-$HOME/btc-test-worktrees}"
REGISTRY_DIR="$HOME/.btc-test-iso"
REGISTRY_FILE="$REGISTRY_DIR/registry.json"
LOCK_FILE="$REGISTRY_DIR/registry.lock"

PORT_MIN=4000
PORT_MAX=4999
PORT_SPAN=$((PORT_MAX - PORT_MIN + 1))

PROTECTED_PORTS=(3000 3010)

mkdir -p "$WORKTREE_ROOT" "$REGISTRY_DIR"
: > "$LOCK_FILE"

# ----------------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------------
CMD="start"
BRANCH_ARG=""
NO_PULL=0
KILL_EXISTING=0
REUSE_EXISTING=0
CANCEL_ON_CONFLICT=0
TARGET_BRANCH=""   # used by --status / --stop / --restart / --nuke / --logs

prev_arg=""
for arg in "$@"; do
  if [[ "$prev_arg" == "--status" || "$prev_arg" == "--stop" \
     || "$prev_arg" == "--restart" || "$prev_arg" == "--nuke" \
     || "$prev_arg" == "--logs" ]]; then
    TARGET_BRANCH="$arg"
    prev_arg=""
    continue
  fi
  case "$arg" in
    --list)        CMD="list" ;;
    --status)      CMD="status"; prev_arg="--status" ;;
    --stop)        CMD="stop"; prev_arg="--stop" ;;
    --restart)     CMD="restart"; prev_arg="--restart" ;;
    --nuke)        CMD="nuke"; prev_arg="--nuke" ;;
    --logs)        CMD="logs"; prev_arg="--logs" ;;
    --doctor)      CMD="doctor" ;;
    --no-pull)     NO_PULL=1 ;;
    --kill-existing)      KILL_EXISTING=1 ;;
    --reuse-existing)     REUSE_EXISTING=1 ;;
    --cancel-on-conflict) CANCEL_ON_CONFLICT=1 ;;
    --help|-h)
      sed -n '2,20p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    -*)
      echo "ERROR: unknown flag: $arg" >&2
      exit 1
      ;;
    *)
      BRANCH_ARG="$arg" ;;
  esac
done

if [[ "$CMD" == "start" && -z "$BRANCH_ARG" ]]; then
  BRANCH_ARG="main"
fi

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

# split_branch_sha "branch@abc123" -> REG_KEY=branch, RESOLVED_SHA=abc123, IS_DETACHED=1
# split_branch_sha "branch"        -> REG_KEY=branch, RESOLVED_SHA=,          IS_DETACHED=0
split_branch_sha() {
  local ref="$1"
  if [[ "$ref" == *"@"* ]]; then
    local left="${ref%@*}"
    local right="${ref##*@}"
    REG_KEY="$left"
    RESOLVED_SHA="$right"
    IS_DETACHED=1
  else
    REG_KEY="$ref"
    RESOLVED_SHA=""
    IS_DETACHED=0
  fi
}

# sanitize_for_dir "feat/foo+bar" -> "feat_foo_bar"
#  - replace '/' with '_'
#  - drop leading '+'
#  - cap at 96 chars; if truncated, append '-<short-hash>' (8 hex) for uniqueness
sanitize_for_dir() {
  local name="$1"
  local safe="${name//\//_}"
  safe="${safe#+}"
  if (( ${#safe} > 96 )); then
    local tag
    tag=$(printf '%s' "$safe" | cksum | awk '{print $1}')
    tag=$(printf '%08x' "$((tag & 0xffffffff))")
    safe="${safe:0:88}-$tag"
  fi
  printf '%s' "$safe"
}

# Deterministic port allocation in [PORT_MIN, PORT_MAX].
# Same key always maps to the same port (no migration on restart).
allocate_port() {
  local key="$1"
  local slot
  slot=$(printf '%s' "$key" | cksum | awk '{print $1}')
  slot=$((slot % PORT_SPAN))
  if (( slot < 0 )); then slot=$((slot + PORT_SPAN)); fi
  echo $((PORT_MIN + slot))
}

# check_port_in_use <port> -> echoes pid (possibly empty)
# Note: under `set -euo pipefail`, grep returns non-zero on no match — must `|| true`
# to avoid the inner grep silently aborting callers. (BTCAAAAA-32422 forensics.)
check_port_in_use() {
  local port=$1
  local pid=""
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -o 'pid=[0-9]*' | grep -o '[0-9]*' | head -1 || true)
  else
    pid=$(lsof -t -i :"$port" 2>/dev/null | grep -v '^$' | head -1 || true)
  fi
  echo "$pid"
}

pid_alive() {
  local pid=$1
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# Atomic registry update: serialize JSON via python3 + flock + tmpfile + mv.
# usage: registry_update <python-script> [extra-args...]
# Extra args are forwarded to python3 as sys.argv[1..N-1]; python3 also receives
# REGISTRY_FILE as the LAST argv (Nth), so scripts that need the path read it from
# sys.argv[-1]. For zero-arg callers, sys.argv[1] IS the path.
registry_update() {
  local script="$1"; shift
  (
    flock -w 10 9 || { echo "ERROR: could not acquire registry lock" >&2; exit 1; }
    python3 -c "$script" "$@" "$REGISTRY_FILE"
  ) 9>"$LOCK_FILE"
}

registry_read() {
  python3 -c '
import json, sys
try:
  with open(sys.argv[1]) as f:
    print(json.dumps(json.load(f)))
except FileNotFoundError:
  print("{}")
except Exception as e:
  print("{}", file=sys.stderr)
  sys.exit(1)
' "$REGISTRY_FILE"
}

registry_get() {
  # registry_get <key> -> JSON object or empty
  python3 -c '
import json, sys
key = sys.argv[1]
try:
  with open(sys.argv[2]) as f:
    data = json.load(f)
except FileNotFoundError:
  print("{}")
  sys.exit(0)
inst = data.get("instances", {}).get(key)
print(json.dumps(inst) if inst else "{}")
' "$1" "$REGISTRY_FILE"
}

registry_set() {
  # registry_set <key> <json-blob> — runs the python mutation under flock via registry_update
  local key="$1" blob="$2"
  # Pass key+blob+path as sys.argv; use json.dumps(blob) so embedded quotes are safe.
  registry_update '
import json, os, sys, tempfile
key, blob_repr, path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
  with open(path) as f:
    data = json.load(f)
except FileNotFoundError:
  data = {"version": 1, "instances": {}}
data.setdefault("version", 1)
data.setdefault("instances", {})
data["instances"][key] = json.loads(blob_repr)
tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".registry.", suffix=".tmp")
with os.fdopen(tmp_fd, "w") as f:
  json.dump(data, f, indent=2, sort_keys=True)
os.replace(tmp_path, path)
' "$key" "$blob" "$REGISTRY_FILE"
}

registry_delete() {
  # registry_delete <key>
  local key="$1"
  registry_update '
import json, os, sys, tempfile
key, path = sys.argv[1], sys.argv[2]
try:
  with open(path) as f:
    data = json.load(f)
except FileNotFoundError:
  sys.exit(0)
data.setdefault("instances", {}).pop(key, None)
tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".registry.", suffix=".tmp")
with os.fdopen(tmp_fd, "w") as f:
  json.dump(data, f, indent=2, sort_keys=True)
os.replace(tmp_path, path)
' "$key" "$REGISTRY_FILE"
}

# ----------------------------------------------------------------------------
# Worktree lifecycle
# ----------------------------------------------------------------------------

ensure_worktree() {
  local key="$1" sha="$2" detached="$3" safe="$4"
  local target="$WORKTREE_ROOT/$safe"

  if [[ -d "$target" ]]; then
    # Reuse existing worktree. Verify it points at the expected ref (best-effort).
    echo "[worktree] reusing existing worktree at $target" >&2
    printf '%s' "$target"
    return 0
  fi

  # Detect collision: a different instance already owns <safe>. Add a short-hash suffix.
  if [[ -e "$target" || -L "$target" ]]; then
    local suffix
    suffix=$(printf '%s' "$key" | cksum | awk '{print $1}' | awk '{printf "%04x", $1%65536}')
    target="$WORKTREE_ROOT/${safe}-${suffix}"
    if [[ -d "$target" ]]; then
      echo "[worktree] reusing collision-suffixed worktree at $target" >&2
      printf '%s' "$target"
      return 0
    fi
  fi

  echo "[worktree] creating new worktree at $target..." >&2
  if (( detached )); then
    ( git -C "$PRIMARY_REPO_ROOT" worktree add --detach "$target" "$sha" ) >&2 || {
      echo "ERROR: git worktree add --detach $target $sha failed" >&2
      return 1
    }
  else
    # For non-detached, use the branch name (REG_KEY) as the ref so callers can
    # pass plain "main" or any local branch without "@<sha>".
    ( git -C "$PRIMARY_REPO_ROOT" worktree add "$target" "$key" ) >&2 || {
      echo "ERROR: git worktree add $target $key failed" >&2
      return 1
    }
  fi
  printf '%s' "$target"
}

refresh_worktree() {
  local target="$1" detached="$2" no_pull="$3"

  if (( no_pull )); then
    echo "[worktree] --no-pull: skipping fetch/reset"
    return 0
  fi

  if (( detached )); then
    echo "[worktree] detached HEAD: skipping pull (state is pinned at requested sha)"
    return 0
  fi

  echo "[worktree] fetching origin and fast-forwarding..."
  (
    cd "$target"
    git fetch --quiet origin 2>/dev/null || true
    if ! git merge-base --is-ancestor origin/"$(git rev-parse --abbrev-ref HEAD)" HEAD 2>/dev/null; then
      git reset --hard "origin/$(git rev-parse --abbrev-ref HEAD)" 2>&1 || {
        echo "ERROR: git reset --hard failed in $target" >&2
        return 1
      }
    fi
  )
}

ensure_per_instance_env() {
  local target="$1" port="$2"
  local env_file="$target/packages/web-ui/.env.local"
  local example="$target/packages/web-ui/.env.example"

  if [[ ! -f "$example" ]]; then
    echo "WARN: $example not found; writing minimal .env.local" >&2
  fi

  # Carry BTE_* from caller environment so the dev server can reach the backend.
  local backend_host="${BTE_API_HOST:-0.0.0.0}"
  local backend_port="${BTE_API_PORT:-8765}"
  local backend_public_host="${BTE_API_PUBLIC_HOST:-${backend_host}}"
  if [[ "$backend_public_host" == "0.0.0.0" || -z "$backend_public_host" ]]; then
    backend_public_host="localhost"
  fi
  local api_url="${NEXT_PUBLIC_API_URL:-http://${backend_public_host}:${backend_port}}"
  local ws_url="${NEXT_PUBLIC_BRIDGE_WS_URL:-ws://${backend_public_host}:${backend_port}}"

  {
    echo "# generated by start-test-iso.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ -f "$example" ]]; then
      # Strip example comments, keep K=V pairs.
      grep -v '^[[:space:]]*#' "$example" | grep -v '^[[:space:]]*$' || true
    fi
    echo "NEXT_PUBLIC_API_URL=${api_url}"
    echo "NEXT_PUBLIC_BRIDGE_WS_URL=${ws_url}"
    echo "BTE_TEST_INSTANCE_PORT=${port}"
  } > "$env_file"
  echo "[env] wrote $env_file"
}

ensure_node_modules() {
  local target="$1"
  if [[ -x "$target/packages/web-ui/node_modules/.bin/next" ]]; then
    return 0
  fi
  echo "[npm] node_modules missing — running npm install (one-time)..."
  # --legacy-peer-deps: the @tremor/react@3.18.7 -> react@^18 peer is intentionally
  # violated because the project pins react@19.2.4; this matches how the
  # primary repo's node_modules is installed and is the only way the install
  # resolves.
  ( cd "$target/packages/web-ui" && npm install --no-audit --no-fund --legacy-peer-deps ) || {
    echo "ERROR: npm install failed in $target/packages/web-ui" >&2
    return 1
  }
}

launch_dev_server() {
  local target="$1" port="$2" log_file="$3" pid_file="$4"
  (
    cd "$target/packages/web-ui"
    # BTE_BRANCH_GATE_OK=1 tells gate-main-branch.sh that branch verification was
    # already done by ensure_worktree. Background via setsid so the entire
    # process group (npm + the next-server child it forks) shares one PGID —
    # that way SIGTERM -- -PGID in do_stop tears down the dev server, not just
    # the npm wrapper.
    BTE_BRANCH_GATE_OK=1 setsid nohup npm run dev -- --port "$port" >>"$log_file" 2>&1 &
    echo $! > "$pid_file"
  )
  local pid
  pid=$(cat "$pid_file")
  echo "[dev] spawned next dev pid=$pid on :$port (log: $log_file)"
}

wait_for_port() {
  local port=$1 timeout=$2
  local waited=0
  while ! check_port_in_use "$port" >/dev/null; do
    sleep 0.5
    waited=$((waited + 1))
    if (( waited >= timeout )); then
      echo "ERROR: :$port did not open within ${timeout}*0.5s" >&2
      return 1
    fi
  done
}

# ----------------------------------------------------------------------------
# Port-conflict handling (mirrors start-test.sh)
# ----------------------------------------------------------------------------
handle_port_conflict() {
  local port=$1 pid=$2

  local cmd etime
  cmd=$(ps -o args= -p "$pid" 2>/dev/null || echo "unknown")
  etime=$(ps -o etime= -p "$pid" 2>/dev/null || echo "unknown")

  echo
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Port :$port is already in use"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "PID:     $pid"
  echo "Command: $cmd"
  echo "Time:    $etime"
  echo

  if [[ $KILL_EXISTING -eq 1 ]]; then
    kill -TERM "$pid" 2>/dev/null || true
    local w=0
    while [[ -n "$(check_port_in_use "$port")" ]] && (( w < 50 )); do
      sleep 0.1
      w=$((w + 1))
    done
    return 0
  fi
  if [[ $REUSE_EXISTING -eq 1 ]]; then
    exit 0
  fi
  if [[ $CANCEL_ON_CONFLICT -eq 1 ]]; then
    exit 1
  fi
  read -p "Action? [k/r/c]: " -r action
  case "$action" in
    k|K)
      kill -TERM "$pid" 2>/dev/null || true
      local w=0
      while [[ -n "$(check_port_in_use "$port")" ]] && (( w < 50 )); do
        sleep 0.1
        w=$((w + 1))
      done
      ;;
    r|R)
      echo "[port-conflict] reusing existing :$port"
      exit 0
      ;;
    c|C)
      exit 1
      ;;
    *) echo "ERROR: invalid action '$action'" >&2; exit 1 ;;
  esac
}

# ----------------------------------------------------------------------------
# Subcommands
# ----------------------------------------------------------------------------

do_start() {
  split_branch_sha "$BRANCH_ARG"
  local safe
  safe=$(sanitize_for_dir "$REG_KEY")
  local port
  port=$(allocate_port "$REG_KEY")

  # Refuse to bind protected ports (defense-in-depth — allocate_port already
  # only returns 4000-4999, but check anyway).
  for pp in "${PROTECTED_PORTS[@]}"; do
    if [[ "$port" == "$pp" ]]; then
      echo "ERROR: allocate_port returned protected port :$port for key '$REG_KEY'" >&2
      exit 1
    fi
  done

  # If an instance already exists for this key and is alive, refuse.
  local existing
  existing=$(registry_get "$REG_KEY")
  if [[ "$existing" != "{}" ]]; then
    local epid
    epid=$(printf '%s' "$existing" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("pid",""))')
    if pid_alive "$epid"; then
      echo "[start] instance for '$REG_KEY' is already running (pid=$epid, port=$port)."
      echo "[start] use --restart '$REG_KEY' to recycle, or --stop '$REG_KEY' first."
      exit 1
    fi
    echo "[start] removing stale registry row for '$REG_KEY' (pid $epid is gone)"
    registry_delete "$REG_KEY"
  fi

  local target
  target=$(ensure_worktree "$REG_KEY" "$RESOLVED_SHA" "$IS_DETACHED" "$safe") || exit 1
  refresh_worktree "$target" "$IS_DETACHED" "$NO_PULL"

  ensure_per_instance_env "$target" "$port"
  ensure_node_modules "$target"

  local pid_file="$target/packages/web-ui/.start-test-iso.pid"
  local log_file="$target/packages/web-ui/dev.log"
  local env_file="$target/packages/web-ui/.env.local"
  local started_at
  started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Port-conflict check (foreign process holding the port).
  local pid_on_port
  pid_on_port=$(check_port_in_use "$port")
  if [[ -n "$pid_on_port" ]]; then
    handle_port_conflict "$port" "$pid_on_port"
  fi

  launch_dev_server "$target" "$port" "$log_file" "$pid_file"
  wait_for_port "$port" 40 || {
    echo "ERROR: instance did not come up on :$port; see $log_file" >&2
    exit 1
  }

  local pid
  pid=$(cat "$pid_file")

  # Write registry row.
  local row
  row=$(python3 -c '
import json, sys
print(json.dumps({
  "branch": sys.argv[1],
  "resolvedSha": sys.argv[2],
  "detached": bool(int(sys.argv[3])),
  "worktree": sys.argv[4],
  "port": int(sys.argv[5]),
  "pid": sys.argv[6],
  "pidFile": sys.argv[7],
  "logFile": sys.argv[8],
  "envFile": sys.argv[9],
  "startedAt": sys.argv[10],
  "status": "running",
}))
' "$REG_KEY" "$RESOLVED_SHA" "$IS_DETACHED" "$target" "$port" "$pid" \
  "$pid_file" "$log_file" "$env_file" "$started_at")
  registry_set "$REG_KEY" "$row"

  echo
  echo "════════════════════════════════════════════════════════════"
  echo "  instance '$REG_KEY' is running"
  echo "  url:   http://localhost:$port"
  echo "  pid:   $pid"
  echo "  log:   $log_file"
  echo "  stop:  ./start-test-iso.sh --stop '$REG_KEY'"
  echo "════════════════════════════════════════════════════════════"
}

do_stop() {
  local key="$TARGET_BRANCH"
  [[ -z "$key" ]] && { echo "ERROR: --stop requires <branch>" >&2; exit 1; }
  split_branch_sha "$key"
  local row
  row=$(registry_get "$REG_KEY")
  if [[ "$row" == "{}" ]]; then
    echo "[stop] no instance for '$REG_KEY' (already stopped?)"
    return 0
  fi
  local pid
  pid=$(printf '%s' "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("pid",""))')
  if pid_alive "$pid"; then
    # SIGTERM the whole process group: launch_dev_server used `setsid` so npm
    # and the next-server child share one PGID. Killing the group ensures the
    # dev server (not just the npm wrapper) is torn down.
    local pgid="${pid}"
    echo "[stop] SIGTERM pid=$pid (pgid=-$pgid)"
    kill -TERM -- "-$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    local w=0
    while pid_alive "$pid" && (( w < 50 )); do
      sleep 0.1
      w=$((w + 1))
    done
    if pid_alive "$pid"; then
      echo "WARN: pid=$pid did not exit after SIGTERM; sending SIGKILL" >&2
      kill -KILL -- "-$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  else
    echo "[stop] pid=$pid already gone"
  fi
  # Clean up pid file if present.
  local pid_file
  pid_file=$(printf '%s' "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("pidFile",""))')
  [[ -n "$pid_file" && -f "$pid_file" ]] && rm -f "$pid_file"
  registry_delete "$REG_KEY"
  echo "[stop] instance '$REG_KEY' stopped and registry row removed"
}

do_restart() {
  local key="$TARGET_BRANCH"
  [[ -z "$key" ]] && { echo "ERROR: --restart requires <branch>" >&2; exit 1; }
  do_stop
  BRANCH_ARG="$key"
  do_start
}

do_nuke() {
  local key="$TARGET_BRANCH"
  [[ -z "$key" ]] && { echo "ERROR: --nuke requires <branch>" >&2; exit 1; }
  split_branch_sha "$key"
  do_stop
  # Locate the worktree path from the registry row we just removed; fall back
  # to the sanitized name.
  local safe worktree_path
  safe=$(sanitize_for_dir "$REG_KEY")
  worktree_path="$WORKTREE_ROOT/$safe"
  if [[ -d "$worktree_path" ]]; then
    echo "[nuke] removing worktree at $worktree_path..."
    git -C "$PRIMARY_REPO_ROOT" worktree remove --force "$worktree_path" 2>/dev/null || {
      echo "WARN: git worktree remove failed; falling back to rm -rf" >&2
      rm -rf "$worktree_path"
    }
  fi
  # Also remove the secondary dir if a collision-suffixed one was used.
  for d in "$WORKTREE_ROOT/${safe}"-*; do
    [[ -d "$d" ]] || continue
    echo "[nuke] removing collision worktree at $d..."
    git -C "$PRIMARY_REPO_ROOT" worktree remove --force "$d" 2>/dev/null || rm -rf "$d"
  done
  # Remove orphaned symlink/ref if the worktree dir is gone but git still tracks it.
  git -C "$PRIMARY_REPO_ROOT" worktree prune 2>/dev/null || true
  echo "[nuke] instance '$REG_KEY' fully removed"
}

do_list() {
  python3 -c '
import json, sys
try:
  with open(sys.argv[1]) as f:
    data = json.load(f)
except FileNotFoundError:
  print("(no instances)")
  sys.exit(0)
instances = data.get("instances", {})
if not instances:
  print("(no instances)")
  sys.exit(0)
rows = sorted(instances.items())
hdr_key, hdr_branch, hdr_port, hdr_pid, hdr_status = "KEY", "BRANCH", "PORT", "PID", "STATUS"
print("%-32s %-32s %-6s %-8s %s" % (hdr_key, hdr_branch, hdr_port, hdr_pid, hdr_status))
print("-" * 96)
for k, v in rows:
  branch = v.get("branch", "")
  port = v.get("port", "")
  pid = v.get("pid", "")
  status = v.get("status", "")
  print("%-32s %-32s %-6s %-8s %s" % (k, branch, port, pid, status))
' "$REGISTRY_FILE"
}

do_status() {
  local key="$TARGET_BRANCH"
  [[ -z "$key" ]] && { echo "ERROR: --status requires <branch>" >&2; exit 1; }
  split_branch_sha "$key"
  local row
  row=$(registry_get "$REG_KEY")
  if [[ "$row" == "{}" ]]; then
    echo "[status] no instance for '$REG_KEY'"
    exit 1
  fi
  echo "$row" | python3 -c '
import json, sys
v = json.load(sys.stdin)
for k in ["branch", "resolvedSha", "detached", "worktree", "port", "pid",
         "pidFile", "logFile", "envFile", "startedAt", "status"]:
  print(f"  {k:<12} {v.get(k, \"\")}")
'
}

do_logs() {
  local key="$TARGET_BRANCH"
  [[ -z "$key" ]] && { echo "ERROR: --logs requires <branch>" >&2; exit 1; }
  split_branch_sha "$key"
  local row
  row=$(registry_get "$REG_KEY")
  [[ "$row" == "{}" ]] && { echo "[logs] no instance for '$REG_KEY'" >&2; exit 1; }
  local log_file
  log_file=$(printf '%s' "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("logFile",""))')
  [[ -f "$log_file" ]] || { echo "[logs] log file $log_file does not exist" >&2; exit 1; }
  exec tail -f "$log_file"
}

do_doctor() {
  echo "[doctor] scanning registry for staleness..."
  local issues=0
  python3 -c '
import json, os, subprocess, sys
path = sys.argv[1]
try:
  with open(path) as f:
    data = json.load(f)
except FileNotFoundError:
  print("[doctor] no registry file yet")
  sys.exit(0)

for key, v in data.get("instances", {}).items():
  pid = v.get("pid", "")
  port = v.get("port", "")
  worktree = v.get("worktree", "")
  log_file = v.get("logFile", "")

  # (a) PID gone
  pid_alive = False
  if pid:
    try:
      os.kill(int(pid), 0)
      pid_alive = True
    except (OSError, ValueError):
      pid_alive = False
  if not pid_alive:
    print(f"[doctor] {key}: pid={pid} is GONE (stale registry row)")
    print(f"          fix: ./start-test-iso.sh --stop {key}")
    continue

  # (b) port held by something else
  port_pid = subprocess.run(
    ["bash", "-c", f"ss -tlnp 2>/dev/null | grep \":{port} \" | grep -o \"pid=[0-9]*\" | grep -o \"[0-9]*\" | head -1"],
    capture_output=True, text=True,
  ).stdout.strip()
  if port_pid and port_pid != pid:
    print(f"[doctor] {key}: port :{port} held by foreign pid {port_pid} (registry pid={pid})")

  # (c) worktree on disk but not in registry
  # (this case is already covered — doctor scans registry. A separate sweep
  #  for orphan worktrees on disk follows.)

# (c) Worktrees on disk missing from registry.
import glob
worktree_root = os.path.expanduser("~/btc-test-worktrees")
if os.path.isdir(worktree_root):
  for d in sorted(glob.glob(os.path.join(worktree_root, "*"))):
    if not os.path.isdir(d):
      continue
    # Heuristic: see if this dir is referenced by any registry row.
    referenced = any(v.get("worktree", "") == d for v in data.get("instances", {}).values())
    if not referenced:
      print(f"[doctor] orphan worktree on disk (no registry row): {d}")
' "$REGISTRY_FILE"
}

# ----------------------------------------------------------------------------
# Main dispatch
# ----------------------------------------------------------------------------
case "$CMD" in
  start)    do_start ;;
  list)     do_list ;;
  status)   do_status ;;
  stop)     do_stop ;;
  restart)  do_restart ;;
  nuke)     do_nuke ;;
  logs)     do_logs ;;
  doctor)   do_doctor ;;
  *)
    echo "ERROR: unknown command: $CMD" >&2
    exit 1
    ;;
esac
