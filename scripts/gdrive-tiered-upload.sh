#!/bin/bash
# gdrive-tiered-upload.sh — tiered snapshot upload to GDrive with retention.
#
# Pushes a recovery snapshot to GDrive under a tier subdir and enforces
# per-tier retention (keep only the newest N). Idempotent: if the snapshot
# is already on gdrive in that tier, the copy is skipped.
#
# Usage:
#   gdrive-tiered-upload.sh --tier daily|hourly --keep N [--snapshot-id ID]
#                            [--snapshots-dir DIR] [--tier-root PREFIX]
#                            [--rclone-config PATH] [--dry-run]
#
# Tiers:
#   daily   - Once-per-day uploads. Recommended max retention: 3 (3 days).
#   hourly  - 6-hourly uploads. Recommended max retention: 2 (~12h of state).
#
# GDrive layout:
#   <tier-root>/<tier>/<snapshot-id>/
#     ├── manifest.json
#     ├── data/
#     ├── db/
#     └── config/
#
# The plugin action `upload-daily-backup` / `upload-hourly-backup` calls
# this script with --keep derived from the plugin's current config
# (gdriveTierDailyKeep, gdriveTierHourlyKeep).

set -euo pipefail

TIER=""
KEEP=""
SNAPSHOT_ID=""
SNAPSHOTS_DIR=""
TIER_ROOT=""
RCLONE_CONFIG=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier)            TIER="$2"; shift 2;;
        --keep)            KEEP="$2"; shift 2;;
        --snapshot-id)     SNAPSHOT_ID="$2"; shift 2;;
        --snapshots-dir)   SNAPSHOTS_DIR="$2"; shift 2;;
        --tier-root)       TIER_ROOT="$2"; shift 2;;
        --rclone-config)   RCLONE_CONFIG="$2"; shift 2;;
        --dry-run)         DRY_RUN=true; shift;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# //; s/^#//'
            exit 0;;
        *)
            echo "ERROR: unknown argument '$1'" >&2
            exit 1;;
    esac
done

# Resolve TIER
[[ -z "$TIER" ]] && { echo "ERROR: --tier required (daily|hourly)" >&2; exit 1; }
[[ "$TIER" != "daily" && "$TIER" != "hourly" ]] && { echo "ERROR: --tier must be 'daily' or 'hourly'" >&2; exit 1; }

# Resolve KEEP
[[ -z "$KEEP" || ! "$KEEP" =~ ^[0-9]+$ || "$KEEP" -lt 1 ]] \
    && { echo "ERROR: --keep required (integer >= 1)" >&2; exit 1; }

# Resolve snapshots dir
if [[ -z "$SNAPSHOTS_DIR" ]]; then
    if [[ -n "${PAPERCLIP_HOME:-}" ]]; then
        SNAPSHOTS_DIR="${PAPERCLIP_HOME}/paperclip-snapshots"
    elif [[ -n "${HOME:-}" ]]; then
        SNAPSHOTS_DIR="${HOME}/paperclip-snapshots"
    else
        SNAPSHOTS_DIR="/home/sirrus/paperclip-snapshots"
    fi
fi
[[ -d "$SNAPSHOTS_DIR" ]] || { echo "ERROR: snapshots dir not found at $SNAPSHOTS_DIR" >&2; exit 1; }

# Resolve tier root
[[ -z "$TIER_ROOT" ]] && TIER_ROOT="Paperclip-Backups"

# Resolve rclone config
if [[ -z "$RCLONE_CONFIG" ]]; then
    if [[ -n "${RCLONE_CONFIG:-}" ]]; then
        RCLONE_CONFIG="${RCLONE_CONFIG}"
    elif [[ -n "${HOME:-}" ]]; then
        RCLONE_CONFIG="${HOME}/.config/rclone/rclone.conf"
    else
        RCLONE_CONFIG="/home/sirrus/.config/rclone/rclone.conf"
    fi
fi
[[ -f "$RCLONE_CONFIG" ]] || { echo "ERROR: rclone config not found at $RCLONE_CONFIG" >&2; exit 1; }

command -v rclone >/dev/null 2>&1 || { echo "ERROR: rclone not found in PATH" >&2; exit 1; }

# Pick the snapshot
if [[ -z "$SNAPSHOT_ID" ]]; then
    SNAPSHOT_ID=$(ls -1 "$SNAPSHOTS_DIR" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}$' | sort -r | head -1 || true)
fi
[[ -n "$SNAPSHOT_ID" ]] || { echo "ERROR: no snapshot found locally" >&2; exit 1; }

LOCAL_PATH="$SNAPSHOTS_DIR/$SNAPSHOT_ID"
[[ -d "$LOCAL_PATH" ]] || { echo "ERROR: snapshot $SNAPSHOT_ID not found at $LOCAL_PATH" >&2; exit 1; }

REMOTE_PATH="${TIER_ROOT}/${TIER}/${SNAPSHOT_ID}"

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

log "tier=$TIER keep=$KEEP snapshot=$SNAPSHOT_ID"
log "  local:  $LOCAL_PATH"
log "  remote: gdrive:$REMOTE_PATH"

# Idempotent upload: skip if destination already exists.
EXISTING=$(rclone lsjson "gdrive:$REMOTE_PATH/" --config "$RCLONE_CONFIG" -q 2>/dev/null | grep -c '"Name"' || true)
if [[ "$EXISTING" -gt 0 ]]; then
    log "already on gdrive; skipping rclone copy (still enforcing retention)"
else
    if [[ "$DRY_RUN" == true ]]; then
        log "DRY-RUN: would rclone copy $LOCAL_PATH → gdrive:$REMOTE_PATH/"
    else
        log "uploading..."
        if ! rclone copy "$LOCAL_PATH/" "gdrive:$REMOTE_PATH/" \
                --config "$RCLONE_CONFIG" \
                --progress \
                --transfers 4 \
                --checkers 8 \
                --drive-chunk-size 64M \
                --stats 30s 2>&1 | tail -20; then
            log "ERROR: rclone copy failed"
            exit 1
        fi
    fi
fi

# Enforce retention: keep newest $KEEP dirs in this tier, purge the rest.
log "enforcing retention: keep newest $KEEP in gdrive:$TIER_ROOT/$TIER/"
ALL=$(rclone lsf "gdrive:$TIER_ROOT/$TIER/" --dirs-only --config "$RCLONE_CONFIG" 2>/dev/null | sed 's:/$::' | sort -r || true)
COUNT=$(printf '%s\n' "$ALL" | grep -c . || true)
log "  current count: $COUNT"

if [[ $COUNT -gt $KEEP ]]; then
    TO_DELETE=$(printf '%s\n' "$ALL" | tail -n +$((KEEP + 1)))
    DEL_COUNT=$(printf '%s\n' "$TO_DELETE" | grep -c . || true)
    log "  deleting $DEL_COUNT old item(s):"
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        log "    - $d"
        if [[ "$DRY_RUN" == true ]]; then
            log "      DRY-RUN: would rclone purge"
        else
            rclone purge "gdrive:$TIER_ROOT/$TIER/$d" --config "$RCLONE_CONFIG" 2>&1 | tail -1 >&2 || log "      WARN: purge failed for $d"
        fi
    done <<< "$TO_DELETE"
fi

# Persist a small sidecar so an operator can reconstruct what is on gdrive.
# We use the snapshot's local manifest.json and add a "gdriveTiers" array.
if [[ "$DRY_RUN" == false && -f "$LOCAL_PATH/manifest.json" ]]; then
    if command -v jq >/dev/null 2>&1; then
        TMPF=$(mktemp)
        jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
           --arg tier "$TIER" \
           --arg keep "$KEEP" \
           '.gdriveTiers = ((.gdriveTiers // []) + [{"tier": $tier, "keep": ($keep|tonumber), "uploadedAt": $ts}] | unique_by(.tier))' \
           "$LOCAL_PATH/manifest.json" > "$TMPF" 2>/dev/null && mv "$TMPF" "$LOCAL_PATH/manifest.json" || true
    fi
fi

if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN complete"
else
    log "done"
fi
