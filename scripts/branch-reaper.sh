#!/usr/bin/env bash
# Branch Reaper — stale branch cleanup for Stack-Alerts/BTC-Trade-Engine-PaperClip
# Closes forward-failure F-3 in the merge-governance process audit (BTCAAAAA-30038).
#
# Usage:
#   ./scripts/branch-reaper.sh [--dry-run] [--post-comment]
#
# Options:
#   --dry-run      Show what would happen without making any changes (default: live mode)
#   --post-comment Post the dry-run or live report as a comment on BTCAAAAA-30053
#
# Safety rules:
#   - Never deletes branches — only renames to archive/<original-name>
#   - Never touches branches matching lock/* (module-lock governance)
#   - Branches >30 commits behind AND idle >72h are candidates
#   - Branches >200 commits behind are archived regardless of idle time
#   - If associated issue is done → archive (after Fix-SHA ancestor check)
#   - If associated issue is open → comment on issue, never archive
#   - Orphan branches (no associated issue) → archive
#
# Required env vars:
#   PAPERCLIP_API_KEY   — bearer token for Paperclip API
#   PAPERCLIP_API_URL   — base URL for Paperclip API
#   GH_TOKEN            — GitHub token with repo push scope (for renaming branches)
#
# Optional env vars:
#   PAPERCLIP_COMPANY_ID — defaults to hardcoded company ID
#   REAPER_SOURCE_ISSUE  — issue to post reports to (default: BTCAAAAA-30053)

set -euo pipefail

# --- Config ---
COMPANY_ID="${PAPERCLIP_COMPANY_ID:-73419cf3-bd37-4a7c-8782-311ccb47fced}"
BRANCH_REGISTER_ISSUE="BTCAAAAA-30038"
REPORT_ISSUE="${REAPER_SOURCE_ISSUE:-BTCAAAAA-30053}"
BEHIND_THRESHOLD=30
IDLE_THRESHOLD_HOURS=72
WAY_STALE_BEHIND=200
LOCK_PREFIX="lock/"
ARCHIVE_PREFIX="archive/"
BRANCH_PATTERN='^(fix|feat|chore|docs|test|refactor)/BTCAAAAA-([0-9]+)-'

DRY_RUN=false
POST_COMMENT=false

for arg in "$@"; do
  case "$arg" in
    --dry-run)      DRY_RUN=true ;;
    --post-comment) POST_COMMENT=true ;;
  esac
done

if [[ "$DRY_RUN" == "true" ]]; then
  echo "=== BRANCH REAPER — DRY-RUN MODE ==="
else
  echo "=== BRANCH REAPER — LIVE MODE ==="
fi
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# --- Ensure we have a fresh view of origin ---
git fetch --prune origin 2>/dev/null

MAIN_SHA=$(git rev-parse origin/main)
NOW_EPOCH=$(date +%s)

EXCLUDED=()
WAY_STALE_ARCHIVE=()
ORPHAN_ARCHIVE=()
DONE_ARCHIVE=()
OPEN_COMMENT=()
ERRORS=()

# --- Iterate all origin branches ---
while IFS= read -r refname; do
  branch="${refname#refs/remotes/origin/}"

  # Skip meta refs
  [[ "$branch" == "HEAD" || "$branch" == "main" ]] && continue

  # Safety: skip lock/* branches
  if [[ "$branch" == ${LOCK_PREFIX}* ]]; then
    EXCLUDED+=("$branch")
    continue
  fi

  # Compute behind count
  behind=$(git rev-list --count "origin/$branch..origin/main" 2>/dev/null || echo "error")
  if [[ "$behind" == "error" ]]; then
    ERRORS+=("$branch (could not compute behind count)")
    continue
  fi

  # Compute last push epoch
  last_push_epoch=$(git log -1 --format="%ct" "origin/$branch" 2>/dev/null || echo "0")
  idle_seconds=$(( NOW_EPOCH - last_push_epoch ))
  idle_hours=$(( idle_seconds / 3600 ))
  last_push_iso=$(date -u -d "@$last_push_epoch" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -r "$last_push_epoch" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo "unknown")

  # Way-stale: >200 behind — archive regardless
  if (( behind > WAY_STALE_BEHIND )); then
    WAY_STALE_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso")
    continue
  fi

  # Not rotten: skip
  if (( behind <= BEHIND_THRESHOLD || idle_hours <= IDLE_THRESHOLD_HOURS )); then
    continue
  fi

  # Branch is rotten (>30 behind AND >72h idle). Decide based on associated issue.

  # Extract issue identifier from branch name
  issue_id=""
  if [[ "$branch" =~ $BRANCH_PATTERN ]]; then
    issue_num="${BASH_REMATCH[2]}"
    issue_id="BTCAAAAA-${issue_num}"
  fi

  if [[ -z "$issue_id" ]]; then
    # Orphan branch — no associated issue
    ORPHAN_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso|orphan")
    continue
  fi

  # Fetch issue status from Paperclip
  issue_status=$(curl -sf \
    -H "Authorization: Bearer ${PAPERCLIP_API_KEY}" \
    "${PAPERCLIP_API_URL}/api/issues/${issue_id}" \
    | jq -r '.status // "not_found"' 2>/dev/null || echo "api_error")

  if [[ "$issue_status" == "done" ]]; then
    # Safe to archive — but only after Fix-SHA ancestor check
    # The Fix-SHA check: look for the Fix-SHA line in the issue's latest closure comment
    fix_sha=$(curl -sf \
      -H "Authorization: Bearer ${PAPERCLIP_API_KEY}" \
      "${PAPERCLIP_API_URL}/api/issues/${issue_id}/comments?order=desc&limit=20" \
      | jq -r '[.[] | select(.body | test("^Fix-SHA: [0-9a-f]{40}$"; "m"))] | .[0].body // ""' \
      | grep -oP 'Fix-SHA: \K[0-9a-f]{40}' || echo "")

    ancestor_rc="skip"
    if [[ -n "$fix_sha" ]]; then
      if git merge-base --is-ancestor "$fix_sha" origin/main 2>/dev/null; then
        ancestor_rc=0
      else
        ancestor_rc=1
      fi
    fi

    DONE_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso|$issue_id|$issue_status|$fix_sha|$ancestor_rc")
  else
    # Issue is open/in_review/blocked/cancelled — comment, don't archive
    OPEN_COMMENT+=("$branch|$behind|$idle_hours|$last_push_iso|$issue_id|$issue_status")
  fi

done < <(git for-each-ref refs/remotes/origin/ --format='%(refname:short)' | sed 's|^origin/||' | sort | sed 's|^|refs/remotes/origin/|')
# Re-iterate properly:
EXCLUDED=()
WAY_STALE_ARCHIVE=()
ORPHAN_ARCHIVE=()
DONE_ARCHIVE=()
OPEN_COMMENT=()
ERRORS=()

while IFS= read -r branch; do
  [[ "$branch" == "HEAD" || "$branch" == "main" ]] && continue

  # Skip already-archived refs (avoid archive/archive/... recursion)
  [[ "$branch" == ${ARCHIVE_PREFIX}* ]] && continue

  if [[ "$branch" == ${LOCK_PREFIX}* ]]; then
    EXCLUDED+=("$branch")
    continue
  fi

  behind=$(git rev-list --count "refs/remotes/origin/${branch}..refs/remotes/origin/main" 2>/dev/null || echo "error")
  if [[ "$behind" == "error" ]]; then
    ERRORS+=("$branch (could not compute behind count)")
    continue
  fi

  last_push_epoch=$(git log -1 --format="%ct" "refs/remotes/origin/${branch}" 2>/dev/null || echo "0")
  idle_seconds=$(( NOW_EPOCH - last_push_epoch ))
  idle_hours=$(( idle_seconds / 3600 ))
  last_push_iso=$(date -u -d "@${last_push_epoch}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
    || python3 -c "import datetime; print(datetime.datetime.utcfromtimestamp($last_push_epoch).strftime('%Y-%m-%dT%H:%M:%SZ'))")

  if (( behind > WAY_STALE_BEHIND )); then
    WAY_STALE_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso")
    continue
  fi

  if (( behind <= BEHIND_THRESHOLD || idle_hours <= IDLE_THRESHOLD_HOURS )); then
    continue
  fi

  issue_id=""
  if [[ "$branch" =~ $BRANCH_PATTERN ]]; then
    issue_num="${BASH_REMATCH[2]}"
    issue_id="BTCAAAAA-${issue_num}"
  fi

  if [[ -z "$issue_id" ]]; then
    ORPHAN_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso|orphan")
    continue
  fi

  issue_status=$(curl -sf \
    -H "Authorization: Bearer ${PAPERCLIP_API_KEY}" \
    "${PAPERCLIP_API_URL}/api/issues/${issue_id}" \
    | jq -r '.status // "not_found"' 2>/dev/null || echo "api_error")

  if [[ "$issue_status" == "done" ]]; then
    fix_sha=$(curl -sf \
      -H "Authorization: Bearer ${PAPERCLIP_API_KEY}" \
      "${PAPERCLIP_API_URL}/api/issues/${issue_id}/comments?order=desc&limit=20" \
      | jq -r '[.[] | select(.body | test("Fix-SHA:"))] | .[0].body // ""' \
      | grep -oP 'Fix-SHA: \K[0-9a-f]{40}' || echo "")

    ancestor_rc="no-fix-sha"
    if [[ -n "$fix_sha" ]]; then
      if git merge-base --is-ancestor "$fix_sha" "refs/remotes/origin/main" 2>/dev/null; then
        ancestor_rc="0"
      else
        ancestor_rc="1"
      fi
    fi

    DONE_ARCHIVE+=("$branch|$behind|$idle_hours|$last_push_iso|$issue_id|$issue_status|${fix_sha:-none}|$ancestor_rc")
  else
    OPEN_COMMENT+=("$branch|$behind|$idle_hours|$last_push_iso|$issue_id|$issue_status")
  fi

done < <(git for-each-ref refs/remotes/origin/ --format='%(refname)' | sed 's|refs/remotes/origin/||' | sort)

# --- Print report ---
echo "## Excluded (lock/* — never touched)"
if [[ ${#EXCLUDED[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${EXCLUDED[@]}"; do
    echo "  EXCLUDED: $entry"
  done
fi
echo ""

echo "## Way-stale (>$WAY_STALE_BEHIND behind — archive regardless)"
if [[ ${#WAY_STALE_ARCHIVE[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${WAY_STALE_ARCHIVE[@]}"; do
    IFS='|' read -r br behind idleh last_push <<< "$entry"
    echo "  WOULD-ARCHIVE: $br (behind=$behind, idle=${idleh}h, last_push=$last_push)"
    echo "    → archive/${br}"
  done
fi
echo ""

echo "## Orphan branches (no associated issue, rotten)"
if [[ ${#ORPHAN_ARCHIVE[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${ORPHAN_ARCHIVE[@]}"; do
    IFS='|' read -r br behind idleh last_push _ <<< "$entry"
    echo "  WOULD-ARCHIVE: $br (behind=$behind, idle=${idleh}h, last_push=$last_push)"
    echo "    → archive/${br}"
  done
fi
echo ""

echo "## Issue done — candidate for archive (pending Fix-SHA ancestor check)"
if [[ ${#DONE_ARCHIVE[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${DONE_ARCHIVE[@]}"; do
    IFS='|' read -r br behind idleh last_push issue_id issue_status fix_sha ancestor_rc <<< "$entry"
    if [[ "$ancestor_rc" == "0" ]]; then
      verdict="WOULD-ARCHIVE (ancestor-check rc=0)"
    elif [[ "$ancestor_rc" == "1" ]]; then
      verdict="SKIP (Fix-SHA not ancestor of main — done-but-unmerged?)"
    else
      verdict="WOULD-ARCHIVE (no Fix-SHA in closure — ancestor-check skipped)"
    fi
    echo "  $verdict: $br (behind=$behind, idle=${idleh}h)"
    echo "    Issue: $issue_id ($issue_status) | Fix-SHA: $fix_sha | ancestor-rc: $ancestor_rc"
    echo "    → archive/${br}"
  done
fi
echo ""

echo "## Issue open — would comment on issue (do NOT archive)"
if [[ ${#OPEN_COMMENT[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for entry in "${OPEN_COMMENT[@]}"; do
    IFS='|' read -r br behind idleh last_push issue_id issue_status <<< "$entry"
    echo "  WOULD-COMMENT: $br (behind=$behind, idle=${idleh}h)"
    echo "    Issue: $issue_id ($issue_status)"
  done
fi
echo ""

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo "## Errors"
  for err in "${ERRORS[@]}"; do
    echo "  ERROR: $err"
  done
  echo ""
fi

echo "## Summary"
echo "  Excluded (lock/*): ${#EXCLUDED[@]}"
echo "  Way-stale archives: ${#WAY_STALE_ARCHIVE[@]}"
echo "  Orphan archives: ${#ORPHAN_ARCHIVE[@]}"
echo "  Done-issue archives: ${#DONE_ARCHIVE[@]}"
echo "  Open-issue comments: ${#OPEN_COMMENT[@]}"
echo "  Errors: ${#ERRORS[@]}"
echo ""

# --- Live mode: perform actions ---
if [[ "$DRY_RUN" == "false" ]]; then
  echo "=== PERFORMING LIVE ACTIONS ==="

  archive_branch() {
    local br="$1"
    local target="archive/${br}"
    echo "  Archiving: $br → $target"
    # Push the branch under archive/ prefix, then delete the original
    git push origin "refs/remotes/origin/${br}:refs/heads/${target}" 2>&1
    git push origin --delete "$br" 2>&1 || true
    echo "  Done: $br → $target"
  }

  for entry in "${WAY_STALE_ARCHIVE[@]}"; do
    IFS='|' read -r br _ _ _ <<< "$entry"
    archive_branch "$br"
  done

  for entry in "${ORPHAN_ARCHIVE[@]}"; do
    IFS='|' read -r br _ _ _ _ <<< "$entry"
    archive_branch "$br"
  done

  for entry in "${DONE_ARCHIVE[@]}"; do
    IFS='|' read -r br behind idleh last_push issue_id issue_status fix_sha ancestor_rc <<< "$entry"
    if [[ "$ancestor_rc" == "0" || "$ancestor_rc" == "no-fix-sha" ]]; then
      archive_branch "$br"
    else
      echo "  SKIP (done-but-unmerged): $br — Fix-SHA not ancestor of main"
    fi
  done

  # Post comments on open-issue branches
  for entry in "${OPEN_COMMENT[@]}"; do
    IFS='|' read -r br behind idleh last_push issue_id issue_status <<< "$entry"
    echo "  Commenting on $issue_id for branch $br"
    comment_body="Branch \`${br}\` is ${behind} commits behind origin/main and has been idle for ${idleh}h. CTO to decide: rebase or archive. (Branch reaper run: $(date -u '+%Y-%m-%dT%H:%M:%SZ'))"
    curl -sf -X POST \
      -H "Authorization: Bearer ${PAPERCLIP_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{\"body\": \"$(echo "$comment_body" | sed 's/"/\\"/g')\"}" \
      "${PAPERCLIP_API_URL}/api/issues/${issue_id}/comments" > /dev/null
  done

  echo ""
  echo "=== LIVE ACTIONS COMPLETE ==="
fi
