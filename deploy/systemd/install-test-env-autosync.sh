#!/bin/bash
# install-test-env-autosync.sh — install the test-env autosync timer (BTCAAAAA-38802)
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

install -m 755 "$SRC_DIR/test-env-autosync.sh" "$UNIT_DIR/test-env-autosync.sh"
install -m 644 "$SRC_DIR/test-env-autosync.service" "$UNIT_DIR/test-env-autosync.service"
install -m 644 "$SRC_DIR/test-env-autosync.timer" "$UNIT_DIR/test-env-autosync.timer"

systemctl --user daemon-reload
systemctl --user enable --now test-env-autosync.timer

echo "Installed. Verify: systemctl --user list-timers | grep test-env-autosync"
