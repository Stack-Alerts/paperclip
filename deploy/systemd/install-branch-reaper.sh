#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${PAPERCLIP_DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/../.."
UNIT_DIR="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/.paperclip/instances/default/logs"
mkdir -p "${UNIT_DIR}"

SERVICE_SRC="${SCRIPT_DIR}/branch-reaper.service"
TIMER_SRC="${SCRIPT_DIR}/branch-reaper.timer"
REAPER_SCRIPT="${PROJECT_DIR}/scripts/branch-reaper.sh"

SERVICE_DST="${UNIT_DIR}/branch-reaper.service"
TIMER_DST="${UNIT_DIR}/branch-reaper.timer"

echo "=== Branch Reaper Daily Timer — Systemd Install ==="
echo "Source dir:  ${SCRIPT_DIR}"
echo "Target dir:  ${UNIT_DIR}"
echo "Dry run:     ${DRY_RUN}"
echo ""

if [ ! -f "${REAPER_SCRIPT}" ]; then
    echo "ERROR: Reaper script not found: ${REAPER_SCRIPT}"
    exit 1
fi
if [ ! -x "${REAPER_SCRIPT}" ]; then
    echo "Making reaper script executable..."
    chmod +x "${REAPER_SCRIPT}"
fi
echo "Reaper script: ${REAPER_SCRIPT}"

if [ ! -f "${SERVICE_SRC}" ]; then
    echo "ERROR: Service unit not found: ${SERVICE_SRC}"
    exit 1
fi
if [ ! -f "${TIMER_SRC}" ]; then
    echo "ERROR: Timer unit not found: ${TIMER_SRC}"
    exit 1
fi

# Best-effort: ensure log dir exists so StandardOutput=append: path is writable.
mkdir -p "${LOG_DIR}" || true

echo ""

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY RUN] Would copy:"
    echo "  ${SERVICE_SRC} -> ${SERVICE_DST}"
    echo "  ${TIMER_SRC}   -> ${TIMER_DST}"
    echo "[DRY RUN] Would run:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable branch-reaper.timer"
    echo "  systemctl --user start branch-reaper.timer"
else
    cp -v "${SERVICE_SRC}" "${SERVICE_DST}"
    cp -v "${TIMER_SRC}" "${TIMER_DST}"

    systemctl --user daemon-reload
    systemctl --user enable branch-reaper.timer
    systemctl --user start branch-reaper.timer

    echo ""
    echo "=== Timer status ==="
    systemctl --user status branch-reaper.timer --no-pager || true
    echo ""
    echo "=== Next trigger ==="
    systemctl --user list-timers branch-reaper.timer --no-pager || true
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
echo "  systemctl --user status branch-reaper.timer"
echo "  systemctl --user list-timers"
echo "  journalctl --user -u branch-reaper.service -n 50"
echo ""
echo "To dry-run the reaper now (no comments, no archive):"
echo "  ${REAPER_SCRIPT} --dry-run"
echo ""
echo "To run the reaper immediately (posts comments on open branches):"
echo "  ${REAPER_SCRIPT} --post-comment"
echo ""
echo "Logs:"
echo "  tail -f ${LOG_DIR}/branch-reaper.log"