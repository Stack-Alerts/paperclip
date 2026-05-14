#!/bin/bash
#
# _rclone_pass.sh -- source this to set RCLONE_CONFIG_PASS for encrypted rclone config
#
# Reads password from ~/.config/rclone/rclone-pass (chmod 600).
# Skips silently if the password file doesn't exist (plaintext config mode).
#
# Usage: source "$(dirname "$0")/_rclone_pass.sh"

RCLONE_PASS_FILE="${RCLONE_PASS_FILE:-$HOME/.config/rclone/rclone-pass}"

if [ -f "$RCLONE_PASS_FILE" ] && [ -r "$RCLONE_PASS_FILE" ]; then
    export RCLONE_CONFIG_PASS
    RCLONE_CONFIG_PASS=$(cat "$RCLONE_PASS_FILE")
fi
