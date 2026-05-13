#!/usr/bin/env bash
set -euo pipefail

# Provision optimizer_v3_drill_test database on system PostgreSQL (port 5432)
# Requires: sudo -u postgres access (run as root or postgres user)
# Intended use: sudo -u postgres bash scripts/provision_drill_db.sh

echo "=== Creating optimizer_v3_drill_test database ==="
psql -c "CREATE DATABASE optimizer_v3_drill_test OWNER optimizer_admin;"

echo "=== Granting schema permissions (PG 15+ compat) ==="
psql -d optimizer_v3_drill_test -c "GRANT USAGE, CREATE ON SCHEMA public TO optimizer_admin;"

echo "=== Verifying ==="
psql -c "\l+ optimizer_v3_drill_test"

echo ""
echo "✅ Done. optimizer_v3_drill_test is ready."
echo "Connect: PGPASSWORD='<password>' psql -h localhost -U optimizer_admin -d optimizer_v3_drill_test"
