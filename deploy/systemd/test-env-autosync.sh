#!/bin/bash
# test-env-autosync.sh — keep the test environment on origin/main (BTCAAAAA-38802)
#
# The test env (/home/sirrus/projects/BTC-Trade-Engine-PaperClip-Testing) serves
# a PRODUCTION build (`next start -p 13000`), which does not hot-reload. Any
# change on origin/main therefore needs: reset --hard, `next build`, and a
# restart of the affected test-bte services.
#
# Runs every 5 min via test-env-autosync.timer:
#   - HEAD == origin/main -> no-op
#   - web-ui changed      -> npm install (if lockfile changed) + next build + restart test-bte-webui
#   - python changed      -> pip install (if requirements changed) + restart test-bte-api/thick

set -euo pipefail

TESTTREE=/home/sirrus/projects/BTC-Trade-Engine-PaperClip-Testing
WEBUI="$TESTTREE/packages/web-ui"

cd "$TESTTREE"
git fetch --quiet origin main

HEAD_SHA=$(git rev-parse HEAD)
MAIN_SHA=$(git rev-parse origin/main)

if [[ "$HEAD_SHA" == "$MAIN_SHA" ]]; then
  exit 0
fi

echo "[test-autosync] test env at $HEAD_SHA, origin/main at $MAIN_SHA — syncing"

CHANGED=$(git diff --name-only "$HEAD_SHA" "$MAIN_SHA")
git reset --hard origin/main

if grep -q '^packages/web-ui/' <<<"$CHANGED"; then
  if grep -qE '^packages/web-ui/(package\.json|package-lock\.json)$' <<<"$CHANGED"; then
    echo "[test-autosync] web-ui deps changed — npm install"
    # npm ci fails: @tremor/react peer-depends on react 18 while the app is on 19
    (cd "$WEBUI" && npm install --legacy-peer-deps --no-audit --no-fund)
  fi
  echo "[test-autosync] rebuilding web-ui"
  (cd "$WEBUI" && npx next build)
  systemctl --user try-restart test-bte-webui.service
fi

if grep -qE '^(src/|scripts/|requirements\.txt)' <<<"$CHANGED"; then
  if grep -q '^requirements\.txt$' <<<"$CHANGED"; then
    echo "[test-autosync] python deps changed — pip install"
    "$TESTTREE/venv/bin/pip" install --quiet -r requirements.txt
  fi
  systemctl --user try-restart test-bte-api.service test-bte-thick.service
fi

echo "[test-autosync] synced to origin/main ($MAIN_SHA)"
