#!/bin/bash
# install-devserver-autosync.sh — install the dev-server autosync timer (BTCAAAAA-38800)
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

install -m 755 "$SRC_DIR/btc-devserver-autosync.sh" "$UNIT_DIR/btc-devserver-autosync.sh"
install -m 644 "$SRC_DIR/btc-devserver-autosync.service" "$UNIT_DIR/btc-devserver-autosync.service"
install -m 644 "$SRC_DIR/btc-devserver-autosync.timer" "$UNIT_DIR/btc-devserver-autosync.timer"

systemctl --user daemon-reload
systemctl --user enable --now btc-devserver-autosync.timer

echo "Installed. Verify: systemctl --user list-timers | grep autosync"
