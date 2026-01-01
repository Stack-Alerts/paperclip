"""
MULTICORE Batch Pattern Testing
Tests all 15 untested patterns in PARALLEL for speed

Expected: 10-12 patterns to pass (67-80%)
Using all CPU cores for maximum speed
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
from typing import Dict, Any, List
from multiprocessing import Pool, cpu_count
import json


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'time' in col_lower and 'timestamp' not in df.columns:
            rename_map[col] = 'timestamp'
        elif col_lower == 'vol':
            rename_map[col] = 'volume'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    if df['timestamp'].dtype == 'object':
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)


def test_single_pattern(args):
    """Test a single pattern (for multiprocessing)"""
    # Import inside function for multiprocessing
    import pandas as pd
    from datetime import timedelta
    import importlib.util
    import sys
    import os
    
    # Add path inside subprocess
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from validate_advanced_signals import AdvancedSignalValidator
    
    pattern_info, data_path = args
    name = pattern_info['name']
    
    try:
        # Load data (each process loads its own copy)
        df = pd.read_csv(data_path)
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'timestamp'})
        if 'Vol' in df.columns:
            df = df.rename(columns={'Vol': 'volume'})
        
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        cutoff_date = df['timestamp'].max() - timedelta(days=180)
        df = df[df['timestamp'] >= cutoff_date].copy()
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        
        # Load block
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / pattern_info['path']
        
        if not block_path.exists():
            return {'name': name, 'error': 'File not found'}
        
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get block class
        if hasattr(module, pattern_info['class']):
            BlockClass = getattr(module, pattern_info['class'])
        else:
            for cls_name in dir(module):
                obj = getattr(module, cls_name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    BlockClass = obj
                    break
            else:
                return {'name': name, 'error': 'Could not find block class'}
        
        # Initialize block
        block = BlockClass(timeframe='15min')
        
        # Generate signals  
        signals = []
        window_size = 800
        
        for i in range(window_size, len(df), 20):  # Sample every 20 bars
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict) and result.get('signal') not in ['ERROR', 'INSUFFICIENT_DATA', 'NEUTRAL']:
                    signals.append({
                        'timestamp': hist_df['timestamp'].iloc[-1],
                        'signal': result.get('signal', ''),
                        'price': hist_df['close'].iloc[-1],
                        'confidence': result.get('confidence', 50)
                    })
            except:
                pass
        
        if len(signals) == 0:
            return {'name': name, 'error': 'No signals generated'}
        
        # Validate signals with flexible validator
        validator = AdvancedSignalValidator(signal_type='pattern')
        validation_report = validator.validate_all_signals(signals)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 MULTICORE BATCH PATTERN TESTING")
    print(f"{'='*80}\n")
    
    # Pattern blocks to test
    patterns_to_test = [
        {'name': 'CupAndHandle', 'path': 'patterns/cup_and_handle.py', 'class': 'CupAndHandle'},
        {'name': 'InverseHeadAndShoulders', 'path': 'patterns/inverse_head_and_shoulders.py', 'class': 'InverseHeadAndShoulders'},
        {'name': 'FallingWedge', 'path': 'patterns/falling_wedge.py', 'class': 'FallingWedge'},
        {'name': 'DescendingTriangle', 'path': 'patterns/descending_triangle.py', 'class': 'DescendingTriangle'},
        {'name': 'RisingWedge', 'path': 'patterns/rising_wedge.py', 'class': 'RisingWedge'},
        {'name': 'TripleTop', 'path': 'patterns/triple_top.py', 'class': 'TripleTop'},
        {'name': 'DoubleBottom', 'path': 'patterns/double_bottom.py', 'class': 'DoubleBottom'},
        {'name': 'FlagPattern', 'path': 'patterns/flag_pattern.py', 'class': 'FlagPattern'},
        {'name': 'TripleBottom', 'path': 'patterns/triple_bottom.py', 'class': 'TripleBottom'},
        {'name': 'AscendingTriangle', 'path': 'patterns/ascending_triangle.py', 'class': 'AscendingTriangle'},
        {'name': 'HeadAndShoulders', 'path': 'patterns/head_and_shoulders.py', 'class': 'HeadAndShoulders'},
        {'name': 'RoundingBottom', 'path': 'patterns/rounding_bottom.py', 'class': 'RoundingBottom'},
        {'name': 'PennantPattern', 'path': 'patterns/pennant_pattern.py', 'class': 'PennantPattern'},
        {'name': 'SymmetricalTriangle', 'path': 'patterns/symmetrical_triangle.py', 'class': 'SymmetricalTriangle'},
        {'name': 'DoubleTop', 'path': 'patterns/double_top.py', 'class': 'DoubleTop'},
    ]
    
    # Prepare data path
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    # Create args for multiprocessing
    args_list = [(pattern_info, str(data_path)) for pattern_info in patterns_to_test]
    
    # Multicore testing
    cores = cpu_count()
    print(f"Using {cores} CPU cores for parallel testing")
    print(f"Testing {len(patterns_to_test)} patterns...\n")
    
    with Pool(processes=cores) as pool:
        results_list = pool.map(test_single_pattern, args_list)
    
    # Convert to dict
    results = {r['name']: r for r in results_list}
    
    # Display results
    print(f"\n{'='*80}")
    print(f"📊 BATCH PATTERN TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/15")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
              f"({results[name].get('accuracy', 0):.1f}% accuracy, "
              f"{results[name].get('total_signals', 0)} signals)")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/15")
        for name in sorted(needs_work):
            print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
                  f"({results[name].get('accuracy', 0):.1f}% accuracy, "
                  f"{results[name].get('total_signals', 0)} signals)")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/15")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    # Overall stats
    total_tested = len([r for r in results.values() if 'error' not in r])
    success_rate = (len(production_ready) / total_tested * 100) if total_tested > 0 else 0
    
    print(f"\n📈 OVERALL STATISTICS")
    print(f"   Patterns Tested: {total_tested}/15")
    print(f"   Production Ready: {len(production_ready)}/15 ({success_rate:.1f}%)")
    print(f"   Impact: +{len(production_ready)} blocks to production total")
    print(f"   New Total: {55 + len(production_ready)}/67 ({(55 + len(production_ready))/67*100:.1f}%)")
    
    print(f"\n{'='*80}\n")
    
    # Save results
    with open('pattern_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Results saved to pattern_test_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
