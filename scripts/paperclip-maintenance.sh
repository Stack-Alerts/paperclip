#!/usr/bin/env bash
# paperclip-maintenance.sh — single command to repair, patch, restart, and
# verify the local BTCAAAAA paperclip instance after a restart or upgrade.
#
# What it does (idempotent, safe to re-run):
#   0. Preflight: resolves npx cache (auto-detects latest installed version).
#   1. (--upgrade only) Upgrades paperclipai to the latest stable release
#      via `npm install -g paperclipai@latest`, then `npx -y paperclipai@latest`
#      to populate the local npx cache the server runs from.
#   2. Patches the npx-cached paperclipai server with two fixes that aren't
#      yet upstream (cross-company-blocker recovery loop + agent-as-board
#      comment misattribution). Skips lines that are already patched.
#   3. Ensures the paperclip-backup plugin is installed (re-installs via
#      POST /api/plugins/install if the live runtime copy is missing).
#   4. Clears stuck `offsite-running` / `backup-running` rows in plugin_state
#      so the recovery loop doesn't churn.
#   5. Restarts the paperclip server, waits for /api/health 200.
#   6. Reports status (plugin list, recovery-flow health, backup listing).
#
# Usage:
#   ./paperclip-maintenance.sh                # full cycle (patch + restart + verify)
#   ./paperclip-maintenance.sh --upgrade      # upgrade to latest + patch + restart + verify
#   ./paperclip-maintenance.sh --patch-only   # just patch the server, don't restart
#   ./paperclip-maintenance.sh --no-restart   # patch + verify, leave server running
#   ./paperclip-maintenance.sh --reinstall-plugin <path>
#   ./paperclip-maintenance.sh --canary       # upgrade to latest canary instead of stable
#
# Requirements: psql + npm + npx on PATH, paperclip running on 127.0.0.1:3100.

set -euo pipefail

PAPERCLIP_HOME="${PAPERCLIP_HOME:-/home/sirrus/.paperclip}"
PAPERCLIP_URL="${PAPERCLIP_URL:-http://127.0.0.1:3100}"
NPM="${NPM:-npm}"
NPX="${NPX:-npx}"
PG="${PG:-/home/sirrus/.pg0/installation/18.1.0/bin/psql}"
PG_HOST="127.0.0.1"
PG_PORT="54329"
PG_USER="paperclip"
PG_DB="paperclip"
PLUGIN_SOURCE_DEFAULT="/home/sirrus/paperclip-btcaaaaa-main/packages/plugins/paperclip-backup"
PLUGIN_INSTALL_DIR="$PAPERCLIP_HOME/plugins/paperclip-backup"

# Resolve the active npx cache dir for paperclipai. Falls back to the
# newest "paperclipai" install in ~/.npm/_npx if the env var isn't set.
NPX_CACHE_DIR="${NPX_CACHE_DIR:-}"
resolve_npx_cache() {
    if [[ -n "$NPX_CACHE_DIR" && -d "$NPX_CACHE_DIR/node_modules/@paperclipai/server" ]]; then
        echo "$NPX_CACHE_DIR"; return 0
    fi
    # find -path with globs doesn't behave well across all shells here; iterate
    # the candidate dirs and pick the most recently modified one that has the
    # @paperclipai/server subpath.
    local best="" best_mtime=0 d mtime
    for d in ~/.npm/_npx/*/; do
        [[ -d "$d/node_modules/@paperclipai/server" ]] || continue
        mtime=$(stat -c %Y "$d" 2>/dev/null || echo 0)
        if (( mtime > best_mtime )); then
            best_mtime=$mtime
            best=$d
        fi
    done
    if [[ -z "$best" ]]; then
        echo "ERROR: could not locate any npx cache with paperclipai server" >&2
        return 1
    fi
    # Strip trailing slash
    echo "${best%/}"
}

NPX_CACHE="$(resolve_npx_cache)"
RECOVERY_FILE="$NPX_CACHE/node_modules/@paperclipai/server/dist/services/recovery/service.js"
ROUTES_FILE="$NPX_CACHE/node_modules/@paperclipai/server/dist/routes/issues.js"
PLUGIN_SOURCE="$PLUGIN_SOURCE_DEFAULT"
PLUGIN_SOURCE_DEFAULT="/home/sirrus/paperclip-btcaaaaa-main/packages/plugins/paperclip-backup"
PLUGIN_INSTALL_DIR="$PAPERCLIP_HOME/plugins/paperclip-backup"
PAPERCLIP_URL="${PAPERCLIP_URL:-http://127.0.0.1:3100}"
PG="${PG:-/home/sirrus/.pg0/installation/18.1.0/bin/psql}"
PG_HOST="127.0.0.1"
PG_PORT="54329"
PG_USER="paperclip"
PG_DB="paperclip"

PATCH_ONLY=0
NO_RESTART=0
DO_UPGRADE=0
USE_CANARY=0
PLUGIN_SOURCE="$PLUGIN_SOURCE_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --patch-only) PATCH_ONLY=1; shift ;;
    --no-restart) NO_RESTART=1; shift ;;
    --upgrade) DO_UPGRADE=1; shift ;;
    --canary) USE_CANARY=1; DO_UPGRADE=1; shift ;;
    --reinstall-plugin) PLUGIN_SOURCE="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$*"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[1;33m!\033[0m %s\n" "$*"; }
die()  { printf "  \033[1;31m✗\033[0m %s\n" "$*"; exit 1; }

# ────────────────────────────────────────────────────────────────────────────
step "0  preflight"

command -v curl >/dev/null || die "curl missing"
command -v jq   >/dev/null || warn "jq missing (will use python for JSON)"
[[ -d "$NPX_CACHE" ]] || die "paperclipai server cache not found at $NPX_CACHE"
[[ -d "$PAPERCLIP_HOME" ]] || die "PAPERCLIP_HOME=$PAPERCLIP_HOME missing"

if curl -sf -m 3 "$PAPERCLIP_URL/api/health" >/dev/null; then
  ok "paperclip server reachable at $PAPERCLIP_URL"
  if [[ -x "$(command -v "$NPM" 2>/dev/null || echo /nonexistent)" ]]; then
    CUR_VER=$(curl -sS "$PAPERCLIP_URL/api/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
    ok "running paperclip version: $CUR_VER"
  fi
else
  warn "paperclip not reachable — will start it after patching"
fi

if [[ -x "$PG" ]]; then
  ok "psql available at $PG"
else
  warn "psql not at $PG; postgres ops will be skipped"
fi

ok "resolved npx cache: $NPX_CACHE"

# ────────────────────────────────────────────────────────────────────────────
if [[ "$DO_UPGRADE" == "1" ]]; then
  step "1  upgrade paperclipai"

  DIST_TAG="latest"
  [[ "$USE_CANARY" == "1" ]] && DIST_TAG="canary"

  LATEST=$("$NPM" view paperclipai@$DIST_TAG version 2>/dev/null || echo "?")
  CUR_VER=$(curl -sS "$PAPERCLIP_URL/api/health" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
  ok "latest paperclipai@$DIST_TAG = $LATEST  |  running = $CUR_VER"

  # Pull into npx cache. npx -y forces a fetch even if a matching cache exists.
  # We then re-resolve NPX_CACHE so subsequent patch steps target the new install.
  "$NPX" -y "paperclipai@$DIST_TAG" --version >/dev/null 2>&1 \
    || warn "npx paperclipai@$DIST_TAG --version failed (continuing)"
  NEW_NPX_CACHE="$(resolve_npx_cache)"
  if [[ "$NEW_NPX_CACHE" != "$NPX_CACHE" ]]; then
    ok "npx cache moved: $NPX_CACHE  →  $NEW_NPX_CACHE"
    NPX_CACHE="$NEW_NPX_CACHE"
    RECOVERY_FILE="$NPX_CACHE/node_modules/@paperclipai/server/dist/services/recovery/service.js"
    ROUTES_FILE="$NPX_CACHE/node_modules/@paperclipai/server/dist/routes/issues.js"
    # New binary path the restart step needs to use
    PAPERCLIP_BIN="$NPX_CACHE/node_modules/.bin/paperclipai"
  else
    ok "npx cache unchanged ($NPX_CACHE) — version was already pinned or up-to-date"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "2" || echo "1")  patch server: recovery-loop cross-company-blocker fix"

if [[ ! -f "$RECOVERY_FILE" ]]; then
  warn "recovery file not at $RECOVERY_FILE — skipping patch (probably upgraded)"
else
  if grep -q 'validBlockerIds' "$RECOVERY_FILE"; then
    ok "recovery loop already patched (validBlockerIds present)"
  else
    cp "$RECOVERY_FILE" "${RECOVERY_FILE}.bak-$(date +%Y%m%d-%H%M%S)"
    /usr/bin/python3 - <<'PY'
import re, pathlib
p = pathlib.Path('/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/@paperclipai/server/dist/services/recovery/service.js')
src = p.read_text()
old = """        const blockerIds = await existingUnresolvedBlockerIssueIds(input.issue.companyId, input.issue.id);
        // Patched: ensure blockedByIssueIds is never empty so the chain graph
        // shows this issue as a leaf of an actionable dependency. Use the
        // recovery action's own issue as the synthetic blocker — that way
        // the operator sees the link from the auto-recovered issue back to the
        // recovery-action record that triggered it, instead of an orphan with
        // no chain context. Falls back to the latest run id if recovery action
        // doesn't have its own issue record yet.
        const fallbackBlockerIds = [
            recoveryAction.id,
            input.latestRun?.id,
        ].filter(Boolean);
        const finalBlockerIds = blockerIds.length > 0 ? blockerIds : fallbackBlockerIds;
        const updated = await issuesSvc.update(input.issue.id, {
            status: "blocked",
            blockedByIssueIds: finalBlockerIds,
            assigneeAgentId: recoveryAction.ownerAgentId ?? input.issue.assigneeAgentId,
        });"""
new = """        const blockerIds = await existingUnresolvedBlockerIssueIds(input.issue.companyId, input.issue.id);
        // Patched: ensure blockedByIssueIds is never empty so the chain graph
        // shows this issue as a leaf of an actionable dependency. Use the
        // recovery action's own issue as the synthetic blocker — that way
        // the operator sees the link from the auto-recovered issue back to the
        // recovery-action record that triggered it, instead of an orphan with
        // no chain context. Falls back to the latest run id if recovery action
        // doesn't have its own issue record yet.
        //
        // HOTFIX 2026-07-04: validate every candidate is a real issue in the
        // same company before passing to update — otherwise syncBlockedByIssueIds
        // rejects with "Blocked-by issues must belong to the same company"
        // because recovery_action.id and latestRun.id aren't in the issues table.
        const fallbackBlockerIds = [
            recoveryAction.id,
            input.latestRun?.id,
        ].filter(Boolean);
        const candidateBlockerIds = blockerIds.length > 0 ? blockerIds : fallbackBlockerIds;
        let validBlockerIds = [];
        if (candidateBlockerIds.length > 0) {
            const found = await db
                .select({ id: issues.id })
                .from(issues)
                .where(and(eq(issues.companyId, input.issue.companyId), inArray(issues.id, candidateBlockerIds)));
            validBlockerIds = found.map((r) => r.id);
        }
        const updatePayload = {
            status: "blocked",
            assigneeAgentId: recoveryAction.ownerAgentId ?? input.issue.assigneeAgentId,
        };
        if (validBlockerIds.length > 0) {
            updatePayload.blockedByIssueIds = validBlockerIds;
        }
        const updated = await issuesSvc.update(input.issue.id, updatePayload);"""
if old in src:
    p.write_text(src.replace(old, new))
    print('recovery-loop patch applied')
else:
    print('recovery-loop already patched (or upstream changed)')
PY
    if grep -q 'validBlockerIds' "$RECOVERY_FILE"; then ok "recovery loop patched"; else die "patch did not apply — check $RECOVERY_FILE manually"; fi
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "3" || echo "2")  patch server: agent-as-board comment misattribution fix"

if [[ ! -f "$ROUTES_FILE" ]]; then
  warn "routes/issues.js not at $ROUTES_FILE — skipping patch"
else
  if grep -q 'inferredAuthorType' "$ROUTES_FILE"; then
    ok "routes already patched (inferredAuthorType present)"
  else
    cp "$ROUTES_FILE" "${ROUTES_FILE}.bak-$(date +%Y%m%d-%H%M%S)"
    /usr/bin/python3 - <<'PY'
import pathlib
p = pathlib.Path('/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/@paperclipai/server/dist/routes/issues.js')
src = p.read_text()

old_non_tx = """            else {
                comment = await svc.addComment(id, req.body.body, {
                    agentId: actor.agentId ?? undefined,
                    userId: actor.actorType === "user" ? actor.actorId : undefined,
                    runId: actor.runId,
                }, {
                    authorType: req.body.authorType ?? (actor.actorType === "agent" ? "agent" : "user"),
                    presentation: req.body.presentation ?? null,
                    metadata: req.body.metadata ?? null,
                    sourceTrust: await sourceTrustForActorWrite(currentIssue, actor),
                });
            }"""
new_non_tx = """            else {
                // HOTFIX 2026-07-04: if actor.agentId is set, force agent attribution
                // regardless of actorType. The previous code derived authorType from
                // actorType === "agent" ? "agent" : "user", which misattributed
                // comments posted by agents running in local-cli mode under a board
                // session (actorType = "user", actorId = "local-board" but
                // agentId = <uuid>). When the agentId is present, the comment is
                // agent-authored; honor that.
                const inferredAuthorType = actor.agentId
                    ? "agent"
                    : (actor.actorType === "agent" ? "agent" : "user");
                comment = await svc.addComment(id, req.body.body, {
                    agentId: actor.agentId ?? undefined,
                    userId: inferredAuthorType === "user" && actor.actorType === "user"
                        ? actor.actorId
                        : undefined,
                    runId: actor.runId,
                }, {
                    authorType: req.body.authorType ?? inferredAuthorType,
                    presentation: req.body.presentation ?? null,
                    metadata: req.body.metadata ?? null,
                    sourceTrust: await sourceTrustForActorWrite(currentIssue, actor),
                });
            }"""

old_tx = """                txResult = await db.transaction(async (tx) => {
                    const insertedComment = await svc.addComment(id, req.body.body, {
                        agentId: actor.agentId ?? undefined,
                        userId: actor.actorType === "user" ? actor.actorId : undefined,
                        runId: actor.runId,
                    }, commentOptions, tx);"""
new_tx = """                txResult = await db.transaction(async (tx) => {
                    // HOTFIX 2026-07-04: same agentId-overrides-actorType fix as
                    // the non-tx path below — don't leak the board userId when
                    // the actor carries an agentId.
                    const insertedComment = await svc.addComment(id, req.body.body, {
                        agentId: actor.agentId ?? undefined,
                        userId: !actor.agentId && actor.actorType === "user"
                            ? actor.actorId
                            : undefined,
                        runId: actor.runId,
                    }, commentOptions, tx);"""

patched = False
if old_non_tx in src:
    src = src.replace(old_non_tx, new_non_tx)
    patched = True
if old_tx in src:
    src = src.replace(old_tx, new_tx)
    patched = True
p.write_text(src)
print('routes patched' if patched else 'routes already patched (upstream changed)')
PY
    if grep -q 'inferredAuthorType' "$ROUTES_FILE"; then ok "routes patched"; else die "routes patch did not apply"; fi
  fi
fi

[[ "$PATCH_ONLY" == "1" ]] && { ok "patch-only mode — stopping here"; exit 0; }

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "4" || echo "3")  ensure paperclip-backup plugin is installed"

BACKUP_PID=$(curl -sS "$PAPERCLIP_URL/api/plugins" 2>/dev/null | python3 -c "
import sys, json
try:
    for p in json.load(sys.stdin):
        if p['pluginKey'] == 'paperclip.backup':
            print(p['id']); break
except: pass
")
if [[ -n "$BACKUP_PID" ]]; then
  ok "paperclip.backup already installed (plugin id $BACKUP_PID)"
else
  warn "paperclip.backup not installed — installing from $PLUGIN_SOURCE"
  [[ -d "$PLUGIN_SOURCE/dist" ]] || die "plugin source missing: $PLUGIN_SOURCE/dist"
  [[ -f "$PLUGIN_SOURCE/package.json" ]] || die "plugin package.json missing: $PLUGIN_SOURCE/package.json"
  INSTALL_RESULT=$(curl -sS -X POST "$PAPERCLIP_URL/api/plugins/install" \
    -H 'Content-Type: application/json' \
    -d "{\"packageName\":\"$PLUGIN_SOURCE\",\"isLocalPath\":true}")
  NEW_STATUS=$(echo "$INSTALL_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('status') or d.get('error','?'))" 2>/dev/null)
  if [[ "$NEW_STATUS" == "ready" ]]; then
    ok "paperclip.backup installed and ready"
  else
    warn "install returned status=$NEW_STATUS — check server.log"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "5" || echo "4")  clear stuck plugin_state running markers"

if [[ -x "$PG" ]]; then
  STUCK=$(PGPASSWORD=paperclip "$PG" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -tA -c \
    "SELECT count(*) FROM plugin_state WHERE state_key IN ('backup-running','offsite-running');" 2>/dev/null || echo "0")
  if [[ "${STUCK:-0}" -gt 0 ]]; then
    PGPASSWORD=paperclip "$PG" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c \
      "DELETE FROM plugin_state WHERE state_key IN ('backup-running','offsite-running');" >/dev/null 2>&1
    ok "cleared $STUCK stuck running-marker rows"
  else
    ok "no stuck running markers"
  fi
else
  warn "skipping plugin_state cleanup (no psql)"
fi

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "6" || echo "5")  restart paperclip server"

if [[ "$NO_RESTART" == "1" ]]; then
  ok "no-restart mode — leaving server running"
else
  SERVER_PID=$(pgrep -f 'paperclipai run --instance default' | head -1 || true)
  if [[ -n "$SERVER_PID" ]]; then
    warn "killing paperclip server PID $SERVER_PID"
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    for i in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$SERVER_PID" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "$SERVER_PID" 2>/dev/null; then
      kill -KILL "$SERVER_PID" 2>/dev/null || true
    fi
    ok "paperclip server stopped"
  else
    warn "no running paperclip server found"
  fi

  cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
  PAPERCLIP_BIN="${PAPERCLIP_BIN:-$NPX_CACHE/node_modules/.bin/paperclipai}"
  [[ -x "$PAPERCLIP_BIN" ]] || die "paperclipai binary not found at $PAPERCLIP_BIN"
  nohup "$PAPERCLIP_BIN" run --instance default > /tmp/paperclip-restart.log 2>&1 &
  ok "started new paperclip server (PID $!) using $(basename "$PAPERCLIP_BIN")"

  step "$([[ "$DO_UPGRADE" == "1" ]] && echo "7" || echo "6")  waiting for server health"
  for i in $(seq 1 30); do
    if curl -sf -m 2 "$PAPERCLIP_URL/api/health" >/dev/null; then
      ok "paperclip healthy after ${i}s"
      break
    fi
    sleep 1
  done
  curl -sf -m 2 "$PAPERCLIP_URL/api/health" >/dev/null || die "server didn't come up; check /tmp/paperclip-restart.log"
fi

# ────────────────────────────────────────────────────────────────────────────
step "$([[ "$DO_UPGRADE" == "1" ]] && echo "8" || echo "7")  final verification"

RUN_VER=$(curl -sS "$PAPERCLIP_URL/api/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
ok "paperclip version after maintenance: $RUN_VER"

PLUGIN_COUNT=$(curl -sS "$PAPERCLIP_URL/api/plugins" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
ok "$PLUGIN_COUNT plugins registered"
curl -sS "$PAPERCLIP_URL/api/plugins" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    print(f\"  {p['pluginKey']:35s} status={p['status']:8s} v={p['version']}\")
"

if [[ -x "$PG" ]]; then
  RECENT_ERRORS=$(grep -c "periodic heartbeat recovery failed" \
    "$PAPERCLIP_HOME/instances/default/logs/server.log" 2>/dev/null || echo 0)
  printf "  total recovery-loop errors in log: %s\n" "$RECENT_ERRORS"
fi

# Show last few server.log lines for sanity
echo
echo "  last 5 server.log lines:"
grep -h 'INFO\|WARN\|ERROR' "$PAPERCLIP_HOME/instances/default/logs/server.log" 2>/dev/null | tail -5 | sed 's/^/    /'

printf "\n\033[1;32m✓ maintenance complete\033[0m\n"