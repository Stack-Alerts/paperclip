"""
MULTICORE Batch Custom Metadata Testing  
Tests 10 remaining metadata blocks with custom validators in PARALLEL

Blocks:
- Fibonacci (fibonacci validator)
- Kill Zones, Session Time (session validator)
- Asia 50%, US Settlement (may need custom logic)
- Anchored VWAP, Market Depth (institutional validator)
- ADR, Bollinger Bands, Ichimoku (hybrid validator)

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
from validate_metadata_blocks import MetadataBlockValidator
from multiprocessing import Pool, cpu_count
import json


def test_single_metadata(args):
    """Test a single metadata block (for multiprocessing)"""
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
        
        # Generate metadata returns
        metadata_returns = []
        window_size = 800
        
        for i in range(window_size, len(df), 20):
            try:
                hist_df = df.iloc[:i+1].copy()
                result = block.analyze(hist_df)
                
                if result and isinstance(result, dict) and result.get('signal') not in ['ERROR', 'INSUFFICIENT_DATA']:
                    metadata_returns.append({
                        'timestamp': hist_df['timestamp'].iloc[-1],
                        'metadata': result.get('metadata', {}),
                        'signal': result.get('signal', ''),
                        'price': hist_df['close'].iloc[-1]
                    })
            except:
                pass
        
        if len(metadata_returns) == 0:
            return {'name': name, 'error': 'No metadata returns generated'}
        
        # Validate with custom validator
        validator = MetadataBlockValidator(metadata_type=block_info['validator_type'])
        validation_report = validator.validate_all_metadata(df, metadata_returns)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 MULTICORE CUSTOM METADATA TESTING")
    print(f"{'='*80}\n")
    
    # 10 remaining metadata blocks with custom validators
    blocks_to_test = [
        # Fibonacci
        {'name': 'Fibonacci', 'path': 'fibonacci/fibonacci_retracements.py', 
         'class': 'FibonacciRetracements', 'validator_type': 'fibonacci'},
        
        # Sessions
        {'name': 'KillZones', 'path': 'sessions/kill_zones.py', 
         'class': 'KillZones', 'validator_type': 'session'},
        {'name': 'SessionTime', 'path': 'sessions/session_time.py', 
         'class': 'SessionTime', 'validator_type': 'session'},
        
        # Complex price levels
        {'name': 'Asia50%', 'path': 'price_levels/asia_session_50_percent.py',
         'class': 'AsiaSession50Percent', 'validator_type': 'price_levels'},
        {'name': 'USSettlement', 'path': 'price_levels/us_settlement.py',
         'class': 'USSettlement', 'validator_type': 'price_levels'},
        
        # Institutional
        {'name': 'AnchoredVWAP', 'path': 'institutional/anchored_vwap.py',
         'class': 'AnchoredVWAP', 'validator_type': 'institutional'},
        {'name': 'MarketDepth', 'path': 'institutional/market_depth.py',
         'class': 'MarketDepth', 'validator_type': 'institutional'},
        
        # Hybrid blocks
        {'name': 'ADR', 'path': 'volatility/adr.py',
         'class': 'ADR', 'validator_type': 'hybrid'},
        {'name': 'BollingerBands', 'path': 'volatility/bollinger_bands.py',
         'class': 'BollingerBands', 'validator_type': 'hybrid'},
        {'name': 'IchimokuCloud', 'path': 'trend/ichimoku_cloud.py',
         'class': 'IchimokuCloud', 'validator_type': 'hybrid'},
    ]
    
    # Prepare data path
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    # Create args for multiprocessing
    args_list = [(block_info, str(data_path)) for block_info in blocks_to_test]
    
    # Multicore testing
    cores = cpu_count()
    print(f"Using {cores} CPU cores for parallel testing")
    print(f"Testing {len(blocks_to_test)} metadata blocks with custom validators...\n")
    
    with Pool(processes=min(cores, len(blocks_to_test))) as pool:
        results_list = pool.map(test_single_metadata, args_list)
    
    # Convert to dict
    results = {r['name']: r for r in results_list}
    
    # Display results
    print(f"\n{'='*80}")
    print(f"📊 CUSTOM METADATA TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/10")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100 "
              f"({results[name].get('validity_rate', 0):.1f}% validity)")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/10")
        for name in sorted(needs_work):
            print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100 "
                  f"({results[name].get('validity_rate', 0):.1f}% validity)")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/10")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    # Overall impact
    total_tested = len([r for r in results.values() if 'error' not in r])
    
    print(f"\n📈 OVERALL IMPACT")
    print(f"   Blocks Tested: {total_tested}/10")
    print(f"   Production Ready: {len(production_ready)}/10")
    print(f"   Total Metadata: {6 + len(production_ready)}/16 ({(6 + len(production_ready))/16*100:.1f}%)")
    print(f"   Total Production: {33 + len(production_ready)}/67 ({(33 + len(production_ready))/67*100:.1f}%)")
    
    print(f"\n{'='*80}\n")
    
    # Save results
    with open('custom_metadata_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Results saved to custom_metadata_results.json\n")
    
    return results


if __name__ == "__main__":
    results = main()
