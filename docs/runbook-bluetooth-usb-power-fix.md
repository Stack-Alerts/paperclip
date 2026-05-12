# Bluetooth USB Power Management Fix

## Issue

Bluetooth controller (`84:9E:56:9C:78:58`) on USB 3-5 (Wireless_Device) was failing to stay enabled because the USB device was allowed to auto-suspend (`power/control = auto`) and on older kernels would not recover properly after resume.

## Root Cause

`/sys/devices/pci0000:00/0000:00:08.3/0000:c8:00.0/usb3/3-5/power/control` was set to `auto` with a 2-second autosuspend delay. When the device suspended, the Bluetooth controller became unavailable. Kernel 6.17.0-22 and earlier did not reliably recover from this state. Kernel 6.17.0-23 appears to handle the resume correctly, but the safest fix is to prevent auto-suspend entirely.

## Fix: udev rule (persistent, declarative)

Create `/etc/udev/rules.d/99-bluetooth-power.rules` with:

```
# Prevent USB auto-suspend for Bluetooth/Wireless device
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0e8d", ATTRS{idProduct}=="0717", ATTR{power/control}="on"
```

Then reload udev and trigger:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger /sys/bus/usb/devices/3-5
```

## Hotfix (immediate, non-persistent)

If the rule cannot be installed immediately, run this after every boot:
```bash
sudo sh -c 'echo on > /sys/bus/usb/devices/3-5/power/control'
```

## Verification

```bash
cat /sys/bus/usb/devices/3-5/power/control
# Expected: on
cat /sys/bus/usb/devices/3-5/power/runtime_status
# Expected: active
bluetoothctl show
# Expected: "Powered: yes"
```

## Rollback

Delete the udev rule file and reload:
```bash
sudo rm /etc/udev/rules.d/99-bluetooth-power.rules
sudo udevadm control --reload-rules
```

## History

- 2026-05-11: Rebooted into kernel 6.17.0-23 (one-shot grub entry consumed). Bluetooth has been stable since.
- 2026-05-12: Phase 1 step 1a (set power/control to "on") not executed — blocked: sysfs file is root-owned, sudo requires interactive auth unavailable to agent.

## Current Status (2026-05-12)

| Check | Status |
|---|---|
| Bluetooth controller | `84:9E:56:9C:78:58` — Powered: yes |
| Kernel | 6.17.0-23-generic (contingency reboot consumed) |
| USB 3-5 power/control | `auto` (hotfix not applied — blocked on root) |
| USB 3-5 runtime_status | `active` |
| bluetooth service | `active (running)` |
| BT uptime | 1d 9h 44m — no crashes in journal |
| SESSION_START | Python 3.13.11, NautilusTrader 1.221.0, pip check: clean |

### Blocked Items

Phase 1 step 1a requires `sudo` with interactive auth, which the agent does not have. The sysfs file `/sys/bus/usb/devices/3-5/power/control` is root-owned (644). To unblock:
1. Either configure passwordless sudo for `sirrus` on this specific command, OR
2. Have a human with root install the udev rule from this doc, OR
3. Manually run: `sudo sh -c 'echo on > /sys/bus/usb/devices/3-5/power/control'`

### Assessment

The contingency reboot (kernel 6.17.0-23) appears to have resolved the original BT stability issue. The USB device suspends/resumes without BT controller loss, which was the failure mode on older kernels. The power/control hotfix is a hardening measure to prevent future occurrences.
