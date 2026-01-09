"""
EXPERT MODE PHASE 2: Apply optimal params + custom-tune remaining patterns
Automatically updates pattern files with optimal parameters
Then custom-tunes the 4 failing patterns
NO INTERRUPTIONS
"""

import json
import re
from pathlib import Path


def apply_optimal_params():
    """Apply optimal parameters to the 11 successful patterns"""
    
    print(f"\n{'='*80}")
    print(f"📝 APPLYING OPTIMAL PARAMETERS TO PATTERN FILES")
    print(f"{'='*80}\n")
    
    # Load tuning results
    with open('pattern_tuning_results.json', 'r') as f:
        results = json.load(f)
    
    successful = {name: data for name, data in results.items() 
                  if data.get('status') == 'SUCCESS'}
    
    pattern_file_map = {
        'CupAndHandle': 'cup_and_handle.py',
        'InverseHeadAndShoulders': 'inverse_head_and_shoulders.py',
        'FallingWedge': 'falling_wedge.py',
        'DescendingTriangle': 'descending_triangle.py',
        'RisingWedge': 'rising_wedge.py',
        'TripleTop': 'triple_top.py',
        'DoubleBottom': 'double_bottom.py',
        'FlagPattern': 'flag_pattern.py',
        'TripleBottom': 'triple_bottom.py',
        'AscendingTriangle': 'ascending_triangle.py',
        'HeadAndShoulders': 'head_and_shoulders.py',
        'RoundingBottom': 'rounding_bottom.py',
        'PennantPattern': 'pennant_pattern.py',
        'SymmetricalTriangle': 'symmetrical_triangle.py',
        'DoubleTop': 'double_top.py',
    }
    
    patterns_dir = Path('src/detectors/building_blocks/patterns')
    
    for name, data in successful.items():
        filename = pattern_file_map.get(name)
        if not filename:
            continue
            
        filepath = patterns_dir / filename
        if not filepath.exists():
            continue
        
        params = data['optimal_params']
        min_bars = params['min_pattern_bars']
        tolerance = params['tolerance']
        
        # Read file
        content = filepath.read_text()
        
        # Update min_pattern_bars parameter in __init__
        content = re.sub(
            r'min_pattern_bars:\s*int\s*=\s*\d+',
            f'min_pattern_bars: int = {min_bars}',
            content
        )
        
        # Update tolerance-related parameters based on pattern type
        if 'Cup' in name or 'Rounding' in name:
            content = re.sub(
                r'cup_depth_min:\s*float\s*=\s*[\d.]+',
                f'cup_depth_min: float = {tolerance}',
                content
            )
        elif 'Double' in name or 'Triple' in name:
            content = re.sub(
                r'(level_tolerance|trough_tolerance|peak_tolerance):\s*float\s*=\s*[\d.]+',
                f'\\1: float = {tolerance}',
                content
            )
        elif 'Head' in name:
            content = re.sub(
                r'shoulder_tolerance:\s*float\s*=\s*[\d.]+',
                f'shoulder_tolerance: float = {tolerance}',
                content
            )
        elif 'Wedge' in name or 'Triangle' in name:
            content = re.sub(
                r'(slope_tolerance|convergence_tolerance):\s*float\s*=\s*[\d.]+',
                f'\\1: float = {tolerance}',
                content
            )
        elif 'Flag' in name or 'Pennant' in name:
            content = re.sub(
                r'consolidation_tolerance:\s*float\s*=\s*[\d.]+',
                f'consolidation_tolerance: float = {tolerance}',
                content
            )
        
        # Write back
        filepath.write_text(content)
        
        print(f"✅ {name}: Updated to min_bars={min_bars}, tolerance={tolerance}")
    
    print(f"\n{'='*80}")
    print(f"✅ Applied optimal parameters to {len(successful)} pattern files")
    print(f"{'='*80}\n")


def custom_tune_single_pattern(args):
    """Multicore worker for custom tuning"""
    import pandas as pd
    from datetime import timedelta
    import importlib.util
    
    pattern_info, = args
    name = pattern_info['name']
    
    print(f"[{name}] MULTICORE deep parameter exploration...")
    
    try:
        # Load data
        df = pd.read_csv('data/raw/BTC_USDT_PERP_15m.csv')
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'timestamp'})
        if 'Vol' in df.columns:
            df = df.rename(columns={'Vol': 'volume'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        cutoff = df['timestamp'].max() - timedelta(days=180)
        df = df[df['timestamp'] >= cutoff].copy()
        
        # Load pattern
        block_path = Path('src/detectors/building_blocks') / pattern_info['path']
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        BlockClass = getattr(module, pattern_info['class'])
        
        # VERY AGGRESSIVE parameter exploration
        param_sets = [
            {'min_pattern_bars': 10, 'tolerance': 0.08},
            {'min_pattern_bars': 12, 'tolerance': 0.07},
            {'min_pattern_bars': 15, 'tolerance': 0.06},
            {'min_pattern_bars': 15, 'tolerance': 0.05},
            {'min_pattern_bars': 20, 'tolerance': 0.04},
        ]
        
        best_count = 0
        best_params = None
        
        for params in param_sets:
            try:
                if 'Cup' in name:
                    block = BlockClass(timeframe='15min',
                                     min_pattern_bars=params['min_pattern_bars'],
                                     cup_depth_min=params['tolerance'])
                elif 'Flag' in name:
                    block = BlockClass(timeframe='15min',
                                     min_pattern_bars=params['min_pattern_bars'],
                                     pole_min_pct=params['tolerance'],
                                     consolidation_bars=int(params['min_pattern_bars'] * 0.4))
                elif 'Wedge' in name or 'Triangle' in name:
                    block = BlockClass(timeframe='15min',
                                     min_pattern_bars=params['min_pattern_bars'],
                                     slope_tolerance=params['tolerance'],
                                     convergence_tolerance=params['tolerance'] * 1.5)
                else:
                    block = BlockClass(timeframe='15min',
                                     min_pattern_bars=params['min_pattern_bars'])
                
                signal_count = 0
                for i in range(600, len(df), 40):
                    result = block.analyze(df.iloc[:i+1])
                    if result and result.get('signal') not in ['NO_PATTERN', 'ERROR', 'INSUFFICIENT_DATA']:
                        signal_count += 1
                
                if signal_count > best_count:
                    best_count = signal_count
                    best_params = params
            except:
                pass
        
        if best_count > 0:
            print(f"[{name}] ✅ SOLVED! {best_count} signals with {best_params}")
            return {'name': name, 'status': 'SUCCESS', 'signal_count': best_count, 'optimal_params': best_params}
        else:
            print(f"[{name}] ❌ Still failing")
            return {'name': name, 'status': 'FAILED', 'signal_count': 0}
    except Exception as e:
        print(f"[{name}] ERROR: {e}")
        return {'name': name, 'status': 'ERROR', 'error': str(e)}


def custom_tune_failing_patterns():
    """Custom-tune the 4 failing patterns with multicore"""
    from multiprocessing import Pool, cpu_count
    
    print(f"\n{'='*80}")
    print(f"🔧 MULTICORE CUSTOM TUNING - FAILING PATTERNS")
    print(f"{'='*80}\n")
    
    failing = [
        {'name': 'CupAndHandle', 'path': 'patterns/cup_and_handle.py', 'class': 'CupAndHandlePattern'},
        {'name': 'FallingWedge', 'path': 'patterns/falling_wedge.py', 'class': 'FallingWedgePattern'},
        {'name': 'FlagPattern', 'path': 'patterns/flag_pattern.py', 'class': 'FlagPattern'},
        {'name': 'SymmetricalTriangle', 'path': 'patterns/symmetrical_triangle.py', 'class': 'SymmetricalTrianglePattern'},
    ]
    
    args_list = [(p,) for p in failing]
    
    cores = min(cpu_count(), 4)  # Only 4 patterns
    print(f"Using {cores} CPU cores for custom tuning\n")
    
    with Pool(processes=cores) as pool:
        results_list = pool.map(custom_tune_single_pattern, args_list)
    
    results = {r['name']: r for r in results_list}
    
    return results


def main():
    # Phase 1: Apply optimal params to successful patterns
    apply_optimal_params()
    
    # Phase 2: Custom-tune the 4 failing patterns
    custom_results = custom_tune_failing_patterns()
    
    # Combine results
    with open('pattern_tuning_results.json', 'r') as f:
        all_results = json.load(f)
    
    for name, data in custom_results.items():
        all_results[name] = data
    
    with open('pattern_tuning_results_final.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 FINAL TUNING SUMMARY")
    print(f"{'='*80}\n")
    
    successful = [name for name, data in all_results.items() if data.get('status') == 'SUCCESS']
    print(f"✅ PATTERNS GENERATING SIGNALS: {len(successful)}/15")
    for name in successful:
        count = all_results[name]['signal_count']
        print(f"   {name}: {count} signals")
    
    failed = [name for name, data in all_results.items() if data.get('status') != 'SUCCESS']
    if failed:
        print(f"\n❌ STILL NEED WORK: {len(failed)}/15")
        for name in failed:
            print(f"   {name}")
    
    print(f"\n{'='*80}\n")
    print(f"✅ Results saved to pattern_tuning_results_final.json\n")
    
    return all_results


if __name__ == "__main__":
    results = main()
