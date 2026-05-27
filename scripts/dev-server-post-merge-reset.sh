#!/bin/bash
# Post-merge dev-server reset routine
set -euo pipefail

REPO_ROOT="/home/sirrus/projects/BTC-Trade-Engine-PaperClip"
LOCK_FILE="/tmp/btc-dev-server-reset.lock"
LOCK_TIMEOUT=600
WEB_UI_DIR="${REPO_ROOT}/packages/web-ui"
DEV_SERVER_PORT=3010

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2; }
error() { log "ERROR: $*"; exit 1; }
warn() { log "WARN: $*"; }

acquire_lock() {
    local timeout=$1
    local start_time=$(date +%s)
    while [ -f "$LOCK_FILE" ]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        if [ $elapsed -gt $timeout ]; then
            error "Lock timeout after ${timeout}s"
        fi
        log "Lock exists, waiting 1s..."
        sleep 1
    done
    touch "$LOCK_FILE"
    log "Lock acquired"
}

release_lock() {
    [ -f "$LOCK_FILE" ] && rm "$LOCK_FILE" && log "Lock released"
}

check_uncommitted_changes() {
    cd "$REPO_ROOT"
    local status=$(git status --porcelain 2>/dev/null | grep -v "^??" || true)
    if [ -n "$status" ]; then
        warn "Uncommitted changes detected, skipping reset this cycle"
        return 1
    fi
    return 0
}

reset_to_main() {
    cd "$REPO_ROOT"
    log "Fetching from origin..."
    git fetch origin main >/dev/null 2>&1
    log "Switching to main..."
    git switch main || git checkout main >/dev/null 2>&1
    log "Pulling from origin/main..."
    git pull --ff-only origin main >/dev/null 2>&1
    log "Successfully reset to origin/main"
}

get_current_sha() {
    cd "$REPO_ROOT"
    git rev-parse HEAD
}

kill_dev_server() {
    log "Checking for dev server on port $DEV_SERVER_PORT..."
    local pids=$(lsof -ti :$DEV_SERVER_PORT 2>/dev/null || true)
    if [ -n "$pids" ]; then
        log "Found dev server processes: $pids"
        kill -9 $pids 2>/dev/null || true
        sleep 2
        log "Killed dev server"
    fi
}

clean_turbopack_cache() {
    log "Cleaning turbopack cache..."
    rm -rf "${WEB_UI_DIR}/.next/dev/cache" 2>/dev/null || true
    rm -rf "${WEB_UI_DIR}/.next/dev/server" 2>/dev/null || true
}

start_dev_server() {
    log "Starting dev server..."
    cd "$REPO_ROOT"
    nohup bash -c "cd '$REPO_ROOT' && pnpm dev" > /tmp/dev-server.log 2>&1 &
    local pid=$!
    log "Dev server started with PID $pid"
    
    log "Waiting for dev server..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:$DEV_SERVER_PORT >/dev/null 2>&1; then
            log "Dev server is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    warn "Dev server did not respond within 30s"
    return 0
}

update_status_document() {
    local current_sha="$1"
    local current_branch=$(cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD)
    local timestamp=$(date -u +'%Y-%m-%d %H:%M:%S UTC')
    
    log "Updating dev-server-status..."
    echo "CURRENT_BRANCH=$current_branch"
    echo "CURRENT_SHA=$current_sha"
    echo "TIMESTAMP=$timestamp"
}

main() {
    log "=== Dev Server Post-Merge Reset Routine ==="
    acquire_lock $LOCK_TIMEOUT
    trap release_lock EXIT
    
    if ! check_uncommitted_changes; then
        warn "Skipping reset due to uncommitted changes"
        return 1
    fi
    
    reset_to_main
    local new_sha=$(get_current_sha)
    log "New HEAD SHA: $new_sha"
    
    kill_dev_server
    clean_turbopack_cache
    start_dev_server
    update_status_document "$new_sha"
    
    log "=== Reset Complete ==="
    return 0
}

main "$@"
