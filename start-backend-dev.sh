#!/usr/bin/env bash
# start-backend-dev.sh — run the FastAPI backend (uvicorn) with --reload
#
# Behavior:
#   1. Activate venv
#   2. Kill any existing uvicorn on :8765
#   3. Start uvicorn in dev mode: --reload watches `src/` and restarts on
#      any *.py change. --reload-include "*.py" skips non-Python noise
#      (CSVs, JSONs, .db).
#   4. Detach (background) so the calling shell can return.
#   5. Poll /health until HTTP 200
#
# Usage:
#   ./start-backend-dev.sh                # Start, then exit
#   ./start-backend-dev.sh --foreground   # Block in foreground
#
# Pair with restart-backend.sh for the production-style restart; this is
# for the dev loop where you want hot reload.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

VENV_PY="${REPO_ROOT}/venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="python"

PORT=8765
HEALTH_URL="http://127.0.0.1:${PORT}/health"

# ─── Stop any existing uvicorn on the port ──────────────────────────
PID=$(ss -tlnpH 2>/dev/null | awk -v p=":${PORT} " '$0 ~ p { match($0, /pid=([0-9]+)/, m); print m[1]; exit }')
if [ -n "$PID" ]; then
  echo "[backend-dev] stopping existing uvicorn PID=$PID on :$PORT"
  kill -TERM "$PID" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    sleep 1
    ss -tln 2>/dev/null | awk -v p=":${PORT} " '$0 ~ p { found=1; exit } END { exit !found }' && break
  done
fi

LOG="${REPO_ROOT}/logs/backend-dev.log"
mkdir -p "$(dirname "$LOG")"

if [[ "${1:-}" == "--foreground" ]]; then
  exec "$VENV_PY" -m uvicorn src.api.app:app \
    --host 127.0.0.1 --port "$PORT" \
    --reload \
    --reload-dir src \
    --reload-include "*.py"
fi

# ─── Background mode ────────────────────────────────────────────────
nohup "$VENV_PY" -m uvicorn src.api.app:app \
  --host 127.0.0.1 --port "$PORT" \
  --reload \
  --reload-dir src \
  --reload-include "*.py" \
  >"$LOG" 2>&1 &
PID=$!
echo "[backend-dev] started uvicorn PID=$PID on :$PORT with --reload (log: $LOG)"

# ─── Wait for /health ───────────────────────────────────────────────
for _ in $(seq 1 30); do
  if curl -sf -o /dev/null --max-time 1 "$HEALTH_URL"; then
    echo "[backend-dev] ✓ $HEALTH_URL ready"
    exit 0
  fi
  sleep 1
done

echo "[backend-dev] ✗ $HEALTH_URL not ready after 30s; check $LOG" >&2
exit 1
