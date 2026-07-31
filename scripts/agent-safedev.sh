#!/usr/bin/env bash
# agent-safedev.sh — safe-development preflight for paperclip-btcaaaaa-main.
#
# Single entry point that an agent (human or AI) calls BEFORE editing any
# code in this worktree. Implements the policy documented in AGENTS.md §13:
#
#   1. Verify we are inside the paperclip-btcaaaaa-main worktree.
#   2. Snapshot the current live state (pre-implementation recovery point).
#   3. Fetch the latest from the configured fork remote so the agent is
#      working on top of the newest golden branch / merge queue state.
#   4. Print a status block the agent can paste into the Paperclip issue
#      comment so the board can see what was checked before work began.
#
# Usage:
#   ./scripts/agent-safedev.sh                       # full preflight
#   ./scripts/agent-safedev.sh --remote <name>       # override remote (default: fork)
#   ./scripts/agent-safedev.sh --base <remote/ref>   # override base (default: <remote>/btcaaaaa-main)
#   ./scripts/agent-safedev.sh --issue <ref>          # include issue ref in receipt
#   ./scripts/agent-safedev.sh --help
#
# Exit codes:
#   0   preflight succeeded — safe to start implementation
#   1   invalid invocation or wrong worktree
#   2   dirty tree — refuse until the current work is committed or stashed
#   3   fetch or base-ref resolution failed
#   4   snapshot failed
#   5   branch does not contain the latest configured base
#   130 interrupted

set -euo pipefail

REMOTE="fork"
BASE_REF="${PAPERCLIP_SAFEDEV_BASE_REF:-}"
ISSUE_REF="${PAPERCLIP_TASK_ID:-${BTCAAAAA:-}}"

usage() {
  sed -n '2,30p' "$0"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote) REMOTE="${2:?missing remote name}"; shift 2 ;;
    --base)   BASE_REF="${2:?missing base ref}"; shift 2 ;;
    --issue)  ISSUE_REF="${2:?missing issue ref}"; shift 2 ;;
    --help|-h) usage ;;
    *)        echo "agent-safedev: unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$BASE_REF" ]]; then
  BASE_REF="$REMOTE/btcaaaaa-main"
fi

REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO" ]] || { echo "agent-safedev: ERROR: not inside a git worktree" >&2; exit 1; }
case "$REPO" in
  *paperclip-btcaaaaa-main*) ;;
  *) echo "agent-safedev: ERROR: not in the paperclip-btcaaaaa-main worktree (got $REPO)" >&2; exit 1 ;;
esac

cd "$REPO"

if [[ -n "$ISSUE_REF" ]]; then
  echo "agent-safedev: issue ref = $ISSUE_REF"
fi
echo "agent-safedev: worktree = $REPO"

if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "agent-safedev: ERROR: working tree has uncommitted changes." >&2
  echo "  Commit or stash the current work before starting another implementation:" >&2
  git status --short | sed 's/^/    /' >&2
  exit 2
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "agent-safedev: ERROR: remote '$REMOTE' is not configured." >&2
  echo "  Available remotes:" >&2
  git remote -v | sed 's/^/    /' >&2
  exit 3
fi

echo "agent-safedev: fetching $REMOTE..."
if ! git fetch --prune --tags "$REMOTE"; then
  echo "agent-safedev: ERROR: git fetch $REMOTE failed" >&2
  exit 3
fi

if ! git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null; then
  echo "agent-safedev: ERROR: base ref '$BASE_REF' does not resolve to a commit." >&2
  exit 3
fi

if ! git merge-base --is-ancestor "$BASE_REF" HEAD; then
  BEHIND="$(git rev-list --count "HEAD..$BASE_REF")"
  echo "agent-safedev: ERROR: HEAD does not contain the latest $BASE_REF ($BEHIND commit(s) behind)." >&2
  echo "  Rebase or merge $BASE_REF into this issue branch, resolve conflicts, then rerun." >&2
  exit 5
fi

RECOVERY="$REPO/scripts/recovery.sh"
if [[ ! -x "$RECOVERY" ]]; then
  echo "agent-safedev: ERROR: $RECOVERY is missing or not executable." >&2
  exit 4
fi

echo "agent-safedev: taking local recovery snapshot..."
SNAPSHOT_OUTPUT="$(mktemp)"
trap 'rm -f "$SNAPSHOT_OUTPUT"' EXIT
if ! "$RECOVERY" snapshot --no-upload >"$SNAPSHOT_OUTPUT" 2>&1; then
  cat "$SNAPSHOT_OUTPUT" >&2
  echo "agent-safedev: ERROR: snapshot failed" >&2
  exit 4
fi
cat "$SNAPSHOT_OUTPUT"
SNAPSHOT_ID="$(sed -n 's/.*snapshot \([0-9][0-9-]*\) complete.*/\1/p' "$SNAPSHOT_OUTPUT" | tail -n 1)"
# Defense in depth: SNAPSHOT_ID is parsed from recovery.sh output. Validate
# the format before splicing it into a filesystem path so a malformed or
# hostile snapshot output cannot redirect the path check.
if [[ ! "$SNAPSHOT_ID" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}$ ]]; then
  echo "agent-safedev: ERROR: recovery snapshot id '$SNAPSHOT_ID' is malformed (expected YYYY-MM-DD-HHMM)." >&2
  exit 4
fi
if [[ ! -d "/home/sirrus/paperclip-snapshots/$SNAPSHOT_ID" ]]; then
  echo "agent-safedev: ERROR: snapshot completed without a verifiable local restore point." >&2
  exit 4
fi

HEAD_SHA="$(git rev-parse HEAD)"
BASE_SHA="$(git rev-parse "$BASE_REF")"
AHEAD="$(git rev-list --count "$BASE_REF..HEAD")"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
GIT_DIR="$(git rev-parse --git-dir)"
RECEIPT="$GIT_DIR/paperclip-safedev.receipt"
printf '%s\n' \
  "head=$HEAD_SHA" \
  "base_ref=$BASE_REF" \
  "base_sha=$BASE_SHA" \
  "branch=$BRANCH" \
  "snapshot_id=$SNAPSHOT_ID" \
  "issue_ref=$ISSUE_REF" \
  "completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$RECEIPT"

cat <<EOF

=== agent-safedev: preflight complete ===
  worktree    : $REPO
  branch      : $BRANCH
  head        : $HEAD_SHA
  base        : $BASE_REF -> $BASE_SHA
  ahead       : +$AHEAD
  snapshot    : $SNAPSHOT_ID
  receipt     : $RECEIPT
  next step   : implement the change in this worktree
                then run ./scripts/agent-premerge-check.sh before pushing
=== safe to start implementation ===
EOF