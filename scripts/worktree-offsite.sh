#!/bin/bash
# worktree-offsite.sh — Upload this worktree to gdrive as a backup
#
# Bundles the source tree (excluding heavy/build artifacts) and uploads
# to gdrive:Paperclip-Backups/<companyId>/<YYYY>/<MM>/<DD>/<HHMM>/.
# Designed to be invoked by the paperclip-backup plugin alongside the
# main backup-to-drive.sh. Subject to the same gdriveTierDaily/Hourly
# retention as the main offsite backup.
#
# Configuration (env):
#   WORKTREE_BACKUP_DIR       (default: dirname of this script)
#   PAPERCLIP_RCLONE_CONFIG  (default: ~/.config/rclone/rclone.conf)
#   RCLONE_REMOTE             (default: gdrive)
#   RCLONE_CONFIG_PASS        (default: read from rclone-pass)
#
# Exit codes:
#   0   success
#   1   rclone missing / not configured
#   2   backup creation failed
#   3   upload failed
#   130 interrupted
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
WORKTREE_BACKUP_DIR="${WORKTREE_BACKUP_DIR:-$SCRIPT_DIR/..}"
RCLONE_CONFIG="${PAPERCLIP_RCLONE_CONFIG:-${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"

echo "--- worktree-offsite.sh: source = $WORKTREE_BACKUP_DIR"

# --- Read rclone encryption password (same convention as recovery.sh) ---
if [[ -z "${RCLONE_CONFIG_PASS:-}" && -f "$HOME/.config/rclone/rclone-pass" ]]; then
  export RCLONE_CONFIG_PASS="$(cat "$HOME/.config/rclone/rclone-pass" 2>/dev/null || true)"
fi

# --- Pick a target companyId (use PAPERCLIP_COMPANY_ID or default) ---
COMPANY_ID="${PAPERCLIP_COMPANY_ID:-73419cf3-bd37-4a7c-8782-311ccb47fced}"
TARGET_BASE="Paperclip-Backups/${COMPANY_ID}"

# --- Destination directory: YYYY/MM/DD/HHMM (same shape as backup-to-drive) ---
TS_UTC=$(date -u +%Y/%m/%d/%H%M)
DEST="${RCLONE_REMOTE}:${TARGET_BASE}/${TS_UTC}"

# --- Build the tarball (exclude heavy / build artifacts so the upload
# stays small and the prune retains only meaningful snapshots) ---
TMPDIR=$(mktemp -d /tmp/worktree-offsite.XXXXXXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

# Build a deterministic archive name so re-running the same trigger
# doesn't create a new dir if the upload is retried inside the script.
# (The dest dir already includes the timestamp, so a retry just rewrites
# the same files.)
ARCHIVE_BASE="worktree-snapshot-$(date -u +%Y%m%dT%H%M%SZ)"

# rsync into a staging dir so we can tar it without the top-level path
# confusion. Exclude:
#   .git             — version control state
#   node_modules     — restoreable from package-lock + registry
#   packages/*/node_modules — same
#   **/dist          — buildable from source
#   data/backups     — huge DB dumps (separate offsite backup stream)
#   .next / .turbo   — build caches
#   .claude / .playwright-mcp  — local tooling
STAGE="$TMPDIR/stage"
mkdir -p "$STAGE"
# Sync the worktree contents (not the parent dir) so the archive's
# top-level is the worktree's files, e.g. ./package.json.
rsync -a \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='packages/*/node_modules/' \
  --exclude='**/dist/' \
  --exclude='.next/' \
  --exclude='.turbo/' \
  --exclude='data/backups/' \
  --exclude='.claude/' \
  --exclude='.playwright-mcp/' \
  --exclude='.cache/' \
  --exclude='.npm/' \
  --exclude='coverage/' \
  "${WORKTREE_BACKUP_DIR%/}/" "$STAGE/"

# Build the manifest
cat > "$STAGE/MANIFEST.json" << JSON
{
  "source": "${WORKTREE_BACKUP_DIR}",
  "companyId": "${COMPANY_ID}",
  "ts_utc": "${TS_UTC//\//-}",
  "type": "worktree-snapshot",
  "size_bytes": $(du -sb "$STAGE" | awk '{print $1}')
}
JSON

# Create the tarball
ARCHIVE_PATH="$TMPDIR/${ARCHIVE_BASE}.tar.gz"
tar -czf "$ARCHIVE_PATH" -C "$STAGE" .

echo "  archive: $(du -h "$ARCHIVE_PATH" | cut -f1)"

# --- Upload to gdrive ---
echo "--- uploading to $DEST/"
if ! command -v rclone >/dev/null 2>&1; then
  echo "ERROR: rclone not installed"
  exit 1
fi

if ! rclone copyto "$ARCHIVE_PATH" "${DEST}/${ARCHIVE_BASE}.tar.gz" --progress 2>&1 | tail -5; then
  echo "ERROR: rclone copyto failed"
  exit 3
fi

if ! rclone copyto "$STAGE/MANIFEST.json" "${DEST}/MANIFEST.json" --progress 2>&1 | tail -5; then
  echo "WARN: manifest upload failed (non-fatal)"
fi

echo "--- worktree-offsite.sh: ok"
