#!/usr/bin/env bash
#
# scripts/lint-branch-name.sh — enforce the BTC merge-governance branch-naming contract.
#
# Effective per BTCAAAAA-30046 (Phase 2 of the merge-governance roll-out drafted on
# BTCAAAAA-30038). The full contract lives in /AGENTS.md § Merge governance.
#
# Exit codes:
#   0 — current branch matches the contract, or is on a known umbrella (main, main-merge)
#   1 — invalid branch name; the offending name is printed to stderr
#   2 — usage / environment error (not a git repo, detached HEAD with no override)
#
# Usage:
#   scripts/lint-branch-name.sh                    # check current HEAD branch
#   BRANCH=fix/BTCAAAAA-30046-foo scripts/lint-branch-name.sh   # check supplied name
#
# Wire into your editor's pre-commit hook (none installed repo-wide yet — Phase 3,
# BTCAAAAA-30040, lands enforcement).
set -euo pipefail

# Allow override for self-testing without checking out a branch.
BRANCH="${BRANCH:-}"
if [[ -z "$BRANCH" ]]; then
  if ! BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"; then
    echo "lint-branch-name: not inside a git work tree" >&2
    exit 2
  fi
  if [[ "$BRANCH" == "HEAD" ]]; then
    echo "lint-branch-name: detached HEAD — pass BRANCH=<name> to check a specific name" >&2
    exit 2
  fi
fi

# Known umbrella branches that bypass the issue-branch contract.
UMBRELLA_RE='^(main|main-merge)$'

# Issue branch contract:
#   {type}/BTCAAAAA-{n}-{kebab-slug}
# where type ∈ {fix, feat, chore, docs, test, refactor}
# and slug is lowercase alnum + hyphens.
ISSUE_RE='^(fix|feat|chore|docs|test|refactor)/BTCAAAAA-[0-9]+-[a-z0-9-]+$'

if [[ "$BRANCH" =~ $UMBRELLA_RE ]] || [[ "$BRANCH" =~ $ISSUE_RE ]]; then
  exit 0
fi

cat >&2 <<EOF
lint-branch-name: branch name does not match the merge-governance contract.

  Offending name: ${BRANCH}

Allowed forms:
  - Issue branch:  (fix|feat|chore|docs|test|refactor)/BTCAAAAA-NNN-kebab-slug
  - Umbrella:      main, main-merge

See /AGENTS.md § Merge governance for the full contract (BTCAAAAA-30046).
EOF
exit 1
