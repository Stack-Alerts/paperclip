#!/bin/bash
set -euo pipefail


# --- Load rclone encryption password (if config is encrypted) ---
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
source "${SCRIPT_DIR}/_rclone_pass.sh"
#
# backup-to-drive.sh — Paperclip offsite backup to Google Drive
#
# Bundles the latest database dump + instance data (companies, projects,
# skills, storage) and uploads to gdrive:Paperclip-Backups/<companyId>/…
#
# Locked with flock so the 4h cron and manual runs never collide.
#

RCLONE_CONFIG="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"

# --- Helper: update deadman switch on auth failure --------------------------
_update_deadman_on_auth_fail() {
    local reason="${1:-unknown}"
    local state_file="$HOME/.paperclip/backup_deadman_switch_state.json"
    local now_utc
    now_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    python3 -c "
import json, os
state_file = os.path.expanduser('$state_file')
state = {}
if os.path.exists(state_file):
    try:
        state = json.load(open(state_file))
    except Exception:
        pass
state['last_auth_failure_utc'] = '$now_utc'
state['last_auth_failure_reason'] = '${reason}'
os.makedirs(os.path.dirname(state_file), exist_ok=True)
json.dump(state, open(state_file, 'w'), indent=2)
" 2>/dev/null || true
    echo "  Deadman state updated (auth failure: ${reason})"
}

# ============================================================================
# Pre-flight: OAuth health check (before flock — no lock needed)
# ============================================================================
NOW_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
DEADMAN_STATE_FILE="$HOME/.paperclip/backup_deadman_switch_state.json"

echo "--- Pre-flight: OAuth health check ---"

if ! command -v rclone &>/dev/null; then
    echo "ERROR: rclone is not installed."
    echo "Fix: sudo apt update && sudo apt install rclone"
    _update_deadman_on_auth_fail "rclone_missing"
    exit 1
fi
echo "  rclone: $(rclone version 2>/dev/null | head -1)"

OAUTH_RESULT=$(python3 2>/dev/null << 'PYEOF'
import os, sys, json
from datetime import datetime, timezone

config_file = os.path.expanduser(os.environ.get("RCLONE_CONFIG", "~/.config/rclone/rclone.conf"))

encrypted = False
try:
    with open(config_file, "r") as f:
        head = f.read(512)
    if "RCLONE_ENCRYPT_V0" in head or "Encrypted rclone configuration" in head:
        encrypted = True
except FileNotFoundError:
    print("FATAL=no_config_file")
    sys.exit(0)

if encrypted:
    print("OK=encrypted_config ENCRYPTED=true")
    sys.exit(0)

import configparser
parser = configparser.ConfigParser()
try:
    parser.read(config_file)
except Exception:
    print("OK=config_parse_error")
    sys.exit(0)

if not parser.has_section("gdrive"):
    print("OK=no_remote MISSING_REMOTE=true")
    sys.exit(0)

if not parser.has_option("gdrive", "token"):
    print("OK=no_token MISSING_TOKEN=true")
    sys.exit(0)

raw = parser.get("gdrive", "token", raw=True)
try:
    t = json.loads(raw)
except json.JSONDecodeError:
    print("OK=parse_error UNPARSEABLE=true")
    sys.exit(0)

access_ok = bool(t.get("access_token", ""))
refresh_ok = bool(t.get("refresh_token", ""))
expiry_str = t.get("expiry", "")

secs_left = None
if expiry_str:
    try:
        exp = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        secs_left = int((exp - now).total_seconds())
    except:
        pass

status = "token_ok"
warnings = []
if not access_ok:
    status = "no_access"
if not refresh_ok:
    status = "no_refresh"
    warnings.append("MISSING_REFRESH=true")

parts = [f"OK={status}"]
if secs_left is not None:
    parts.append(f"EXPIRY_SECS={secs_left}")
parts.extend(warnings)
print(" ".join(parts))
PYEOF
)

if echo "$OAUTH_RESULT" | grep -q "^FATAL="; then
    echo "ERROR: rclone config file not found at ${RCLONE_CONFIG}."
    _update_deadman_on_auth_fail "config_missing"
    exit 1
fi

OK_VAL=$(echo "$OAUTH_RESULT" | grep -oP '(?<=^| )OK=\K\S+' || true)
EXP_SECS=$(echo "$OAUTH_RESULT" | grep -oP '(?<=^| )EXPIRY_SECS=\K-?\d+' || true)
IS_ENCRYPTED=$(echo "$OAUTH_RESULT" | grep -oP 'ENCRYPTED=\K\S+' || true)

case "${OK_VAL:-}" in
    encrypted_config)
        echo "  config: encrypted (token details not inspectable)"
        ;;
    config_parse_error)
        echo "  config: present but unparseable"
        ;;
    no_remote)
        echo "  gdrive remote: NOT CONFIGURED"
        ;;
    no_token)
        echo "  token: MISSING (no OAuth token in rclone config)"
        ;;
    parse_error)
        echo "  token: PRESENT but unparseable JSON"
        ;;
    no_access)
        echo "  token: PRESENT but access_token is empty"
        echo "  refresh_token: MISSING"
        ;;
    no_refresh)
        if [ -n "${EXP_SECS:-}" ] && [[ "${EXP_SECS:-}" =~ ^-?[0-9]+$ ]]; then
            if [ "$EXP_SECS" -lt 0 ]; then
                echo "  token: EXPIRED ($(( EXP_SECS * -1 / 60 ))m ago)"
            elif [ "$EXP_SECS" -lt 3600 ]; then
                echo "  token: valid but EXPIRES in ${EXP_SECS}s (< 1h) — and no refresh_token"
            else
                echo "  token: valid (expires in ~$(( EXP_SECS / 60 ))m) — but no refresh_token"
            fi
        else
            echo "  token: present — but no refresh_token"
        fi
        echo "  refresh_token: MISSING (token cannot auto-refresh)"
        ;;
    token_ok)
        if [ -n "${EXP_SECS:-}" ] && [[ "${EXP_SECS:-}" =~ ^-?[0-9]+$ ]]; then
            if [ "$EXP_SECS" -lt 0 ]; then
                echo "  token: EXPIRED ($(( EXP_SECS * -1 / 60 ))m ago)"
            elif [ "$EXP_SECS" -lt 3600 ]; then
                echo "  token: valid but EXPIRES in ${EXP_SECS}s (WARNING)"
            else
                echo "  token: valid (expires in ~$(( EXP_SECS / 60 ))m)"
            fi
        else
            echo "  token: present (expiry time unknown)"
        fi
        echo "  refresh_token: present (auto-refresh available)"
        ;;
esac

_do_oauth_connectivity_check() {
    if rclone lsd gdrive:Paperclip-Backups --config "$RCLONE_CONFIG" --ask-password=false </dev/null 2>/dev/null; then
        return 0
    elif [ "${IS_ENCRYPTED:-}" = "true" ]; then
        if rclone lsd gdrive:Paperclip-Backups --config "$RCLONE_CONFIG" </dev/null 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

echo "  connectivity check..."
CONN_FAILED=false
if _do_oauth_connectivity_check; then
    echo "  connectivity: OK"
else
    CONN_FAILED=true
fi

if $CONN_FAILED; then
    echo "ERROR: Cannot access gdrive:Paperclip-Backups."
    case "${OK_VAL:-}" in
        encrypted_config)
            echo "  Root cause: Encrypted rclone config without password in headless environment."
            echo "  Either set RCLONE_CONFIG_PASS or use an unencrypted config."
            ;;
        no_remote)
            echo "  Root cause: gdrive remote not configured in rclone."
            echo "  Fix: ~/.paperclip/scripts/rclone-bootstrap.sh"
            ;;
        no_token)
            echo "  Root cause: No OAuth token in rclone config."
            ;;
        no_access)
            echo "  Root cause: Token has no access_token."
            ;;
        *)
            if [ -n "${EXP_SECS:-}" ] && [[ "${EXP_SECS:-}" =~ ^-?[0-9]+$ ]] && [ "$EXP_SECS" -lt 0 ]; then
                echo "  Root cause: Token is expired."
            else
                echo "  Root cause: Token may be invalid, revoked, or network issue."
            fi
            ;;
    esac
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
    _update_deadman_on_auth_fail "connectivity"
    exit 1
fi

echo "  OAuth health: PASS"
echo ""

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

# ============================================================================
# Change-detection gate (BTCAAAAA-33092)
# ----------------------------------------------------------------------------
# Computes a signature over (code HEAD, DB write counters, instance-dir mtime
# walk). If unchanged from the last uploaded signature, exit 0 with
# result=skipped_no_change and update last-success.json so the deadman switch
# treats the no-op as a healthy run (see backup_deadman_switch.py).
# ============================================================================

BACKUP_STATE_DIR="${INSTANCE_DIR}/backup-state"
mkdir -p "$BACKUP_STATE_DIR"
LAST_SIG_FILE="$BACKUP_STATE_DIR/last-signature.txt"
LAST_RESULT_FILE="$BACKUP_STATE_DIR/last-result.json"
LAST_SUCCESS_FILE="$BACKUP_STATE_DIR/last-success.json"

LAST_SIG_PREV=""
if [ -f "$LAST_SIG_FILE" ]; then
    LAST_SIG_PREV=$(tr -d '[:space:]' < "$LAST_SIG_FILE")
fi

# Code signal: git HEAD of the company's primary repo, if present.
BTE_REPO="${BTE_REPO_PATH:-$HOME/projects/BTC-Trade-Engine-PaperClip}"
if [ -d "$BTE_REPO/.git" ]; then
    CODE_SIG=$(git -C "$BTE_REPO" rev-parse HEAD 2>/dev/null || echo "unknown")
else
    CODE_SIG="no-repo"
fi

# Files signal: size+mtime+path walk over the instance dirs that the offsite
# tarball includes. No content read — purely metadata.
FILES_SIG=$(
    cd "$INSTANCE_DIR" 2>/dev/null && \
    find companies projects skills data/storage -type f -printf '%T@ %s %p\n' 2>/dev/null \
        | LC_ALL=C sort | sha256sum | cut -d' ' -f1
)
FILES_SIG="${FILES_SIG:-empty}"

# DB signal: SHA-256 of the freshest dump's content with the two known
# non-deterministic markers stripped (per-dump timestamp comment + per-run
# breakpoint UUID). Equal SQL data -> equal hash. Deterministic across
# environments — no dependency on psycopg2 / pip / venv / miniconda paths,
# which prevents the systemd-vs-interactive-env signature mismatch problem.
#
# Cost: one gunzip + grep + sha256 over the freshest dump (~5-10s for 500MB).
# Run once per 4h backup, this is comfortably cheap.

DB_SIG=""
DB_SIG_SOURCE=""
FRESHEST_FOR_SIG=$(ls -1t "$BACKUPS_DIR"/paperclip-*.sql.gz 2>/dev/null | head -1)
if [ -n "$FRESHEST_FOR_SIG" ] && [ -f "$FRESHEST_FOR_SIG" ]; then
    DB_SIG=$(gunzip -c "$FRESHEST_FOR_SIG" 2>/dev/null \
        | grep -vE '^-- (Created:|paperclip statement breakpoint)' \
        | sha256sum | cut -d' ' -f1)
    DB_SIG_SOURCE="dump-content-hash($(basename "$FRESHEST_FOR_SIG"))"
fi
DB_SIG="${DB_SIG:-unavailable}"
DB_SIG_SOURCE="${DB_SIG_SOURCE:-unavailable}"

SIGNATURE=$(printf "code=%s\ndb=%s\nfiles=%s\n" "$CODE_SIG" "$DB_SIG" "$FILES_SIG" \
    | sha256sum | cut -d' ' -f1)

echo "--- Change-detection ---"
echo "  code:      ${CODE_SIG:0:16}..."
echo "  db:        ${DB_SIG:0:16}...  (source: ${DB_SIG_SOURCE})"
echo "  files:     ${FILES_SIG:0:16}..."
echo "  signature: ${SIGNATURE:0:16}..."
echo "  previous:  ${LAST_SIG_PREV:0:16}..."

if [ -n "$LAST_SIG_PREV" ] && [ "$SIGNATURE" = "$LAST_SIG_PREV" ]; then
    SHORT_PREV="${LAST_SIG_PREV:0:12}"
    echo ""
    echo "no-op: no changes since ${SHORT_PREV}"
    echo "Skipping backup creation and upload."

    # Skip is a healthy run; refresh last-success.json timestamp so the
    # deadman switch does not alarm on legitimate no-op runs.
    NOW_UTC="$NOW_UTC" SIGNATURE="$SIGNATURE" \
    CODE_SIG="$CODE_SIG" DB_SIG="$DB_SIG" FILES_SIG="$FILES_SIG" \
    HOSTNAME_VAL="$(hostname)" \
    LAST_SUCCESS_FILE="$LAST_SUCCESS_FILE" \
    LAST_RESULT_FILE="$LAST_RESULT_FILE" \
    python3 <<'PYEOF'
import json, os
now_utc = os.environ["NOW_UTC"]
sig = os.environ["SIGNATURE"]
last_success_file = os.environ["LAST_SUCCESS_FILE"]
last_result_file = os.environ["LAST_RESULT_FILE"]

state = {}
if os.path.exists(last_success_file):
    try:
        state = json.load(open(last_success_file))
    except Exception:
        state = {}
state["lastSuccess"] = now_utc
state["lastRunResult"] = "skipped_no_change"
state["signature"] = sig
state["hostname"] = os.environ.get("HOSTNAME_VAL", "")
json.dump(state, open(last_success_file, "w"), indent=2)

result = {
    "timestamp": now_utc,
    "result": "skipped_no_change",
    "reason": "signature unchanged",
    "signature": sig,
    "codeSig": os.environ["CODE_SIG"],
    "dbSig": os.environ["DB_SIG"],
    "filesSig": os.environ["FILES_SIG"],
}
json.dump(result, open(last_result_file, "w"), indent=2)
PYEOF
    echo "  last-success.json + last-result.json updated."
    echo ""
    echo "=========================================="
    echo "  Result: skipped_no_change"
    echo "=========================================="
    exit 0
fi

if [ -n "$LAST_SIG_PREV" ]; then
    echo "  Signature CHANGED — proceeding with backup."
else
    echo "  No prior signature — first backup; proceeding."
fi
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

rclone copy "$PAYLOAD_FILE" "$DEST/" --config "$RCLONE_CONFIG" --progress --verbose
rclone copy "$TMPDIR/MANIFEST.json" "$DEST/" --config "$RCLONE_CONFIG" --progress --verbose
if [ -n "$DUMP_FILENAME" ]; then
    rclone copy "$TMPDIR/$DUMP_FILENAME" "$DEST/" --config "$RCLONE_CONFIG" --progress --verbose
fi

echo ""
echo "=========================================="
echo "  Backup complete!"
echo "  Destination: ${DEST}"
echo "  Payload:     ${PAYLOAD_NAME}"
echo "  Manifest:    MANIFEST.json"
echo "  DB dump:     ${DUMP_FILENAME:-none}"
echo "=========================================="

# Write success state (BACKUP_STATE_DIR was created above by the change-detection gate)
NOW_UTC="$NOW_UTC" DEST="$DEST" SIGNATURE="$SIGNATURE" \
CODE_SIG="$CODE_SIG" DB_SIG="$DB_SIG" FILES_SIG="$FILES_SIG" \
HOSTNAME_VAL="$(hostname)" \
TMPDIR="$TMPDIR" \
LAST_SUCCESS_FILE="$LAST_SUCCESS_FILE" \
LAST_RESULT_FILE="$LAST_RESULT_FILE" \
LAST_SIG_FILE="$LAST_SIG_FILE" \
python3 <<'PYEOF'
import json, os
now_utc = os.environ["NOW_UTC"]
dest = os.environ["DEST"]
sig = os.environ["SIGNATURE"]
tmpdir = os.environ["TMPDIR"]
last_success_file = os.environ["LAST_SUCCESS_FILE"]
last_result_file = os.environ["LAST_RESULT_FILE"]
last_sig_file = os.environ["LAST_SIG_FILE"]

manifest_path = os.path.join(tmpdir, "MANIFEST.json")
payload_sha = ""
payload_size = 0
if os.path.exists(manifest_path):
    try:
        m = json.load(open(manifest_path))
        payload_sha = m.get("payloadSha256", "")
        payload_size = m.get("payloadSizeBytes", 0)
    except Exception:
        pass

state = {
    "lastSuccess": now_utc,
    "lastRunResult": "ok",
    "destination": dest,
    "payloadSha256": payload_sha,
    "payloadSizeBytes": payload_size,
    "signature": sig,
    "hostname": os.environ.get("HOSTNAME_VAL", ""),
}
json.dump(state, open(last_success_file, "w"), indent=2)
print(f"State written: {last_success_file}")

result = {
    "timestamp": now_utc,
    "result": "ok",
    "destination": dest,
    "signature": sig,
    "codeSig": os.environ["CODE_SIG"],
    "dbSig": os.environ["DB_SIG"],
    "filesSig": os.environ["FILES_SIG"],
    "payloadSha256": payload_sha,
    "payloadSizeBytes": payload_size,
}
json.dump(result, open(last_result_file, "w"), indent=2)
print(f"Result written: {last_result_file}")

with open(last_sig_file, "w") as f:
    f.write(sig + "\n")
print(f"Signature recorded: {last_sig_file}")
PYEOF

# ============================================================================
# Offsite retention: keep newest 10 (BTCAAAAA-33092)
# ----------------------------------------------------------------------------
# Lists leaf YYYY/MM/DD/HHMM dirs under the company root and purges all but
# the 10 most-recent. Reverse-sort works because the path components are
# zero-padded and sort lexicographically.
# ============================================================================
echo ""
echo "--- Offsite retention (keep newest 10) ---"
RETENTION_KEEP="${BACKUP_RETENTION_KEEP:-10}"

OFFSITE_DIRS=$(rclone lsf "${REMOTE_ROOT}/${COMPANY_ID}" \
    --config "$RCLONE_CONFIG" --recursive --dirs-only --format p 2>/dev/null \
    | grep -E '^[0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9]{4}/?$' \
    | sed 's:/*$::' \
    | LC_ALL=C sort -r) || true

if [ -z "$OFFSITE_DIRS" ]; then
    echo "  (no offsite directories matched leaf pattern)"
else
    TOTAL=$(echo "$OFFSITE_DIRS" | wc -l)
    KEEP_LIST=$(echo "$OFFSITE_DIRS" | head -n "$RETENTION_KEEP")
    PURGE_LIST=$(echo "$OFFSITE_DIRS" | tail -n +$((RETENTION_KEEP + 1)))
    PURGE_COUNT=0
    if [ -n "$PURGE_LIST" ]; then
        PURGE_COUNT=$(echo "$PURGE_LIST" | grep -c .)
    fi
    echo "  Found: ${TOTAL} backup dirs"
    echo "  Keep:  ${RETENTION_KEEP} newest"
    echo "  Purge: ${PURGE_COUNT}"
    if [ "$PURGE_COUNT" -gt 0 ]; then
        echo "$PURGE_LIST" | while IFS= read -r d; do
            [ -z "$d" ] && continue
            echo "    purging: $d"
            rclone purge "${REMOTE_ROOT}/${COMPANY_ID}/$d" --config "$RCLONE_CONFIG" 2>&1 \
                | grep -v "^$" | tail -3 || true
        done
    fi
fi
echo ""

# Clean up manifest SHA reference before trap
