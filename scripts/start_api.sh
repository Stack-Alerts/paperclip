#!/bin/bash
# Start the BTC Trade Engine FastAPI backend (port 8765)
# Loads .env so Postgres credentials are available to the strategy builder DB.
#
# Usage:  ./scripts/start_api.sh
#
# The frontend is started separately:
#   cd packages/web-ui && npm run dev

set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ERROR: .env not found in project root. Copy .env.example and fill in your credentials."
  exit 1
fi

# Export every valid VAR=value line from .env.
# Using `source .env` with `set -a` fails when .env contains bare values
# (e.g. floats, JSON fragments) that aren't valid shell assignments.
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip blank lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue
  # Only export lines that start with a valid shell identifier followed by =
  [[ "$line" =~ ^[A-Za-z_][A-Za-z_0-9]*= ]] || continue
  export "$line"
done < .env

echo "Starting BTE API server on http://localhost:${BTE_API_PORT:-8765}"
echo "Database: ${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-optimizer_v3}"
if [ "${BTE_API_DEV_MODE:-}" = "1" ]; then
  echo "WARNING: BTE_API_DEV_MODE=1 — JWT auth is DISABLED (dev only)"
fi
echo ""

exec uvicorn src.api.app:app \
  --host "${BTE_API_HOST:-0.0.0.0}" \
  --port "${BTE_API_PORT:-8765}" \
  --reload \
  --log-level info
