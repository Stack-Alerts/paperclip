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

# Resolve the rclone encryption password (if config is encrypted). The
# helper file _rclone_pass.sh reads ~/.config/rclone/rclone-pass and exports
# RCLONE_CONFIG_PASS so rclone can decrypt the config non-interactively.
# Skips silently when the password file doesn't exist (plaintext config).
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if [[ -f "${SCRIPT_DIR}/_rclone_pass.sh" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/_rclone_pass.sh"
fi

TIER=""
KEEP=""
SNAPSHOT_ID=""
SNAPSHOTS_DIR=""
TIER_ROOT=""
RCLONE_CONFIG=""
DRY_RUN=false

# Track tempdirs we create so we can clean them up on exit regardless of
# which path creates them (hourly-delta staging, downloaded parent base, ...).
CLEANUP_DIRS=()
cleanup() {
    local d
    for d in "${CLEANUP_DIRS[@]:-}"; do
        [[ -n "$d" && -d "$d" ]] && /usr/bin/rm -rf "$d" 2>/dev/null || true
    done
}
trap cleanup EXIT

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

# Default upload source is the local snapshot dir. Hourly tier swaps this
# for a staged delta against the parent daily snapshot below.
UPLOAD_SOURCE="$LOCAL_PATH"

# --- Hourly tier: stage a delta against the parent daily snapshot ---
#
# Goal (BTCAAAAA-38952): tiered-hourly-upload uploads ONLY files that
# changed since the most recent successful daily snapshot — not the full
# snapshot. We achieve that by:
#   1. locating the parent daily (newest local `*-0000` dir, falling back
#      to gdrive:$TIER_ROOT/daily/ if not present locally)
#   2. running rsync --compare-dest=PARENT_BASE/ to drop unchanged files
#   3. writing a manifest.json sidecar into the staged delta recording
#      parentDailyId + restore instructions
#   4. uploading the staged delta instead of LOCAL_PATH
if [[ "$TIER" == "hourly" ]]; then
    log "hourly tier: locating parent daily snapshot..."

    PARENT_ID=""
    # Prefer a parent daily we already have on local disk (avoids a
    # full re-download from gdrive). Local snapshot naming is
    # YYYY-MM-DD-HHMM, so daily snapshots end in -0000.
    PARENT_ID=$(ls -1 "$SNAPSHOTS_DIR" 2>/dev/null \
        | /usr/bin/grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-0000$' \
        | sort -r \
        | head -1 || true)

    if [[ -z "$PARENT_ID" ]]; then
        log "  no local daily parent; checking gdrive:$TIER_ROOT/daily/ ..."
        PARENT_ID=$(rclone lsf "gdrive:$TIER_ROOT/daily/" \
            --dirs-only --config "$RCLONE_CONFIG" 2>/dev/null \
            | sed 's:/$::' \
            | sort -r \
            | head -1 || true)
    fi

    if [[ -z "$PARENT_ID" ]]; then
        log "ERROR: hourly upload requires a parent daily snapshot; none found locally or at gdrive:$TIER_ROOT/daily/" >&2
        exit 1
    fi
    log "  parent daily: $PARENT_ID"

    # Resolve a local parent base. Use the local snapshot dir when it has
    # the parent; otherwise pull the parent daily from gdrive into a
    # tempdir and register it for trap-based cleanup.
    PARENT_BASE=""
    if [[ -d "$SNAPSHOTS_DIR/$PARENT_ID" ]]; then
        PARENT_BASE="$SNAPSHOTS_DIR/$PARENT_ID"
        log "  parent base: local $PARENT_BASE"
    else
        PARENT_BASE=$(mktemp -d -t paperclip-parent-XXXXXX)
        CLEANUP_DIRS+=("$PARENT_BASE")
        log "  downloading parent from gdrive to $PARENT_BASE ..."
        if ! rclone copy "gdrive:$TIER_ROOT/daily/$PARENT_ID/" "$PARENT_BASE/" \
                --config "$RCLONE_CONFIG" -q 2>&1 | tail -5 >&2; then
            log "ERROR: failed to download parent daily $PARENT_ID" >&2
            exit 1
        fi
    fi

    # Stage the delta. --compare-dest (NOT --link-dest) skips files whose
    # content matches the parent — hardlinks would not survive the
    # rclone upload anyway, and the operator wants the smallest gdrive
    # payload possible. --checksum forces content-based comparison; the
    # default quick-check (size+mtime) can miss changes that happen to
    # keep the same byte count, which would corrupt the recovery chain.
    STAGE_DIR=$(mktemp -d -t paperclip-delta-XXXXXX)
    CLEANUP_DIRS+=("$STAGE_DIR")
    log "  staging delta at $STAGE_DIR (compare-dest=$PARENT_BASE, checksum mode) ..."
    if ! rsync -a --checksum --compare-dest="$PARENT_BASE/" "$LOCAL_PATH/" "$STAGE_DIR/" 2>&1 \
            | tail -10 >&2; then
        log "ERROR: rsync --compare-dest delta staging failed" >&2
        exit 1
    fi

    # Measure the staged delta for the manifest sidecar.
    DELTA_BYTES=$(du --block-size=1 -s "$STAGE_DIR" 2>/dev/null | awk '{print $1}' || echo "0")
    DELTA_FILE_COUNT=$(/usr/bin/find "$STAGE_DIR" -type f 2>/dev/null | wc -l)
    PARENT_BASELINE_BYTES=$(du --block-size=1 -s "$PARENT_BASE" 2>/dev/null | awk '{print $1}' || echo "0")
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    log "  delta: $DELTA_FILE_COUNT file(s), ${DELTA_BYTES} bytes (parent baseline: ${PARENT_BASELINE_BYTES} bytes)"

    # Write the delta manifest sidecar at the stage root so it lands in
    # the same upload. Captures everything the operator needs to
    # reconstruct this tier from gdrive alone.
    cat > "$STAGE_DIR/manifest.json" <<MANIFEST
{
  "tier": "hourly",
  "snapshotId": "$SNAPSHOT_ID",
  "parentDailyId": "$PARENT_ID",
  "deltaBytes": $DELTA_BYTES,
  "deltaFileCount": $DELTA_FILE_COUNT,
  "parentBaselineBytes": $PARENT_BASELINE_BYTES,
  "timestamp": "$TIMESTAMP",
  "restoreInstructions": [
    "1. Restore parent daily first: gdrive:$TIER_ROOT/daily/$PARENT_ID/",
    "2. Download this hourly delta: gdrive:$REMOTE_PATH/",
    "3. Overlay delta onto parent: rsync -a REMOTE_PATH/ PARENT_RESTORE/",
    "4. Run paperclipai instance restore <combined-id> as usual"
  ]
}
MANIFEST
    log "  wrote delta manifest: $STAGE_DIR/manifest.json"

    UPLOAD_SOURCE="$STAGE_DIR"
    log "  upload source switched: $LOCAL_PATH → $UPLOAD_SOURCE (delta)"
fi

# Idempotent upload: skip if destination already exists.
EXISTING=$(rclone lsjson "gdrive:$REMOTE_PATH/" --config "$RCLONE_CONFIG" -q 2>/dev/null | grep -c '"Name"' || true)
if [[ "$EXISTING" -gt 0 ]]; then
    log "already on gdrive; skipping rclone copy (still enforcing retention)"
else
    if [[ "$DRY_RUN" == true ]]; then
        log "DRY-RUN: would rclone copy $UPLOAD_SOURCE → gdrive:$REMOTE_PATH/"
    else
        log "uploading..."
        if ! rclone copy "$UPLOAD_SOURCE/" "gdrive:$REMOTE_PATH/" \
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
