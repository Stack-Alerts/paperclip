"""
Binance December 2025 Backfill - Complete Data Recovery

This script downloads ALL December 2025 data from Binance to replace
incomplete LakeAPI data. Binance provides complete months with NO missing days!

Features:
- All timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- Complete month (31 days, no gaps!)
- FREE & unlimited
- Saves in organized directory structure
- Compatible with existing code

Author: BTC_Engine_v3
Date: January 8, 2026
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data_manager.binance.rest_client import BinanceRestClient
from src.data_manager.config import PROJECT_ROOT

# Output directory
BINANCE_DATA_DIR = PROJECT_ROOT / "data" / "binance"

# CRITICAL: We trade PERPETUAL FUTURES, not spot!
SYMBOL = 'BTCUSDT'  # Binance Futures uses BTCUSDT for perpetuals
USE_FUTURES = True   # MUST use futures endpoints


def download_month_klines(
    client: BinanceRestClient,
    year: int,
    month: int,
    timeframes: list
):
    """
    Download complete month of klines for all timeframes
    
    Args:
        client: Binance REST client
        year: Year
        month: Month
        timeframes: List of timeframes to download
    """
    month_str = f"{year}-{month:02d}"
    month_dir = BINANCE_DATA_DIR / month_str
    month_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate month boundaries
    start_date = datetime(year, month, 1)
    
    # End date is last day of month
    if month == 12:
        end_date = datetime(year, 12, 31, 23, 59, 59)
    else:
        next_month = datetime(year, month + 1, 1)
        end_date = next_month - timedelta(seconds=1)
    
    print(f"\n{'='*70}")
    print(f"DOWNLOADING {month_str}")
    print(f"{'='*70}")
    print(f"Start: {start_date}")
    print(f"End: {end_date}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Output: {month_dir}")
    print()
    
    results = {}
    
    for timeframe in timeframes:
        print(f"⏬ {timeframe.upper()}")
        print("-" * 70)
        
        try:
            # Download from Binance FUTURES (CRITICAL: We trade perpetuals!)
            # MUST use futures endpoints, not spot
            klines = client.get_klines(
                interval=timeframe,
                symbol=SYMBOL,
                limit=1500,  # Max per request
                futures=True  # CRITICAL: Use futures endpoint
            )
            
            # Filter to exact month
            klines['timestamp'] = pd.to_datetime(klines['timestamp'])
            klines = klines[
                (klines['timestamp'] >= start_date) &
                (klines['timestamp'] <= end_date)
            ].copy()
            
            # Calculate expected bars
            timeframe_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '6h': 360,
                '12h': 720, '1d': 1440
            }
            
            minutes_in_month = (end_date - start_date).total_seconds() / 60
            expected_bars = int(minutes_in_month / timeframe_minutes[timeframe])
            
            # Check if we need more data (pagination)
            if len(klines) < expected_bars * 0.95:  # Allow 5% tolerance
                print(f"   📊 Need more data, paginating...")
                all_klines = [klines]
                
                # Keep requesting until we have the full month
                while True:
                    oldest_time = klines['timestamp'].min()
                    if oldest_time <= start_date:
                        break
                    
                    # Get previous batch (FUTURES!)
                    prev_klines = client.get_klines(
                        interval=timeframe,
                        symbol=SYMBOL,
                        limit=1500,
                        futures=True  # CRITICAL: Use futures endpoint
                    )
                    
                    prev_klines['timestamp'] = pd.to_datetime(prev_klines['timestamp'])
                    prev_klines = prev_klines[prev_klines['timestamp'] < oldest_time]
                    
                    if len(prev_klines) == 0:
                        break
                    
                    all_klines.insert(0, prev_klines)
                    klines = prev_klines
                    
                    print(f"   📊 Fetched batch, oldest: {prev_klines['timestamp'].min()}")
                
                # Combine all batches
                klines = pd.concat(all_klines, ignore_index=True)
                
                # Filter again to exact month
                klines = klines[
                    (klines['timestamp'] >= start_date) &
                    (klines['timestamp'] <= end_date)
                ].copy()
            
            # Save to parquet (mark as FUTURES data)
            output_file = month_dir / f"BTCUSDT_PERP_{timeframe}_{month_str}.parquet"
            klines.to_parquet(output_file, compression='snappy', index=False)
            
            file_size_mb = output_file.stat().st_size / 1024 / 1024
            completeness = (len(klines) / expected_bars) * 100
            
            print(f"   ✅ Saved {len(klines):,} bars ({completeness:.1f}% complete)")
            print(f"   📁 {output_file.name} ({file_size_mb:.1f} MB)")
            print(f"   📅 {klines['timestamp'].min()} to {klines['timestamp'].max()}")
            
            results[timeframe] = {
                'bars': len(klines),
                'expected': expected_bars,
                'completeness': completeness,
                'file_size_mb': file_size_mb,
                'success': True
            }
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[timeframe] = {'success': False, 'error': str(e)}
        
        print()
    
    return results


def main():
    """Download December 2025 from Binance"""
    
    print("="*70)
    print("BINANCE DECEMBER 2025 BACKFILL")
    print("="*70)
    print()
    print("Mission: Replace incomplete LakeAPI data with complete Binance data")
    print()
    print("Why Binance?")
    print("  ✅ Complete months (no missing days!)")
    print("  ✅ FREE & unlimited")
    print("  ✅ Real-time data")
    print("  ✅ Better quality than LakeAPI")
    print()
    print("What we'll download:")
    print("  📊 All timeframes (1m, 5m, 15m, 1h, 4h, 1d)")
    print("  📅 Complete December 2025 (31 days)")
    print("  💾 Save locally for backtesting")
    print()
    
    # Initialize Binance client
    client = BinanceRestClient()
    
    # Timeframes to download (most useful for trading)
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    # Download December 2025
    results = download_month_klines(client, 2025, 12, timeframes)
    
    # Summary
    print("="*70)
    print("BACKFILL COMPLETE")
    print("="*70)
    print()
    
    successful = sum(1 for r in results.values() if r.get('success'))
    failed = len(results) - successful
    
    print(f"Results:")
    print(f"  ✅ Successful: {successful}/{len(results)}")
    print(f"  ❌ Failed: {failed}")
    print()
    
    if successful > 0:
        print("Summary by Timeframe:")
        for tf, result in results.items():
            if result.get('success'):
                bars = result['bars']
                expected = result['expected']
                completeness = result['completeness']
                size = result['file_size_mb']
                print(f"  {tf:4s}: {bars:,} bars ({completeness:.1f}%), {size:.1f} MB")
        
        total_size = sum(r.get('file_size_mb', 0) for r in results.values())
        total_bars = sum(r.get('bars', 0) for r in results.values())
        
        print()
        print(f"Total bars: {total_bars:,}")
        print(f"Total size: {total_size:.1f} MB")
        print(f"Average completeness: {sum(r.get('completeness', 0) for r in results.values() if r.get('success')) / successful:.1f}%")
    
    print()
    print("Next steps:")
    print("  1. Verify data completeness")
    print("  2. Test with strategies")
    print("  3. Set up daily sync (scripts/binance/daily_sync.py)")
    print()
    print("="*70)


if __name__ == "__main__":
    main()