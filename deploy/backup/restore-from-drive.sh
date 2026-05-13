#!/bin/bash
set -euo pipefail

#
# restore-from-drive.sh — Restore Paperclip backup from Google Drive
#
# Lists available backups from GDrive and restores selected payload.
# Supports: listing, downloading, extracting, and optional DB restore.
#
# Usage:
#   restore-from-drive.sh list                        # show available backups
#   restore-from-drive.sh latest [dest-dir]           # restore most recent
#   restore-from-drive.sh 2026/05/12/1008 [dest-dir]  # restore specific backup
#

LOCKFILE="/tmp/paperclip-restore.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Another restore instance is running."; exit 1; }

PAPERCLIP_HOME="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
INSTANCE_DIR="${PAPERCLIP_HOME}/instances/default"
INSTANCE_ENV="${INSTANCE_DIR}/.env"

REMOTE_ROOT="gdrive:Paperclip-Backups"
COMPANY_ID="${PAPERCLIP_COMPANY_ID:-}"
if [ -z "$COMPANY_ID" ] && [ -f "$INSTANCE_ENV" ]; then
    COMPANY_ID=$(grep -E '^PAPERCLIP_COMPANY_ID=' "$INSTANCE_ENV" | cut -d= -f2- | tr -d "'\"" || true)
fi
if [ -z "$COMPANY_ID" ]; then
    echo "PAPERCLIP_COMPANY_ID not set. Set env var or add to $INSTANCE_ENV"
    exit 1
fi

REMOTE_BASE="${REMOTE_ROOT}/${COMPANY_ID}"

usage() {
    echo "Usage: $(basename "$0") <command> [args]"
    echo ""
    echo "Commands:"
    echo "  list                          List available backups"
    echo "  latest  [dest-dir]            Restore most recent backup"
    echo "  <path>  [dest-dir]            Restore specific backup (e.g. 2026/05/12/1008)"
    echo ""
    echo "Examples:"
    echo "  $(basename "$0") list"
    echo "  $(basename "$0") latest /tmp/restore"
    echo "  $(basename "$0") 2026/05/12/1008 /tmp/restore"
}

list_backups() {
    echo "Fetching available backups from ${REMOTE_BASE}..."
    echo ""
    if ! rclone lsd "$REMOTE_BASE" 2>/dev/null; then
        echo "No backups found or remote not accessible."
        echo "Ensure the 'gdrive' remote is configured (run rclone-bootstrap.sh)."
        exit 1
    fi

    echo ""
    echo "Backup paths (YYYY/MM/DD/HHMM):"
    rclone tree "$REMOTE_BASE" --depth 4 2>/dev/null || \
    rclone ls "$REMOTE_BASE" --max-depth 4 2>/dev/null | awk '{print $2}' | sort -r | head -20
}

find_latest() {
    rclone ls "$REMOTE_BASE" --max-depth 4 &>/dev/null || return 1
    rclone ls "$REMOTE_BASE" --max-depth 4 2>/dev/null | \
        awk '{print $2}' | grep -E '^[0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9]{4}/$' | \
        sort -r | head -1
}

download_backup() {
    local remote_path="$1"
    local dest_dir="$2"
    local full_remote="${REMOTE_BASE}/${remote_path}"

    echo "Downloading from: ${full_remote}"
    echo "Destination:      ${dest_dir}"
    echo ""

    mkdir -p "$dest_dir"

    rclone copy "$full_remote" "$dest_dir" --progress --verbose

    echo ""
    echo "Downloaded files:"
    ls -lh "$dest_dir"
}

extract_payload() {
    local dest_dir="$1"
    local manifest_file="$dest_dir/MANIFEST.json"

    if [ -f "$manifest_file" ]; then
        echo ""
        echo "=== MANIFEST ==="
        python3 -m json.tool "$manifest_file"
    fi

    local tarball
    tarball=$(find "$dest_dir" -name "paperclip-instance-*.tar.gz" | head -1)
    if [ -n "$tarball" ]; then
        echo ""
        echo "Extracting: $(basename "$tarball")"
        tar xzf "$tarball" -C "$dest_dir"
        echo "Extracted to: ${dest_dir}"
        echo ""
        echo "Contents:"
        ls -la "$dest_dir" | grep -v '\.tar\.gz$'
    fi

    local sql_dump
    sql_dump=$(find "$dest_dir" -name "paperclip-*.sql.gz" -not -path "*/paperclip-instance-*" | head -1)
    if [ -n "$sql_dump" ]; then
        echo ""
        echo "DB dump available: $(basename "$sql_dump") ($(du -h "$sql_dump" | cut -f1))"
        echo "To restore DB: gunzip -c '$sql_dump' | psql -h localhost paperclip"
    fi
}

case "${1:-help}" in
    list)
        list_backups
        ;;
    latest)
        LATEST=$(find_latest) || true
        if [ -z "$LATEST" ]; then
            echo "No backups found."
            exit 1
        fi
        echo "Latest backup: ${LATEST%/}"
        DEST_DIR="${2:-/tmp/paperclip-restore-latest}"
        download_backup "${LATEST%/}" "$DEST_DIR"
        extract_payload "$DEST_DIR"
        echo ""
        echo "Restore complete. Files in: ${DEST_DIR}"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        # Treat as a path like 2026/05/12/1008
        REMOTE_PATH="$1"
        DEST_DIR="${2:-/tmp/paperclip-restore-$(echo "$REMOTE_PATH" | tr '/' '-')}"
        download_backup "$REMOTE_PATH" "$DEST_DIR"
        extract_payload "$DEST_DIR"
        echo ""
        echo "Restore complete. Files in: ${DEST_DIR}"
        ;;
esac
