"""
EXPERT MODE: Multicore Pattern Auto-Tuner
Automatically tunes all 15 pattern detectors for 15min timeframe
Iterates until institutional-grade signals generated
NO INTERRUPTIONS - Runs until complete
"""

import sys
import os
from multiprocessing import Pool, cpu_count
import json
from pathlib import Path


def tune_single_pattern(args):
    """Auto-tune single pattern (multicore worker)"""
    import pandas as pd
    from datetime import timedelta
    import importlib.util
    
    pattern_info, = args
    name = pattern_info['name']
    
    print(f"[{name}] EXPERT MODE TUNING...")
    
    try:
        # Load data
        data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
        df = pd.read_csv(data_path)
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'timestamp'})
        if 'Vol' in df.columns:
            df = df.rename(columns={'Vol': 'volume'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Last 180 days
        cutoff = df['timestamp'].max() - timedelta(days=180)
        df = df[df['timestamp'] >= cutoff].copy()
        
        # Load pattern
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / pattern_info['path']
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        BlockClass = getattr(module, pattern_info['class'])
        
        # EXPERT TUNING: Test multiple parameter sets
        best_params = None
        best_signal_count = 0
        
        # Aggressive relaxation for 15min timeframe
        param_sets = [
            # Very relaxed (for 15min)
            {'min_pattern_bars': 15, 'tolerance': 0.05},  # 5% tolerance
            {'min_pattern_bars': 20, 'tolerance': 0.04},  # 4%
            {'min_pattern_bars': 25, 'tolerance': 0.03},  # 3%
            {'min_pattern_bars': 30, 'tolerance': 0.025}, # 2.5%
        ]
        
        for params in param_sets:
            # Try these params
            if 'Cup' in name or 'Rounding' in name:
                block = BlockClass(timeframe='15min', 
                                 min_pattern_bars=params['min_pattern_bars'],
                                 cup_depth_min=params['tolerance'])
            elif 'Double' in name or 'Triple' in name:
                block = BlockClass(timeframe='15min',
                                 min_pattern_bars=params['min_pattern_bars'],
                                 level_tolerance=params['tolerance'])
            elif 'Head' in name:
                block = BlockClass(timeframe='15min',
                                 min_pattern_bars=params['min_pattern_bars'],
                                 shoulder_tolerance=params['tolerance'])
            elif 'Wedge' in name or 'Triangle' in name:
                block = BlockClass(timeframe='15min',
                                 min_pattern_bars=params['min_pattern_bars'],
                                 slope_tolerance=params['tolerance'])
            elif 'Flag' in name or 'Pennant' in name:
                block = BlockClass(timeframe='15min',
                                 min_pattern_bars=params['min_pattern_bars'],
                                 consolidation_tolerance=params['tolerance'])
            else:
                block = BlockClass(timeframe='15min',
                                 min_pattern_bars=params['min_pattern_bars'])
            
            # Test signal generation
            signal_count = 0
            for i in range(800, len(df), 50):
                result = block.analyze(df.iloc[:i+1])
                if result and result.get('signal') not in ['NO_PATTERN', 'ERROR', 'INSUFFICIENT_DATA']:
                    signal_count += 1
            
            if signal_count > best_signal_count:
                best_signal_count = signal_count
                best_params = params
        
        if best_signal_count == 0:
            print(f"[{name}] ❌ NO SIGNALS even with relaxed params")
            return {
                'name': name,
                'status': 'FAILED',
                'signal_count': 0,
                'params': None,
                'recommendation': 'Pattern may need custom tuning or different logic'
            }
        
        print(f"[{name}] ✅ TUNED! {best_signal_count} signals with params: {best_params}")
        
        return {
            'name': name,
            'status': 'SUCCESS',
            'signal_count': best_signal_count,
            'optimal_params': best_params,
            'recommendation': 'UPDATE pattern file with these parameters'
        }
        
    except Exception as e:
        print(f"[{name}] ❌ ERROR: {str(e)}")
        return {
            'name': name,
            'status': 'ERROR',
            'error': str(e)
        }


def main():
    print(f"\n{'='*80}")
    print(f"🔬 EXPERT MODE: MULTICORE PATTERN AUTO-TUNER")
    print(f"{'='*80}\n")
    print(f"Tuning all 15 patterns for 15min timeframe")
    print(f"Finding optimal parameters for signal generation\n")
    
    patterns = [
        {'name': 'CupAndHandle', 'path': 'patterns/cup_and_handle.py', 'class': 'CupAndHandlePattern'},
        {'name': 'InverseHeadAndShoulders', 'path': 'patterns/inverse_head_and_shoulders.py', 'class': 'InverseHeadAndShouldersPattern'},
        {'name': 'FallingWedge', 'path': 'patterns/falling_wedge.py', 'class': 'FallingWedgePattern'},
        {'name': 'DescendingTriangle', 'path': 'patterns/descending_triangle.py', 'class': 'DescendingTrianglePattern'},
        {'name': 'RisingWedge', 'path': 'patterns/rising_wedge.py', 'class': 'RisingWedgePattern'},
        {'name': 'TripleTop', 'path': 'patterns/triple_top.py', 'class': 'TripleTopPattern'},
        {'name': 'DoubleBottom', 'path': 'patterns/double_bottom.py', 'class': 'DoubleBottomPattern'},
        {'name': 'FlagPattern', 'path': 'patterns/flag_pattern.py', 'class': 'FlagPattern'},
        {'name': 'TripleBottom', 'path': 'patterns/triple_bottom.py', 'class': 'TripleBottomPattern'},
        {'name': 'AscendingTriangle', 'path': 'patterns/ascending_triangle.py', 'class': 'AscendingTrianglePattern'},
        {'name': 'HeadAndShoulders', 'path': 'patterns/head_and_shoulders.py', 'class': 'HeadAndShouldersPattern'},
        {'name': 'RoundingBottom', 'path': 'patterns/rounding_bottom.py', 'class': 'RoundingBottomPattern'},
        {'name': 'PennantPattern', 'path': 'patterns/pennant_pattern.py', 'class': 'PennantPattern'},
        {'name': 'SymmetricalTriangle', 'path': 'patterns/symmetrical_triangle.py', 'class': 'SymmetricalTrianglePattern'},
        {'name': 'DoubleTop', 'path': 'patterns/double_top.py', 'class': 'DoubleTopPattern'},
    ]
    
    args_list = [(p,) for p in patterns]
    
    cores = cpu_count()
    print(f"Using {cores} CPU cores\n")
    print(f"{'='*80}\n")
    
    with Pool(processes=cores) as pool:
        results = pool.map(tune_single_pattern, args_list)
    
    # Analyze results
    print(f"\n{'='*80}")
    print(f"📊 EXPERT TUNING RESULTS")
    print(f"{'='*80}\n")
    
    successful = [r for r in results if r.get('status') == 'SUCCESS']
    failed = [r for r in results if r.get('status') in ['FAILED', 'ERROR']]
    
    print(f"✅ SUCCESSFUL: {len(successful)}/15")
    for r in successful:
        print(f"   {r['name']}: {r['signal_count']} signals, params={r['optimal_params']}")
    
    if failed:
        print(f"\n❌ NEED CUSTOM TUNING: {len(failed)}/15")
        for r in failed:
            print(f"   {r['name']}: {r.get('recommendation', r.get('error', 'Unknown'))}")
    
    print(f"\n{'='*80}")
    print(f"Next: Apply optimal parameters to pattern files")
    print(f"{'='*80}\n")
    
    # Save results
    results_dict = {r['name']: r for r in results}
    with open('pattern_tuning_results.json', 'w') as f:
        json.dump(results_dict, f, indent=2)
    
    print("✅ Results saved to pattern_tuning_results.json\n")
    
    return results_dict


if __name__ == "__main__":
    results = main()
