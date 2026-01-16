"""
Script to identify and fix UNKNOWN signal emissions across all building blocks.

CRITICAL ISSUE:
Multiple blocks emitting UNKNOWN instead of proper signals (NEUTRAL, NO_PATTERN, etc.)
This breaks strategy builder as UNKNOWN not in valid_signals.

BLOCKS TO FIX:
1. initial_balance_breakout - 81.6% UNKNOWN
2. ict_silver_bullet - 60.9% UNKNOWN
3. macd_price_forecasting - 92.2% UNKNOWN
4. swing_breakout_sequence - 96.5% UNKNOWN
5. swing_failure_pattern - 85.7% UNKNOWN
6. rising_wedge - 81.7% UNKNOWN
7. rounding_bottom - 88.9% UNKNOWN
8. supply_demand_zones - 100% UNKNOWN (but we just fixed this)
"""

import os
import re

BLOCKS_TO_FIX = {
    'initial_balance_breakout': {
        'path': 'src/detectors/building_blocks/price_action/initial_balance_breakout.py',
        'unknown_replacement': 'NEUTRAL',
        'fallback_signal': 'NO_IB'
    },
    'ict_silver_bullet': {
        'path': 'src/detectors/building_blocks/smc_ict/ict_silver_bullet.py',
        'unknown_replacement': 'NEUTRAL',
    },
    'macd_price_forecasting': {
        'path': 'src/detectors/building_blocks/momentum/macd_price_forecasting.py',
        'unknown_replacement': 'NEUTRAL',
    },
    'swing_breakout_sequence': {
        'path': 'src/detectors/building_blocks/market_structure/swing_breakout_sequence.py',
        'unknown_replacement': 'NEUTRAL',
    },
    'swing_failure_pattern': {
        'path': 'src/detectors/building_blocks/smc_ict/swing_failure_pattern.py',
        'unknown_replacement': 'NEUTRAL',
    },
    'rising_wedge': {
        'path': 'src/detectors/building_blocks/chart_patterns/rising_wedge.py',
        'unknown_replacement': 'NO_PATTERN',
    },
    'rounding_bottom': {
        'path': 'src/detectors/building_blocks/chart_patterns/rounding_bottom.py',
        'unknown_replacement': 'NO_PATTERN',
    },
}

def find_unknown_returns(filepath):
    """Find all places where UNKNOWN is returned"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find return statements with UNKNOWN
    pattern = r"'signal':\s*'UNKNOWN'"
    matches = re.findall(pattern, content)
    
    return len(matches), content

def main():
    print("="*80)
    print("FINDING UNKNOWN SIGNAL EMISSIONS")
    print("="*80)
    
    for block_name, config in BLOCKS_TO_FIX.items():
        filepath = config['path']
        if not os.path.exists(filepath):
            print(f"❌ {block_name}: File not found - {filepath}")
            continue
        
        count, content = find_unknown_returns(filepath)
        print(f"\n{block_name}:")
        print(f"  Path: {filepath}")
        print(f"  UNKNOWN returns found: {count}")
        print(f"  Should be: {config['unknown_replacement']}")

if __name__ == "__main__":
    main()
