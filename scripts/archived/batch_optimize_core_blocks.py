"""
BATCH CORE BLOCK OPTIMIZER (NON-PATTERNS)
Optimizes all core building blocks (excluding patterns which are deferred)

Target: 37 non-pattern blocks
Priority: Price action, institutional, trend, market structure first
Patterns: Deferred to last

Author: Cline (Expert Mode)
Date: 2026-01-01
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
from multiprocessing import Pool, cpu_count

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.multicore_block_tuner import BlockParameterTuner, load_btc_data


# Define CORE blocks to optimize (no patterns)
CORE_BLOCKS = [
    # PRICE ACTION (4 blocks) - HIGH PRIORITY
    {
        'name': 'fair_value_gap',
        'path': 'src/detectors/building_blocks/price_action/fair_value_gap.py',
        'param_grid': {'lookback': [3, 5, 7], 'timeframe': ['15min']}
    },
    {
        'name': 'order_block',
        'path': 'src/detectors/building_blocks/price_action/order_block.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    {
        'name': 'liquidity_sweep',
        'path': 'src/detectors/building_blocks/price_action/liquidity_sweep.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    {
        'name': 'breaker_block',
        'path': 'src/detectors/building_blocks/price_action/breaker_block.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    
    # INSTITUTIONAL (5 blocks) - HIGH PRIORITY
    {
        'name': 'vwap',
        'path': 'src/detectors/building_blocks/institutional/vwap.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'anchored_vwap',
        'path': 'src/detectors/building_blocks/institutional/anchored_vwap.py',
        'param_grid': {'anchor_period': ['1D', '1W'], 'timeframe': ['15min']}
    },
    {
        'name': 'order_flow_imbalance',
        'path': 'src/detectors/building_blocks/institutional/order_flow_imbalance.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    {
        'name': 'market_depth',
        'path': 'src/detectors/building_blocks/institutional/market_depth.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    {
        'name': 'ema_crossover',
        'path': 'src/detectors/building_blocks/institutional/ema_crossover.py',
        'param_grid': {'fast_period': [10, 12, 15], 'slow_period': [20, 24, 26], 'timeframe': ['15min']}
    },
    
    # TREND (2 blocks) - HIGH PRIORITY  
    {
        'name': 'ichimoku_cloud',
        'path': 'src/detectors/building_blocks/trend/ichimoku_cloud.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'adx',
        'path': 'src/detectors/building_blocks/trend/adx.py',
        'param_grid': {'period': [12, 14, 16], 'timeframe': ['15min']}
    },
    
    # MARKET STRUCTURE (3 blocks)
    {
        'name': 'swing_points',
        'path': 'src/detectors/building_blocks/market_structure/swing_points.py',
        'param_grid': {'lookback': [8, 10, 12], 'timeframe': ['15min']}
    },
    {
        'name': 'premium_discount_zones',
        'path': 'src/detectors/building_blocks/market_structure/premium_discount_zones.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    {
        'name': 'range_liquidity',
        'path': 'src/detectors/building_blocks/market_structure/range_liquidity.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    
    # PRICE LEVELS (6 blocks)
    {
        'name': 'hod',
        'path': 'src/detectors/building_blocks/price_levels/hod.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'how',
        'path': 'src/detectors/building_blocks/price_levels/how.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'lod',
        'path': 'src/detectors/building_blocks/price_levels/lod.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'low',
        'path': 'src/detectors/building_blocks/price_levels/low.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'asia_session_50_percent',
        'path': 'src/detectors/building_blocks/price_levels/asia_session_50_percent.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'us_settlement',
        'path': 'src/detectors/building_blocks/price_levels/us_settlement.py',
        'param_grid': {'timeframe': ['15min']}
    },
    
    # SESSIONS (2 blocks)
    {
        'name': 'kill_zones',
        'path': 'src/detectors/building_blocks/sessions/kill_zones.py',
        'param_grid': {'timeframe': ['15min']}
    },
    {
        'name': 'session_time',
        'path': 'src/detectors/building_blocks/sessions/session_time.py',
        'param_grid': {'timeframe': ['15min']}
    },
    
    # FIBONACCI (1 block)
    {
        'name': 'fibonacci_retracements',
        'path': 'src/detectors/building_blocks/fibonacci/fibonacci_retracements.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    
    # ELLIOTT WAVE (2 blocks)
    {
        'name': 'elliott_wave_count',
        'path': 'src/detectors/building_blocks/elliott_wave/elliott_wave_count.py',
        'param_grid': {'lookback': [25, 30, 35], 'timeframe': ['15min']}
    },
    {
        'name': 'elliott_wave_oscillator',
        'path': 'src/detectors/building_blocks/elliott_wave/elliott_wave_oscillator.py',
        'param_grid': {'fast_period': [5, 7, 10], 'slow_period': [30, 35, 40], 'timeframe': ['15min']}
    },
    
    # WYCKOFF (3 blocks)
    {
        'name': 'wyckoff_accumulation',
        'path': 'src/detectors/building_blocks/wyckoff/wyckoff_accumulation.py',
        'param_grid': {'lookback': [25, 30, 35], 'timeframe': ['15min']}
    },
    {
        'name': 'wyckoff_distribution',
        'path': 'src/detectors/building_blocks/wyckoff/wyckoff_distribution.py',
        'param_grid': {'lookback': [25, 30, 35], 'timeframe': ['15min']}
    },
    {
        'name': 'wyckoff_reaccumulation',
        'path': 'src/detectors/building_blocks/wyckoff/wyckoff_reaccumulation.py',
        'param_grid': {'lookback': [25, 30, 35], 'timeframe': ['15min']}
    },
    
    # SUPPLY/DEMAND (1 block)
    {
        'name': 'supply_demand_zones',
        'path': 'src/detectors/building_blocks/supply_demand/supply_demand_zones.py',
        'param_grid': {'lookback': [15, 20, 25], 'timeframe': ['15min']}
    },
    
    # VOLATILITY (3 blocks) - UTILITY - Different validation
    {
        'name': 'atr',
        'path': 'src/detectors/building_blocks/volatility/atr.py',
        'param_grid': {'period': [12, 14, 16], 'timeframe': ['15min']}
    },
    {
        'name': 'bollinger_bands',
        'path': 'src/detectors/building_blocks/volatility/bollinger_bands.py',
        'param_grid': {'period': [18, 20, 22], 'std_dev': [2.0], 'timeframe': ['15min']}
    },
    {
        'name': 'adr',
        'path': 'src/detectors/building_blocks/volatility/adr.py',
        'param_grid': {'period': [12, 14, 16], 'timeframe': ['15min']}
    },
]


def optimize_single_block(args):
    """Optimize a single block"""
    block_config, df_path = args
    
    import pandas as pd
    df = pd.read_pickle(df_path)
    
    print(f"\n{'='*80}")
    print(f"🎯 OPTIMIZING: {block_config['name'].upper()}")
    print(f"{'='*80}\n")
    
    block_path = Path(__file__).parent.parent / block_config['path']
    
    if not block_path.exists():
        print(f"❌ Block not found: {block_path}")
        return None
    
    try:
        tuner = BlockParameterTuner(
            block_path=str(block_path),
            block_name=block_config['name'],
            data=df,
            cache_file=f"{block_config['name']}_tuning_cache.pkl"
        )
        
        print(f"Parameter grid: {block_config['param_grid']}\n")
        
        results = tuner.run_grid_search(
            param_grid=block_config['param_grid'],
            max_combinations=None,
            n_cores=None
        )
        
        if len(results) > 0:
            tuner.print_top_results(results, top_n=10)
            tuner.save_top_results(results, f"top_params_{block_config['name']}.json", top_n=10)
            
            best = results[0]
            print(f"\n✅ BEST: Quality={best['quality_score']}/100, Accuracy={best['accuracy']:.1f}%, Signals={best['total_signals']}\n")
            
            return {
                'block': block_config['name'],
                'status': 'SUCCESS',
                'best_params': best['params'],
                'quality': best['quality_score'],
                'accuracy': best['accuracy'],
                'signals': best['total_signals'],
                'reward_risk': best['reward_risk']
            }
        else:
            print(f"\n❌ No successful configurations found for {block_config['name']}\n")
            return {
                'block': block_config['name'],
                'status': 'FAILED',
                'reason': 'No successful configurations'
            }
            
    except Exception as e:
        print(f"\n❌ Error optimizing {block_config['name']}: {str(e)}\n")
        return {
            'block': block_config['name'],
            'status': 'ERROR',
            'error': str(e)
        }


def main():
    """Main batch optimization function"""
    print(f"\n{'='*80}")
    print(f"🌙 BATCH OPTIMIZER - CORE BLOCKS (NO PATTERNS)")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Blocks to optimize: {len(CORE_BLOCKS)}")
    print(f"Strategy: Sequential blocks, multicore within")
    print(f"Estimated time: 6-8 hours")
    print(f"{'='*80}\n")
    
    # Load data
    print("📊 Loading BTC 15min data (180 days)...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Save to temp file
    import tempfile
    temp_data_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl').name
    df.to_pickle(temp_data_path)
    print(f"💾 Data cached: {temp_data_path}\n")
    
    # Prepare args
    args_list = [(block_config, temp_data_path) for block_config in CORE_BLOCKS]
    
    # Run sequentially with multicore
    n_parallel = 1
    
    print(f"🚀 Starting optimization (sequential blocks, all cores per block)...\n")
    
    results_summary = []
    successful = 0
    failed = 0
    
    # Run blocks sequentially without Pool (avoid daemon issue)
    results = []
    for args in args_list:
        result = optimize_single_block(args)
        results.append(result)
    
    os.unlink(temp_data_path)
    
    for result in results:
        if result:
            results_summary.append(result)
            if result['status'] == 'SUCCESS':
                successful += 1
            else:
                failed += 1
    
    # Save summary
    summary_path = Path(__file__).parent.parent / 'batch_core_optimization_summary.json'
    with open(summary_path, 'w') as f:
        json.dump({
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_blocks': len(CORE_BLOCKS),
            'successful': successful,
            'failed': failed,
            'results': results_summary
        }, f, indent=2)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"🎉 BATCH OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"Total blocks: {len(CORE_BLOCKS)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/len(CORE_BLOCKS)*100):.1f}%")
    print(f"\nSummary: {summary_path}")
    print(f"{'='*80}\n")
    
    if successful > 0:
        print("✅ SUCCESSFUL:")
        for result in results_summary:
            if result['status'] == 'SUCCESS':
                print(f"  - {result['block']}: {result['quality']}/100, {result['accuracy']:.1f}%")
    
    if failed > 0:
        print("\n❌ FAILED:")
        for result in results_summary:
            if result['status'] != 'SUCCESS':
                print(f"  - {result['block']}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
