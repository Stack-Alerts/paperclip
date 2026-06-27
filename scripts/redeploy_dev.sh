#!/usr/bin/env bash
# Redeploy dev environment to a specific commit (or HEAD).
# Called by action_dispatch_routine.py for [no-sha: redeploy] issues.
#
# Usage: bash scripts/redeploy_dev.sh [<commit-sha>]
#
# Exit codes:
#   0 — success
#   1 — commit not found
#   2 — dependency install failed

set -euo pipefail

COMMIT="${1:-HEAD}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[redeploy_dev] target commit: ${COMMIT}"
echo "[redeploy_dev] repo root: ${REPO_ROOT}"

# Fetch latest refs so the SHA is available locally
git -C "${REPO_ROOT}" fetch origin --prune 2>&1

# Verify the commit exists
if ! git -C "${REPO_ROOT}" cat-file -e "${COMMIT}^{commit}" 2>/dev/null; then
    echo "[redeploy_dev] ERROR: commit ${COMMIT} not found after fetch" >&2
    exit 1
fi

# Check out the target commit (skip if HEAD was requested)
if [[ "${COMMIT}" != "HEAD" ]]; then
    echo "[redeploy_dev] checking out ${COMMIT}..."
    git -C "${REPO_ROOT}" checkout "${COMMIT}" -- 2>&1
fi

echo "[redeploy_dev] installing dependencies..."
if [[ -f "${REPO_ROOT}/requirements.txt" ]]; then
    pip install -q -r "${REPO_ROOT}/requirements.txt" 2>&1
fi

# Restart the dev server process (pm2 is the process manager if present)
if command -v pm2 &>/dev/null; then
    echo "[redeploy_dev] restarting via pm2..."
    pm2 restart all 2>&1 || true
elif command -v systemctl &>/dev/null && systemctl is-active --quiet btc-dev.service 2>/dev/null; then
    echo "[redeploy_dev] restarting btc-dev.service..."
    systemctl restart btc-dev.service 2>&1
else
    echo "[redeploy_dev] no process manager detected — manual restart may be required"
fi

ACTUAL_SHA="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
echo "[redeploy_dev] deployed SHA: ${ACTUAL_SHA}"
echo "[redeploy_dev] done"
