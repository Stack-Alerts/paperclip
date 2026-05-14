#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${PAPERCLIP_DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/../.."
UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "${UNIT_DIR}"

SERVICE_SRC="${SCRIPT_DIR}/tmp-cleanup.service"
TIMER_SRC="${SCRIPT_DIR}/tmp-cleanup.timer"
CLEANUP_SCRIPT="${PROJECT_DIR}/scripts/cleanup_tmp_artifacts.sh"

SERVICE_DST="${UNIT_DIR}/tmp-cleanup.service"
TIMER_DST="${UNIT_DIR}/tmp-cleanup.timer"

echo "=== TMP Cleanup Timer — Systemd Install ==="
echo "Source dir:  ${SCRIPT_DIR}"
echo "Target dir:  ${UNIT_DIR}"
echo "Dry run:     ${DRY_RUN}"
echo ""

if [ ! -f "${CLEANUP_SCRIPT}" ]; then
    echo "ERROR: Cleanup script not found: ${CLEANUP_SCRIPT}"
    exit 1
fi
if [ ! -x "${CLEANUP_SCRIPT}" ]; then
    echo "Making cleanup script executable..."
    chmod +x "${CLEANUP_SCRIPT}"
fi
echo "Cleanup script: ${CLEANUP_SCRIPT}"

if [ ! -f "${SERVICE_SRC}" ]; then
    echo "ERROR: Service unit not found: ${SERVICE_SRC}"
    exit 1
fi
if [ ! -f "${TIMER_SRC}" ]; then
    echo "ERROR: Timer unit not found: ${TIMER_SRC}"
    exit 1
fi

echo ""

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY RUN] Would copy:"
    echo "  ${SERVICE_SRC} -> ${SERVICE_DST}"
    echo "  ${TIMER_SRC}   -> ${TIMER_DST}"
    echo "[DRY RUN] Would run:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable tmp-cleanup.timer"
    echo "  systemctl --user start tmp-cleanup.timer"
else
    cp -v "${SERVICE_SRC}" "${SERVICE_DST}"
    cp -v "${TIMER_SRC}" "${TIMER_DST}"

    systemctl --user daemon-reload
    systemctl --user enable tmp-cleanup.timer
    systemctl --user start tmp-cleanup.timer

    echo ""
    echo "=== Timer status ==="
    systemctl --user status tmp-cleanup.timer --no-pager || true
    echo ""
    echo "=== Next trigger ==="
    systemctl --user list-timers tmp-cleanup.timer --no-pager || true
fi

echo ""
echo "=== Linger check ==="
LINGER=$(loginctl show-user "$USER" --property=Linger 2>/dev/null | cut -d= -f2 || echo "?")
if [ "$LINGER" = "yes" ]; then
    echo "  linger: enabled (timers run when logged out)"
else
    echo "  WARNING: linger is '$LINGER' — timers stop on logout"
    echo "  Fix: sudo loginctl enable-linger $USER"
fi

echo ""
echo "Install complete. To verify:"
echo "  systemctl --user status tmp-cleanup.timer"
echo "  systemctl --user list-timers"
echo "  journalctl --user -u tmp-cleanup.service -n 20"
echo ""
echo "To test cleanup immediately (dry run):"
echo "  DRY_RUN=true ${CLEANUP_SCRIPT}"
echo ""
echo "To run cleanup immediately:"
echo "  ${CLEANUP_SCRIPT}"
