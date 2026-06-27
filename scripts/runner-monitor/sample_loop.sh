#!/usr/bin/env bash
# sample_loop.sh — BTC-38522 24h sampler loop
# Runs sample.sh every INTERVAL_SEC for DURATION_SEC in the background.
# Writes a PID file for clean shutdown. Logs each sample to loop.log.

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SAMPLE="$SCRIPT_DIR/sample.sh"
LOG="$SCRIPT_DIR/loop.log"
PIDFILE="$SCRIPT_DIR/loop.pid"
STOPFILE="$SCRIPT_DIR/loop.stop"

INTERVAL_SEC="${INTERVAL_SEC:-900}"   # 15 minutes
DURATION_SEC="${DURATION_SEC:-86400}" # 24 hours

if [ ! -x "$SAMPLE" ]; then
    chmod +x "$SAMPLE" || true
fi

echo "$$" > "$PIDFILE"

trap 'rm -f "$PIDFILE"; exit 0' EXIT INT TERM

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sample_loop starting (interval=${INTERVAL_SEC}s duration=${DURATION_SEC}s pid=$$)" >> "$LOG"

END_AT=$(( $(date +%s) + DURATION_SEC ))

while true; do
    NOW="$(date +%s)"
    if [ "$NOW" -ge "$END_AT" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sample_loop reached duration (${DURATION_SEC}s), exiting" >> "$LOG"
        break
    fi
    if [ -f "$STOPFILE" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sample_loop stopfile detected, exiting" >> "$LOG"
        rm -f "$STOPFILE"
        break
    fi
    "$SAMPLE" >> "$LOG" 2>&1 || echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sample.sh FAILED (exit=$?)" >> "$LOG"
    sleep "$INTERVAL_SEC"
done