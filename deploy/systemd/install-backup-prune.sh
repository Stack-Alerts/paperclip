#!/bin/bash
#
# install-backup-prune.sh — install user-mode systemd timer for prune-local-dumps.sh.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
TARGET_DIR="$HOME/.config/systemd/user"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/paperclip-backup-prune.service" "$TARGET_DIR/"
cp "$SCRIPT_DIR/paperclip-backup-prune.timer"   "$TARGET_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now paperclip-backup-prune.timer

echo "Installed:"
systemctl --user status paperclip-backup-prune.timer --no-pager --lines=0 || true
echo ""
echo "Next firing:"
systemctl --user list-timers paperclip-backup-prune.timer --no-pager || true
