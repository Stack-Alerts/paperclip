#!/usr/bin/env bash
set -euo pipefail
echo "=== git-filter-repo — Purge compromised AWS key from git history ==="
echo ""
echo "PREREQUISITE: Human board must confirm key rotation on BTCAAAAA-7256 before running."
echo "Running this script while the key is still active creates a dangerous window:"
echo "the rewritten history invalidates the key, but observers may have cached the old commits."
echo ""

REPO_DIR="${1:-$(pwd)}"
BACKUP_REF="backup-before-key-purge-$(date +%Y%m%d-%H%M%S)"

echo "Repository: $REPO_DIR"
echo "Backup ref:  $BACKUP_REF"
echo ""

echo "[1/4] Creating backup tag before rewrite..."
git -C "$REPO_DIR" tag "$BACKUP_REF"
echo "  Backup tag $BACKUP_REF created."

echo "[2/4] Checking git-filter-repo is available..."
if ! command -v git-filter-repo &>/dev/null; then
    echo "  ERROR: git-filter-repo not installed."
    echo "  Install: pip install git-filter-repo"
    echo "  See: https://github.com/newren/git-filter-repo"
    exit 1
fi
echo "  OK: $(which git-filter-repo)"

echo "[3/4] Creating replacement expressions file..."
REPLACE_FILE=$(mktemp)
cat > "$REPLACE_FILE" << 'REPLACEMENTS'
AKIA************DBUD==>REDACTED_AWS_KEY
REDACTED_AWS_SECRET_ACCESS_KEY>REDACTED_AWS_SECRET
REPLACEMENTS

echo "  Replacement patterns:"
cat "$REPLACE_FILE"
echo ""

echo "[4/4] Running git-filter-repo --replace-text..."
echo "  WARNING: This rewrites ALL commits containing these patterns."
echo "  This is a DESTRUCTIVE operation."
echo ""
read -rp "  Type 'YES' to proceed: " confirm
if [ "$confirm" != "YES" ]; then
    echo "  Aborted. Backup tag $BACKUP_REF remains for recovery."
    rm -f "$REPLACE_FILE"
    exit 0
fi

git -C "$REPO_DIR" filter-repo --replace-text "$REPLACE_FILE" --force

rm -f "$REPLACE_FILE"

echo ""
echo "=== Purge complete ==="
echo ""
echo "Post-purge verification:"
echo "  git log --all -S 'AKIA************DBUD'    # should return nothing"
echo "  git log --all -S 'V7HUS+ngdCHLolOz'       # should return nothing"
echo ""
echo "To push rewritten history (FORCE):"
echo "  git push --force --all origin"
echo "  git push --force --tags origin"
echo ""
echo "Backup tag: $BACKUP_REF (delete after verifying clean push)"
