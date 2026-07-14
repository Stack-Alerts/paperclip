#!/usr/bin/env bash
# agent-premerge-check.sh — mandatory quality gate before pushing Paperclip mods.

set -euo pipefail

REMOTE="fork"
BASE_REF="${PAPERCLIP_SAFEDEV_BASE_REF:-}"

usage() {
  sed -n '2,20p' "$0"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote) REMOTE="${2:?missing remote name}"; shift 2 ;;
    --base)   BASE_REF="${2:?missing base ref}"; shift 2 ;;
    --help|-h) usage ;;
    *) echo "agent-premerge-check: unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$BASE_REF" ]]; then
  BASE_REF="$REMOTE/btcaaaaa-main"
fi

REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO" ]] || { echo "agent-premerge-check: ERROR: not inside a git worktree" >&2; exit 1; }
case "$REPO" in
  *paperclip-btcaaaaa-main*) ;;
  *) echo "agent-premerge-check: ERROR: wrong worktree: $REPO" >&2; exit 1 ;;
esac
cd "$REPO"

if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "agent-premerge-check: ERROR: commit or stash all changes before running the gate." >&2
  git status --short | sed 's/^/    /' >&2
  exit 2
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "agent-premerge-check: ERROR: remote '$REMOTE' is not configured." >&2
  exit 3
fi

echo "agent-premerge-check: fetching $REMOTE..."
git fetch --prune --tags "$REMOTE"
if ! git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null; then
  echo "agent-premerge-check: ERROR: base ref '$BASE_REF' does not resolve to a commit." >&2
  exit 3
fi
if ! git merge-base --is-ancestor "$BASE_REF" HEAD; then
  echo "agent-premerge-check: ERROR: HEAD does not contain the latest $BASE_REF." >&2
  echo "  Update the branch and rerun ./scripts/agent-safedev.sh before continuing." >&2
  exit 4
fi

GIT_DIR="$(git rev-parse --git-dir)"
SAFEDEV_RECEIPT="$GIT_DIR/paperclip-safedev.receipt"
if [[ ! -f "$SAFEDEV_RECEIPT" ]]; then
  echo "agent-premerge-check: ERROR: no safe-development receipt." >&2
  echo "  Run ./scripts/agent-safedev.sh before implementation." >&2
  exit 5
fi

receipt_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "$SAFEDEV_RECEIPT" | tail -n 1
}

SAFE_HEAD="$(receipt_value head)"
SAFE_BASE_REF="$(receipt_value base_ref)"
SAFE_BASE_SHA="$(receipt_value base_sha)"
SNAPSHOT_ID="$(receipt_value snapshot_id)"
CURRENT_BASE_SHA="$(git rev-parse "$BASE_REF")"

if [[ -z "$SAFE_HEAD" || -z "$SAFE_BASE_SHA" || -z "$SNAPSHOT_ID" ]]; then
  echo "agent-premerge-check: ERROR: safe-development receipt is incomplete." >&2
  exit 5
fi
if [[ "$SAFE_BASE_REF" != "$BASE_REF" || "$SAFE_BASE_SHA" != "$CURRENT_BASE_SHA" ]]; then
  echo "agent-premerge-check: ERROR: $BASE_REF changed since the pre-implementation snapshot." >&2
  echo "  Update the branch and rerun ./scripts/agent-safedev.sh before continuing." >&2
  exit 5
fi
if ! git merge-base --is-ancestor "$SAFE_HEAD" HEAD; then
  echo "agent-premerge-check: ERROR: current HEAD did not descend from the preflight HEAD." >&2
  exit 5
fi
if [[ ! -d "/home/sirrus/paperclip-snapshots/$SNAPSHOT_ID" ]]; then
  echo "agent-premerge-check: ERROR: recovery snapshot $SNAPSHOT_ID is missing." >&2
  exit 5
fi

HEAD_SHA="$(git rev-parse HEAD)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="$GIT_DIR/paperclip-premerge"
LOG_FILE="$LOG_DIR/${HEAD_SHA:0:12}-$STAMP.log"
mkdir -p "$LOG_DIR"

run_logged() {
  local label="$1"
  shift
  printf '\n=== %s ===\n' "$label" | tee -a "$LOG_FILE"
  set +e
  "$@" 2>&1 | tee -a "$LOG_FILE"
  local status="${PIPESTATUS[0]}"
  set -e
  if [[ "$status" -ne 0 ]]; then
    echo "agent-premerge-check: ERROR: $label failed (exit $status)." >&2
    echo "  Full log: $LOG_FILE" >&2
    exit "$status"
  fi
}

printf 'head=%s\nbase_ref=%s\nbase_sha=%s\nsnapshot_id=%s\nstarted_at=%s\n' \
  "$HEAD_SHA" "$BASE_REF" "$CURRENT_BASE_SHA" "$SNAPSHOT_ID" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$LOG_FILE"

run_logged "diff whitespace check" git diff --check "$BASE_REF...HEAD"
run_logged "test iteration 1 of 2" pnpm test
run_logged "test iteration 2 of 2" pnpm test
run_logged "workspace typecheck" pnpm -r typecheck
run_logged "production build" pnpm build

if [[ "$(git rev-parse HEAD)" != "$HEAD_SHA" ]]; then
  echo "agent-premerge-check: ERROR: HEAD changed while checks were running." >&2
  exit 6
fi
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "agent-premerge-check: ERROR: checks changed the working tree." >&2
  git status --short | sed 's/^/    /' >&2
  exit 6
fi

RECEIPT="$GIT_DIR/paperclip-premerge.receipt"
printf '%s\n' \
  "head=$HEAD_SHA" \
  "base_ref=$BASE_REF" \
  "base_sha=$CURRENT_BASE_SHA" \
  "snapshot_id=$SNAPSHOT_ID" \
  "test_iterations=2" \
  "typecheck=passed" \
  "build=passed" \
  "log=$LOG_FILE" \
  "completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$RECEIPT"

cat <<EOF

=== agent-premerge-check: gate passed ===
  head            : $HEAD_SHA
  base            : $BASE_REF -> $CURRENT_BASE_SHA
  snapshot        : $SNAPSHOT_ID
  test iterations : 2 passed
  typecheck/build : passed
  receipt         : $RECEIPT
  log             : $LOG_FILE
=== safe to push into the merge queue ===
EOF
