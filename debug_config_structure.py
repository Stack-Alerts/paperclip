"""
Debug script to inspect HOD Rejection v14 config structure
"""
import sys
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

from src.strategy_builder.config.strategy_config import StrategyConfig
from src.optimizer_v3.database.strategy_manager import StrategyManager

# Load HOD Rejection v14
manager = StrategyManager()
strategy_data = manager.load_strategy("HOD Rejection", 14)

if strategy_data:
    config = StrategyConfig.from_dict(strategy_data['config'])
    
    print("=" * 80)
    print("HOD REJECTION V14 - CONFIG STRUCTURE")
    print("=" * 80)
    
    print(f"\nBlocks count: {len(config.blocks)}")
    
    total_signals = 0
    total_rechecks = 0
    entry_count = 0
    exit_count = 0
    
    for i, block in enumerate(config.blocks):
        print(f"\n[Block {i+1}] {block.name}")
        print(f"  Signals in block: {len(block.signals)}")
        total_signals += len(block.signals)
        
        for j, signal in enumerate(block.signals):
            print(f"\n  [Signal {j+1}] {signal.name}")
            print(f"    Type: {type(signal)}")
            print(f"    Attributes: {dir(signal)}")
            
            # Check recheck_conditions
            if hasattr(signal, 'recheck_conditions'):
                recheckattr = signal.recheck_conditions
                print(f"    recheck_conditions exists: {recheckattr}")
                print(f"    Type: {type(recheckattr)}")
                if recheckattr:
                    print(f"    Length: {len(recheckattr)}")
                    total_rechecks += len(recheckattr)
            else:
                print(f"    recheck_conditions: ATTRIBUTE MISSING")
            
            # Check exit signal status
            is_exit = False
            
            if hasattr(signal, 'is_exit_signal'):
                print(f"    is_exit_signal: {signal.is_exit_signal}")
                if signal.is_exit_signal:
                    is_exit = True
            else:
                print(f"    is_exit_signal: ATTRIBUTE MISSING")
            
            if hasattr(signal, 'exit_for'):
                print(f"    exit_for: {signal.exit_for}")
                if signal.exit_for and len(signal.exit_for) > 0:
                    is_exit = True
            else:
                print(f"    exit_for: ATTRIBUTE MISSING")
            
            if is_exit:
                exit_count += 1
                print(f"    >>> Classification: EXIT SIGNAL")
            else:
                entry_count += 1
                print(f"    >>> Classification: ENTRY SIGNAL")
    
    print(f"\n{'=' * 80}")
    print(f"Exit Conditions:")
    if hasattr(config, 'exit_conditions'):
        print(f"  exit_conditions exists: {config.exit_conditions}")
        print(f"  Type: {type(config.exit_conditions)}")
        if config.exit_conditions:
            print(f"  Count: {len(config.exit_conditions)}")
            for i, exit_cond in enumerate(config.exit_conditions):
                print(f"  [{i+1}] {exit_cond}")
        else:
            print(f"  Count: 0 (empty or None)")
    else:
        print(f"  exit_conditions: ATTRIBUTE MISSING")
    
    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Building Blocks: {len(config.blocks)}")
    print(f"  Total Signals: {total_signals}")
    print(f"  Entry Signals: {entry_count}")
    print(f"  Exit Signals (in blocks): {exit_count}")
    print(f"  RECHECK Conditions: {total_rechecks}")
    print(f"  Exit Conditions: {len(config.exit_conditions) if hasattr(config, 'exit_conditions') and config.exit_conditions else 0}")
    print(f"=" * 80)
else:
    print("Strategy not found")
