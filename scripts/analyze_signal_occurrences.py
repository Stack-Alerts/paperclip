"""
Signal Occurrence Analysis Script
Analyzes 180 days of BTC 15min data to count signal occurrences per building block

This provides users with historical frequency data for decision-making:
- How often does each signal occur?
- Which signals are rare vs common?
- What's the occurrence percentage?

Output: JSON cache with occurrence statistics for Strategy Builder UI

Author: Strategy Builder Team
Date: 2026-01-17
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detectors.building_blocks.registry import BlockRegistry


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """
    Load BTC 15min data for specified number of days.
    
    Args:
        days: Number of days to load (default 180)
        
    Returns:
        DataFrame with OHLCV data
    """
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.pkl'
    
    print(f"Loading BTC 15min data from: {data_path}")
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Load pickle file
    df = pd.read_pickle(data_path)
    
    # Ensure timestamp column
    if 'timestamp' not in df.columns and df.index.name == 'timestamp':
        df = df.reset_index()
    
    # Convert timestamp to datetime if needed
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df_filtered = df[df['timestamp'] >= cutoff_date].copy()
    
    print(f"Loaded {len(df_filtered)} candles from {df_filtered['timestamp'].min()} to {df_filtered['timestamp'].max()}")
    print(f"Date range: {(df_filtered['timestamp'].max() - df_filtered['timestamp'].min()).days} days")
    
    return df_filtered


def analyze_block_with_registry(block_name: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze a single building block using registry instantiation.
    
    Args:
        block_name: Name of the block
        df: Historical OHLCV data
        
    Returns:
        Dict with signal occurrence statistics
    """
    print(f"\n  Analyzing: {block_name}")
    
    # Get registry
    registry = BlockRegistry()
    
    # Get block metadata
    block_meta = registry.get_block(block_name)
    
    if not block_meta:
        print(f"  ❌ Block metadata not found: {block_name}")
        return {
            'block_name': block_name,
            'error': 'Block metadata not found',
            'signals': {}
        }
    
    # Instantiate block using registry
    try:
        block_instance = registry.instantiate(block_name)
    except Exception as e:
        print(f"  ❌ Failed to instantiate {block_name}: {e}")
        return {
            'block_name': block_name,
            'error': str(e),
            'signals': {}
        }
    
    # Get valid signals
    valid_signals = block_meta.valid_signals if hasattr(block_meta, 'valid_signals') else []
    
    # Initialize signal counters
    signal_counts = {signal: 0 for signal in valid_signals}
    total_candles = 0
    errors = 0
    
    # Sliding window analysis - analyze at each candle
    # Use minimum 40 candles for initial context
    min_lookback = 40
    
    for i in tqdm(range(min_lookback, len(df)), desc=f"    {block_name}", leave=False):
        # Get data up to current candle
        window_df = df.iloc[:i+1].copy()
        
        try:
            # Run block analysis
            result = block_instance.analyze(window_df)
            
            # Count signal occurrence
            signal = result.get('signal', 'ERROR')
            
            if signal in signal_counts:
                signal_counts[signal] += 1
            else:
                # Unexpected signal - should not happen with valid_signals
                print(f"    ⚠️  Unexpected signal: {signal}")
                if signal not in signal_counts:
                    signal_counts[signal] = 1
            
            total_candles += 1
            
        except Exception as e:
            errors += 1
            if errors <= 3:  # Only print first 3 errors
                print(f"    ⚠️  Analysis error at candle {i}: {e}")
    
    # Calculate percentages
    signal_stats = {}
    for signal, count in signal_counts.items():
        if total_candles > 0:
            percentage = (count / total_candles) * 100
        else:
            percentage = 0
        
        signal_stats[signal] = {
            'count': count,
            'percentage': round(percentage, 2),
            'total_candles': total_candles
        }
    
    # Sort by count descending
    signal_stats = dict(sorted(signal_stats.items(), key=lambda x: x[1]['count'], reverse=True))
    
    print(f"  ✅ Complete: {total_candles} candles analyzed, {errors} errors")
    print(f"     Top signals: {list(signal_stats.keys())[:3]}")
    
    return {
        'block_name': block_name,
        'total_candles': total_candles,
        'errors': errors,
        'signals': signal_stats
    }


def analyze_block_signals(block_name: str, block_class: type, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze a single building block across all data.
    
    Args:
        block_name: Name of the block
        block_class: Block class to instantiate
        df: Historical OHLCV data
        
    Returns:
        Dict with signal occurrence statistics
    """
    print(f"\n  Analyzing: {block_name}")
    
    # Initialize block
    try:
        block_instance = block_class()
    except Exception as e:
        print(f"  ❌ Failed to initialize {block_name}: {e}")
        return {
            'block_name': block_name,
            'error': str(e),
            'signals': {}
        }
    
    # Get valid signals from registry
    registry = BlockRegistry()
    block_meta = registry.get_block(block_name)
    
    if not block_meta:
        print(f"  ❌ Block metadata not found: {block_name}")
        return {
            'block_name': block_name,
            'error': 'Block metadata not found',
            'signals': {}
        }
    
    # BlockMetadata object - access valid_signals attribute
    valid_signals = block_meta.valid_signals if hasattr(block_meta, 'valid_signals') else []
    
    # Initialize signal counters
    signal_counts = {signal: 0 for signal in valid_signals}
    total_candles = 0
    errors = 0
    
    # Sliding window analysis - analyze at each candle
    # Use minimum 40 candles for initial context
    min_lookback = 40
    
    for i in tqdm(range(min_lookback, len(df)), desc=f"    {block_name}", leave=False):
        # Get data up to current candle
        window_df = df.iloc[:i+1].copy()
        
        try:
            # Run block analysis
            result = block_instance.analyze(window_df)
            
            # Count signal occurrence
            signal = result.get('signal', 'ERROR')
            
            if signal in signal_counts:
                signal_counts[signal] += 1
            else:
                # Unexpected signal - should not happen with valid_signals
                print(f"    ⚠️  Unexpected signal: {signal}")
                if signal not in signal_counts:
                    signal_counts[signal] = 1
            
            total_candles += 1
            
        except Exception as e:
            errors += 1
            if errors <= 3:  # Only print first 3 errors
                print(f"    ⚠️  Analysis error at candle {i}: {e}")
    
    # Calculate percentages
    signal_stats = {}
    for signal, count in signal_counts.items():
        if total_candles > 0:
            percentage = (count / total_candles) * 100
        else:
            percentage = 0
        
        signal_stats[signal] = {
            'count': count,
            'percentage': round(percentage, 2),
            'total_candles': total_candles
        }
    
    # Sort by count descending
    signal_stats = dict(sorted(signal_stats.items(), key=lambda x: x[1]['count'], reverse=True))
    
    print(f"  ✅ Complete: {total_candles} candles analyzed, {errors} errors")
    print(f"     Top signals: {list(signal_stats.keys())[:3]}")
    
    return {
        'block_name': block_name,
        'total_candles': total_candles,
        'errors': errors,
        'signals': signal_stats
    }


def analyze_all_blocks(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze all registered building blocks.
    
    Args:
        df: Historical OHLCV data
        
    Returns:
        Dict with all blocks' signal statistics
    """
    registry = BlockRegistry()
    all_blocks = registry.get_all_blocks()
    
    print(f"\n{'='*60}")
    print(f"ANALYZING {len(all_blocks)} BUILDING BLOCKS")
    print(f"{'='*60}")
    
    results = {}
    
    for idx, block_name in enumerate(all_blocks.keys(), 1):
        print(f"\n[{idx}/{len(all_blocks)}] Processing: {block_name}")
        
        try:
            # Use registry.instantiate() to get block instance
            # This handles all the dynamic import logic
            block_stats = analyze_block_with_registry(block_name, df)
            results[block_name] = block_stats
        except Exception as e:
            print(f"  ❌ Failed to analyze {block_name}: {e}")
            import traceback
            traceback.print_exc()
            results[block_name] = {
                'block_name': block_name,
                'error': str(e),
                'signals': {}
            }
    
    return results


def save_results(results: Dict[str, Any], output_path: Path):
    """
    Save analysis results to JSON file.
    
    Args:
        results: Analysis results
        output_path: Path to save JSON file
    """
    # Add metadata
    output = {
        'analysis_date': datetime.now().isoformat(),
        'data_timeframe': '15min',
        'data_days': 180,
        'total_blocks': len(results),
        'blocks': results
    }
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ RESULTS SAVED: {output_path}")
    print(f"{'='*60}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Total blocks analyzed: {len(results)}")
    
    # Count blocks with errors
    errors = sum(1 for r in results.values() if 'error' in r)
    print(f"  Blocks with errors: {errors}")
    
    # Show some interesting stats
    print(f"\nTop 10 most frequent signals across all blocks:")
    all_signals = []
    for block_name, block_data in results.items():
        if 'signals' in block_data and block_data['signals']:
            for signal, stats in block_data['signals'].items():
                # Skip ERROR and INSUFFICIENT_DATA
                if signal not in ['ERROR', 'INSUFFICIENT_DATA', 'NEUTRAL', 'NO_PATTERN']:
                    all_signals.append({
                        'block': block_name,
                        'signal': signal,
                        'count': stats['count'],
                        'percentage': stats['percentage']
                    })
    
    # Sort by count
    all_signals.sort(key=lambda x: x['count'], reverse=True)
    
    for i, sig in enumerate(all_signals[:10], 1):
        print(f"  {i:2d}. {sig['block']:30s} → {sig['signal']:25s}: {sig['count']:5d} ({sig['percentage']:5.2f}%)")


def main():
    """Main execution function."""
    print(f"\n{'='*60}")
    print(f"SIGNAL OCCURRENCE ANALYSIS")
    print(f"BTC 15min Data - 180 Days")
    print(f"{'='*60}")
    print(f"Started: {datetime.now()}")
    
    try:
        # Load data
        df = load_btc_data(days=180)
        
        # Analyze all blocks
        results = analyze_all_blocks(df)
        
        # Save results
        output_path = Path(__file__).parent.parent / 'data' / 'catalog' / 'signal_occurrence_statistics.json'
        save_results(results, output_path)
        
        print(f"\n✅ ANALYSIS COMPLETE!")
        print(f"Finished: {datetime.now()}")
        
    except Exception as e:
        print(f"\n❌ ANALYSIS FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
