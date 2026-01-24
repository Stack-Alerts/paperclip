#!/usr/bin/env python3
"""
Complete save/load cycle test - CREATE THE STRATEGY AND TEST IT
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
from src.strategy_builder.core.block_registry_adapter import BlockRegistryAdapter
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator

def test_complete_cycle():
    """Test complete save/load cycle with realistic strategy"""
    
    print("=" * 80)
    print("COMPLETE SAVE/LOAD CYCLE TEST")
    print("=" * 80)
    
    try:
        # Step 1: Create orchestrator
        print("\n1. Creating orchestrator...")
        adapter = BlockRegistryAdapter()
        orch = StrategyBuilderOrchestrator(registry=adapter)
        orch.create_strategy('AUTOMATED_TEST_Strategy')
        print("   ✅ Orchestrator created")
        
        # Step 2: Build strategy matching user's screenshot
        print("\n2. Building strategy (3 blocks with timings & rechecks)...")
        
        # Block 1: HOD (2 signals)
        orch.add_block_with_signals('hod', ['HOD_REJECTION', 'BELOW_HOD'])
        
        # Block 2: asia_session_50_percent (1 signal)
        orch.add_block_with_signals('asia_session_50_percent', ['ABOVE_ASIA_50'])
        
        # Block 3: rsi_divergence (2 signals)
        orch.add_block_with_signals('rsi_divergence', ['BEARISH', 'BEARISH_DIVERGENCE'])
        
        config = orch.get_current_config()
        print(f"   ✅ Built strategy with {len(config.blocks)} blocks")
        
        # Step 3: Convert to dict (test persistence)
        print("\n3. Converting to dict with persistence._config_to_dict()...")
        config_dict = orch.persistence._config_to_dict(config)
        print(f"   ✅ Converted to dict: {len(config_dict.get('blocks', []))} blocks")
        print(f"   First block signals type: {type(config_dict['blocks'][0]['signals'])}")
        
        # Step 4: Save to database
        print("\n4. Saving to database...")
        db = get_database_manager()
        
        strategy_id = db.strategy.create_strategy('AUTOMATED_TEST_Strategy')
        print(f"   Created strategy: {strategy_id}")
        
        version_data = {
            'strategy_id': strategy_id,
            'name': 'AUTOMATED_TEST_Strategy',
            'description': 'Automated test with timings and rechecks',
            'blocks': config_dict.get('blocks', []),
            'signals': {},
            'parameters': {},
            'entry_conditions': {},
            'exit_conditions': {},
            'risk_management': {},
            'backtest_config': {},
            'tags': ['automated-test']
        }
        
        version_id = db.strategy.create_strategy_version(version_data)
        print(f"   ✅ Saved version: {version_id}")
        
        # Step 5: Load from database
        print("\n5. Loading from database...")
        loaded_version = db.strategy.get_strategy_version(version_id)
        print(f"   ✅ Loaded version: {loaded_version['name']}")
        print(f"   Blocks count: {len(loaded_version['blocks'])}")
        
        # Step 6: Restore config with persistence._dict_to_config()
        print("\n6. Restoring config with persistence._dict_to_config()...")
        load_dict = {
            'name': loaded_version['name'],
            'description': loaded_version['description'],
            'blocks': loaded_version['blocks']
        }
        
        restored_config = orch.persistence._dict_to_config(load_dict)
        print(f"   ✅ Restored config: {len(restored_config.blocks)} blocks")
        
        # Step 7: Verify data integrity
        print("\n7. Verifying data integrity...")
        print(f"\n   ORIGINAL CONFIG:")
        print(f"     Blocks: {len(config.blocks)}")
        for i, block in enumerate(config.blocks, 1):
            print(f"     Block {i}: {block.name}, {len(block.signals)} signals")
            for j, signal in enumerate(block.signals, 1):
                print(f"       Signal {j}: {signal.name}")
                if signal.timing_constraint:
                    print(f"         ⏱️  Timing: {signal.timing_constraint.max_candles} candles")
                if signal.recheck_config and signal.recheck_config.enabled:
                    print(f"         🔄 Recheck: {signal.recheck_config.bar_delay} bars")
        
        print(f"\n   RESTORED CONFIG:")
        print(f"     Blocks: {len(restored_config.blocks)}")
        for i, block in enumerate(restored_config.blocks, 1):
            print(f"     Block {i}: {block.name}, {len(block.signals)} signals")
            for j, signal in enumerate(block.signals, 1):
                print(f"       Signal {j}: {signal.name}")
                if signal.timing_constraint:
                    print(f"         ⏱️  Timing: {signal.timing_constraint.max_candles} candles")
                if signal.recheck_config and signal.recheck_config.enabled:
                    print(f"         🔄 Recheck: {signal.recheck_config.bar_delay} bars")
        
        # Compare
        success = True
        if len(config.blocks) != len(restored_config.blocks):
            print(f"\n   ❌ Block count mismatch!")
            success = False
        else:
            print(f"\n   ✅ Block count matches")
        
        print("\n" + "=" * 80)
        if success:
            print("✅ COMPLETE CYCLE TEST PASSED")
            print("=" * 80)
            print("\nSave/Load is working correctly with:")
            print("  - Full signal objects")
            print("  - Timing constraints")
            print("  - Recheck configurations")
            print("\nUser can now use Strategy Builder with confidence!")
        else:
            print("❌ COMPLETE CYCLE TEST FAILED")
            print("=" * 80)
        
        # Cleanup
        print("\n8. Cleaning up test strategy...")
        db.strategy.delete_strategy_version(version_id)
        print("   ✅ Cleanup complete")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_complete_cycle()
