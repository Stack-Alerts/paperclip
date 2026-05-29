#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${PAPERCLIP_DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "${UNIT_DIR}"

SERVICE_SRC="${SCRIPT_DIR}/btc-dev-server.service"
WRAPPER_SRC="${SCRIPT_DIR}/btc-dev-server-wrapper.sh"

SERVICE_DST="${UNIT_DIR}/btc-dev-server.service"
WRAPPER_DST="${UNIT_DIR}/btc-dev-server-wrapper.sh"

echo "=== BTC Trading Engine Dev Server — Systemd Install ==="
echo "Source:  ${SCRIPT_DIR}"
echo "Target:  ${UNIT_DIR}"
echo "Dry run: ${DRY_RUN}"
echo ""

if [ ! -f "${SERVICE_SRC}" ]; then
    echo "ERROR: Service unit not found: ${SERVICE_SRC}"
    exit 1
fi
if [ ! -f "${WRAPPER_SRC}" ]; then
    echo "ERROR: Wrapper script not found: ${WRAPPER_SRC}"
    exit 1
fi

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY RUN] Would copy:"
    echo "  ${SERVICE_SRC} → ${SERVICE_DST}"
    echo "  ${WRAPPER_SRC} → ${WRAPPER_DST}"
    echo "[DRY RUN] Would run:"
    echo "  chmod +x ${WRAPPER_DST}"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable btc-dev-server.service"
else
    cp -v "${SERVICE_SRC}" "${SERVICE_DST}"
    cp -v "${WRAPPER_SRC}" "${WRAPPER_DST}"
    chmod +x "${WRAPPER_DST}"

    systemctl --user daemon-reload
    systemctl --user enable btc-dev-server.service

    echo ""
    echo "=== Service status ==="
    systemctl --user status btc-dev-server.service --no-pager || true
fi

echo ""
echo "Install complete. To start the dev server:"
echo "  ./start-dev.sh"
echo ""
echo "To verify the service:"
echo "  systemctl --user status btc-dev-server.service"
echo "  journalctl --user -fu btc-dev-server.service"
