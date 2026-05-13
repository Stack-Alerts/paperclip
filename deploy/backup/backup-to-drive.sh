#!/bin/bash
set -euo pipefail

#
# backup-to-drive.sh — Paperclip offsite backup to Google Drive
#
# Bundles the latest database dump + instance data (companies, projects,
# skills, storage) and uploads to gdrive:Paperclip-Backups/<companyId>/…
#
# Locked with flock so the 4h cron and manual runs never collide.
#

LOCKFILE="/tmp/paperclip-backup.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Another backup instance is running (lock held). Exiting."; exit 1; }

trap 'rm -rf "$TMPDIR"' EXIT
TMPDIR=$(mktemp -d /tmp/paperclip-backup.XXXXXXXXXX)

PAPERCLIP_HOME="$(cd "$(dirname "$0")/.." && pwd)"
INSTANCE_DIR="${PAPERCLIP_HOME}/instances/default"
BACKUPS_DIR="${INSTANCE_DIR}/data/backups"
CONFIG_FILE="${INSTANCE_DIR}/config.json"
INSTANCE_ENV="${INSTANCE_DIR}/.env"

NOW_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
YEAR=$(date -u +%Y)
MONTH=$(date -u +%m)
DAY=$(date -u +%d)
HOURMIN=$(date -u +%H%M)

# --- Resolve company ID ---------------------------------------------------
COMPANY_ID="${PAPERCLIP_COMPANY_ID:-}"
if [ -z "$COMPANY_ID" ] && [ -f "$INSTANCE_ENV" ]; then
    COMPANY_ID=$(grep -E '^PAPERCLIP_COMPANY_ID=' "$INSTANCE_ENV" | cut -d= -f2- | tr -d "'\"" || true)
fi
if [ -z "$COMPANY_ID" ]; then
    COMPANY_ID="unknown"
fi

# --- Paperclip version ----------------------------------------------------
PAPERCLIP_VERSION="unknown"
if [ -f "${PAPERCLIP_HOME}/package.json" ]; then
    PAPERCLIP_VERSION=$(python3 -c "import json; print(json.load(open('${PAPERCLIP_HOME}/package.json')).get('version','unknown'))" 2>/dev/null || echo "unknown")
fi

echo "=========================================="
echo "  Paperclip Backup to Google Drive"
echo "=========================================="
echo "  Timestamp:  ${NOW_UTC}"
echo "  Company ID: ${COMPANY_ID}"
echo "  Version:    ${PAPERCLIP_VERSION}"
echo "  Hostname:   $(hostname)"
echo ""

# --- Pre-flight: verify rclone auth ----------------------------------------
if ! rclone lsd gdrive:Paperclip-Backups &>/dev/null; then
    echo "ERROR: rclone gdrive remote is not authenticated."
    echo "The OAuth token is missing or expired."
    echo ""
    echo "To fix (headless server):"
    echo "  1. On a machine WITH a browser, run:"
    echo '     SCOPE_BLOB=$(echo -n '"'"'{"scope":"drive.file"}'"'"' | base64 -w0 | sed '"'"'s/=//g'"'"')'
    echo '     rclone authorize "drive" "${SCOPE_BLOB}" --auth-no-open-browser'
    echo "  2. Copy the JSON token block output"
    echo "  3. On this server, run:"
    echo "     ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token"
    echo "  4. Paste the token block, press Ctrl+D"
    echo ""
    echo "Or see full instructions:"
    echo "  ~/.paperclip/scripts/rclone-headless-auth.sh --help"
    exit 1
fi
echo "rclone auth check: OK"
echo ""

# --- Pick freshest database dump ------------------------------------------
FRESHEST=$(ls -1t "$BACKUPS_DIR"/paperclip-*.sql.gz 2>/dev/null | head -1)
if [ -z "$FRESHEST" ]; then
    echo "No database dumps found in ${BACKUPS_DIR}."
    echo "Skipping DB dump — shipping instance data only."
    DUMP_FILENAME=""
else
    DUMP_FILENAME=$(basename "$FRESHEST")
    echo "DB dump: ${DUMP_FILENAME} ($(du -h "$FRESHEST" | cut -f1))"
    cp "$FRESHEST" "$TMPDIR/$DUMP_FILENAME"
fi

# --- Sanitize config.json -------------------------------------------------
echo "Sanitizing config.json..."

# Write the sanitizer to a temp file to avoid heredoc expansion issues
cat > "$TMPDIR/sanitize_config.py" << 'PYEOF'
import json, sys, os, re

src = sys.argv[1]
dst = sys.argv[2]
now_utc = os.environ.get("NOW_UTC", "unknown")

with open(src) as f:
    cfg = json.load(f)

# Strip entire secrets block
cfg.pop('secrets', None)

# Strip token-like fields inside auth block
if 'auth' in cfg and isinstance(cfg['auth'], dict):
    AUTH_TOKEN_KEYS = {'token', 'accessToken', 'refreshToken', 'secret', 'apiKey', 'apiSecret', 'clientSecret'}
    for k in list(cfg['auth'].keys()):
        if k in AUTH_TOKEN_KEYS:
            cfg['auth'][k] = 'REDACTED'

# Walk the entire tree and redact credential-like strings
def redact_credentials(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = redact_credentials(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = redact_credentials(v)
    elif isinstance(obj, str) and len(obj) > 20:
        if re.match(r'^[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}$', obj):
            return 'REDACTED_JWT'
        if re.match(r'^(sk|pk|test|live)_[A-Za-z0-9]{20,}$', obj):
            return 'REDACTED_API_KEY'
        if re.match(r'^[A-Za-z0-9+/]{40,}={0,2}$', obj):
            return 'REDACTED_BASE64'
    return obj

cfg = redact_credentials(cfg)
cfg['_sanitized'] = True
cfg['_sanitized_at'] = now_utc

with open(dst, 'w') as f:
    json.dump(cfg, f, indent=2)

filesize = len(json.dumps(cfg, indent=2))
print(f"  Sanitized config written ({filesize} bytes) -> {dst}")
PYEOF

NOW_UTC="$NOW_UTC" python3 "$TMPDIR/sanitize_config.py" "$CONFIG_FILE" "$TMPDIR/config.json"

# --- Build instance data tarball -------------------------------------------
PAYLOAD_NAME="paperclip-instance-${YEAR}${MONTH}${DAY}-${HOURMIN}.tar.gz"
PAYLOAD_FILE="$TMPDIR/$PAYLOAD_NAME"

echo "Building payload: ${PAYLOAD_NAME} ..."

# Collect paths that exist for tar
TAR_INCLUDE=""
for d in companies projects skills; do
    if [ -d "$INSTANCE_DIR/$d" ]; then
        TAR_INCLUDE="$TAR_INCLUDE -C $INSTANCE_DIR $d"
    else
        echo "  (skipping ${d}/ — does not exist)"
    fi
done
if [ -d "$INSTANCE_DIR/data/storage" ]; then
    TAR_INCLUDE="$TAR_INCLUDE -C $INSTANCE_DIR/data storage"
else
    echo "  (skipping data/storage/ — does not exist)"
fi

tar czf "$PAYLOAD_FILE" \
    $TAR_INCLUDE \
    -C "$TMPDIR" config.json \
    ${DUMP_FILENAME:+ -C "$TMPDIR" "$DUMP_FILENAME"}

echo "  Payload size: $(du -h "$PAYLOAD_FILE" | cut -f1)"

# --- Build MANIFEST.json ---------------------------------------------------
echo "Building MANIFEST.json..."

cat > "$TMPDIR/build_manifest.py" << 'PYEOF'
import hashlib, json, os, sys

payload_file = sys.argv[1]
output_dir = sys.argv[2]
now_utc = os.environ.get("NOW_UTC", "unknown")
hostname = os.environ.get("HOSTNAME", "unknown")
pc_version = os.environ.get("PAPERCLIP_VERSION", "unknown")
company_id = os.environ.get("COMPANY_ID", "unknown")
dump_filename = os.environ.get("DUMP_FILENAME", "")

manifest = {
    "timestamp": now_utc,
    "hostname": hostname,
    "paperclipVersion": pc_version,
    "companyId": company_id,
    "sourceDump": dump_filename,
    "files": [],
    "totalBytes": 0,
}

# SHA-256 of the payload tarball
sha256 = hashlib.sha256()
with open(payload_file, "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        sha256.update(chunk)

manifest["payloadSha256"] = sha256.hexdigest()
manifest["payloadSizeBytes"] = os.path.getsize(payload_file)

manifest_path = os.path.join(output_dir, "MANIFEST.json")
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"  Payload: {manifest['payloadSizeBytes']:,} bytes")
print(f"  SHA-256: {manifest['payloadSha256']}")
print(f"  Manifest: {manifest_path}")
PYEOF

export NOW_UTC HOSTNAME PAPERCLIP_VERSION COMPANY_ID DUMP_FILENAME
python3 "$TMPDIR/build_manifest.py" "$PAYLOAD_FILE" "$TMPDIR"

# --- Upload to Google Drive ------------------------------------------------
REMOTE_ROOT="gdrive:Paperclip-Backups"
DEST="${REMOTE_ROOT}/${COMPANY_ID}/${YEAR}/${MONTH}/${DAY}/${HOURMIN}"

echo ""
echo "Uploading to: ${DEST}"
echo ""

rclone copy "$PAYLOAD_FILE" "$DEST/" --progress --verbose
rclone copy "$TMPDIR/MANIFEST.json" "$DEST/" --progress --verbose
if [ -n "$DUMP_FILENAME" ]; then
    rclone copy "$TMPDIR/$DUMP_FILENAME" "$DEST/" --progress --verbose
fi

echo ""
echo "=========================================="
echo "  Backup complete!"
echo "  Destination: ${DEST}"
echo "  Payload:     ${PAYLOAD_NAME}"
echo "  Manifest:    MANIFEST.json"
echo "  DB dump:     ${DUMP_FILENAME:-none}"
echo "=========================================="

# Write success state
BACKUP_STATE_DIR="${INSTANCE_DIR}/backup-state"
mkdir -p "$BACKUP_STATE_DIR"
python3 -c "
import json, os
state = {
    'lastSuccess': '$NOW_UTC',
    'destination': '$DEST',
    'payloadSha256': open('${TMPDIR}/MANIFEST.json' if os.path.exists('${TMPDIR}/MANIFEST.json') else '/dev/null'),
}
with open('${TMPDIR}/MANIFEST.json') as f:
    m = json.load(f)
state['payloadSha256'] = m.get('payloadSha256', '')
state['payloadSizeBytes'] = m.get('payloadSizeBytes', 0)
state['hostname'] = '$(hostname)'
with open('${BACKUP_STATE_DIR}/last-success.json', 'w') as f:
    json.dump(state, f, indent=2)
print(f'State written: ${BACKUP_STATE_DIR}/last-success.json')
"

# Clean up manifest SHA reference before trap
