#!/usr/bin/env python3
"""
Test script to verify database save functionality
SPRINT 1.6.1 - Debugging
"""

import os
import sys

# Add project root to path
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager

def test_database():
    """Test database connectivity and check saved strategies"""
    
    print("=" * 80)
    print("DATABASE VERIFICATION TEST")
    print("=" * 80)
    
    try:
        # Get database manager
        print("\n1. Connecting to database...")
        db = get_database_manager()
        print("   ✅ Connected successfully")
        
        # Check strategies table
        print("\n2. Querying strategies table...")
        strategies = db.strategy.get_all_strategies()
        print(f"   Found {len(strategies)} strategies in database")
        
        if strategies:
            print("\n   Strategies:")
            for s in strategies:
                print(f"     - {s['strategy_id']}: {s['name']}")
                print(f"       Created: {s['created_at']}")
                print(f"       Latest version: {s.get('latest_version', 'N/A')}")
        
        # Check strategy_versions table
        print("\n3. Querying strategy_versions table...")
        for strategy in strategies:
            versions = db.strategy.get_strategy_versions(strategy['strategy_id'])
            print(f"\n   Strategy '{strategy['name']}' has {len(versions)} version(s):")
            
            for v in versions:
                print(f"     - Version {v['version_number']}: {v['name']}")
                print(f"       Description: {v.get('description', 'N/A')}")
                print(f"       Blocks: {len(v.get('blocks', []))} blocks")
                print(f"       Tags: {v.get('tags', [])}")
                print(f"       Created: {v['created_at']}")
        
        # Test get_latest_version (what Browser uses)
        print("\n4. Testing get_latest_version() (Browser method)...")
        for strategy in strategies:
            latest = db.strategy.get_latest_version(strategy['strategy_id'])
            if latest:
                print(f"\n   Latest version of '{strategy['name']}':")
                print(f"     - Version: {latest['version_number']}")
                print(f"     - Name: {latest['name']}")
                print(f"     - Blocks type: {type(latest.get('blocks'))}")
                print(f"     - Tags type: {type(latest.get('tags'))}")
                print(f"     - Tags value: {latest.get('tags', [])}")
        
        print("\n" + "=" * 80)
        if strategies:
            print("✅ DATABASE HAS DATA - Strategy Browser should show strategies")
        else:
            print("❌ DATABASE IS EMPTY - Save did not work")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    test_database()
