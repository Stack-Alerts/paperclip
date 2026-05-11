#!/usr/bin/env bash
# Install the opencode watchdog as a systemd --user timer.
#
# Usage:
#   bash scripts/setup_opencode_watchdog.sh          # install
#   bash scripts/setup_opencode_watchdog.sh --remove  # uninstall
#   bash scripts/setup_opencode_watchdog.sh --status  # check status

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$REPO_DIR/scripts/opencode-watchdog.service"
TIMER_SRC="$REPO_DIR/scripts/opencode-watchdog.timer"
SERVICE_DST="$HOME/.config/systemd/user/opencode-watchdog.service"
TIMER_DST="$HOME/.config/systemd/user/opencode-watchdog.timer"

ACTION="${1:-install}"

case "$ACTION" in
    install)
        mkdir -p "$HOME/.config/systemd/user"
        cp "$SERVICE_SRC" "$SERVICE_DST"
        cp "$TIMER_SRC" "$TIMER_DST"

        # Fix the ExecStart path in the service file
        sed -i "s|%h/projects|$HOME/projects|g" "$SERVICE_DST"
        sed -i "s|User=%i|User=$USER|" "$SERVICE_DST" 2>/dev/null || true
        sed -i "s|Group=%i|Group=$USER|" "$SERVICE_DST" 2>/dev/null || true

        systemctl --user daemon-reload
        systemctl --user enable opencode-watchdog.timer
        systemctl --user start opencode-watchdog.timer
        systemctl --user status opencode-watchdog.timer --no-pager
        echo "opencode watchdog installed and started."
        ;;
    remove)
        systemctl --user stop opencode-watchdog.timer 2>/dev/null || true
        systemctl --user disable opencode-watchdog.timer 2>/dev/null || true
        rm -f "$SERVICE_DST" "$TIMER_DST"
        systemctl --user daemon-reload
        echo "opencode watchdog removed."
        ;;
    status)
        echo "=== Timer ==="
        systemctl --user status opencode-watchdog.timer --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Service ==="
        systemctl --user status opencode-watchdog.service --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Last kills ==="
        cat "$HOME/.paperclip/opencode_watchdog_killed.log" 2>/dev/null || echo "(no kills recorded)"
        ;;
    *)
        echo "Usage: $0 [install|remove|status]"
        exit 1
        ;;
esac
