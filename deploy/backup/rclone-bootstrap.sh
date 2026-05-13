#!/bin/bash
set -euo pipefail

RCLONE_REMOTE="gdrive"
RCLONE_DRIVE_SCOPE="drive.file"
RCLONE_CONFIG_FILE="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
PAPERCLIP_HOME="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo "  Paperclip -- rclone GDrive Bootstrap"
echo "========================================"
echo ""

if ! command -v rclone &>/dev/null; then
    echo "rclone not found. Install it first:"
    echo "  sudo apt update && sudo apt install rclone"
    exit 1
fi

echo "rclone: $(rclone version 2>/dev/null | head -1)"
echo ""

DETECT_HEADLESS="no"
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    DETECT_HEADLESS="yes"
fi

MODE="${1:-}"

if rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE}:"; then
    echo "Remote '${RCLONE_REMOTE}' already configured."
    if [ "$MODE" = "--force" ]; then
        echo "Reconfiguring (--force)..."
    elif [ "$MODE" = "--headless" ] || [ "$DETECT_HEADLESS" = "yes" ]; then
        echo ""
        echo "Headless environment detected."
        echo "To re-authorize, run:"
        echo "  ${PAPERCLIP_HOME}/scripts/rclone-headless-auth.sh"
        echo ""
        echo "Verifying remote..."
        if rclone lsd "${RCLONE_REMOTE}:Paperclip-Backups" 2>/dev/null; then
            echo "Remote '${RCLONE_REMOTE}' is working and authorized."
            exit 0
        else
            echo "Remote exists but token may be expired."
            echo "Run: rclone config reconnect ${RCLONE_REMOTE}:"
            echo "Or use headless auth: ${PAPERCLIP_HOME}/scripts/rclone-headless-auth.sh"
            exit 1
        fi
    fi
fi

if [ "$DETECT_HEADLESS" = "yes" ]; then
    echo "HEADLESS ENVIRONMENT DETECTED (no DISPLAY/WAYLAND_DISPLAY)"
    echo ""
    echo "OAuth requires a browser. Use the headless helper:"
    echo ""
    echo "  ${PAPERCLIP_HOME}/scripts/rclone-headless-auth.sh"
    echo ""
    echo "Or read the full instructions:"
    echo "  ${PAPERCLIP_HOME}/scripts/rclone-headless-auth.sh --help"
    echo ""
    echo "Quick summary:"
    echo "  1. On a machine WITH a browser, run:"
    echo "     SCOPE_BLOB=$(echo -n '{"scope":"'${RCLONE_DRIVE_SCOPE}'"}' | base64 -w0 | sed 's/=//g')\n     rclone authorize \"drive\" \"${SCOPE_BLOB}\" --auth-no-open-browser"
    echo "  2. Copy the JSON token block output"
    echo "  3. On this server, run:"
    echo "     ${PAPERCLIP_HOME}/scripts/rclone-headless-auth.sh --apply-token"
    echo "  4. Paste the token block, press Ctrl+D"
    exit 0
fi

echo "Step 1: Creating rclone remote '${RCLONE_REMOTE}' (scope: ${RCLONE_DRIVE_SCOPE})"
echo ""
echo "A browser URL will be printed. On a headless server:"
echo "  1. Copy the URL"
echo "  2. Open it in a browser on any machine"
echo "  3. Authorize with your Google account"
echo "  4. Paste the returned verification code here"
echo ""

mkdir -p "$(dirname "$RCLONE_CONFIG_FILE")"

rclone config create "$RCLONE_REMOTE" drive \
    --config "$RCLONE_CONFIG_FILE" \
    --drive-scope "$RCLONE_DRIVE_SCOPE" \
    --drive-auth-owner-only \
    --all

echo ""
echo "Step 2: Verifying remote..."
if rclone about "$RCLONE_REMOTE": 2>/dev/null; then
    echo "Remote '${RCLONE_REMOTE}' is working."
else
    echo "(about check skipped -- expected for drive.file scope)"
    rclone lsd "$RCLONE_REMOTE": 2>&1 || echo "(empty root is normal)"
fi

echo ""
echo "Step 3: Creating Paperclip-Backups root..."
rclone mkdir "$RCLONE_REMOTE":Paperclip-Backups 2>/dev/null || true
echo "Done."

echo ""
echo "========================================"
echo "  Bootstrap complete!"
echo "  Remote:  ${RCLONE_REMOTE}:"
echo "  Root:    ${RCLONE_REMOTE}:Paperclip-Backups/"
echo "  Config:  ${RCLONE_CONFIG_FILE}"
echo "========================================"
echo ""
echo "To run a backup now:"
echo "  ${PAPERCLIP_HOME}/scripts/backup-to-drive.sh"
echo ""
echo "Scheduling is handled by systemd timer:"
echo "  systemctl --user status paperclip-backup.timer"
