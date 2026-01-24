#!/usr/bin/env python3
"""
Deep trace to find where database load is failing
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator

def test_load_cycle():
    """Test complete load cycle"""
    
    print("=" * 80)
    print("DEEP TRACE: DATABASE LOAD CYCLE")
    print("=" * 80)
    
    try:
        # Step 1: Get data from database
        print("\n1. Loading from database...")
        db = get_database_manager()
        strategies = db.strategy.get_all_strategies()
        
        if not strategies:
            print("❌ No strategies in database!")
            return
        
        strategy = strategies[0]
        print(f"   Strategy ID: {strategy['strategy_id']}")
        print(f"   Strategy Name: {strategy['name']}")
        
        # Step 2: Get version data (what load_strategy_from_browser gets)
        print("\n2. Getting version data...")
        version = db.strategy.get_latest_version(strategy['strategy_id'])
        
        print(f"   Version keys: {version.keys() if version else 'None'}")
        if version:
            print(f"   Version ID: {version.get('version_id', version.get('id', 'NO ID'))}")
            print(f"   Name: {version.get('name', 'NO NAME')}")
            print(f"   Description: {version.get('description', 'N/A')[:100]}...")
        
        # Step 3: Check blocks data structure
        print("\n3. Checking blocks data...")
        blocks_data = version.get('blocks', [])
        print(f"   Blocks count: {len(blocks_data)}")
        print(f"   Blocks type: {type(blocks_data)}")
        
        if blocks_data:
            print(f"\n   First block structure:")
            print(json.dumps(blocks_data[0], indent=4)[:500])
            
        # Step 4: Test persistence._dict_to_config()
        print("\n4. Testing persistence._dict_to_config()...")
        orchestrator = StrategyBuilderOrchestrator()
        
        config_dict = {
            'name': version['name'],
            'description': version.get('description', ''),
            'blocks': blocks_data
        }
        
        print(f"   Config dict keys: {config_dict.keys()}")
        print(f"   Config dict blocks count: {len(config_dict.get('blocks', []))}")
        
        try:
            restored_config = orchestrator.persistence._dict_to_config(config_dict)
            print(f"   ✅ Deserialize SUCCESS")
            print(f"   Restored config type: {type(restored_config)}")
            print(f"   Restored config name: {restored_config.name}")
            print(f"   Restored blocks count: {len(restored_config.blocks)}")
            
            # Check if blocks have signals
            if restored_config.blocks:
                first_block = restored_config.blocks[0]
                print(f"\n   First block:")
                print(f"     Name: {first_block.name}")
                print(f"     Logic: {first_block.logic}")
                print(f"     Signals count: {len(first_block.signals)}")
                
                if first_block.signals:
                    first_signal = first_block.signals[0]
                    print(f"\n   First signal:")
                    print(f"     Name: {first_signal.name}")
                    print(f"     Logic: {first_signal.logic}")
                    print(f"     Has timing_constraint: {first_signal.timing_constraint is not None}")
                    print(f"     Has recheck_config: {first_signal.recheck_config is not None}")
                    
                    if first_signal.timing_constraint:
                        print(f"       Timing: max_candles={first_signal.timing_constraint.max_candles}, reference={first_signal.timing_constraint.reference}")
                    
                    if first_signal.recheck_config:
                        print(f"       Recheck: enabled={first_signal.recheck_config.enabled}, delay={first_signal.recheck_config.bar_delay}")
            
        except Exception as e:
            print(f"   ❌ Deserialize FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("TRACE COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    test_load_cycle()
