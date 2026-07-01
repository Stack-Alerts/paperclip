#!/usr/bin/env bash
# Recover Paperclip + the Git Merges plugin after a server reboot.
#
# Reboots wipe three things that need re-applying:
#   1. The embedded Postgres (PID dies, port 54329 unbound)
#   2. The plugin-loader.js patches (§4.1 + §4.2 in INSTALL.md)
#   3. The Service Worker patches at all three locations (§4.5)
#
# Everything else is durable:
#   - The Paperclip DB lives at /home/sirrus/.paperclip/instances/default/db
#   - The 5 installed plugins live in the DB (paperclip.git-merges included)
#   - The BTC worktree at /home/sirrus/btc-test-worktrees/fix-38557
#   - The git history on the fork remote
#
# Usage:   bash scripts/recover-from-reboot.sh
# Verify: bash scripts/recover-from-reboot.sh --check
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Config — adjust these if your machine layout differs
# ---------------------------------------------------------------------------

NPX_CACHE="${PAPERCLIP_NPX_CACHE:-/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules}"
PGDATA="${PAPERCLIP_PG_DATA:-/home/sirrus/.paperclip/instances/default/db}"
PGPORT="${PAPERCLIP_PG_PORT:-54329}"
PGUSER="${PAPERCLIP_PG_USER:-paperclip}"
PGDATABASE="${PAPERCLIP_PG_DB:-paperclip}"
PSQL_BIN="${PAPERCLIP_PSQL:-/home/sirrus/.pg0/installation/18.1.0/bin/psql}"
PAPERCLIP_BIN="$NPX_CACHE/.bin/paperclipai"
PAPERCLIP_UI="${PAPERCLIP_UI:-/home/sirrus/projects/paperclip/ui}"
PLUGIN_LOADER="$NPX_CACHE/@paperclipai/server/dist/services/plugin-loader.js"
SW_SOURCE="$PAPERCLIP_UI/public/sw.js"
SW_DIST="$PAPERCLIP_UI/dist/sw.js"
SW_NPX="$NPX_CACHE/@paperclipai/server/ui-dist/sw.js"
LOG_FILE="${PAPERCLIP_LOG:-/tmp/paperclip-restart.log}"

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*" >&2; }
fail() { log "FAIL: $*"; exit 1; }

port_listening() {
  ss -tlnp 2>/dev/null | grep -qE ":${1} "
}

psql_query() {
  PGPASSWORD="" "$PSQL_BIN" -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
    -t -A -c "$1" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Step 1 — embedded Postgres
# ---------------------------------------------------------------------------

start_postgres() {
  if port_listening "$PGPORT"; then
    log "postgres already listening on :$PGPORT"
    return
  fi
  if [ ! -d "$PGDATA" ] || [ ! -f "$PGDATA/PG_VERSION" ]; then
    fail "Paperclip data dir missing or uninitialised at $PGDATA"
  fi
  # The embedded-postgres npm package ships its own native postgres binary.
  # Fall back to PATH if that's missing.
  local pgbin="$NPX_CACHE/@embedded-postgres/linux-x64/native/bin/postgres"
  [ -x "$pgbin" ] || pgbin="$(command -v postgres || true)"
  [ -x "$pgbin" ] || fail "no postgres binary found"
  log "starting postgres from $pgbin"
  nohup "$pgbin" -D "$PGDATA" -p "$PGPORT" -k /tmp > /tmp/pg.log 2>&1 < /dev/null & disown
  for _ in $(seq 1 15); do
    port_listening "$PGPORT" && return
    sleep 1
  done
  fail "postgres did not bind :$PGPORT within 15s"
}

# ---------------------------------------------------------------------------
# Step 2 — plugin-loader.js patches (§4.1 + §4.2)
# ---------------------------------------------------------------------------

patch_plugin_loader() {
  if [ ! -f "$PLUGIN_LOADER" ]; then
    log "WARN: $PLUGIN_LOADER missing — patch 4.1/4.2 skipped"
    return
  fi
  # 4.1 — point DEV_TSX_LOADER_PATH at the right tsx subpath
  if grep -q '"../../../cli/node_modules/tsx/dist/loader.mjs"' "$PLUGIN_LOADER"; then
    sed -i 's|"../../../cli/node_modules/tsx/dist/loader.mjs"|"../../../../tsx/dist/loader.mjs"|' "$PLUGIN_LOADER"
    log "applied 4.1 (DEV_TSX_LOADER_PATH)"
  else
    log "4.1 already patched (or upstream changed)"
  fi
  # 4.2 — preserve packagePath across the manifest refresh
  if ! grep -q "activePlugin.packagePath = activePlugin.packagePath ?? plugin.packagePath" "$PLUGIN_LOADER"; then
    sed -i 's|activePlugin = await refreshPluginManifestFromPackage(activePlugin, packageRoot);|activePlugin = await refreshPluginManifestFromPackage(activePlugin, packageRoot);\n            activePlugin.packagePath = activePlugin.packagePath ?? plugin.packagePath;|' "$PLUGIN_LOADER"
    log "applied 4.2 (preserve packagePath)"
  else
    log "4.2 already patched"
  fi
}

# ---------------------------------------------------------------------------
# Step 3 — Service Worker patch at all three locations (§4.5)
# ---------------------------------------------------------------------------

# The SW source gets copied into ui/dist/ by Vite, and from there into the
# npx cache by the install workflow. Any build reverts the patch at the
# source. We keep the canonical content as a heredoc and write it to all
# three locations, so even if the upstream Paperclip gets rebuilt the next
# time this script runs the fix is reapplied.

SW_FIXED_CONTENT='const CACHE_NAME = "paperclip-v2";
const OFFLINE_FALLBACK = "/";

self.addEventListener("install", () => { self.skipWaiting(); });

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
    await self.clients.claim();
    const hadPreviousCache = keys.length > 0;
    if (hadPreviousCache) {
      const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of clients) {
        try { await client.navigate(client.url); } catch {}
      }
    }
  })());
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.pathname.startsWith("/api")) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && url.origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(async () => {
        if (request.mode === "navigate") {
          const cached = (await caches.match(OFFLINE_FALLBACK)) ||
            (await caches.match(request)) ||
            new Response("Offline", { status: 503 });
          return cached;
        }
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response("Offline", { status: 503 });
      })
  );
});'

patch_sw() {
  for path in "$SW_SOURCE" "$SW_DIST" "$SW_NPX"; do
    if [ -f "$path" ]; then
      printf '%s\n' "$SW_FIXED_CONTENT" > "$path"
    fi
  done
  # Validate the npx-cache copy (the one the browser actually fetches).
  node --check "$SW_NPX" 2>/dev/null || fail "patched sw.js failed syntax check"
  # Confirm all three locations are in sync.
  local source_md5
  source_md5=$(md5sum "$SW_NPX" | awk '{print $1}')
  for path in "$SW_SOURCE" "$SW_DIST" "$SW_NPX"; do
    [ -f "$path" ] || continue
    local actual
    actual=$(md5sum "$path" | awk '{print $1}')
    [ "$actual" = "$source_md5" ] || fail "sw.js md5 mismatch on $path (got $actual, want $source_md5)"
  done
  log "sw.js patched + in sync across 3 locations (md5 $source_md5)"
}

# ---------------------------------------------------------------------------
# Step 4 — Paperclip main process
# ---------------------------------------------------------------------------

start_paperclip() {
  if [ ! -x "$PAPERCLIP_BIN" ]; then
    fail "paperclipai binary missing at $PAPERCLIP_BIN — run: npx paperclipai@latest --help"
  fi

  # Ensure the canonical port is free BEFORE we start. A previous instance
  # (often a `pnpm dev:watch` from /home/sirrus/projects/paperclip) may
  # have bound to :3101 because :3100 was occupied at that time. Without
  # this step the new server would also bind to :3101 (its next-free
  # attempt) and we'd be back in port-drift hell.
  free_port() {
    local port="$1"
    if port_listening "$port"; then
      local pids
      pids=$(ss -tlnpH 2>/dev/null | awk -v p=":${port} " '$0 ~ p { print $0 }' \
             | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)
      if [ -z "$pids" ]; then
        log "WARN: port $port is in use but I can't identify the process — refusing to kill"
        return 1
      fi
      log "killing processes holding port $port: $pids"
      for pid in $pids; do
        kill "$pid" 2>/dev/null || log "WARN: kill $pid failed (already gone?)"
      done
      for _ in $(seq 1 10); do
        port_listening "$port" || return 0
        sleep 1
      done
      fail "port $port still occupied after kill"
    fi
  }
  free_port 3100

  # Sweep adjacent ports (3101-3110) and kill any *paperclip* process
  # still holding them. These are always drift artifacts from prior
  # failed starts; killing them prevents confusion about which server
  # is the canonical one.
  log "sweeping 3101-3110 for stray paperclip instances"
  for port in $(seq 3101 3110); do
    if port_listening "$port"; then
      # Only kill if the holder is a paperclip process (cmdline match).
      local holder_pid
      holder_pid=$(ss -tlnpH 2>/dev/null | awk -v p=":${port} " '$0 ~ p' \
                   | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
      if [ -n "$holder_pid" ]; then
        local cmdline
        cmdline=$(tr '\0' ' ' < "/proc/$holder_pid/cmdline" 2>/dev/null || echo "")
        if echo "$cmdline" | grep -q "paperclipai\|paperclip.*dist/index"; then
          log "killing stray paperclip PID $holder_pid on :$port"
          kill "$holder_pid" 2>/dev/null || true
        else
          log "port $port held by non-paperclip PID $holder_pid ($cmdline) — leaving alone"
        fi
      fi
    fi
  done

  if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:3100/api/health; then
    log "paperclip already healthy on :3100"
    return
  fi

  log "starting paperclip (log → $LOG_FILE)"
  nohup "$PAPERCLIP_BIN" run --instance default > "$LOG_FILE" 2>&1 < /dev/null & disown

  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:3100/api/health; then
      # Sanity-check we actually bound to the canonical port, not :3101+
      if port_listening 3100; then
        log "paperclip healthy on :3100 after ${_}s"
        return
      else
        fail "paperclip started but is NOT listening on :3100 — check $LOG_FILE"
      fi
    fi
    sleep 1
  done
  fail "paperclip did not become healthy within 60s — tail $LOG_FILE"
}

# ---------------------------------------------------------------------------
# Step 5 — verify the Git Merges plugin survives the reboot intact
# ---------------------------------------------------------------------------

verify_git_merges() {
  if [ ! -x "$PSQL_BIN" ]; then
    log "psql not found at $PSQL_BIN — skipping git-merges verification"
    return
  fi
  local plugin_status
  plugin_status=$(psql_query "SELECT status FROM plugins WHERE plugin_key = 'paperclip.git-merges';" 2>/dev/null || echo "")
  if [ "$plugin_status" != "ready" ]; then
    log "WARN: paperclip.git-merges plugin is not ready (status='$plugin_status')"
    log "      This is OK if Paperclip's plugin-dev-watcher hasn't attached yet."
    log "      Check $LOG_FILE for 'plugin setup complete'."
    return
  fi
  log "paperclip.git-merges: ready ✓"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log "=== Paperclip reboot recovery ==="

start_postgres
patch_plugin_loader
patch_sw

if [ "$CHECK_ONLY" = "1" ]; then
  log "(--check mode: paperclip not started)"
else
  start_paperclip
  verify_git_merges
fi

log "=== done ==="
log "next steps:"
log "  - open http://127.0.0.1:3100/BTCAAAAA/git-merges"
log "  - hard-refresh (Ctrl/Cmd-Shift-R) to register the new Service Worker"
log "  - tail -f $LOG_FILE for live logs"