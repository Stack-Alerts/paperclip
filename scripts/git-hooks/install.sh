#!/bin/bash
# install.sh — install the git hooks for paperclip-btcaaaaa-main
#
# Run this once to wire the worktree to take a snapshot on every
# pre-commit / post-merge:
#   ./scripts/git-hooks/install.sh

set -euo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$REPO" ] || { echo "ERROR: not in a git repo"; exit 1; }

case "$REPO" in
  *paperclip-btcaaaaa-main*) ;;
  *) echo "ERROR: this script only works in the paperclip-btcaaaaa-main worktree (got $REPO)"; exit 1 ;;
esac

# option A: per-worktree .git/hooks symlink (only affects THIS worktree)
# option B: core.hooksPath (only affects THIS worktree too)
# both work because the worktree is its own git dir

HOOKS_DIR="$REPO/scripts/git-hooks"
GIT_DIR="$(git rev-parse --git-dir)"

echo "installing git hooks in $GIT_DIR/hooks/ ..."
for h in pre-commit post-merge; do
  if [ -f "$HOOKS_DIR/$h" ]; then
    rm -f "$GIT_DIR/hooks/$h"
    ln -s "$HOOKS_DIR/$h" "$GIT_DIR/hooks/$h"
    echo "  + $h -> $HOOKS_DIR/$h"
  fi
done

echo
echo "verify:"
ls -l "$GIT_DIR/hooks/" 2>/dev/null | head
echo
echo "next commits and merges in this worktree will trigger a snapshot."
echo "snapshots are non-blocking (run in background) and go to:"
echo "  /home/sirrus/paperclip-snapshots/<YYYY-MM-DD-HHMM>/"
echo
echo "to uninstall:"
echo "  rm $GIT_DIR/hooks/pre-commit $GIT_DIR/hooks/post-merge"
