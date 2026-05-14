#!/bin/bash
set -euo pipefail

CONFIG_FILE="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
REMOTE="gdrive"
SCOPE="drive.file"
ACTION=""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

_source_rclone_pass() {
    if [ -f "$SCRIPT_DIR/_rclone_pass.sh" ]; then
        source "$SCRIPT_DIR/_rclone_pass.sh"
    fi
}

print_header() {
    echo "========================================"
    echo "  Paperclip — Headless rclone OAuth"
    echo "========================================"
    echo ""
    echo "Remote:  ${REMOTE}"
    echo "Scope:   ${SCOPE}"
    echo "Config:  ${CONFIG_FILE}"
    if [ -n "${RCLONE_CONFIG_PASS:-}" ]; then
        echo "Auth:    encrypted config (pass found)"
    fi
    echo ""
}

print_help() {
    cat << 'HELPEOF'

HEADLESS SERVER OAuth — you have two options:

--- Option A: rclone authorize (recommended) ---
On a machine WITH a browser, run:
    rclone authorize "drive" "<scope>" --auth-no-open-browser

This prints a URL. Open it, authorize with Google, paste the code
back on that machine. You'll receive a JSON token block.

Copy that JSON token block. Then on THIS server, run:
    ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token
    (paste the JSON token block, then press Ctrl+D)

To use a different scope (e.g. for restoring historical backups):
    ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token --scope drive

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
        --scope)
            ACTION="set-scope"
            ;;
        --scope-from)
            ACTION="scope-from"
            ;;
        *)
            if [ "${arg#--scope=}" != "$arg" ]; then
                SCOPE="${arg#--scope=}"
            elif [ -z "${_POS1:-}" ]; then
                _POS1="$arg"
            elif [ -z "${_POS2:-}" ]; then
                _POS2="$arg"
            fi
            ;;
    esac
done

REMOTE="${_POS1:-gdrive}"
SCOPE="${_POS2:-drive.file}"

_source_rclone_pass
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
    scope-from)
        echo "Reading current scope from rclone config..."
        CURRENT=$(rclone config show "${REMOTE}:" 2>/dev/null | grep -E '^scope' | sed 's/^scope *= *//' || echo "unknown")
        echo "Current scope: ${CURRENT}"
        exit 0
        ;;
    set-scope)
        echo "Setting scope for '${REMOTE}' to '${SCOPE}'..."
        if [ -z "${RCLONE_CONFIG_PASS:-}" ]; then
            echo "WARNING: RCLONE_CONFIG_PASS is not set. Config may be encrypted."
            echo "If the config is encrypted, run: source ~/.paperclip/scripts/_rclone_pass.sh"
            echo "Then re-run this command."
        fi

        python3 << PYEOF
import subprocess
import os
import sys

remote = "${REMOTE}"
scope = "${SCOPE}"
rclone_pass = os.environ.get("RCLONE_CONFIG_PASS", "")

env = os.environ.copy()
env["RCLONE_CONFIG_PASS"] = rclone_pass

result = subprocess.run(
    ["rclone", "config", "update", f"{remote}:", "scope", scope],
    env=env,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print(f"ERROR: {result.stderr.strip()}")
    sys.exit(1)
print(f"Scope updated to '{scope}' on remote '{remote}'")
print(result.stderr.strip() or "(no output)")
PYEOF
        if [ $? -eq 0 ]; then
            echo "Verifying remote with new scope..."
            rclone lsd "${REMOTE}:Paperclip-Backups" 2>&1 | head -5
        fi
        ;;
    apply-token)
        TOKEN_TMP=$(mktemp /tmp/rclone-token.XXXXXX.json)
        trap 'rm -f "$TOKEN_TMP"' EXIT

        echo "Paste the rclone authorize JSON token block below, then press Ctrl+D:"
        echo "(Run on a browser machine: rclone authorize \"drive\" \"${SCOPE}\" --auth-no-open-browser)"
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
        echo "Token JSON is valid. Applying to remote '${REMOTE}' with scope '${SCOPE}'..."

        if [ -z "${RCLONE_CONFIG_PASS:-}" ]; then
            echo "NOTE: RCLONE_CONFIG_PASS is not set. If the config is encrypted, this will fail."
            echo "      Source _rclone_pass.sh first: source ~/.paperclip/scripts/_rclone_pass.sh"
        fi

        python3 << PYEOF
import json
import os
import subprocess
import sys

config_file = os.path.expanduser("${CONFIG_FILE}")
remote = "${REMOTE}"
scope = "${SCOPE}"
token_file = "${TOKEN_TMP}"
rclone_pass = os.environ.get("RCLONE_CONFIG_PASS", "")

with open(token_file) as f:
    token_data = json.load(f)

required = {"access_token", "token_type", "refresh_token", "expiry"}
missing = required - set(token_data.keys())
if missing:
    print(f"WARNING: token is missing fields: {missing}")
    print("The token may not be complete. Continuing anyway...")

token_str = json.dumps(token_data)

env = os.environ.copy()
env["RCLONE_CONFIG_PASS"] = rclone_pass

# Update token
result = subprocess.run(
    ["rclone", "config", "update", f"{remote}:", "token", token_str],
    env=env,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print(f"ERROR setting token: {result.stderr.strip()}")
    sys.exit(1)

print(f"Token applied to [{remote}]")

# Update scope if different from current
show_result = subprocess.run(
    ["rclone", "config", "show", f"{remote}:"],
    env=env,
    capture_output=True,
    text=True,
)
current_scope = ""
for line in show_result.stdout.split("\\n"):
    if line.strip().startswith("scope "):
        current_scope = line.split("=", 1)[-1].strip() if "=" in line else line.split(None, 1)[-1].strip()
        break

if current_scope and current_scope != scope:
    print(f"Updating scope: {current_scope} -> {scope}")
    scope_result = subprocess.run(
        ["rclone", "config", "update", f"{remote}:", "scope", scope],
        env=env,
        capture_output=True,
        text=True,
    )
    if scope_result.returncode != 0:
        print(f"WARNING: scope update failed: {scope_result.stderr.strip()}")
    else:
        print(f"Scope updated to '{scope}'")
else:
    print(f"Scope: {current_scope or scope} (unchanged)")

print("\nDone. Token applied successfully.")
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
            echo "  source ~/.paperclip/scripts/_rclone_pass.sh && rclone config show ${REMOTE}"
            echo "  rclone lsd ${REMOTE}: --verbose"
            exit 1
        fi
        ;;
    *)
        print_help
        ;;
esac
