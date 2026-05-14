#!/bin/bash
set -euo pipefail


# --- Load rclone encryption password (if config is encrypted) ---
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
source "${SCRIPT_DIR}/_rclone_pass.sh"
RCLONE_CONFIG="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"

echo "=========================================="
echo "  Paperclip Backup Pipeline Health Check"
echo "=========================================="
echo ""

FAILS=0
ok()  { echo "  [OK]    $1"; }
warn(){ echo "  [WARN]  $1"; ((FAILS++)) || true; }
fail(){ echo "  [FAIL]  $1"; ((FAILS++)) || true; }

# 1. rclone auth
echo "--- rclone ---"
if command -v rclone &>/dev/null; then
    ok "rclone installed ($(rclone version 2>/dev/null | head -1))"
    if rclone lsd gdrive:Paperclip-Backups --config "$RCLONE_CONFIG" &>/dev/null; then
        ok "gdrive remote authenticated"
    else
        fail "gdrive remote NOT authenticated (empty/missing/expired token)"
        echo "       Fix: ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token"
    fi
else
    fail "rclone not installed"
fi
echo ""

# 2. Paperclip DB backup freshness
echo "--- Database Dumps ---"
BACKUPS_DIR="$HOME/.paperclip/instances/default/data/backups"
if [ -d "$BACKUPS_DIR" ]; then
    COUNT=$(ls -1 "$BACKUPS_DIR"/paperclip-*.sql.gz 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        ok "$COUNT dumps found"
        FRESHEST=$(ls -1t "$BACKUPS_DIR"/paperclip-*.sql.gz 2>/dev/null | head -1)
        AGE_MIN=$(( ($(date +%s) - $(stat -c %Y "$FRESHEST")) / 60 ))
        if [ "$AGE_MIN" -lt 90 ]; then
            ok "freshest dump: $(basename "$FRESHEST") (${AGE_MIN}m ago)"
        elif [ "$AGE_MIN" -lt 180 ]; then
            warn "freshest dump: $(basename "$FRESHEST") (${AGE_MIN}m ago)"
        else
            fail "freshest dump: $(basename "$FRESHEST") (${AGE_MIN}m ago — over 3h)"
        fi
    else
        fail "no database dumps found in $BACKUPS_DIR"
    fi
else
    fail "backups directory missing: $BACKUPS_DIR"
fi
echo ""

# 3. Last offsite backup
echo "--- Offsite Backup Liveness ---"
STATE_FILE="$HOME/.paperclip/instances/default/backup-state/last-success.json"
if [ -f "$STATE_FILE" ]; then
    LAST=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('lastSuccess','unknown'))" 2>/dev/null || echo "parse-error")
    if [ "$LAST" != "parse-error" ] && [ "$LAST" != "unknown" ]; then
        AGE_H=$(python3 -c "
import json
from datetime import datetime, timezone
d = json.load(open('$STATE_FILE'))
ts = datetime.fromisoformat(d['lastSuccess'].replace('Z','+00:00'))
age = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds()/3600
print(f'{age:.1f}')
" 2>/dev/null || echo "?")
        DEST=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('destination','unknown'))" 2>/dev/null || echo "?")
        if [ "${AGE_H:-0}" = "?" ]; then
            warn "last success: $LAST (age unknown)"
        elif (( $(echo "$AGE_H > 12" | bc -l 2>/dev/null || echo 0) )); then
            fail "last offsite backup: ${AGE_H}h ago (threshold: 12h)"
            echo "       Destination: $DEST"
        elif (( $(echo "$AGE_H > 6" | bc -l 2>/dev/null || echo 0) )); then
            warn "last offsite backup: ${AGE_H}h ago"
            echo "       Destination: $DEST"
        else
            ok "last offsite backup: ${AGE_H}h ago"
            echo "       Destination: $DEST"
        fi
    else
        warn "cannot parse last-success.json timestamp"
    fi
else
    fail "no last-success.json — offsite backup has never run"
fi
echo ""

# 4. systemd timer
echo "--- systemd Timer ---"
if systemctl --user is-active paperclip-backup.timer &>/dev/null; then
    ok "paperclip-backup.timer is active"
    NEXT=$(systemctl --user list-timers paperclip-backup.timer --no-legend 2>/dev/null | awk '{print $1, $2, $3}' || echo "?")
    echo "       Next trigger: $NEXT"
else
    fail "paperclip-backup.timer is not active"
    echo "       Fix: systemctl --user enable --now paperclip-backup.timer"
fi

LINGER=$(loginctl show-user "$USER" --property=Linger 2>/dev/null | cut -d= -f2 || echo "?")
if [ "$LINGER" = "yes" ]; then
    ok "user linger enabled (timers run when logged out)"
else
    warn "user linger is '$LINGER' — timers stop on logout"
    echo "       Fix: sudo loginctl enable-linger $USER"
fi
echo ""

# 5. Dead-man switch
echo "--- Dead-Man Switch ---"
DEADMAN_STATE="$HOME/.paperclip/backup_deadman_switch_state.json"
if [ -f "$DEADMAN_STATE" ]; then
    RUNS=$(python3 -c "import json; print(json.load(open('$DEADMAN_STATE')).get('total_runs',0))" 2>/dev/null || echo "?")
    ok "dead-man switch: $RUNS runs"
else
    warn "dead-man switch state file missing (has never run?)"
fi

MONITOR_STATE="$HOME/.paperclip/deadman_switch_monitor_state.json"
if [ -f "$MONITOR_STATE" ]; then
    MON_RUNS=$(python3 -c "import json; print(json.load(open('$MONITOR_STATE')).get('total_runs',0))" 2>/dev/null || echo "?")
    ok "dead-man switch monitor (GH Actions): $MON_RUNS runs"
else
    warn "dead-man switch monitor (GH Actions) state missing"
fi

LOCAL_MONITOR_STATE="$HOME/.paperclip/deadman_switch_local_monitor_state.json"
if [ -f "$LOCAL_MONITOR_STATE" ]; then
    LOCAL_RUNS=$(python3 -c "import json; print(json.load(open('$LOCAL_MONITOR_STATE')).get('total_runs',0))" 2>/dev/null || echo "?")
    ok "dead-man switch monitor (local): $LOCAL_RUNS runs"
else
    warn "dead-man switch local monitor state missing (timer may not be enabled)"
fi
echo ""

# 6. Google Drive destination
echo "--- Google Drive ---"
if rclone lsd gdrive:Paperclip-Backups --config "$RCLONE_CONFIG" &>/dev/null; then
    DIR_COUNT=$(rclone lsd gdrive:Paperclip-Backups --config "$RCLONE_CONFIG" 2>/dev/null | wc -l)
    ok "gdrive:Paperclip-Backups accessible ($DIR_COUNT entries)"
else
    fail "gdrive:Paperclip-Backups NOT accessible"
fi
echo ""

echo "=========================================="
echo "  Summary: $FAILS issue(s) found"
echo "=========================================="
if [ "$FAILS" -gt 0 ]; then
    echo ""
    echo "Quick fixes:"
    echo "  rclone auth:  ~/.paperclip/scripts/rclone-headless-auth.sh --apply-token"
    echo "  manual backup: ~/.paperclip/scripts/backup-to-drive.sh"
    echo "  timer status:  systemctl --user status paperclip-backup.timer"
    echo "  full runbook:  docs/runbook-backup-restore.md"
fi
