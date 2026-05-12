#!/usr/bin/env bash
# ============================================================================
# P0 SECURITY: Purge compromised keys from git history
# Issue: BTCAAAAA-7293
# ============================================================================
# Thin wrapper around the canonical purge_aws_keys.sh. For full documentation,
# audit trail, and safety features use that script directly.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Purge compromised keys from git history ==="
echo ""
echo "This is a convenience wrapper. For full audit/safety features, run:"
echo "  bash ${SCRIPT_DIR}/purge_aws_keys.sh"
echo ""

if [[ -z "${PURGE_SECRET_KEY:-}" ]] && [[ -z "${1:-}" ]]; then
    echo "Usage: PURGE_SECRET_KEY=<the-actual-secret-key> bash $0"
    echo "   or: bash $0 <the-actual-secret-key>"
    echo ""
    echo "The secret key is NOT stored in this repository."
    echo "Obtain it from the security incident report (BTCAAAAA-7280)."
    exit 1
fi

exec bash "${SCRIPT_DIR}/purge_aws_keys.sh" "$@"
