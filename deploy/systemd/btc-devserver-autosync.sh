#!/bin/bash
# btc-devserver-autosync.sh — keep the dev server worktree on origin/main (BTCAAAAA-38800)
#
# Root cause: btc-dev-server.service syncs its dedicated worktree
# (/home/sirrus/projects/btc-devserver-main) to origin/main only at service
# START. Nothing resynced it after a merge, so :3010 kept serving the build
# from whenever the service last restarted.
#
# This script runs every 60s via btc-devserver-autosync.timer:
#   - HEAD == origin/main            -> no-op
#   - only source files changed      -> git reset --hard origin/main
#                                       (`next dev` file watcher hot-reloads)
#   - deps/config changed            -> restart btc-dev-server.service
#                                       (its ExecStartPre re-syncs + recompiles)

set -euo pipefail

DEVTREE=/home/sirrus/projects/btc-devserver-main

cd "$DEVTREE"
git fetch --quiet origin main

HEAD_SHA=$(git rev-parse HEAD)
MAIN_SHA=$(git rev-parse origin/main)

if [[ "$HEAD_SHA" == "$MAIN_SHA" ]]; then
  exit 0
fi

echo "[autosync] dev worktree at $HEAD_SHA, origin/main at $MAIN_SHA — syncing"

# Dependency or build-config changes need a full service restart; plain source
# changes are picked up by the running `next dev` watcher after the reset.
if git diff --name-only "$HEAD_SHA" "$MAIN_SHA" \
   | grep -qE '(^|/)(package\.json|pnpm-lock\.yaml|package-lock\.json|next\.config\.(js|mjs|ts)|tsconfig\.json)$'; then
  echo "[autosync] deps/config changed — restarting btc-dev-server.service"
  systemctl --user restart btc-dev-server.service
else
  git reset --hard origin/main
  echo "[autosync] hot-synced to origin/main ($MAIN_SHA); next dev will hot-reload"
fi
