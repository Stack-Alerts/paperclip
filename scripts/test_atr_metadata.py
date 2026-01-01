"""
Test ATR as Metadata Block
Uses MetadataBlockValidator to verify data quality

ATR is a risk management tool - validates:
- ATR value accuracy
- Stop-loss calculations
- Position sizing factors
- Data completeness
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util

from validate_metadata_blocks import MetadataBlockValidator


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Standardize columns
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
    
    # Filter to last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)


def test_atr_metadata():
    """Test ATR block as metadata (not signal)"""
    
    print(f"\n{'='*80}")
    print(f"🔬 TESTING ATR AS METADATA BLOCK")
    print(f"{'='*80}\n")
    
    # Load data
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Load ATR block
    block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / 'volatility' / 'atr.py'
    spec = importlib.util.spec_from_file_location("atr", block_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get ATR class
    ATR = module.ATR
    
    # Initialize ATR
    atr_block = ATR(period=14, timeframe='15min')
    
    # Generate metadata returns for all bars
    print(f"Generating ATR metadata for {len(df)} bars...")
    metadata_returns = []
    window_size = 800
    
    for i in range(window_size, len(df), 20):  # Sample every 20 bars for speed
        try:
            hist_df = df.iloc[:i+1].copy()
            result = atr_block.analyze(hist_df)
            
            if result and isinstance(result, dict) and result.get('signal') not in ['ERROR', 'INSUFFICIENT_DATA']:
                metadata_returns.append({
                    'timestamp': hist_df['timestamp'].iloc[-1],
                    'metadata': result.get('metadata', {}),
                    'signal': result.get('signal', ''),
                    'price': hist_df['close'].iloc[-1]
                })
        except Exception as e:
            pass
   
    print(f"✅ Generated {len(metadata_returns)} metadata returns\n")
    
    # Validate with metadata validator
    validator = MetadataBlockValidator(metadata_type='volatility')
    validation_report = validator.validate_all_metadata(df, metadata_returns)
    
    # Print results
    print(f"\n{'='*80}")
    print(f"🎯 ATR METADATA VALIDATION RESULTS")
    print(f"{'='*80}\n")
    print(f"Total Returns: {validation_report['total_returns']}")
    print(f"Valid Returns: {validation_report['valid_returns']}")
    print(f"Validity Rate: {validation_report['validity_rate']:.1f}%")
    print(f"Avg Quality Score: {validation_report['avg_quality_score']:.1f}/100")
    print(f"Production Ready: {'✅ YES' if validation_report['production_ready'] else '❌ NO'}")
    print(f"\n{'='*80}\n")
    
    return validation_report


if __name__ == "__main__":
    report = test_atr_metadata()
    
    # Summary
    if report['production_ready']:
        print("✅ ATR METADATA BLOCK: PRODUCTION READY")
        print(f"   Quality: {report['avg_quality_score']:.1f}/100")
        print(f"   Validity: {report['validity_rate']:.1f}%")
    else:
        print("❌ ATR METADATA BLOCK: NEEDS IMPROVEMENT")
        print(f"   Issues: {len(report['all_issues'])}")
        print(f"   Warnings: {len(report['all_warnings'])}")
