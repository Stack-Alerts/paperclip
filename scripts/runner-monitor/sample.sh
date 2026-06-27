#!/usr/bin/env bash
# sample.sh — BTC-38522 24h host-monitor sample collector
# Captures the 4 metrics from BTC-38522 spec; writes a per-sample record
# and a one-line verdict. Designed to be invoked by sample_loop.sh.
#
# Trigger thresholds (from BTC-38519 CTO assessment):
#   1. Available RAM < 4 GB sustained > 5 min          -> FAIL_RAM
#   2. Disk await > 50 ms sustained > 5 min            -> FAIL_DISK
#   3. Load average > 2x core count sustained > 5 min   -> FAIL_LOAD
#   4. Any runner Offline / NotRegistered in 2 samples  -> FAIL_RUNNER
#
# A single failing sample does NOT fire a trigger (per "sustained > 5 min"
# wording) — the aggregator script sample_summarize.sh tracks consecutive
# violations and only fires when 2+ consecutive samples violate the same
# condition.

set -u
SAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)/samples"
mkdir -p "$SAMPLE_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT="$SAMPLE_DIR/${TS}.json"

# --- Metric 1: free RAM (MB available) ---
AVAIL_MB="$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)"
TOTAL_MB="$(awk '/^MemTotal:/ {print int($2/1024)}' /proc/meminfo)"

# --- Metric 2: disk IO + await (1s iostat sample, primary device = nvme0n1) ---
# iostat -dx nvme0n1 1 2 emits 2 reports: first = avg since boot, second = avg
# over the 1-second sampling window. We want the second (recent interval).
IOSTAT="$(iostat -dx nvme0n1 1 2 2>/dev/null | awk '$1=="nvme0n1"' | sed -n '2p')"
if [ -z "$IOSTAT" ]; then
    # fall back: take the last nvme line
    IOSTAT="$(iostat -dx 1 2 2>/dev/null | awk '$1 ~ /^nvme/' | tail -1)"
fi
# iostat -dx nvme0n1 1 2 column layout on this host (verified 2026-06-25):
#   $1=Device $2=r/s $3=rkB/s $4=rrqm/s $5=%rrqm $6=r_await $7=rareq-sz
#   $8=w/s $9=wkB/s $10=wrqm/s $11=%wrqm $12=w_await $13=wareq-sz ...
# Earlier script read $7 for WKB_S (rareq-sz) and $11 for W_AWAIT_MS (%wrqm);
# both were positional mismatches that produced false-positive FAIL_DISK verdicts
# whenever %wrqm exceeded 50%. Fixed to $9 (wkB/s) and $12 (w_await).
RKB_S="$(echo "$IOSTAT" | awk '{print $3}')"
WKB_S="$(echo "$IOSTAT" | awk '{print $9}')"
R_AWAIT_MS="$(echo "$IOSTAT" | awk '{print $6 * 1.0}')"
W_AWAIT_MS="$(echo "$IOSTAT" | awk '{print $12 * 1.0}')"
R_AWAIT_MS="$(awk -v v="$R_AWAIT_MS" 'BEGIN { printf("%.2f", v) }')"
W_AWAIT_MS="$(awk -v v="$W_AWAIT_MS" 'BEGIN { printf("%.2f", v) }')"
MAX_AWAIT_MS="$(awk -v a="$R_AWAIT_MS" -v b="$W_AWAIT_MS" 'BEGIN { printf("%.2f", (a>b?a:b)) }')"

# --- Metric 3: load average (1m/5m/15m) and core count ---
LOAD1="$(awk '{print $1}' /proc/loadavg)"
LOAD5="$(awk '{print $2}' /proc/loadavg)"
LOAD15="$(awk '{print $3}' /proc/loadavg)"
CORES="$(nproc)"
LOAD_LIMIT="$(awk -v c="$CORES" 'BEGIN { printf("%.2f", c*2) }')"

# --- Metric 4: GitHub self-hosted runner status ---
if command -v gh >/dev/null 2>&1; then
    RUNNERS_JSON="$(gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/runners --jq '.runners[] | "\(.name)\t\(.status)\t\(.busy)"' 2>/dev/null || echo "GH_API_ERROR")"
else
    RUNNERS_JSON="GH_NOT_INSTALLED"
fi
RUNNER_ONLINE_COUNT="$(printf '%s\n' "$RUNNERS_JSON" | awk -F'\t' '$2=="online"' | wc -l)"
RUNNER_TOTAL_COUNT="$(printf '%s\n' "$RUNNERS_JSON" | awk -F'\t' '$2!="GH_API_ERROR" && $2!="GH_NOT_INSTALLED"' | wc -l)"
RUNNER_OFFLINE="$(printf '%s\n' "$RUNNERS_JSON" | awk -F'\t' '$2!="online" && $2!="GH_API_ERROR" && $2!="GH_NOT_INSTALLED" {print $1":"$2}' | paste -sd, -)"

# --- Single-sample verdict (per-condition; sustained check happens in aggregator) ---
VERDICT="GREEN"
if [ "${AVAIL_MB:-0}" -lt 4096 ]; then
    VERDICT="FAIL_RAM"
fi
if awk -v v="$MAX_AWAIT_MS" 'BEGIN { exit !(v > 50) }'; then
    VERDICT="FAIL_DISK"
fi
if awk -v l="$LOAD1" -v lim="$LOAD_LIMIT" 'BEGIN { exit !(l > lim) }'; then
    if [ "$VERDICT" = "GREEN" ]; then
        VERDICT="FAIL_LOAD"
    fi
fi

# --- Write JSON record ---
cat > "$OUT" <<JSON
{
  "ts": "$ISO",
  "metrics": {
    "ram": {"available_mb": $AVAIL_MB, "total_mb": $TOTAL_MB},
    "disk": {"r_kb_s": $RKB_S, "w_kb_s": $WKB_S, "r_await_ms": $R_AWAIT_MS, "w_await_ms": $W_AWAIT_MS, "max_await_ms": $MAX_AWAIT_MS, "device": "nvme0n1"},
    "load": {"load1": $LOAD1, "load5": $LOAD5, "load15": $LOAD15, "cores": $CORES, "limit_2x": $LOAD_LIMIT},
    "runners": {"online": $RUNNER_ONLINE_COUNT, "total": $RUNNER_TOTAL_COUNT, "offline": "$RUNNER_OFFLINE"}
  },
  "verdict": "$VERDICT"
}
JSON

# --- Append one-line summary to NDJSON for easy tail/aggregation ---
printf '{"ts":"%s","avail_mb":%s,"max_await_ms":%s,"load1":%s,"runner_online":%s,"runner_total":%s,"verdict":"%s"}\n' \
    "$ISO" "$AVAIL_MB" "$MAX_AWAIT_MS" "$LOAD1" "$RUNNER_ONLINE_COUNT" "$RUNNER_TOTAL_COUNT" "$VERDICT" \
    >> "$SAMPLE_DIR/../stream.ndjson"

# --- Print one-line verdict for stdout (loop log) ---
echo "[$ISO] avail_mb=$AVAIL_MB await_ms=$MAX_AWAIT_MS load1=$LOAD1 runners=$RUNNER_ONLINE_COUNT/$RUNNER_TOTAL_COUNT verdict=$VERDICT"