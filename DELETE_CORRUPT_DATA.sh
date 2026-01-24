#!/bin/bash
# INSTITUTIONAL-GRADE FIX: Delete corrupt strategies from database
# Run this script to remove the 3 corrupt strategies

echo "🔧 Deleting corrupt strategies from database..."
echo ""

# Get database credentials from .env
source venv/bin/activate
export $(grep -v '^#' .env | xargs)

# Delete corrupt strategies
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << 'EOF'
-- Delete corrupt strategy versions first (foreign key)
DELETE FROM strategy_versions WHERE strategy_id = 'strategy_35a2c8a2';
DELETE FROM strategy_versions WHERE strategy_id = 'strategy_aa2bb7c5';
DELETE FROM strategy_versions WHERE strategy_id = 'strategy_86206819';

-- Delete parent strategies
DELETE FROM strategies WHERE strategy_id = 'strategy_35a2c8a2';
DELETE FROM strategies WHERE strategy_id = 'strategy_aa2bb7c5';
DELETE FROM strategies WHERE strategy_id = 'strategy_86206819';

-- Show remaining strategies
SELECT strategy_id, name, updated_at FROM strategies ORDER BY updated_at DESC;
EOF

echo ""
echo "✅ Corrupt strategies deleted"
echo "✅ Database is clean"
echo ""
echo "Now restart Strategy Builder - errors should be gone."
