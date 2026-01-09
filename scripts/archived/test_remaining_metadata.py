"""
Test Remaining 7 Pure Metadata Blocks
Excludes hybrid blocks (ADR, Bollinger, Ichimoku)

Tests with MetadataBlockValidator for data quality
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


def test_metadata_block(block_info: Dict, df: pd.DataFrame) -> Dict[str, Any]:
    """Test a single metadata block"""
    name = block_info['name']
    
    try:
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
        
        for i in range(window_size, len(df), 20):  # Sample every 20 bars
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
        
        # Validate metadata
        validator = MetadataBlockValidator(metadata_type=block_info['type'])
        validation_report = validator.validate_all_metadata(df, metadata_returns)
        validation_report['name'] = name
        
        return validation_report
        
    except Exception as e:
        return {'name': name, 'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🔬 REMAINING METADATA BLOCKS TEST")
    print(f"{'='*80}\n")
    
    # Load data
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Remaining pure metadata blocks
    blocks_to_test = [
        # Fibonacci (uses price_levels validator for now)
        {'name': 'Fibonacci', 'path': 'fibonacci/fibonacci_retracements.py', 
         'class': 'FibonacciRetracements', 'type': 'price_levels'},
        
        # Sessions (time-based, use price_levels for now)
        {'name': 'KillZones', 'path': 'sessions/kill_zones.py', 
         'class': 'KillZones', 'type': 'price_levels'},
        {'name': 'SessionTime', 'path': 'sessions/session_time.py', 
         'class': 'SessionTime', 'type': 'price_levels'},
        
        # Price Levels
        {'name': 'Asia50%', 'path': 'price_levels/asia_session_50_percent.py',
         'class': 'AsiaSession50Percent', 'type': 'price_levels'},
        {'name': 'USSettlement', 'path': 'price_levels/us_settlement.py',
         'class': 'USSettlement', 'type': 'price_levels'},
        
        # Institutional
        {'name': 'AnchoredVWAP', 'path': 'institutional/anchored_vwap.py',
         'class': 'AnchoredVWAP', 'type': 'price_levels'},
        {'name': 'MarketDepth', 'path': 'institutional/market_depth.py',
         'class': 'MarketDepth', 'type': 'price_levels'},
    ]
    
    results = {}
    
    for block_info in blocks_to_test:
        print(f"\n{'='*80}")
        print(f"Testing: {block_info['name']}")
        print(f"{'='*80}\n")
        
        result = test_metadata_block(block_info, df)
        results[result['name']] = result
        
        if 'error' in result:
            print(f"❌ {result['name']}: {result['error']}")
        elif result.get('production_ready'):
            print(f"✅ {result['name']}: PRODUCTION READY")
            print(f"   Quality: {result.get('avg_quality_score', 0):.1f}/100")
            print(f"   Validity: {result.get('validity_rate', 0):.1f}%")
        else:
            print(f"⚠️  {result['name']}: Needs Improvement")
            print(f"   Quality: {result.get('avg_quality_score', 0):.1f}/100")
            print(f"   Validity: {result.get('validity_rate', 0):.1f}%")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 REMAINING METADATA TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/7")
    for name in sorted(production_ready):
        print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/7")
        for name in sorted(needs_work):
            print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/7")
        for name in sorted(errors):
            print(f"   - {name}: {results[name]['error']}")
    
    # Impact
    print(f"\n📈 OVERALL IMPACT")
    print(f"   Metadata Blocks Tested: 7/7")
    print(f"   Production Ready: {len(production_ready)}/7")
    print(f"   Total Metadata: {6 + len(production_ready)}/16 ({(6 + len(production_ready))/16*100:.1f}%)")
    print(f"   Total Production: {33 + len(production_ready)}/67 ({(33 + len(production_ready))/67*100:.1f}%)")
    
    print(f"\n{'='*80}\n")
    
    return results


if __name__ == "__main__":
    results = main()
