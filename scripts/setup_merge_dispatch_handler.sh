#!/usr/bin/env bash
# Install and enable the merge-dispatch execution handler as a user systemd service.
#
# This creates a systemd timer that runs the handler every 5 minutes,
# completely independent of the Paperclip agent's availability (no Claude rate-limit dependency).
#
# Usage:
#   bash scripts/setup_merge_dispatch_handler.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=== Merge-Dispatch Execution Handler Setup ==="
echo "Script dir: $SCRIPT_DIR"
echo "Systemd user dir: $SYSTEMD_USER_DIR"

# Ensure systemd user directory exists
mkdir -p "$SYSTEMD_USER_DIR"

# Link service and timer into systemd user directory
echo "Linking systemd units..."
ln -sf "$SCRIPT_DIR/merge-dispatch-handler.service" "$SYSTEMD_USER_DIR/merge-dispatch-handler.service"
ln -sf "$SCRIPT_DIR/merge-dispatch-handler.timer" "$SYSTEMD_USER_DIR/merge-dispatch-handler.timer"

# Verify venv has required packages
VENV_PYTHON="$HOME/projects/BTC-Trade-Engine-PaperClip/venv/bin/python"
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "WARNING: venv python not found at $VENV_PYTHON"
    echo "Run: cd ~/projects/BTC-Trade-Engine-PaperClip && python -m venv venv && pip install -r requirements.txt"
else
    echo "Verifying venv has required packages..."
    "$VENV_PYTHON" -c "import requests, dotenv" 2>/dev/null && echo "OK: requests, dotenv available" || \
        echo "WARNING: missing packages — run: pip install requests python-dotenv"
fi

# Reload systemd and enable
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

echo "Enabling and starting timer..."
systemctl --user enable --now merge-dispatch-handler.timer

echo ""
echo "=== Setup Complete ==="
echo "Timer status:"
systemctl --user status merge-dispatch-handler.timer --no-pager || true
echo ""
echo "Next run:"
systemctl --user list-timers merge-dispatch-handler.timer --no-pager 2>/dev/null || true
echo ""
echo "To check logs: journalctl --user -u merge-dispatch-handler.service -n 50"
echo "To run manually: python3 $SCRIPT_DIR/merge_dispatch_execution_handler.py"
echo "To dry-run: python3 $SCRIPT_DIR/merge_dispatch_execution_handler.py --dry-run"
