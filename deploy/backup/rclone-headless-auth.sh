#!/bin/bash
set -euo pipefail

CONFIG_FILE="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
REMOTE="gdrive"
SCOPE="drive.file"
ACTION=""

print_header() {
    echo "========================================"
    echo "  Paperclip — Headless rclone OAuth"
    echo "========================================"
    echo ""
    echo "Remote:  ${REMOTE}"
    echo "Scope:   ${SCOPE}"
    echo "Config:  ${CONFIG_FILE}"
    echo ""
}

print_help() {
    cat << 'HELPEOF'

HEADLESS SERVER OAuth — you have two options:

--- Option A: rclone authorize (recommended) ---
On a machine WITH a browser, run:
    rclone authorize "drive" "drive.file" --auth-no-open-browser

This prints a URL. Open it, authorize with Google, paste the code
back on that machine. You'll receive a JSON token block.

Copy that JSON token block. Then on THIS server, run:
    ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token
    (paste the JSON token block, then press Ctrl+D)

--- Option B: direct reconnect (needs SSH forwarding) ---
If you can reach this server's localhost via SSH tunnel:
    ssh -L 53682:127.0.0.1:53682 sirrus-serv
Then run:
    rclone config reconnect gdrive:
Open the URL in your browser; callback is forwarded to the server.

--- Option C: restore from backup ---
If a backup of rclone.conf exists, restore it:
    cp /home/sirrus/backups/system/rclone.conf.YYYYMMDD ~/.config/rclone/rclone.conf

HELPEOF
}

for arg in "$@"; do
    case "$arg" in
        --help|-h|help)
            ACTION="help"
            ;;
        --check)
            ACTION="check"
            ;;
        --verify)
            ACTION="verify"
            ;;
        --apply-token)
            ACTION="apply-token"
            ;;
        --*)
            echo "Unknown flag: $arg"
            print_help
            exit 2
            ;;
        *)
            if [ -z "${_POS1:-}" ]; then
                _POS1="$arg"
            elif [ -z "${_POS2:-}" ]; then
                _POS2="$arg"
            fi
            ;;
    esac
done

REMOTE="${_POS1:-gdrive}"
SCOPE="${_POS2:-drive.file}"

print_header

case "${ACTION}" in
    help)
        print_help
        exit 0
        ;;
    check)
        echo "Checking remote '${REMOTE}'..."
        if rclone lsd "${REMOTE}:Paperclip-Backups" &>/dev/null; then
            echo "Remote '${REMOTE}' is authenticated and working."
            exit 0
        else
            echo "Remote '${REMOTE}' is NOT authenticated."
            echo ""
            echo "Run: ~/.paperclip/scripts/rclone-headless-auth.sh --help"
            echo "Or:  ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token"
            exit 1
        fi
        ;;
    verify)
        echo "Verifying remote '${REMOTE}'..."
        if rclone lsd "${REMOTE}:Paperclip-Backups" &>/dev/null; then
            echo "Remote '${REMOTE}' is authenticated and working."
            rclone mkdir "${REMOTE}:Paperclip-Backups" &>/dev/null || true
            exit 0
        else
            echo "ERROR: Remote verification failed."
            echo "Run: rclone config reconnect ${REMOTE}:"
            echo "Or:  ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token"
            exit 1
        fi
        ;;
    apply-token)
        TOKEN_TMP=$(mktemp /tmp/rclone-token.XXXXXX.json)
        trap 'rm -f "$TOKEN_TMP"' EXIT

        echo "Paste the rclone authorize JSON token block below, then press Ctrl+D:"
        echo ""
        cat > "$TOKEN_TMP"

        TOKEN_CONTENT=$(cat "$TOKEN_TMP")
        if [ -z "$TOKEN_CONTENT" ]; then
            echo "ERROR: No token provided."
            exit 1
        fi

        if ! python3 -c "import json; json.load(open('$TOKEN_TMP'))" 2>/dev/null; then
            echo "ERROR: Invalid JSON token block. Expected output from 'rclone authorize'."
            echo "Content received:"
            head -c 200 "$TOKEN_TMP"
            echo ""
            exit 1
        fi

        echo ""
        echo "Token JSON is valid. Applying to remote '${REMOTE}'..."

        mkdir -p "$(dirname "$CONFIG_FILE")"

        python3 << PYEOF
import json
import os
import configparser
import shutil

config_file = os.path.expanduser("${CONFIG_FILE}")
remote = "${REMOTE}"
scope = "${SCOPE}"
token_file = "${TOKEN_TMP}"

with open(token_file) as f:
    token_data = json.load(f)

required = {"access_token", "token_type", "refresh_token", "expiry"}
missing = required - set(token_data.keys())
if missing:
    print(f"WARNING: token is missing fields: {missing}")
    print("The token may not be complete. Continuing anyway...")

token_str = json.dumps(token_data)

parser = configparser.ConfigParser()
if os.path.exists(config_file):
    parser.read(config_file)

existing = dict(parser.items(remote)) if parser.has_section(remote) else {}
existing["type"] = "drive"
existing["scope"] = scope
existing["token"] = token_str
existing.pop("service_account_file", None)
existing.pop("root_folder_id", None)

if not parser.has_section(remote):
    parser.add_section(remote)
for k, v in existing.items():
    parser.set(remote, k, str(v))

if os.path.exists(config_file):
    backup_path = config_file + ".bak"
    shutil.copy2(config_file, backup_path)
    print(f"Backup saved: {backup_path}")

with open(config_file, "w") as f:
    parser.write(f)

print(f"Token applied to [{remote}] in {config_file}")
PYEOF

        echo ""
        echo "Verifying remote..."
        if rclone lsd "${REMOTE}:Paperclip-Backups" &>/dev/null; then
            echo "Remote '${REMOTE}' is working and authenticated."
            rclone mkdir "${REMOTE}:Paperclip-Backups" &>/dev/null || true
            echo ""
            echo "Backup pipeline is now operational."
            echo "To run a backup immediately: ~/.paperclip/scripts/backup-to-drive.sh"
            exit 0
        else
            echo "ERROR: Remote verification failed after applying token."
            echo "The token may be invalid or expired."
            echo ""
            echo "Diagnostic commands:"
            echo "  rclone config show ${REMOTE}"
            echo "  rclone lsd ${REMOTE}: --verbose"
            echo ""
            if [ -f "${CONFIG_FILE}.bak" ]; then
                echo "If needed, restore the previous config from backup:"
                echo "  cp ${CONFIG_FILE}.bak ${CONFIG_FILE}"
            fi
            exit 1
        fi
        ;;
    *)
        print_help
        ;;
esac
