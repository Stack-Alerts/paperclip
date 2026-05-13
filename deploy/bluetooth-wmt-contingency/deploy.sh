#!/bin/bash
# Deploy MediaTek WMT Bluetooth contingency
# Board-approved BTCAAAAA-1233
# Requires root (sudo)
set -euo pipefail

echo "=== Deploying Bluetooth WMT Contingency ==="

# 1. Install btusb module parameter (disable autosuspend)
install -m 644 btusb-wmt.conf /etc/modprobe.d/btusb-wmt.conf
echo "  [OK] btusb-wmt.conf installed"

# 2. Install systemd override (faster restart on crash)
mkdir -p /etc/systemd/system/bluetooth.service.d
install -m 644 wmt-contingency.conf /etc/systemd/system/bluetooth.service.d/wmt-contingency.conf
echo "  [OK] systemd override installed"

# 3. Reload systemd and restart bluetooth
systemctl daemon-reload
systemctl restart bluetooth
echo "  [OK] bluetooth restarted"

echo "=== Deployment Complete ==="
echo "Verify: systemctl status bluetooth"
