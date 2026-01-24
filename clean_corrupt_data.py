#!/usr/bin/env python3
"""
INSTITUTIONAL-GRADE FIX: Clean corrupt strategy data

These 3 strategies have corrupt data causing InFailedSqlTransaction errors.
Delete them so they can be re-imported fresh.
"""

from src.optimizer_v3.database import get_database_manager
from sqlalchemy import text

def clean_corrupt_strategies():
    """Remove corrupt strategies from database"""
    
    corrupt_strategy_ids = [
        'strategy_35a2c8a2',
        'strategy_aa2bb7c5',
        'strategy_86206819'
    ]
    
    print("🔧 INSTITUTIONAL-GRADE DATABASE CLEANUP")
    print("=" * 60)
    print(f"Removing {len(corrupt_strategy_ids)} corrupt strategies...")
    print()
    
    db = get_database_manager()
    
    for strategy_id in corrupt_strategy_ids:
        try:
            # Delete versions first (foreign key)
            query = text("DELETE FROM strategy_versions WHERE strategy_id = :strategy_id")
            result = db.strategy.session.execute(query, {'strategy_id': strategy_id})
            versions_deleted = result.rowcount
            
            # Delete parent strategy
            query = text("DELETE FROM strategies WHERE strategy_id = :strategy_id")
            result = db.strategy.session.execute(query, {'strategy_id': strategy_id})
            strategies_deleted = result.rowcount
            
            db.strategy.session.commit()
            
            print(f"✅ Deleted {strategy_id}")
            print(f"   - Versions deleted: {versions_deleted}")
            print(f"   - Strategy deleted: {strategies_deleted}")
            
        except Exception as e:
            print(f"❌ Error deleting {strategy_id}: {e}")
            db.strategy.session.rollback()
    
    print()
    print("=" * 60)
    print("✅ DATABASE CLEANUP COMPLETE")
    print()
    print("Remaining strategies:")
    
    # Show remaining strategies
    query = text("SELECT strategy_id, name, updated_at FROM strategies ORDER BY updated_at DESC")
    results = db.strategy.session.execute(query).fetchall()
    
    if results:
        for row in results:
            print(f"  - {row[0]}: {row[1]} (updated: {row[2]})")
    else:
        print("  (No strategies in database)")
    
    print()
    print("Next steps:")
    print("1. Restart Strategy Builder")
    print("2. Import strategies from JSON (Tools → Import Strategy from JSON)")
    print("3. Verify no more errors")
    
    db.close()

if __name__ == "__main__":
    clean_corrupt_strategies()
