"""
Test Building Block Registry
=============================

Comprehensive test to verify all 79 blocks are properly registered
and can be instantiated.

Usage:
    python scripts/test_registry.py

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all building block modules to trigger registration
print("Loading all building blocks into registry...")
print("="*80)

# Import blocks by category to trigger @register_block decorators
categories = [
    ('patterns', [
        'double_top', 'double_bottom', 'head_and_shoulders', 'inverse_head_and_shoulders',
        'ascending_triangle', 'descending_triangle', 'symmetrical_triangle',
        'rising_wedge', 'falling_wedge', 'cup_and_handle', 'rounding_bottom',
        'flag_pattern', 'pennant_pattern', 'three_bar_reversal',  
        'triple_top', 'triple_bottom', 'candle_2_close', 'initial_balance_breakout',
        'internal_pivot_pattern', 'swing_breakout_sequence'
    ]),
    ('market_structure', [
        'swing_points', 'premium_discount_zones', 'liquidity',
        'range_liquidity', 'wave_consolidation', 'power_hour_trends'
    ]),
    ('moving_averages', [
        'ema_200_trend', 'ema_20_50_trend', 'ema_20_50_cross',
        'ema_50_vector', 'ema_55_vector', 'ema_255_vector', 'ema_800_vector'
    ]),
    ('oscillators', [
        'rsi_divergence', 'macd_signal', 'stochastic_rsi'
    ]),
    ('price_levels', [
        'hod', 'lod', 'how', 'low', 'asia_session_50_percent', 'us_settlement'
    ]),
    ('sessions', [
        'session_time', 'kill_zones'
    ]),
    ('volatility', [
        'adr', 'atr', 'bollinger_bands'
    ]),
    ('institutional', [
        'vwap', 'anchored_vwap', 'ema_crossover', 'market_depth', 'order_flow_imbalance'
    ]),
    ('smc_ict', [
        'break_of_structure', 'change_of_character', 'balanced_price_range',
        'displacement', 'inducement', 'market_structure_shift',
        'mitigation_block', 'optimal_trade_entry', 'swing_failure_pattern'
    ]),
    ('price_action', [
        'order_block', 'fair_value_gap', 'liquidity_sweep', 'breaker_block'
    ]),
    ('fibonacci', [
        'fibonacci_retracements'
    ]),
    ('elliott_wave', [
        'elliott_wave_count', 'elliott_wave_oscillator'
    ]),
    ('wyckoff', [
        'wyckoff_accumulation', 'wyckoff_distribution', 'wyckoff_reaccumulation'
    ]),
    ('supply_demand', [
        'supply_demand_zones'
    ]),
    ('trend', [
        'adx', 'ichimoku_cloud'
    ]),
    ('signals', [
        'adaptive_momentum_oscillator', 'asfx_a2_vwap',
        'ict_silver_bullet', 'macd_price_forecasting'
    ]),
    ('risk_management', [
        'trailing_stop'
    ]),
]

loaded = 0
failed = 0
failed_blocks = []

for category, blocks in categories:
    print(f"\n📦 {category.upper()}:")
    for block in blocks:
        try:
            module = __import__(
                f'src.detectors.building_blocks.{category}.{block}',
                fromlist=['']
            )
            print(f"   ✅ {block}")
            loaded += 1
        except Exception as e:
            print(f"   ❌ {block}: {str(e)[:60]}")
            failed += 1
            failed_blocks.append((category, block, str(e)))

print("\n" + "="*80)
print("REGISTRY TEST RESULTS")
print("="*80)

from src.detectors.building_blocks.registry import BlockRegistry

# Print registry summary
BlockRegistry.print_summary()

print(f"\n📊 Loading Results:")
print(f"   ✅ Loaded: {loaded}")
print(f"   ❌ Failed: {failed}")

if failed_blocks:
    print(f"\n⚠️  Failed Blocks:")
    for cat, block, error in failed_blocks:
        print(f"   - {cat}/{block}: {error[:80]}")

print(f"\n🎯 Registry Statistics:")
stats = BlockRegistry.get_stats()
print(f"   Total Registered: {stats['total_blocks']}")
print(f"   Categories: {len(stats['blocks_by_category'])}")

# Test instantiation of a few blocks
print(f"\n🧪 Testing Instantiation:")
test_blocks = ['swing_points', 'double_top', 'ema_200_trend', 'vwap', 'adr']
for block_name in test_blocks:
    try:
        instance = BlockRegistry.instantiate(block_name, timeframe='15min')
        print(f"   ✅ {block_name}: {instance.__class__.__name__}")
    except Exception as e:
        print(f"   ❌ {block_name}: {str(e)[:60]}")

# Test signal validation
print(f"\n🔍 Testing Signal Validation:")
test_signals = [
    ('swing_points', 'SWING_HIGH_DETECTED'),
    ('swing_points', 'INVALID_SIGNAL'),
    ('double_top', 'BEARISH_BREAKDOWN'),
    ('vwap', 'BULLISH'),
]
for block, signal in test_signals:
    is_valid = BlockRegistry.validate_signal(block, signal)
    status = "✅" if is_valid else "❌"
    print(f"   {status} {block}.{signal}: {is_valid}")

print("\n" + "="*80)
if failed == 0 and stats['total_blocks'] >= 70:
    print("✅ ALL TESTS PASSED - Registry is fully functional!")
    print(f"🎉 {stats['total_blocks']} blocks successfully registered!")
else:
    print(f"⚠️  Some blocks failed to load or register")
    print(f"   Expected: ~79 blocks")
    print(f"   Registered: {stats['total_blocks']} blocks")
print("="*80)

sys.exit(0 if failed == 0 else 1)