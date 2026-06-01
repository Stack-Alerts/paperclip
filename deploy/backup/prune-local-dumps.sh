#!/bin/bash
#
# prune-local-dumps.sh — keep the newest N local DB dumps (BTCAAAAA-33092)
#
# Companion to backup-to-drive.sh. Runs on its own systemd timer so the local
# DB dumper pile (~$INSTANCE_DIR/data/backups/paperclip-*.sql.gz) never grows
# unbounded. Idempotent; safe to run between dumper invocations.
#
# Inputs (env):
#   PAPERCLIP_HOME       — defaults to $HOME/.paperclip
#   BACKUP_RETENTION_KEEP — defaults to 10
#
set -euo pipefail

PAPERCLIP_HOME="${PAPERCLIP_HOME:-$HOME/.paperclip}"
INSTANCE_DIR="${PAPERCLIP_HOME}/instances/default"
BACKUPS_DIR="${INSTANCE_DIR}/data/backups"
KEEP="${BACKUP_RETENTION_KEEP:-10}"

NOW_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "=========================================="
echo "  Paperclip local DB-dump pruner"
echo "=========================================="
echo "  Timestamp: ${NOW_UTC}"
echo "  Dir:       ${BACKUPS_DIR}"
echo "  Keep:      ${KEEP}"

if [ ! -d "$BACKUPS_DIR" ]; then
    echo "  (backup dir does not exist; nothing to prune)"
    exit 0
fi

# Collect candidate files, newest-first.
mapfile -t ALL_DUMPS < <(
    find "$BACKUPS_DIR" -maxdepth 1 -type f -name 'paperclip-*.sql.gz' -printf '%T@ %p\n' \
        | LC_ALL=C sort -r -n -k1,1 \
        | awk '{ $1=""; sub(/^ /,""); print }'
)

TOTAL=${#ALL_DUMPS[@]}
echo "  Found:     ${TOTAL}"

if [ "$TOTAL" -le "$KEEP" ]; then
    echo "  (nothing to prune)"
    exit 0
fi

BYTES_BEFORE=$(du -sb "$BACKUPS_DIR" 2>/dev/null | awk '{print $1}')
COUNT_PURGED=0
BYTES_PURGED=0

for ((i = KEEP; i < TOTAL; i++)); do
    f="${ALL_DUMPS[$i]}"
    if [ -z "$f" ] || [ ! -f "$f" ]; then
        continue
    fi
    sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
    rm -f -- "$f"
    BYTES_PURGED=$((BYTES_PURGED + sz))
    COUNT_PURGED=$((COUNT_PURGED + 1))
    echo "    purged: $(basename "$f") ($(numfmt --to=iec --suffix=B "$sz" 2>/dev/null || echo "${sz}B"))"
done

BYTES_AFTER=$(du -sb "$BACKUPS_DIR" 2>/dev/null | awk '{print $1}')

echo ""
echo "--- Summary ---"
echo "  Purged:   ${COUNT_PURGED} files / $(numfmt --to=iec --suffix=B "$BYTES_PURGED" 2>/dev/null || echo "${BYTES_PURGED}B")"
echo "  Before:   $(numfmt --to=iec --suffix=B "$BYTES_BEFORE" 2>/dev/null || echo "${BYTES_BEFORE}B")"
echo "  After:    $(numfmt --to=iec --suffix=B "$BYTES_AFTER" 2>/dev/null || echo "${BYTES_AFTER}B")"

# Write a small state file so the deadman switch / monitoring can see when
# the pruner last ran successfully.
BACKUP_STATE_DIR="${INSTANCE_DIR}/backup-state"
mkdir -p "$BACKUP_STATE_DIR"
NOW_UTC="$NOW_UTC" \
COUNT_PURGED="$COUNT_PURGED" \
BYTES_PURGED="$BYTES_PURGED" \
BYTES_BEFORE="$BYTES_BEFORE" \
BYTES_AFTER="$BYTES_AFTER" \
KEEP="$KEEP" \
TOTAL="$TOTAL" \
BACKUP_STATE_DIR="$BACKUP_STATE_DIR" \
python3 <<'PYEOF'
import json, os
state = {
    "timestamp": os.environ["NOW_UTC"],
    "kept": int(os.environ["KEEP"]),
    "totalBefore": int(os.environ["TOTAL"]),
    "purgedCount": int(os.environ["COUNT_PURGED"]),
    "purgedBytes": int(os.environ["BYTES_PURGED"]),
    "bytesBefore": int(os.environ["BYTES_BEFORE"] or 0),
    "bytesAfter": int(os.environ["BYTES_AFTER"] or 0),
}
out = os.path.join(os.environ["BACKUP_STATE_DIR"], "last-prune.json")
json.dump(state, open(out, "w"), indent=2)
print(f"  State written: {out}")
PYEOF
