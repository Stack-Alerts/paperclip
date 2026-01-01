"""
BATCH PATTERN BLOCK OPTIMIZER
Runs to optimize all 15 pattern blocks systematically

Target: 15 pattern blocks
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
from multiprocessing import Pool, cpu_count

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.multicore_block_tuner import BlockParameterTuner, load_btc_data


# Define pattern blocks to optimize
PATTERN_BLOCKS = [
    {
        'name': 'ascending_triangle',
        'path': 'src/detectors/building_blocks/patterns/ascending_triangle.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'descending_triangle',
        'path': 'src/detectors/building_blocks/patterns/descending_triangle.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'symmetrical_triangle',
        'path': 'src/detectors/building_blocks/patterns/symmetrical_triangle.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'head_and_shoulders',
        'path': 'src/detectors/building_blocks/patterns/head_and_shoulders.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'inverse_head_and_shoulders',
        'path': 'src/detectors/building_blocks/patterns/inverse_head_and_shoulders.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'double_top',
        'path': 'src/detectors/building_blocks/patterns/double_top.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'double_bottom',
        'path': 'src/detectors/building_blocks/patterns/double_bottom.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'triple_top',
        'path': 'src/detectors/building_blocks/patterns/triple_top.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'triple_bottom',
        'path': 'src/detectors/building_blocks/patterns/triple_bottom.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'rising_wedge',
        'path': 'src/detectors/building_blocks/patterns/rising_wedge.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'falling_wedge',
        'path': 'src/detectors/building_blocks/patterns/falling_wedge.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'flag_pattern',
        'path': 'src/detectors/building_blocks/patterns/flag_pattern.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'pennant_pattern',
        'path': 'src/detectors/building_blocks/patterns/pennant_pattern.py',
        'param_grid': {
            'lookback': [15, 20, 25],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'cup_and_handle',
        'path': 'src/detectors/building_blocks/patterns/cup_and_handle.py',
        'param_grid': {
            'lookback': [25, 30, 35],
            'timeframe': ['15min']
        }
    },
    {
        'name': 'rounding_bottom',
        'path': 'src/detectors/building_blocks/patterns/rounding_bottom.py',
        'param_grid': {
            'lookback': [25, 30, 35],
            'timeframe': ['15min']
        }
    }
]


def optimize_single_block(args):
    """Optimize a single block (wrapper for multiprocessing)"""
    block_config, df_path = args
    
    # Load data in each process
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
            n_cores=None  # Use all cores within each block (blocks run sequentially)
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
    print(f"🌙 BATCH OPTIMIZER - PATTERN BLOCKS (MULTICORE)")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Blocks to optimize: {len(PATTERN_BLOCKS)}")
    print(f"CPU cores available: {cpu_count()}")
    print(f"Parallel blocks: {min(len(PATTERN_BLOCKS), max(1, cpu_count() // 4))}")
    print(f"Estimated time: 3-4 hours (parallel processing)")
    print(f"{'='*80}\n")
    
    # Load data once and save to temp file for multiprocessing
    print("📊 Loading BTC 15min data (180 days)...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Save data to temp pickle for multiprocessing
    import tempfile
    temp_data_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pkl').name
    df.to_pickle(temp_data_path)
    print(f"💾 Data cached for multiprocessing: {temp_data_path}\n")
    
    # Prepare arguments for multiprocessing
    args_list = [(block_config, temp_data_path) for block_config in PATTERN_BLOCKS]
    
    # Run blocks sequentially (no nested multiprocessing)
    # Each block will use all cores internally
    n_parallel = 1
    
    print(f"🚀 Starting parallel optimization ({n_parallel} blocks at a time)...\n")
    
    # Process blocks in parallel
    results_summary = []
    successful = 0
    failed = 0
    
    with Pool(n_parallel) as pool:
        results = pool.map(optimize_single_block, args_list)
    
    # Cleanup temp file
    os.unlink(temp_data_path)
    
    # Process results
    for result in results:
        if result:
            results_summary.append(result)
            if result['status'] == 'SUCCESS':
                successful += 1
            else:
                failed += 1
    
    # Save summary
    summary_path = Path(__file__).parent.parent / 'batch_patterns_optimization_summary.json'
    with open(summary_path, 'w') as f:
        json.dump({
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_blocks': len(PATTERN_BLOCKS),
            'successful': successful,
            'failed': failed,
            'results': results_summary
        }, f, indent=2)
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"🎉 BATCH OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total blocks: {len(PATTERN_BLOCKS)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/len(PATTERN_BLOCKS)*100):.1f}%")
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
