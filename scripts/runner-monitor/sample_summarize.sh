#!/usr/bin/env bash
# sample_summarize.sh — BTC-38522 24h aggregate verifier
# Reads stream.ndjson, counts samples, finds min/max for each metric,
# detects sustained trigger violations (2+ consecutive samples failing
# the same condition).

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NDJSON="$SCRIPT_DIR/stream.ndjson"

if [ ! -f "$NDJSON" ]; then
    echo "no stream.ndjson found; no samples yet" >&2
    exit 1
fi

TOTAL="$(wc -l < "$NDJSON")"
echo "=== Sample count: $TOTAL ==="

echo ""
echo "=== Min/Max per metric ==="
python3 - "$NDJSON" <<'PY'
import json, sys
path = sys.argv[1]
avail, await_, load1 = [], [], []
verdicts = {}
with open(path) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        avail.append(r.get("avail_mb", 0))
        await_.append(r.get("max_await_ms", 0.0))
        load1.append(r.get("load1", 0.0))
        v = r.get("verdict", "?")
        verdicts[v] = verdicts.get(v, 0) + 1

def stats(name, vals, fmt="{:.2f}"):
    if not vals: return
    print(f"{name}: min={fmt.format(min(vals))} max={fmt.format(max(vals))} avg={fmt.format(sum(vals)/len(vals))}")

stats("avail_mb", avail, "{:d}")
stats("max_await_ms", await_)
stats("load1", load1)
print("verdict_counts:", verdicts)
PY

echo ""
echo "=== Sustained violation scan (2+ consecutive) ==="
python3 - "$NDJSON" <<'PY'
import json, sys
path = sys.argv[1]
prev = None
streak = 0
sustained = []
last_r = None
with open(path) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        last_r = r
        v = r.get("verdict", "GREEN")
        if v != "GREEN" and v == prev:
            streak += 1
        else:
            if streak >= 2 and prev and prev != "GREEN":
                sustained.append((r.get("ts"), prev, streak))
            streak = 1 if v != "GREEN" else 0
        prev = v
    if streak >= 2 and prev and prev != "GREEN" and last_r:
        sustained.append((last_r.get("ts"), prev, streak))

if sustained:
    for ts, kind, n in sustained:
        print(f"  {ts} :: {kind} for {n} consecutive samples")
else:
    print("  none")
PY

echo ""
echo "=== Window ==="
FIRST_TS="$(head -n1 "$NDJSON" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("ts","?"))')"
LAST_TS="$(tail -n1 "$NDJSON" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("ts","?"))')"
echo "first: $FIRST_TS"
echo "last:  $LAST_TS"