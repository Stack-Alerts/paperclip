#!/usr/bin/env python3
"""
Delete old strategy with broken data
"""

import os
import sys

# Add project root to path
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager

def delete_old_strategies():
    """Delete all strategies so user can save fresh"""
    
    print("=" * 80)
    print("DELETING OLD STRATEGIES")
    print("=" * 80)
    
    try:
        db = get_database_manager()
        
        # Get all strategies
        strategies = db.strategy.get_all_strategies()
        print(f"\nFound {len(strategies)} strategies")
        
        for strategy in strategies:
            print(f"\nDeleting: {strategy['name']} (ID: {strategy['strategy_id']})")
            
            # Delete all versions first (using strategy_manager API)
            versions = db.strategy.get_strategy_versions(strategy['strategy_id'])
            for version in versions:
                print(f"  Deleting version {version['version_number']}...")
                db.strategy.delete_strategy_version(version['version_id'])
            
            print(f"  All versions deleted for {strategy['name']}")
        
        print("\n" + "=" * 80)
        print("✅ ALL OLD STRATEGIES DELETED")
        print("=" * 80)
        print("\nNow you can:")
        print("1. Restart Strategy Builder")
        print("2. Build your HOD Rejection strategy")
        print("3. Save it (Ctrl+S) - will use CORRECT format now")
        print("4. Load it - will work perfectly!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    delete_old_strategies()
