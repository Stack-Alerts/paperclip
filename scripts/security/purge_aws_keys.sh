#!/usr/bin/env bash
# ============================================================================
# P0 SECURITY: Purge compromised AWS keys from entire git history
# Issue: BTCAAAAA-7293
# ============================================================================
# PREREQUISITES:
#   1. git-filter-repo installed: pip install git-filter-repo
#   2. Run on a FRESH CLONE — this script creates its own working directory
#   3. Closed PRs / stale branches on the remote will NOT be rewritten
#   4. All team members must discard local clones and re-clone after this runs
#   5. AWS credentials MUST be rotated BEFORE pushing the cleaned history
#      (purging git history does NOT revoke the keys from AWS IAM)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPLACEMENTS_FILE="${SCRIPT_DIR}/purge_aws_keys_replacements.txt"
WORK_DIR="/tmp/btc-engine-repo-purge-$$"
BACKUP_BUNDLE="/tmp/btc-engine-before-purge-$(date +%Y%m%d-%H%M%S).bundle"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_prerequisites() {
    if ! command -v git-filter-repo &>/dev/null; then
        log_error "git-filter-repo is not installed."
        log_error "Install it: pip install git-filter-repo"
        exit 1
    fi

    if [[ ! -f "${REPLACEMENTS_FILE}" ]]; then
        log_error "Replacements file not found: ${REPLACEMENTS_FILE}"
        exit 1
    fi

    if [[ ! -d .git ]]; then
        log_error "This script must be run from the root of the git repository."
        exit 1
    fi
}

scan_exposure() {
    log_info "Scanning git history for exposed keys..."
    echo ""

    echo "--- Secret Access Key (commits where it appears in diffs) ---"
    git log --all -S "REDACTED_AWS_SECRET_ACCESS_KEY" \
        --format="  %h  %ad  %s" --date=short 2>/dev/null | head -20
    echo ""

    echo "--- Access Key ID (commits where it appears in diffs) ---"
    git log --all -S "AKIA************DBUD" \
        --format="  %h  %ad  %s" --date=short 2>/dev/null | head -20
    echo ""

    echo "--- Key ID in commit messages ---"
    git log --all --format="%h %s" 2>/dev/null | grep -F "AKIA************DBUD" || \
        log_info "(no commit messages contain the key ID)"
    echo ""
}

execute_purge() {
    log_info "Creating backup bundle: ${BACKUP_BUNDLE}"
    git bundle create "${BACKUP_BUNDLE}" --all || true

    log_info "Cloning bare mirror to: ${WORK_DIR}"
    rm -rf "${WORK_DIR}"
    git clone --mirror "$(git rev-parse --git-dir)" "${WORK_DIR}"

    pushd "${WORK_DIR}" > /dev/null

    log_info "Running git filter-repo --replace-text ..."
    git filter-repo --replace-text "${REPLACEMENTS_FILE}" --force

    log_info "Running git filter-repo --replace-message ..."
    git filter-repo --replace-message "${REPLACEMENTS_FILE}" --force || true

    log_info "Verifying purge..."
    if git log --all -S "REDACTED_AWS_SECRET_ACCESS_KEY" 2>/dev/null | grep -q .; then
        log_error "VERIFICATION FAILED: Secret Access Key still in history!"
        popd > /dev/null
        exit 1
    fi

    if git log --all -S "AKIA************DBUD" 2>/dev/null | grep -q .; then
        log_error "VERIFICATION FAILED: Key ID still in history!"
        popd > /dev/null
        exit 1
    fi

    log_info "Purge verified. No exposed keys remain."
    popd > /dev/null
}

main() {
    echo ""
    log_info "=== P0 SECURITY: Purge AWS Keys from Git History ==="
    log_info "Issue: BTCAAAAA-7293"
    log_info "Replacements: ${REPLACEMENTS_FILE}"
    echo ""

    check_prerequisites
    scan_exposure

    log_warn "============================================================"
    log_warn " ABOUT TO REWRITE ENTIRE GIT HISTORY — IRREVERSIBLE"
    log_warn " Press Ctrl+C within 10 seconds to abort..."
    log_warn "============================================================"
    sleep 10

    execute_purge

    echo ""
    log_info "NEXT STEPS (manual):"
    log_info "  1. Rotate the AWS keys in IAM (purging git != revoking)"
    log_info "  2. Push cleaned history: git push --mirror <remote-url>"
    log_info "  3. All team members must re-clone"
    log_info "  4. Delete backup bundle when done: rm ${BACKUP_BUNDLE}"
}

main "$@"
