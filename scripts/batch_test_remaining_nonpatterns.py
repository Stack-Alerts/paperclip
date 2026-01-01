"""
Test Remaining Non-Pattern Blocks
Quick multicore test of likely untested blocks
"""

import sys
import os
from multiprocessing import Pool, cpu_count
import json
from pathlib import Path


def test_single_block(args):
    """Test block with imports inside for multiprocessing"""
    import pandas as pd
    from datetime import timedelta
    import importlib.util
    import sys
    import os
    
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from validate_advanced_signals import AdvancedSignalValidator
    
    block_info, data_path = args
    name = block_info['name']
    
    try:
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
        
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / block_info['path']
        
        if not block_path.exists():
            return {'name': name, 'error': 'File not found'}
        
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, block_info['class']):
            BlockClass = getattr(module, block_info['class'])
        else:
            for cls_name in dir(module):
                obj = getattr(module, cls_name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    BlockClass = obj
                    break
            else:
                return {'name': name, 'error': 'No class found'}
        
        block = BlockClass(timeframe='15min')
        
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
        
        validator = AdvancedSignalValidator(signal_type='general')
        validation_report = validator.validate_all_signals(signals)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🚀 TESTING REMAINING NON-PATTERN BLOCKS")
    print(f"{'='*80}\n")
    
    blocks_to_test = [
        {'name': 'OrderFlowImbalance', 'path': 'institutional/order_flow_imbalance.py', 
         'class': 'OrderFlowImbalance'},
        {'name': 'EmaCrossover', 'path': 'institutional/ema_crossover.py',
         'class': 'EmaCrossover'},
        {'name': 'VWAP', 'path': 'institutional/vwap.py',
         'class': 'VWAP'},
        {'name': 'PremiumDiscountZones', 'path': 'market_structure/premium_discount_zones.py',
         'class': 'PremiumDiscountZones'},
        {'name': 'RangeLiquidity', 'path': 'market_structure/range_liquidity.py',
         'class': 'RangeLiquidity'},
        {'name': 'SwingPoints', 'path': 'market_structure/swing_points.py',
         'class': 'SwingPoints'},
        {'name': 'SupplyDemandZones', 'path': 'supply_demand/supply_demand_zones.py',
         'class': 'SupplyDemandZones'},
    ]
    
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    args_list = [(block_info, str(data_path)) for block_info in blocks_to_test]
    
    cores = cpu_count()
    print(f"Using {cores} CPU cores")
    print(f"Testing {len(blocks_to_test)} blocks...\n")
    
    with Pool(processes=min(cores, len(blocks_to_test))) as pool:
        results_list = pool.map(test_single_block, args_list)
    
    results = {r['name']: r for r in results_list}
    
    print(f"\n{'='*80}")
    print(f"📊 RESULTS")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/{len(blocks_to_test)}")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/{len(blocks_to_test)}")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    print(f"\n📈 OVERALL")
    print(f"   Tested: {len(blocks_to_test)}/7")
    print(f"   Production Ready: {len(production_ready)}/{len(blocks_to_test)}")
    print(f"   NEW TOTAL: {48 + len(production_ready)}/67 ({(48 + len(production_ready))/67*100:.1f}%)")
    print(f"\n{'='*80}\n")
    
    with open('remaining_nonpattern_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("✅ Results saved\n")
    
    return results


if __name__ == "__main__":
    results = main()
