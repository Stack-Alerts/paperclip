"""
MULTICORE Non-Pattern Signal Block Testing
Tests Elliott Wave (2) + Wyckoff (3) = 5 blocks

All CPU cores for maximum speed
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
from typing import Dict, Any
from validate_walkforward_signals import SignalValidator
from multiprocessing import Pool, cpu_count
import json


def test_single_block(args):
    """Test a single signal block (for multiprocessing)"""
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
        
        # Validate signals
        validator = SignalValidator()
        validation_report = validator.validate_all_signals(df, signals)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 MULTICORE NON-PATTERN SIGNAL TESTING")
    print(f"{'='*80}\n")
    
    # Non-pattern signal blocks to test
    blocks_to_test = [
        # Elliott Wave (2)
        {'name': 'ElliottWaveCount', 'path': 'elliott_wave/elliott_wave_count.py', 'class': 'ElliottWaveCount'},
        {'name': 'ElliottWaveOscillator', 'path': 'elliott_wave/elliott_wave_oscillator.py', 'class': 'ElliottWaveOscillator'},
        
        # Wyckoff (3)
        {'name': 'WyckoffAccumulation', 'path': 'wyckoff/wyckoff_accumulation.py', 'class': 'WyckoffAccumulation'},
        {'name': 'WyckoffDistribution', 'path': 'wyckoff/wyckoff_distribution.py', 'class': 'WyckoffDistribution'},
        {'name': 'WyckoffReaccumulation', 'path': 'wyckoff/wyckoff_reaccumulation.py', 'class': 'WyckoffReaccumulation'},
    ]
    
    # Prepare data path
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    # Create args for multiprocessing
    args_list = [(block_info, str(data_path)) for block_info in blocks_to_test]
    
    # Multicore testing
    cores = cpu_count()
    print(f"Using {cores} CPU cores for parallel testing")
    print(f"Testing {len(blocks_to_test)} non-pattern signal blocks...\n")
    
    with Pool(processes=min(cores, len(blocks_to_test))) as pool:
        results_list = pool.map(test_single_block, args_list)
    
    # Convert to dict
    results = {r['name']: r for r in results_list}
    
    # Display results
    print(f"\n{'='*80}")
    print(f"📊 NON-PATTERN SIGNAL TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/5")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
              f"({results[name].get('accuracy', 0):.1f}% accuracy, "
              f"{results[name].get('total_signals', 0)} signals)")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/5")
        for name in sorted(needs_work):
            print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
                  f"({results[name].get('accuracy', 0):.1f}% accuracy, "
                  f"{results[name].get('total_signals', 0)} signals)")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/5")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    # Overall stats
    total_tested = len([r for r in results.values() if 'error' not in r])
    success_rate = (len(production_ready) / total_tested * 100) if total_tested > 0 else 0
    
    print(f"\n📈 OVERALL STATISTICS")
    print(f"   Blocks Tested: {total_tested}/5")
    print(f"   Production Ready: {len(production_ready)}/5 ({success_rate:.1f}%)")
    print(f"   Impact: +{len(production_ready)} signal blocks to production total")
    print(f"   New Total: {33 + len(production_ready)}/67 ({(33 + len(production_ready))/67*100:.1f}%)")
    
    print(f"\n{'='*80}\n")
    
    # Save results
    with open('nonpattern_signal_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Results saved to nonpattern_signal_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
