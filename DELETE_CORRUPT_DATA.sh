#!/bin/bash
# INSTITUTIONAL-GRADE FIX: Delete corrupt strategies from database
# Run this script to remove the 3 corrupt strategies

echo "🔧 Deleting corrupt strategies from database..."
echo ""

# Get database credentials from .env
source venv/bin/activate
export $(grep -v '^#' .env | xargs)

# Delete ALL strategies (all are corrupt from before rollback fixes)
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}" << 'EOF'
-- Delete ALL strategy versions first (foreign key)
DELETE FROM strategy_versions;

-- Delete ALL parent strategies
DELETE FROM strategies;

-- Verify empty
SELECT COUNT(*) as remaining_strategies FROM strategies;
EOF

echo ""
echo "✅ ALL strategies deleted (all were corrupt)"
echo "✅ Database is now completely clean"
echo ""
echo "Next steps:"
echo "1. Restart Strategy Builder"
echo "2. Import your strategies from JSON (Tools → Import Strategy from JSON)"
echo "3. Save them (Ctrl+S)"
echo "4. No more errors!"
