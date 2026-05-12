#!/usr/bin/env bash
# ============================================================================
# P0 SECURITY: Purge compromised AWS keys from entire git history
# Issue: BTCAAAAA-7293
# ============================================================================
# PREREQUISITES:
#   1. git-filter-repo installed: pip install git-filter-repo
#   2. Run on a FRESH CLONE — this script creates its own working directory
#   3. Set PURGE_SECRET_KEY env var to the actual AWS Secret Access Key
#      OR pass it as the first argument to this script
#   4. AWS credentials MUST be rotated in IAM before pushing
#   5. All team members must discard local clones and re-clone after push
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPLACEMENTS_TEMPLATE="${SCRIPT_DIR}/purge_aws_keys_replacements.txt"
WORK_DIR="/tmp/btc-engine-repo-purge-$$"
BACKUP_BUNDLE="/tmp/btc-engine-before-purge-$(date +%Y%m%d-%H%M%S).bundle"
REPLACEMENTS_WORKING="/tmp/btc-engine-replacements-$$.txt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_fatal() { log_error "$*"; exit 1; }

get_secret_key() {
    if [[ -n "${PURGE_SECRET_KEY:-}" ]]; then
        echo "${PURGE_SECRET_KEY}"
    elif [[ -n "${1:-}" ]]; then
        echo "$1"
    else
        log_fatal "Secret key required. Set PURGE_SECRET_KEY env var or pass as argument."
    fi
}

check_prerequisites() {
    command -v git-filter-repo &>/dev/null || \
        log_fatal "git-filter-repo not installed. Run: pip install git-filter-repo"
    [[ -f "${REPLACEMENTS_TEMPLATE}" ]] || \
        log_fatal "Replacements template not found: ${REPLACEMENTS_TEMPLATE}"
    [[ -d .git ]] || \
        log_fatal "Must be run from the root of the git repository."
}

prepare_replacements() {
    local secret="$1"
    sed "s/REDACTED_ACTUAL_SECRET/${secret}/g" "${REPLACEMENTS_TEMPLATE}" > "${REPLACEMENTS_WORKING}"
    chmod 600 "${REPLACEMENTS_WORKING}"
    log_info "Replacements file prepared (permissions: 600)"
}

scan_exposure() {
    local secret="$1"
    log_info "Scanning git history for exposed keys..."
    echo ""
    echo "--- Secret Access Key (commits where it appears in diffs) ---"
    git log --all -S "${secret}" --format="  %h  %ad  %s" --date=short 2>/dev/null | head -20
    echo ""
    echo "--- Key ID (commits where it appears in diffs) ---"
    git log --all -S "AKIA************DBUD" --format="  %h  %ad  %s" --date=short 2>/dev/null | head -20
    echo ""
}

execute_purge() {
    local secret="$1"

    log_info "Creating backup bundle: ${BACKUP_BUNDLE}"
    git bundle create "${BACKUP_BUNDLE}" --all || \
        log_warn "Bundle creation failed (non-fatal)"

    log_info "Cloning bare mirror to: ${WORK_DIR}"
    rm -rf "${WORK_DIR}"
    git clone --mirror "$(git rev-parse --git-dir)" "${WORK_DIR}"

    pushd "${WORK_DIR}" > /dev/null

    log_info "Running git filter-repo --replace-text ..."
    git filter-repo --replace-text "${REPLACEMENTS_WORKING}" --force

    log_info "Running git filter-repo --replace-message ..."
    git filter-repo --replace-message "${REPLACEMENTS_WORKING}" --force || \
        log_warn "--replace-message had non-fatal issues"

    log_info "Verifying purge..."
    if git log --all -S "${secret}" 2>/dev/null | grep -q .; then
        log_error "VERIFICATION FAILED: Secret key still in history!"
        popd > /dev/null; exit 1
    fi
    if git log --all -S "AKIA************DBUD" 2>/dev/null | grep -q .; then
        log_error "VERIFICATION FAILED: Key ID still in history!"
        popd > /dev/null; exit 1
    fi

    log_info "Purge verified. No exposed keys remain."
    popd > /dev/null
}

cleanup() {
    rm -f "${REPLACEMENTS_WORKING}"
}

main() {
    trap cleanup EXIT

    local secret
    secret="$(get_secret_key "${1:-}")"

    echo ""
    log_info "=== P0 SECURITY: Purge AWS Keys from Git History ==="
    log_info "Issue: BTCAAAAA-7293"
    log_info "Template: ${REPLACEMENTS_TEMPLATE}"
    echo ""

    check_prerequisites
    prepare_replacements "${secret}"
    scan_exposure "${secret}"

    log_warn "============================================================"
    log_warn " ABOUT TO REWRITE ENTIRE GIT HISTORY — IRREVERSIBLE"
    log_warn " Press Ctrl+C within 10 seconds to abort..."
    log_warn "============================================================"
    sleep 10

    execute_purge "${secret}"

    echo ""
    log_info "NEXT STEPS (manual):"
    log_info "  1. Rotate the AWS keys in IAM (purging git != revoking)"
    log_info "  2. Push: git push --mirror <remote-url>"
    log_info "  3. All team members must re-clone"
    log_info "  4. Delete backup bundle when confirmed: rm ${BACKUP_BUNDLE}"
}

main "$@"
