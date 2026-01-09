"""
Batch Test Multiple Metadata Blocks
Tests all metadata blocks systematically with appropriate validators

Metadata blocks to test (16 total, 1 complete):
1. ✅ ATR - Complete (95/100)
2. ADX - Trend strength
3-8. Price Levels - HOD, HOW, LOD, LOW, Asia 50%, US Settlement
9-10. Sessions - Kill Zones, Session High/Low
11. Fibonacci - Retracements
12-13. Volume - Profile, Analyzer
14-15. Institutional - Anchored VWAP, Market Depth
16. Keltner Channels
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


def test_metadata_block(block_path: Path, block_class_name: str, metadata_type: str, 
                       df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Test a single metadata block"""
    
    try:
        # Load block
        spec = importlib.util.spec_from_file_location("block", block_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get block class
        if hasattr(module, block_class_name):
            BlockClass = getattr(module, block_class_name)
        else:
            # Try to find any class with analyze method
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, 'analyze'):
                    BlockClass = obj
                    break
            else:
                return {'error': 'Could not find block class'}
        
        # Initialize block
        block = BlockClass(**kwargs)
        
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
            return {'error': 'No metadata returns generated'}
        
        # Validate
        validator = MetadataBlockValidator(metadata_type=metadata_type)
        validation_report = validator.validate_all_metadata(df, metadata_returns)
        
        return validation_report
        
    except Exception as e:
        return {'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🔬 BATCH METADATA BLOCK TESTING")
    print(f"{'='*80}\n")
    
    # Load data
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Define metadata blocks to test
    blocks_to_test = [
        # Already tested
        # {'name': 'ATR', 'path': 'volatility/atr.py', 'class': 'ATR', 'type': 'volatility', 
        #  'kwargs': {'period': 14, 'timeframe':'15min'}},
        # {'name': 'ADX', 'path': 'trend/adx.py', 'class': 'ADX', 'type': 'trend_strength',
        #  'kwargs': {'period': 14, 'timeframe': '15min'}},
        
        # Already tested price levels: LOD, HOD, HOW, LOW (all 100/100)
        
        # Remaining price levels
        {'name': 'Asia50%', 'path': 'price_levels/asia_session_50_percent.py', 'class': 'AsiaSession50Percent',
         'type': 'price_levels', 'kwargs': {'timeframe': '15min'}},
        
        {'name': 'USSettlement', 'path': 'price_levels/us_settlement.py', 'class': 'USSettlement',
         'type': 'price_levels', 'kwargs': {'timeframe': '15min'}},
    ]
    
    results = {}
    
    for block_info in blocks_to_test:
        name = block_info['name']
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / block_info['path']
        
        print(f"\n{'='*80}")
        print(f"Testing: {name}")
        print(f"{'='*80}\n")
        
        if not block_path.exists():
            print(f"❌ Block file not found: {block_path}")
            results[name] = {'error': 'File not found'}
            continue
        
        result = test_metadata_block(
            block_path=block_path,
            block_class_name=block_info['class'],
            metadata_type=block_info['type'],
            df=df,
            **block_info['kwargs']
        )
        
        results[name] = result
        
        if 'error' in result:
            print(f"❌ {name}: {result['error']}")
        elif result.get('production_ready'):
            print(f"✅ {name}: PRODUCTION READY")
            print(f"   Quality: {result['avg_quality_score']:.1f}/100")
            print(f"   Validity: {result['validity_rate']:.1f}%")
        else:
            print(f"⚠️  {name}: Needs Improvement")
            print(f"   Quality: {result.get('avg_quality_score', 0):.1f}/100")
            print(f"   Issues: {len(result.get('all_issues', []))}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 BATCH TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}")
    for name in production_ready:
        print(f"   - {name}: {results[name]['avg_quality_score']:.1f}/100")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}")
        for name in needs_work:
            print(f"   - {name}: {results[name].get('avg_quality_score', 0):.1f}/100")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for name in errors:
            print(f"   - {name}: {results[name]['error']}")
    
    print(f"\n{'='*80}\n")
    
    return results


if __name__ == "__main__":
    results = main()
