"""
Batch Test Untested Pattern Signal Blocks
Tests all pattern blocks that haven't been validated yet

Expected: 10-12 patterns to pass (62-75% success rate)
Patterns are tested with DirectionalSignalValidator (walk-forward)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
from typing import Dict, Any, List
from validate_walkforward_signals import SignalValidator


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


def test_pattern_block(block_path: Path, block_class_name: str, 
                      df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Test a single pattern block"""
    
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
        
        # Generate signals using walk-forward
        signals = []
        window_size = 800  # Start after enough history
        
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
            return {'error': 'No signals generated'}
        
        # Validate signals
        validator = SignalValidator()
        validation_report = validator.validate_all_signals(df, signals)
        
        return validation_report
        
    except Exception as e:
        return {'error': str(e)}


def main():
    print(f"\n{'='*80}")
    print(f"🔬 BATCH PATTERN BLOCK TESTING")
    print(f"{'='*80}\n")
    
    # Load data
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Define untested pattern blocks
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
    
    results = {}
    
    for pattern_info in patterns_to_test:
        name = pattern_info['name']
        block_path = Path(__file__).parent.parent / 'src' / 'detectors' / 'building_blocks' / pattern_info['path']
        
        print(f"\n{'='*80}")
        print(f"Testing: {name}")
        print(f"{'='*80}\n")
        
        if not block_path.exists():
            print(f"❌ Block file not found: {block_path}")
            results[name] = {'error': 'File not found'}
            continue
        
        result = test_pattern_block(
            block_path=block_path,
            block_class_name=pattern_info['class'],
            df=df,
            timeframe='15min'
        )
        
        results[name] = result
        
        if 'error' in result:
            print(f"❌ {name}: {result['error']}")
        elif result.get('production_ready'):
            print(f"✅ {name}: PRODUCTION READY")
            print(f"   Quality: {result.get('quality_score', 0):.1f}/100")
            print(f"   Accuracy: {result.get('accuracy', 0):.1f}%")
            print(f"   Signals: {result.get('total_signals', 0)}")
        else:
            print(f"⚠️  {name}: Needs Improvement")
            print(f"   Quality: {result.get('quality_score', 0):.1f}/100")
            print(f"   Accuracy: {result.get('accuracy', 0):.1f}%")
            print(f"   Signals: {result.get('total_signals', 0)}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 BATCH PATTERN TEST SUMMARY")
    print(f"{'='*80}\n")
    
    production_ready = [name for name, result in results.items() if result.get('production_ready')]
    needs_work = [name for name, result in results.items() if not result.get('production_ready') and 'error' not in result]
    errors = [name for name, result in results.items() if 'error' in result]
    
    print(f"✅ Production Ready: {len(production_ready)}/15")
    for name in production_ready:
        print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
              f"({results[name].get('accuracy', 0):.1f}% accuracy, "
              f"{results[name].get('total_signals', 0)} signals)")
    
    if needs_work:
        print(f"\n⚠️  Needs Work: {len(needs_work)}/15")
        for name in needs_work:
            print(f"   - {name}: {results[name].get('quality_score', 0):.1f}/100 "
                  f"({results[name].get('accuracy', 0):.1f}% accuracy)")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}/15")
        for name in errors:
            print(f"   - {name}: {results[name]['error']}")
    
    # Overall stats
    total_tested = len([r for r in results.values() if 'error' not in r])
    success_rate = (len(production_ready) / total_tested * 100) if total_tested > 0 else 0
    
    print(f"\n📈 OVERALL PATTERN STATISTICS")
    print(f"   Tested: {total_tested}/15 patterns")
    print(f"   Production Ready: {len(production_ready)}/15 ({success_rate:.1f}%)")
    print(f"   Expected Impact: +{len(production_ready)} blocks to production total")
    
    print(f"\n{'='*80}\n")
    
    return results


if __name__ == "__main__":
    results = main()
