#!/usr/bin/env bash
# Install the provider usage monitor as a systemd --user timer.
#
# Usage:
#   bash scripts/setup_provider_monitor.sh          # install
#   bash scripts/setup_provider_monitor.sh --remove # uninstall
#   bash scripts/setup_provider_monitor.sh --status # check status

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$REPO_DIR/scripts/provider-monitor.service"
TIMER_SRC="$REPO_DIR/scripts/provider-monitor.timer"
SERVICE_DST="$HOME/.config/systemd/user/provider-monitor.service"
TIMER_DST="$HOME/.config/systemd/user/provider-monitor.timer"

ACTION="${1:-install}"

case "$ACTION" in
    install)
        mkdir -p "$HOME/.config/systemd/user"
        cp "$SERVICE_SRC" "$SERVICE_DST"
        cp "$TIMER_SRC" "$TIMER_DST"

        sed -i "s|%h/projects|$HOME/projects|g" "$SERVICE_DST"

        systemctl --user daemon-reload
        systemctl --user enable provider-monitor.timer
        systemctl --user start provider-monitor.timer
        systemctl --user status provider-monitor.timer --no-pager
        echo "Provider monitor installed and started."
        ;;
    remove)
        systemctl --user stop provider-monitor.timer 2>/dev/null || true
        systemctl --user disable provider-monitor.timer 2>/dev/null || true
        rm -f "$SERVICE_DST" "$TIMER_DST"
        systemctl --user daemon-reload
        echo "Provider monitor removed."
        ;;
    status)
        echo "=== Timer ==="
        systemctl --user status provider-monitor.timer --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Service ==="
        systemctl --user status provider-monitor.service --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Recent log ==="
        journalctl --user -u provider-monitor.service -n 20 --no-pager 2>/dev/null || echo "(no logs)"
        echo ""
        echo "=== State file ==="
        cat "$HOME/.paperclip/provider_monitor_state.json" 2>/dev/null || echo "(no state file)"
        ;;
    *)
        echo "Usage: $0 [install|remove|status]"
        exit 1
        ;;
esac
