#!/usr/bin/env bash
# Install the Touch Index bug-close worker as a systemd --user timer.
#
# Polls Paperclip for done non-FDR issues closed in the last 30 minutes,
# extracts touched files from git/comments/description, and upserts to
# touch_index_bug_files.  Runs every 15 minutes with a 2-minute random delay.
#
# Usage:
#   bash scripts/setup_touch_index_bug_worker.sh          # install
#   bash scripts/setup_touch_index_bug_worker.sh --remove  # uninstall
#   bash scripts/setup_touch_index_bug_worker.sh --status  # check status

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$REPO_DIR/scripts/touch-index-bug-worker.service"
TIMER_SRC="$REPO_DIR/scripts/touch-index-bug-worker.timer"
SERVICE_DST="$HOME/.config/systemd/user/touch-index-bug-worker.service"
TIMER_DST="$HOME/.config/systemd/user/touch-index-bug-worker.timer"

ACTION="${1:-install}"

case "$ACTION" in
    install)
        mkdir -p "$HOME/.config/systemd/user"
        cp "$SERVICE_SRC" "$SERVICE_DST"
        cp "$TIMER_SRC" "$TIMER_DST"

        # Fix the ExecStart paths in the service file to use absolute home path
        sed -i "s|%h/projects|$HOME/projects|g" "$SERVICE_DST"

        systemctl --user daemon-reload
        systemctl --user enable touch-index-bug-worker.timer
        systemctl --user start touch-index-bug-worker.timer
        systemctl --user status touch-index-bug-worker.timer --no-pager
        echo "Touch Index bug-close worker installed and started."
        ;;
    remove)
        systemctl --user stop touch-index-bug-worker.timer 2>/dev/null || true
        systemctl --user disable touch-index-bug-worker.timer 2>/dev/null || true
        rm -f "$SERVICE_DST" "$TIMER_DST"
        systemctl --user daemon-reload
        echo "Touch Index bug-close worker removed."
        ;;
    status)
        echo "=== Timer ==="
        systemctl --user status touch-index-bug-worker.timer --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Service ==="
        systemctl --user status touch-index-bug-worker.service --no-pager 2>/dev/null || echo "Not installed"
        echo ""
        echo "=== Last 20 journal lines ==="
        journalctl --user -u touch-index-bug-worker.service --no-pager -n 20 2>/dev/null || echo "(no logs)"
        ;;
    *)
        echo "Usage: $0 [install|remove|status]"
        exit 1
        ;;
esac
