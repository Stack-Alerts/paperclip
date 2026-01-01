"""
BATCH ICT/SMC BLOCK OPTIMIZER
Runs overnight to optimize all remaining ICT blocks systematically

Target: 8 ICT/SMC blocks
Estimated time: 3-4 hours
Output: Optimized parameters for each block

Author: Cline (Expert Mode)
Date: 2026-01-01
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.multicore_block_tuner import BlockParameterTuner, load_btc_data


# Define ICT blocks to optimize
ICT_BLOCKS = [
    {
        'name': 'market_structure_shift',
        'path': 'src/detectors/building_blocks/smc_ict/market_structure_shift.py',
        'param_grid': {
            'swing_lookback': [8, 10, 12],
            'min_break_pct': [0.05, 0.1, 0.15],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'displacement',
        'path': 'src/detectors/building_blocks/smc_ict/displacement.py',
        'param_grid': {
            'lookback': [5, 7, 10],
            'min_displacement_pct': [0.5, 1.0, 1.5],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'inducement',
        'path': 'src/detectors/building_blocks/smc_ict/inducement.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'trap_threshold_pct': [0.3, 0.5, 0.7],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'optimal_trade_entry',
        'path': 'src/detectors/building_blocks/smc_ict/optimal_trade_entry.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'mitigation_block',
        'path': 'src/detectors/building_blocks/smc_ict/mitigation_block.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'balanced_price_range',
        'path': 'src/detectors/building_blocks/smc_ict/balanced_price_range.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'change_of_character',
        'path': 'src/detectors/building_blocks/smc_ict/change_of_character.py',
        'param_grid': {
            'swing_lookback': [8, 10, 12],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'swing_failure_pattern',
        'path': 'src/detectors/building_blocks/smc_ict/swing_failure_pattern.py',
        'param_grid': {
            'lookback': [10, 15, 20],
            'failure_threshold_pct': [0.3, 0.5, 0.7],
            'timeframe': ['15min']
        }
    }
]


def optimize_single_block(block_config: dict, df):
    """Optimize a single block"""
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
    print(f"🌙 OVERNIGHT BATCH OPTIMIZER - ICT/SMC BLOCKS")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Blocks to optimize: {len(ICT_BLOCKS)}")
    print(f"Estimated time: 3-4 hours")
    print(f"{'='*80}\n")
    
    # Load data once
    print("📊 Loading BTC 15min data (180 days)...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Process each block
    results_summary = []
    successful = 0
    failed = 0
    
    for i, block_config in enumerate(ICT_BLOCKS, 1):
        print(f"\n{'#'*80}")
        print(f"# BLOCK {i}/{len(ICT_BLOCKS)}: {block_config['name'].upper()}")
        print(f"{'#'*80}")
        
        result = optimize_single_block(block_config, df)
        if result:
            results_summary.append(result)
            if result['status'] == 'SUCCESS':
                successful += 1
            else:
                failed += 1
    
    # Save summary
    summary_path = Path(__file__).parent.parent / 'batch_ict_optimization_summary.json'
    with open(summary_path, 'w') as f:
        json.dump({
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_blocks': len(ICT_BLOCKS),
            'successful': successful,
            'failed': failed,
            'results': results_summary
        }, f, indent=2)
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"🎉 BATCH OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total blocks: {len(ICT_BLOCKS)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/len(ICT_BLOCKS)*100):.1f}%")
    print(f"\nSummary saved to: {summary_path}")
    print(f"{'='*80}\n")
    
    # Print successful blocks
    if successful > 0:
        print("✅ SUCCESSFUL OPTIMIZATIONS:")
        for result in results_summary:
            if result['status'] == 'SUCCESS':
                print(f"  - {result['block']}: {result['quality']}/100, {result['accuracy']:.1f}%, {result['signals']} signals")
    
    # Print failed blocks
    if failed > 0:
        print("\n❌ FAILED OPTIMIZATIONS:")
        for result in results_summary:
            if result['status'] != 'SUCCESS':
                print(f"  - {result['block']}: {result.get('reason', result.get('error', 'Unknown'))}")
    
    print(f"\n{'='*80}")
    print("🌅 Ready for next session!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
