#!/usr/bin/env bash
# BTCAAAAA-7258 — One-shot branch protection enforcer
#
# Prerequisites:
#   gh auth status  # Must show a token with admin:repo scope for Stack-Alerts/BTC-Trade-Engine-PaperClip
#
# Usage:
#   ./scripts/apply-branch-protection.sh

set -euo pipefail

REPO="Stack-Alerts/BTC-Trade-Engine-PaperClip"

echo "=== BTCAAAAA-7258: Apply Branch Protection to main ==="
echo "Target: $REPO"
echo ""

# Verify API access
echo "[1/5] Verifying API access..."
if ! gh api "repos/$REPO" --silent 2>/dev/null; then
  echo "ERROR: Cannot access repo via API. Token lacks permissions."
  echo "Fix: Create a PAT with 'administration: write' + 'contents: read'"
  echo "granted to $REPO, or use a classic PAT with 'repo' scope."
  exit 1
fi
echo "  OK"

# Check current state
echo "[2/5] Checking current protection state..."
CURRENT=$(gh api "repos/$REPO/branches/main/protection" \
  --jq '.required_pull_request_reviews.required_approving_review_count' \
  2>/dev/null || echo "not_protected")
echo "  Current: $CURRENT"

if [ "$CURRENT" != "not_protected" ] && [ "$CURRENT" -ge 1 ] 2>/dev/null; then
  echo "  Already protected (approvals: $CURRENT). Nothing to do."
  exit 0
fi

# Step 1: Apply basic protection (no status checks)
echo "[3/5] Applying basic protection..."
gh api --method PUT "repos/$REPO/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON
echo "  Basic protection applied."

# Step 2: Add status checks
echo "[4/5] Adding required status checks..."
gh api --method PUT "repos/$REPO/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "Lint / Ruff lint (no-print + datetime)"},
      {"context": "Lint / Secrets audit (DIAG-2)"},
      {"context": "Test and Coverage / pytest + coverage gate"},
      {"context": "Test and Coverage / Real-data regression (BTCAAAAA-745)"},
      {"context": "Test and Coverage / Canary trade-execution (BTCAAAAA-1476)"},
      {"context": "lock-gate / Module lock gate"},
      {"context": "Freeze-Lift Evidence / Freeze-lift evidence suite"}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON
echo "  Status checks applied."

# Step 3: Verify
echo "[5/5] Verifying protection..."
gh api "repos/$REPO/branches/main/protection" --jq '
{
  reviews: .required_pull_request_reviews.required_approving_review_count,
  dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
  strict_checks: .required_status_checks.strict,
  check_count: (.required_status_checks.checks | length),
  enforce_admins: .enforce_admins.enabled,
  no_force_push: (.allow_force_pushes == false),
  no_delete: (.allow_deletions == false),
  conversation_resolution: .required_conversation_resolution.enabled
}'
echo ""
echo "=== Branch protection applied and verified ==="
