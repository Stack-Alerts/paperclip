#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${PAPERCLIP_DRY_RUN:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="itm-testnet-dry-run.service"
SERVICE_SRC="${SCRIPT_DIR}/${SERVICE_NAME}"
SERVICE_DST="${UNIT_DIR}/${SERVICE_NAME}"

echo "=== ITM Testnet Paper Trading — Systemd Install ==="
echo "Project:  ${PROJECT_ROOT}"
echo "Source:   ${SERVICE_SRC}"
echo "Target:   ${SERVICE_DST}"
echo "Dry run:  ${DRY_RUN}"
echo ""

# Validate service file exists
if [ ! -f "${SERVICE_SRC}" ]; then
    echo "ERROR: Service unit not found: ${SERVICE_SRC}"
    exit 1
fi

# Validate venv exists
if [ ! -f "${PROJECT_ROOT}/venv/bin/python" ]; then
    echo "ERROR: Virtual environment not found at ${PROJECT_ROOT}/venv"
    echo "Create it: python -m venv ${PROJECT_ROOT}/venv && ${PROJECT_ROOT}/venv/bin/pip install -r ${PROJECT_ROOT}/requirements.txt"
    exit 1
fi

# Validate .env exists
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo "WARNING: .env file not found at ${PROJECT_ROOT}/.env"
    echo "  Copy from .env.example and configure credentials."
fi

# Create logs directory
mkdir -p "${PROJECT_ROOT}/logs/dry_run"

# Unit directory
mkdir -p "${UNIT_DIR}"

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY RUN] Would copy: ${SERVICE_SRC} → ${SERVICE_DST}"
    echo "[DRY RUN] Would run:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable ${SERVICE_NAME}"
    echo "  systemctl --user start ${SERVICE_NAME}"
else
    cp -v "${SERVICE_SRC}" "${SERVICE_DST}"
    systemctl --user daemon-reload
    systemctl --user enable "${SERVICE_NAME}"
    systemctl --user start "${SERVICE_NAME}"

    echo ""
    echo "=== Service status ==="
    systemctl --user status "${SERVICE_NAME}" --no-pager || true
fi

echo ""
echo "=== Linger check ==="
LINGER=$(loginctl show-user "$USER" --property=Linger 2>/dev/null | cut -d= -f2 || echo "?")
if [ "$LINGER" = "yes" ]; then
    echo "  linger: enabled (service runs when logged out)"
else
    echo "  WARNING: linger is '$LINGER' — service stops on logout"
    echo "  Fix: sudo loginctl enable-linger $USER"
fi

echo ""
echo "Install complete. To manage the service:"
echo "  systemctl --user status ${SERVICE_NAME}"
echo "  systemctl --user stop    ${SERVICE_NAME}"
echo "  systemctl --user start   ${SERVICE_NAME}"
echo "  journalctl --user -u ${SERVICE_NAME} -n 50 -f"
echo ""
echo "To switch to live testnet mode (requires testnet credentials):"
echo "  1. Edit UNIT_FILE: systemctl --user edit ${SERVICE_NAME}"
echo "  2. Add: Environment=ITM_PAPER_TRADING=false"
echo "  3. Restart: systemctl --user restart ${SERVICE_NAME}"
