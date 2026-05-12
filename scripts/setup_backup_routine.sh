#!/usr/bin/env bash
# setup_backup_routine.sh
#
# Install the 4-hourly backup routine + dead-man's-switch as systemd --user
# timers.
#
# Usage:
#   bash scripts/setup_backup_routine.sh             # install
#   bash scripts/setup_backup_routine.sh --remove    # uninstall
#   bash scripts/setup_backup_routine.sh --status    # check status
#   bash scripts/setup_backup_routine.sh --dry-run   # test backup + deadman
#
# The dead-man's-switch checks every hour whether a backup was created within
# the last 5 hours (4h interval + 1h grace) and creates a Paperclip alert
# issue assigned to the CTO if not.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SERVICES=(
  "backup-routine.service:backup-routine.service:backup-routine.timer"
  "backup-deadman-switch.service:backup-deadman-switch.service:backup-deadman-switch.timer"
)

ACTION="${1:-install}"

install_units() {
  mkdir -p "$HOME/.config/systemd/user"

  for entry in "${SERVICES[@]}"; do
    IFS=":" read -r name svc timer <<< "$entry"
    cp "$REPO_DIR/scripts/$svc" "$HOME/.config/systemd/user/$svc"
    cp "$REPO_DIR/scripts/$timer" "$HOME/.config/systemd/user/$timer"

    # Fix the ExecStart path
    sed -i "s|%h/projects|$HOME/projects|g" "$HOME/.config/systemd/user/$svc"
  done

  systemctl --user daemon-reload
  systemctl --user enable backup-routine.timer
  systemctl --user start backup-routine.timer
  systemctl --user enable backup-deadman-switch.timer
  systemctl --user start backup-deadman-switch.timer

  echo ""
  echo "=== Backup Routine Timer ==="
  systemctl --user status backup-routine.timer --no-pager 2>/dev/null || true
  echo ""
  echo "=== Dead-Man's-Switch Timer ==="
  systemctl --user status backup-deadman-switch.timer --no-pager 2>/dev/null || true
  echo ""
  echo "Backup routine installed and started."
}

remove_units() {
  systemctl --user stop backup-routine.timer 2>/dev/null || true
  systemctl --user disable backup-routine.timer 2>/dev/null || true
  systemctl --user stop backup-deadman-switch.timer 2>/dev/null || true
  systemctl --user disable backup-deadman-switch.timer 2>/dev/null || true

  for entry in "${SERVICES[@]}"; do
    IFS=":" read -r name svc timer <<< "$entry"
    rm -f "$HOME/.config/systemd/user/$svc"
    rm -f "$HOME/.config/systemd/user/$timer"
  done

  systemctl --user daemon-reload
  echo "Backup routine removed."
}

check_status() {
  echo "=== Backup Routine Timer ==="
  systemctl --user status backup-routine.timer --no-pager 2>/dev/null || echo "Not installed"
  echo ""
  echo "=== Backup Routine Service (last run) ==="
  systemctl --user status backup-routine.service --no-pager 2>/dev/null || echo "Not installed"
  echo ""
  echo "=== Dead-Man's-Switch Timer ==="
  systemctl --user status backup-deadman-switch.timer --no-pager 2>/dev/null || echo "Not installed"
  echo ""
  echo "=== Dead-Man's-Switch Service (last run) ==="
  systemctl --user status backup-deadman-switch.service --no-pager 2>/dev/null || echo "Not installed"
  echo ""
  echo "=== Backup Routine Log (last 20 lines) ==="
  tail -20 "$HOME/.paperclip/backup_routine.log" 2>/dev/null || echo "(no log yet)"
  echo ""
  echo "=== Dead-Man's-Switch Log (last 20 lines) ==="
  tail -20 "$HOME/.paperclip/backup_deadman_switch.log" 2>/dev/null || echo "(no log yet)"
}

dry_run_test() {
  echo "=== Dry-run: Backup Routine ==="
  python3 "$REPO_DIR/scripts/run_backup_routine.py" --dry-run
  echo ""
  echo "=== Dry-run: Dead-Man's-Switch ==="
  python3 "$REPO_DIR/scripts/backup_deadman_switch.py" --dry-run
}

case "$ACTION" in
  install|--install)
    install_units
    ;;
  remove|--remove|uninstall|--uninstall)
    remove_units
    ;;
  status|--status)
    check_status
    ;;
  dry-run|--dry-run)
    dry_run_test
    ;;
  *)
    echo "Usage: $0 [install|remove|status|dry-run]"
    exit 1
    ;;
esac
