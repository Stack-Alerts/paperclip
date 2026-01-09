"""
Systematic Block Classification Script
Adds clear type classification to all building blocks

Block Types:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective)
- CONTEXT BLOCK: Continuous state provider (always active)
- EVENT BLOCK: Specific market event detection (selective)
- HYBRID BLOCK: Combination of signal + context
"""

import os
from pathlib import Path

# Classification based on code analysis
BLOCK_CLASSIFICATIONS = {
    # Elliott Wave
    'elliott_wave/elliott_wave_count.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Always tracks current wave position (1-5), provides HTF context'
    },
    'elliott_wave/elliott_wave_oscillator.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous momentum state, always provides EWO value and direction'
    },
    
    # Fibonacci
    'fibonacci/fibonacci_retracements.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous Fibonacci levels, always provides retracement zones'
    },
    
    # Institutional
    'institutional/anchored_vwap.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous price vs VWAP state, always active'
    },
    'institutional/ema_crossover.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'EMA crossover events, selective signals on cross'
    },
    'institutional/vwap.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous VWAP state, always active'
    },
    'institutional/order_flow_imbalance.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Detects order flow imbalances, fires on significant events'
    },
    'institutional/market_depth.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous market depth analysis'
    },
    
    # Moving Averages
    'moving_averages/ema_20_50_cross.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'EMA crossover signals, selective on golden/death cross'
    },
    'moving_averages/ema_20_50_trend.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous trend state based on EMA relationship'
    },
    'moving_averages/ema_50_vector.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'Price breaks through 50 EMA, selective signals'
    },
    'moving_averages/ema_55_vector.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'Price breaks through 55 EMA, selective signals'
    },
    'moving_averages/ema_200_trend.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous HTF trend state above/below 200 EMA'
    },
    'moving_averages/ema_255_vector.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'Price breaks through 255 EMA (HTF), very selective'
    },
    'moving_averages/ema_800_vector.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'Price breaks through 800 EMA (macro), ultra selective'
    },
    
    # Oscillators
    'oscillators/macd_signal.py': {
        'type': 'SIGNAL BLOCK',
        'mode': 'EVENT-DRIVEN',
        'description': 'MACD crossover signals, selective on cross events'
    },
    'oscillators/rsi_divergence.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'RSI divergence detection, fires on divergence events'
    },
    'oscillators/stochastic_rsi.py': {
        'type': 'HYBRID BLOCK',
        'mode': 'CONTINUOUS + EVENT',
        'description': 'Continuous overbought/oversold + crossover events'
    },
    
    # Patterns (all EVENT BLOCKS)
    'patterns/ascending_triangle.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/cup_and_handle.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/descending_triangle.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/double_bottom.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/double_top.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/falling_wedge.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/flag_pattern.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/head_and_shoulders.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/inverse_head_and_shoulders.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/pennant_pattern.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/rising_wedge.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/rounding_bottom.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/symmetrical_triangle.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/triple_bottom.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    'patterns/triple_top.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Pattern formation detection, fires when complete'
    },
    
    # Price Action (mostly EVENT BLOCKS)
    'price_action/breaker_block.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Breaker block detection, fires when structure breaks'
    },
    'price_action/fair_value_gap.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'FVG detection, fires when gap forms'
    },
    'price_action/liquidity_sweep.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Liquidity sweep detection, fires on sweep events'
    },
    'price_action/order_block.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Order block detection, fires when block forms'
    },
    
    # Price Levels (CONTEXT BLOCKS)
    'price_levels/asia_session_50_percent.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous Asia session midpoint reference'
    },
    'price_levels/hod.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous high of day level'
    },
    'price_levels/how.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous high of week level'
    },
    'price_levels/lod.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous low of day level'
    },
    'price_levels/low.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous low of week level'
    },
    'price_levels/us_settlement.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous US settlement price reference'
    },
    
    # Sessions
    'sessions/kill_zones.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'TIME-BASED',
        'description': 'Continuous kill zone state (in/out)'
    },
    'sessions/session_time.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'TIME-BASED',
        'description': 'Continuous session state tracking'
    },
    'sessions/us_settlement.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'TIME-BASED',
        'description': 'US settlement time state'
    },
    
    # SMC/ICT (mostly EVENT BLOCKS)
    'smc_ict/balanced_price_range.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous fair value range state'
    },
    'smc_ict/break_of_structure.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'BOS detection, fires on structure break'
    },
    'smc_ict/change_of_character.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'ChoCh detection, fires on character change'
    },
    'smc_ict/displacement.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Displacement detection, fires on strong moves'
    },
    'smc_ict/inducement.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Inducement detection, fires when setup complete'
    },
    'smc_ict/market_structure_shift.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'MSS detection, fires on trend reversal'
    },
    'smc_ict/mitigation_block.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Mitigation block detection, fires when formed'
    },
    'smc_ict/optimal_trade_entry.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'OTE zone detection, fires in Fibonacci zone'
    },
    'smc_ict/premium_discount.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous premium/discount state'
    },
    'smc_ict/swing_failure_pattern.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'SFP detection, fires on failure pattern'
    },
    
    # Supply/Demand
    'supply_demand/supply_demand_zones.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Zone detection, fires when zones form'
    },
    
    # Market Structure
    'market_structure/premium_discount_zones.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous premium/discount state'
    },
    'market_structure/range_liquidity.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous range state tracking'
    },
    'market_structure/range_liquidity_advanced.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous advanced range analysis'
    },
    'market_structure/swing_points.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous swing high/low tracking'
    },
    
    # Trend
    'trend/adx.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous trend strength measurement'
    },
    'trend/ichimoku_cloud.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous cloud state and trend'
    },
    
    # Volatility
    'volatility/adr.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous Average Daily Range reference'
    },
    'volatility/atr.py': {
        'type': 'CONTEXT BLOCK',
        'mode': 'CONTINUOUS',
        'description': 'Continuous Average True Range reference'
    },
    'volatility/bollinger_bands.py': {
        'type': 'HYBRID BLOCK',
        'mode': 'CONTINUOUS + EVENT',
        'description': 'Continuous band state + squeeze/expansion events'
    },
    
    # Wyckoff (EVENT BLOCKS)
    'wyckoff/wyckoff_accumulation.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Accumulation phase detection, fires when identified'
    },
    'wyckoff/wyckoff_distribution.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Distribution phase detection, fires when identified'
    },
    'wyckoff/wyckoff_reaccumulation.py': {
        'type': 'EVENT BLOCK',
        'mode': 'SELECTIVE',
        'description': 'Reaccumulation phase detection, fires when identified'
    },
}


def create_block_header(block_type, mode, description):
    """Create standardized block classification header"""
    return f'''"""
Building Block Classification: {block_type}
Mode: {mode}
Purpose: {description}

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""
'''


def main():
    blocks_dir = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks'
    
    print("=" * 80)
    print("SYSTEMATIC BLOCK CLASSIFICATION")
    print("=" * 80)
    print(f"\nTotal blocks to classify: {len(BLOCK_CLASSIFICATIONS)}")
    print("\nClassification Summary:")
    
    type_counts = {}
    for info in BLOCK_CLASSIFICATIONS.values():
        btype = info['type']
        type_counts[btype] = type_counts.get(btype, 0) + 1
    
    for btype, count in sorted(type_counts.items()):
        print(f"  {btype}: {count} blocks")
    
    print("\n" + "=" * 80)
    print("Will add classification headers to all blocks")
    print("=" * 80)
    
    for block_path, info in BLOCK_CLASSIFICATIONS.items():
        full_path = blocks_dir / block_path
        if not full_path.exists():
            print(f"⚠️  SKIP: {block_path} (file not found)")
            continue
        
        print(f"\n✅ {block_path}")
        print(f"   Type: {info['type']}")
        print(f"   Mode: {info['mode']}")
        print(f"   Description: {info['description']}")
    
    print("\n" + "=" * 80)
    print("Classification mapping complete!")
    print("Run with --apply flag to update files")
    print("=" * 80)


if __name__ == '__main__':
    main()
