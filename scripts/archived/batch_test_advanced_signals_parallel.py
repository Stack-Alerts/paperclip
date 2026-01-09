"""
MULTICORE Batch Test Advanced Signals
Tests 5 non-pattern signal blocks with advanced validator

Elliott Wave (2) + Wyckoff (3)
All generate signals, need flexible validation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from multiprocessing import Pool, cpu_count
import json
from pathlib import Path


def test_single_block(args):
    """Test a single advanced signal block - ALL IMPORTS INSIDE FOR MULTIPROCESSING"""
    # Import inside function for multiprocessing
    import pandas as pd
    from datetime import timedelta
    import importlib.util
    import sys
    import os
    
    # Add path inside subprocess
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from validate_advanced_signals import AdvancedSignalValidator
    
    block_info, data_path = args
    name = block_info['name']
    
    try:
        # Load data
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
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / block_info['path']
        
        if not block_path.exists():
            return {'name': name, 'error': 'File not found'}
        
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get block class
        if hasattr(module, block_info['class']):
            BlockClass = getattr(module, block_info['class'])
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
        
        for i in range(window_size, len(df), 20):
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict):
                    signals.append(result)
            except:
                pass
        
        if len(signals) == 0:
            return {'name': name, 'error': 'No signals generated'}
        
        # Validate with advanced validator
        validator = AdvancedSignalValidator(signal_type=block_info['type'])
        validation_report = validator.validate_all_signals(signals)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 MULTICORE ADVANCED SIGNAL TESTING")
    print(f"{'='*80}\n")
    
    # 5 non-pattern signal blocks
    blocks_to_test = [
        # Elliott Wave
        {'name': 'ElliottWaveCount', 'path': 'elliott_wave/elliott_wave_count.py', 
         'class': 'ElliottWaveCount', 'type': 'elliott_wave'},
        {'name': 'ElliottWaveOscillator', 'path': 'elliott_wave/elliott_wave_oscillator.py', 
         'class': 'ElliottWaveOscillator', 'type': 'elliott_wave'},
        
        # Wyckoff
        {'name': 'WyckoffAccumulation', 'path': 'wyckoff/wyckoff_accumulation.py',
         'class': 'WyckoffAccumulation', 'type': 'wyckoff'},
        {'name': 'WyckoffDistribution', 'path': 'wyckoff/wyckoff_distribution.py',
         'class': 'WyckoffDistribution', 'type': 'wyckoff'},
        {'name': 'WyckoffReaccumulation', 'path': 'wyckoff/wyckoff_reaccumulation.py',
         'class': 'WyckoffReaccumulation', 'type': 'wyckoff'},
    ]
    
    # Prepare data path
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    # Create args for multiprocessing
    args_list = [(block_info, str(data_path)) for block_info in blocks_to_test]
    
    # Multicore testing
    cores = cpu_count()
    print(f"Using {cores} CPU cores for parallel testing")
    print(f"Testing {len(blocks_to_test)} advanced signal blocks...\n")
    
    with Pool(processes=min(cores, len(blocks_to_test))) as pool:
        results_list = pool.map(test_single_block, args_list)
    
    # Convert to dict
    results = {r['name']: r for r in results_list}
    
    # Display results
    print(f"\n{'='*80}")
    print(f"📊 ADVANCED SIGNAL TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/5")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100 "
              f"({results[name].get('validity_rate', 0):.1f}% validity)")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/5")
        for name in sorted(needs_work):
            print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100 "
                  f"({results[name].get('validity_rate', 0):.1f}% validity)")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/5")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    # Overall impact
    print(f"\n📈 OVERALL IMPACT")
    print(f"   Non-Pattern Signals Tested: 5/5")
    print(f"   Production Ready: {len(production_ready)}/5")
    print(f"   Total Production: {43 + len(production_ready)}/67 ({(43 + len(production_ready))/67*100:.1f}%)")
    
    print(f"\n{'='*80}\n")
    
    # Save results
    with open('advanced_signal_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Results saved to advanced_signal_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
