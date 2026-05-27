#!/usr/bin/env bash
# lint-pr-scope.sh — Phase 6b scope-creep detector (BTCAAAAA-30054).
#
# Detects when a PR/branch carries commits whose subjects reference an issue
# identifier that does NOT match the branch's own identifier. Source of truth:
# the shared-working-tree forward-failure F-4 in [BTCAAAAA-30038 process-audit].
#
# Exit codes:
#   0 — clean: every commit references the branch's identifier or none at all
#   1 — scope creep: at least one commit references a different BTCAAAAA-NNN
#   2 — cannot determine context (not in a git repo / detached HEAD / no branch
#       identifier and no --branch override)
#
# Usage:
#   bash scripts/lint-pr-scope.sh
#     → uses current branch name and `git log origin/main..HEAD --format=%s`
#
#   bash scripts/lint-pr-scope.sh --branch <name> --base <ref>
#     → uses provided branch name and `git log <base>..HEAD --format=%s`
#
#   printf '%s\n' "subj1" "subj2" | bash scripts/lint-pr-scope.sh \
#       --branch <name> --stdin
#     → reads commit subjects from stdin (one per line); used by the routine
#       so the same logic governs local pre-push and remote PR scanning.
#
# Wiring:
#   - Pre-push hook installer: scripts/hooks/pre-push references this script.
#   - Routine: scripts/pr_scope_check_routine.py reimplements the same logic
#     in Python for the remote-PR scanner.

set -u

ID_REGEX='BTCAAAAA-[0-9]+'
BRANCH=""
BASE="origin/main"
USE_STDIN=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --branch)
      BRANCH="${2-}"
      shift 2
      ;;
    --base)
      BASE="${2-}"
      shift 2
      ;;
    --stdin)
      USE_STDIN=1
      shift
      ;;
    -h|--help)
      sed -n '2,30p' "$0" >&2
      exit 0
      ;;
    *)
      echo "lint-pr-scope.sh: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$BRANCH" ]; then
  if ! BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"; then
    echo "lint-pr-scope.sh: not inside a git repository" >&2
    exit 2
  fi
  if [ "$BRANCH" = "HEAD" ]; then
    echo "lint-pr-scope.sh: detached HEAD — pass --branch <name>" >&2
    exit 2
  fi
fi

case "$BRANCH" in
  main|main-merge)
    exit 0
    ;;
esac

BRANCH_ID="$(printf '%s' "$BRANCH" | grep -oE "$ID_REGEX" | head -n1)"
if [ -z "$BRANCH_ID" ]; then
  cat >&2 <<EOF
lint-pr-scope.sh: branch "$BRANCH" carries no BTCAAAAA-NNN identifier.

The merge-governance contract requires every code branch to be named
<type>/BTCAAAAA-NNN-<slug>. Without an identifier we cannot determine the
intended scope, so we refuse to merge.
EOF
  exit 2
fi

if [ "$USE_STDIN" -eq 1 ]; then
  SUBJECTS="$(cat)"
else
  if ! git rev-parse --verify "$BASE" >/dev/null 2>&1; then
    echo "lint-pr-scope.sh: base ref '$BASE' not found — fetch origin first." >&2
    exit 2
  fi
  SUBJECTS="$(git log "${BASE}..HEAD" --format='%H %s' 2>/dev/null || true)"
fi

if [ -z "${SUBJECTS//[[:space:]]/}" ]; then
  exit 0
fi

offenders=""
while IFS= read -r line; do
  [ -z "${line//[[:space:]]/}" ] && continue
  refs="$(printf '%s' "$line" | grep -oE "$ID_REGEX" || true)"
  [ -z "$refs" ] && continue
  for r in $refs; do
    if [ "$r" != "$BRANCH_ID" ]; then
      offenders="${offenders}${line}\n"
      break
    fi
  done
done <<EOF
$SUBJECTS
EOF

if [ -n "$offenders" ]; then
  cat >&2 <<EOF
lint-pr-scope.sh: scope creep detected on branch "$BRANCH" (identifier: $BRANCH_ID).

The following commit(s) reference a different BTCAAAAA-NNN identifier:

$(printf '%b' "$offenders")
Each issue must live on its own branch (merge-governance Phase 2 contract,
BTCAAAAA-30046). Move the offending commit(s) to a branch named for the
issue they actually fix, e.g.

  git switch -c <type>/BTCAAAAA-NNN-<slug> origin/main
  git cherry-pick <commit-sha>

If a commit legitimately references multiple issues (e.g. a follow-up that
also closes a duplicate), use a "Refs:" trailer in the commit body instead
of putting the second identifier in the subject line.
EOF
  exit 1
fi

exit 0
