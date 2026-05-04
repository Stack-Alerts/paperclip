#!/usr/bin/env bash
# verify-push-sync.sh — Push-sync gate for BTC Trade Engine
#
# PURPOSE: Detect unpushed commits and push them to the remote before an agent
#          marks a Paperclip issue as done.
#
# USAGE:
#   scripts/verify-push-sync.sh              # check and push current branch
#   scripts/verify-push-sync.sh --check-only # report status, do NOT push
#   scripts/verify-push-sync.sh --branch <b> # check a specific branch
#
# EXIT CODES:
#   0  — remote is in sync (after push if needed)
#   1  — push failed or repo is in an unexpected state
#   2  — uncommitted changes present (must commit first)
#
# GITHUB_EXPERT protocol: §10 Agent Push Protocol

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── defaults ──────────────────────────────────────────────────────────────────
CHECK_ONLY=false
TARGET_BRANCH=""

# ── argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=true ; shift ;;
    --branch)     TARGET_BRANCH="$2" ; shift 2 ;;
    -h|--help)
      sed -n '3,14p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2 ; exit 1 ;;
  esac
done

cd "$REPO_ROOT"

# ── pre-operation safety check ────────────────────────────────────────────────
echo "=== Push-Sync Gate ==="
echo ""

CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")"
BRANCH="${TARGET_BRANCH:-$CURRENT_BRANCH}"

echo "Branch  : $BRANCH"
echo "Remote  : $(git remote get-url origin 2>/dev/null || echo 'NO REMOTE')"
echo ""

# Check for detached HEAD
if [[ "$CURRENT_BRANCH" == "DETACHED" ]]; then
  echo "ERROR: Detached HEAD state — cannot determine branch to push." >&2
  exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: Uncommitted changes detected. Commit all changes first:" >&2
  git status --short >&2
  exit 2
fi

# Refresh remote-tracking refs (avoids stale-ref false positives)
echo "Fetching remote refs..."
if ! git fetch origin "$BRANCH" 2>&1; then
  echo "WARNING: fetch failed — cannot verify remote state. Proceeding with local check." >&2
fi
echo ""

# ── sync check ────────────────────────────────────────────────────────────────
LOCAL_SHA="$(git rev-parse "$BRANCH")"
REMOTE_SHA="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "NONE")"

if [[ "$LOCAL_SHA" == "$REMOTE_SHA" ]]; then
  echo "OK  Local $BRANCH is in sync with origin/$BRANCH."
  echo "    Local : $LOCAL_SHA"
  echo "    Remote: $REMOTE_SHA"
  exit 0
fi

if [[ "$REMOTE_SHA" == "NONE" ]]; then
  AHEAD="(new branch, no remote tracking)"
  BEHIND=0
else
  AHEAD=$(git rev-list --count "origin/$BRANCH..${BRANCH}" 2>/dev/null || echo "?")
  BEHIND=$(git rev-list --count "${BRANCH}..origin/${BRANCH}" 2>/dev/null || echo "0")
fi

echo "DIVERGENCE DETECTED"
echo "  Local SHA : $LOCAL_SHA"
echo "  Remote SHA: $REMOTE_SHA"
echo "  Ahead by  : $AHEAD commit(s)"
if [[ "${BEHIND}" != "0" ]]; then
  echo "  Behind by : $BEHIND commit(s)"
  echo ""
  echo "WARNING: Remote has commits not present locally (behind by $BEHIND)."
  echo "         Run 'git pull origin $BRANCH' to reconcile before pushing." >&2
  exit 1
fi
echo ""

# Show unpushed commits
echo "Unpushed commits:"
git log "origin/${BRANCH}..${BRANCH}" --oneline 2>/dev/null || git log --oneline -"${AHEAD}" 2>/dev/null
echo ""

# ── push or report ────────────────────────────────────────────────────────────
if [[ "$CHECK_ONLY" == "true" ]]; then
  echo "CHECK-ONLY mode: push skipped."
  echo "Run without --check-only to push, or: git push origin $BRANCH"
  exit 1
fi

echo "Pushing to origin/$BRANCH ..."
if git push origin "$BRANCH"; then
  echo ""
  # Re-fetch to confirm
  git fetch origin "$BRANCH" 2>/dev/null
  NEW_REMOTE_SHA="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "NONE")"
  if [[ "$LOCAL_SHA" == "$NEW_REMOTE_SHA" ]]; then
    echo "VERIFIED  origin/$BRANCH now matches local ($LOCAL_SHA)."
    echo ""
    echo "Issue close gate: PASSED — safe to mark Paperclip issue as done."
    exit 0
  else
    echo "ERROR: Push reported success but remote SHA still differs." >&2
    echo "  Expected: $LOCAL_SHA" >&2
    echo "  Got     : $NEW_REMOTE_SHA" >&2
    exit 1
  fi
else
  echo "ERROR: git push failed." >&2
  exit 1
fi
