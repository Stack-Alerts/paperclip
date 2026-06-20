#!/usr/bin/env bash
# setup-monitor-worktree.sh — ensure the pinned monitor worktree exists.
# Called by install-backup-deadman-monitor.sh and siblings before deploying units.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKTREE_PATH="${HOME}/.paperclip/monitor-worktrees/btc-main"
REMOTE="origin"
BRANCH="monitor-main"
TRACKING="origin/main"

echo "=== Monitor Worktree Setup ==="
echo "  Repo:     ${REPO_ROOT}"
echo "  Worktree: ${WORKTREE_PATH}"
echo ""

if [ -d "${WORKTREE_PATH}/.git" ] || [ -f "${WORKTREE_PATH}/.git" ]; then
    echo "  Worktree already exists — fast-forwarding to ${TRACKING}..."
    git -C "${WORKTREE_PATH}" fetch "${REMOTE}" main
    git -C "${WORKTREE_PATH}" merge --ff-only "${REMOTE}/main" || {
        echo "  WARNING: fast-forward failed (local edits?). Continuing with existing state."
    }
else
    echo "  Creating worktree at ${WORKTREE_PATH} tracking ${TRACKING}..."
    mkdir -p "$(dirname "${WORKTREE_PATH}")"
    git -C "${REPO_ROOT}" fetch "${REMOTE}" main
    git -C "${REPO_ROOT}" worktree add "${WORKTREE_PATH}" "${REMOTE}/main"
    git -C "${WORKTREE_PATH}" checkout -b "${BRANCH}" --track "${REMOTE}/main"
fi

echo "  Worktree HEAD: $(git -C "${WORKTREE_PATH}" rev-parse --short HEAD)"
echo "  Branch:        $(git -C "${WORKTREE_PATH}" branch --show-current)"
echo "  Setup complete."
