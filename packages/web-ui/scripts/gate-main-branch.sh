#!/usr/bin/env bash
# packages/web-ui/scripts/gate-main-branch.sh
#
# BTCAAAAA-31217 — predev branch-gate. Closes the `npm run dev` bypass of the
# start.sh main-branch gate ([[BTCAAAAA-30590]]).
#
# Runs as the `predev` script in packages/web-ui/package.json before
# `next dev` boots. Refuses to start when HEAD is not origin/main unless the
# operator explicitly opts out.
#
# Escape hatches (any one allows the dev server to start):
#   BTE_BRANCH_GATE_OK=1     — set by start.sh after its own gate ran (the
#                              "intentional non-main" marker). Quiet allow.
#   FORCE_NON_MAIN_DEV=1     — operator-level escape hatch (loud banner).
#   BTE_SKIP_BRANCH_GATE=1   — same semantics as start.sh's --skip-branch-gate
#                              (loud banner).
#
# Exit codes:
#   0  — allowed (on main, or escape hatch set)
#   1  — refused (HEAD != origin/main, no escape hatch)
#   0  — silent skip if cwd is not a git working tree (e.g. tarball deploy)

set -euo pipefail

red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }

# start.sh-issued bypass: silent allow.
if [[ "${BTE_BRANCH_GATE_OK:-0}" == "1" ]]; then
  exit 0
fi

# Not a git worktree (e.g. node_modules-only deploy) — nothing to enforce.
if ! command -v git >/dev/null 2>&1; then
  exit 0
fi
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Operator escape hatches (loud banner).
loud_banner() {
  local reason="$1" head_sha="$2" main_sha="${3:-unknown}"
  red    '================================================================'
  red    '  BRANCH-GATE BYPASS ACTIVE — DEV SERVER STARTING ON NON-MAIN'
  red    "  reason:     $reason"
  red    "  HEAD:       $head_sha"
  red    "  origin/main:$main_sha"
  red    '  Any UI you see may reflect stale or unmerged code.'
  red    '  Cross-check /health { commit_sha, branch } before reporting bugs.'
  red    '================================================================'
}

# Resolve HEAD + origin/main.
HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"

# Best-effort fetch (silent on failure — air-gapped runners must still work).
git -C "$REPO_ROOT" fetch --quiet origin main 2>/dev/null || true
MAIN_SHA="$(git -C "$REPO_ROOT" rev-parse origin/main 2>/dev/null || echo unknown)"

if [[ "${FORCE_NON_MAIN_DEV:-0}" == "1" ]]; then
  loud_banner "FORCE_NON_MAIN_DEV=1" "$HEAD_SHA" "$MAIN_SHA"
  exit 0
fi

if [[ "${BTE_SKIP_BRANCH_GATE:-0}" == "1" ]]; then
  loud_banner "BTE_SKIP_BRANCH_GATE=1" "$HEAD_SHA" "$MAIN_SHA"
  exit 0
fi

# Hard check.
if [[ "$MAIN_SHA" == "unknown" ]]; then
  red 'ERROR: cannot resolve origin/main; dev server refusing to start.'
  red '       run `git fetch origin main` manually, or set FORCE_NON_MAIN_DEV=1.'
  exit 1
fi

if [[ "$HEAD_SHA" == "$MAIN_SHA" ]]; then
  green "[predev-gate] HEAD is origin/main ($MAIN_SHA) — OK"
  exit 0
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"

# Check if we're on main but diverged from origin/main (unpushed/unpulled commits).
if [[ "$CURRENT_BRANCH" == "main" ]]; then
  COMMIT_COUNTS="$(git -C "$REPO_ROOT" rev-list --left-right --count "origin/main...HEAD" 2>/dev/null || echo unknown)"
  if [[ "$COMMIT_COUNTS" != "unknown" ]]; then
    COMMITS_BEHIND="${COMMIT_COUNTS%$'\t'*}"
    COMMITS_AHEAD="${COMMIT_COUNTS#*$'\t'}"

    # Only refuse if there's actual divergence (either ahead or behind or both)
    if [[ "$COMMITS_AHEAD" -gt 0 ]] || [[ "$COMMITS_BEHIND" -gt 0 ]]; then
      red    '================================================================'
      red    '  predev branch-gate REFUSED to start `next dev`.'
      red    ''

      # Report the divergence state
      if [[ "$COMMITS_BEHIND" -gt 0 ]] && [[ "$COMMITS_AHEAD" -gt 0 ]]; then
        red    "  Local main is $COMMITS_AHEAD commit(s) ahead of and $COMMITS_BEHIND commit(s) behind origin/main."
        REMEDY="git pull --rebase origin main && git push origin main"
      elif [[ "$COMMITS_AHEAD" -gt 0 ]]; then
        red    "  Local main is $COMMITS_AHEAD commit(s) ahead of origin/main."
        REMEDY="git push origin main"
      else
        red    "  Local main is $COMMITS_BEHIND commit(s) behind origin/main."
        REMEDY="git pull --ff-only origin main"
      fi

      red    "  HEAD ($HEAD_SHA) vs origin/main ($MAIN_SHA)."
      red    ''
      red    '  Why this matters (BTCAAAAA-31217):'
      red    '    npm run dev compiles whatever is on disk. The dev server should'
      red    '    run against published code on origin/main, not unpushed work.'
      red    ''
      red    '  How to proceed:'
      red    "    1. $REMEDY                    (recommended — sync with origin)"
      red    '    2. ./start-dev.sh                          (supervised dev on origin/main)'
      red    '    3. FORCE_NON_MAIN_DEV=1 npm run dev        (intentional non-main, loud banner)'
      red    '================================================================'
      exit 1
    fi
  fi
fi

red    '================================================================'
red    '  predev branch-gate REFUSED to start `next dev`.'
red    ''
red    "  Local HEAD ($HEAD_SHA) on branch '$CURRENT_BRANCH'"
red    "  is not origin/main ($MAIN_SHA)."
red    ''
red    '  Why this matters (BTCAAAAA-31217):'
red    '    npm run dev compiles whatever is on disk. If you are on a stale'
red    '    branch (e.g. feature branch), the board will see old UI'
red    '    and wrongly conclude "no progress was made".'
red    ''
red    '  How to proceed:'
red    '    1. ./start-dev.sh                              (recommended — supervised :3010)'
red    '    2. git pull --ff-only origin main && ./start-test.sh  (sync + ephemeral :3000)'
red    '    3. FORCE_NON_MAIN_DEV=1 npm run dev            (intentional non-main, loud banner)'
red    '================================================================'
exit 1
