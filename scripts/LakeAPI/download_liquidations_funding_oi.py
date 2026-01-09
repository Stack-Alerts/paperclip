"""
Download Liquidations, Funding Rates, and Open Interest from Crypto-Lake API

This script downloads the missing data types needed for Layer TBD enhancements.
Uses the same monthly chunking approach as the existing orderbook/trades downloader.

Data Types:
- Liquidations: Liquidation events with price levels and volumes
- Funding: Funding rate snapshots for perpetual futures
- Open Interest: Open interest snapshots across exchanges

Author: BTC_Engine_LLM Team
Date: December 26, 2025
"""

from lakeapi import load_data
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import boto3
import gc
import sys
import os

# Get project root directory (two levels up from this script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Create boto3 session with Crypto-Lake credentials
session = boto3.Session(
    aws_access_key_id='REDACTED_AWS_KEY',
    aws_secret_access_key='REDACTED_AWS_SECRET',
    region_name='eu-west-1'
)

def get_month_ranges(start_year, end_year):
    """Generate monthly date ranges for download."""
    ranges = []
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Skip future months
            if year == end_year and month > datetime.now().month:
                break
                
            start_date = datetime(year, month, 1)
            
            # Calculate end date (last day of month)
            if month == 12:
                end_date = datetime(year, 12, 31)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # Don't go past today
            if end_date > datetime.now():
                end_date = datetime.now()
            
            ranges.append((
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                f"{year}-{month:02d}"
            ))
    
    return ranges

def download_chunk(table, start_date, end_date, chunk_name, data_type_name, force_redownload=False):
    """Download a single chunk of data."""
    try:
        # Check if file already exists (use absolute path from project root)
        output_dir = PROJECT_ROOT / "data" / "raw" / data_type_name
        output_file = output_dir / f"BTC-USDT_{data_type_name}_{chunk_name}.parquet"
        
        # Check if this is the current month
        now = datetime.now()
        current_month_str = f"{now.year}-{now.month:02d}"
        is_current_month = (chunk_name == current_month_str)
        
        if output_file.exists() and not force_redownload:
            file_size_mb = output_file.stat().st_size / 1024 / 1024
            
            if is_current_month:
                # Check file age for current month
                file_age_hours = (datetime.now().timestamp() - output_file.stat().st_mtime) / 3600
                
                if file_age_hours > 24:
                    print(f"  🔄 Re-downloading {chunk_name}... (outdated: {file_age_hours:.1f}h old)")
                    # Remove old file
                    output_file.unlink()
                else:
                    print(f"  ✅ Skipping {chunk_name}... (recent: {file_age_hours:.1f}h old, {file_size_mb:.1f} MB)")
                    return "skipped"
            else:
                print(f"  ✅ Skipping {chunk_name}... (already exists, {file_size_mb:.1f} MB)")
                return "skipped"
        
        print(f"  📥 Downloading {chunk_name}...", end='', flush=True)
        
        # Note: All futures-related data (liquidations, funding, open_interest) use BINANCE_FUTURES
        exchange = 'BINANCE_FUTURES' if table in ['liquidations', 'funding', 'open_interest'] else 'BINANCE'
        
        # Note: For BINANCE_FUTURES, symbol format includes -PERP suffix
        symbol = 'BTC-USDT-PERP' if exchange == 'BINANCE_FUTURES' else 'BTC-USDT'
        
        df = load_data(
            table=table,
            start=datetime.strptime(start_date, '%Y-%m-%d'),
            end=datetime.strptime(end_date, '%Y-%m-%d'),
            symbols=[symbol],
            exchanges=[exchange],
            boto3_session=session
        )
        
        if df is not None and not df.empty:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save immediately to disk
            df.to_parquet(output_file, compression='gzip')
            
            file_size_mb = output_file.stat().st_size / 1024 / 1024
            row_count = len(df)
            
            print(f" ✅ {row_count:,} rows, {file_size_mb:.1f} MB")
            
            # Free memory immediately
            del df
            gc.collect()
            
            return "downloaded"
        else:
            print(f" ⚠️  No data")
            return "no_data"
            
    except Exception as e:
        print(f" ❌ Error: {type(e).__name__}: {str(e)}")
        return "error"

def download_data_type(table, data_type_name, start_year, end_year):
    """Download all chunks for a data type."""
    print(f"\n{'='*80}")
    print(f"DOWNLOADING {data_type_name.upper().replace('_', ' ')}")
    print(f"{'='*80}")
    
    month_ranges = get_month_ranges(start_year, end_year)
    
    # Pre-scan to see what needs downloading (use absolute path from project root)
    output_dir = PROJECT_ROOT / "data" / "raw" / data_type_name
    now = datetime.now()
    current_month_str = f"{now.year}-{now.month:02d}"
    
    needs_download = []
    already_exists = []
    
    for start_date, end_date, chunk_name in month_ranges:
        output_file = output_dir / f"BTC-USDT_{data_type_name}_{chunk_name}.parquet"
        is_current_month = (chunk_name == current_month_str)
        
        if output_file.exists():
            if is_current_month:
                file_age_hours = (datetime.now().timestamp() - output_file.stat().st_mtime) / 3600
                if file_age_hours > 24:
                    needs_download.append(chunk_name)
                else:
                    already_exists.append(chunk_name)
            else:
                already_exists.append(chunk_name)
        else:
            needs_download.append(chunk_name)
    
    print(f"📊 Status: {len(already_exists)} exist, {len(needs_download)} need download")
    
    if needs_download:
        print(f"📥 Will download: {', '.join(needs_download)}")
    else:
        print(f"✅ All files up to date!")
    print()
    
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    no_data_count = 0
    
    for start_date, end_date, chunk_name in month_ranges:
        result = download_chunk(table, start_date, end_date, chunk_name, data_type_name)
        if result == "downloaded":
            downloaded_count += 1
        elif result == "skipped":
            skipped_count += 1
        elif result == "no_data":
            no_data_count += 1
        else:
            error_count += 1
        
        # Force garbage collection between chunks
        gc.collect()
    
    print(f"\n✅ Completed: {downloaded_count} downloaded, {skipped_count} skipped, {no_data_count} no data, {error_count} errors")
    return downloaded_count, error_count, no_data_count

def main():
    """Download liquidations, funding rates, and open interest data."""
    
    print("="*80)
    print("CRYPTO-LAKE DOWNLOADER - LIQUIDATIONS, FUNDING, OPEN INTEREST")
    print("="*80)
    print()
    print("This script downloads the MISSING data types for comprehensive analysis:")
    print()
    print("Data types to download:")
    print("  1. ⚡ Liquidations  - Liquidation events with price levels and volumes")
    print("  2. 💰 Funding Rates - Funding rate snapshots for perpetual futures")
    print("  3. 📊 Open Interest - Open interest snapshots across exchanges")
    print()
    print("Date range: Jan 2024 to TODAY")
    print("Chunk size: 1 month per download")
    print("Exchange: BINANCE (BTC-USDT perpetual futures)")
    print()
    print("Purpose:")
    print("  - Liquidations: Identify stop-loss clusters for Layer TBD level trading")
    print("  - Funding: Market sentiment and position bias analysis")
    print("  - Open Interest: Market participation and trend strength")
    print()
    print("Expected:")
    print("  - Download time: 1-2 hours (3 data types × 24 months)")
    print("  - Memory usage: < 4 GB (chunked downloads)")
    print("  - Disk space: ~10-15 GB additional")
    print()
    
    proceed = input("Proceed with download? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Download cancelled.")
        return
    
    # Download from Jan 2024 to today (matching existing data range)
    start_year = 2024
    end_year = datetime.now().year
    
    month_ranges = get_month_ranges(start_year, end_year)
    
    print()
    print(f"Starting download: Jan 2024 to Today")
    print(f"Total months: {len(month_ranges)}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Download each data type
    # All data types use BINANCE_FUTURES exchange
    data_types = [
        ('liquidations', 'liquidations'),
        ('funding', 'funding'),
        ('open_interest', 'open_interest'),
    ]
    
    total_downloaded = 0
    total_errors = 0
    total_no_data = 0
    
    for table, data_type_name in data_types:
        downloaded, errors, no_data = download_data_type(table, data_type_name, start_year, end_year)
        total_downloaded += downloaded
        total_errors += errors
        total_no_data += no_data
        
        # Small delay between data types
        gc.collect()
        print()
    
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print()
    print(f"Total chunks downloaded: {total_downloaded}")
    print(f"Total errors: {total_errors}")
    print(f"Total no data: {total_no_data}")
    print()
    print("Data saved to:")
    print("  - data/raw/liquidations/BTC-USDT_liquidations_YYYY-MM.parquet")
    print("  - data/raw/funding/BTC-USDT_funding_YYYY-MM.parquet")
    print("  - data/raw/open_interest/BTC-USDT_open_interest_YYYY-MM.parquet")
    print()
    print("NEXT STEPS:")
    print("1. Verify downloads:")
    print("   ls -lh data/raw/liquidations/")
    print("   ls -lh data/raw/funding/")
    print("   ls -lh data/raw/open_interest/")
    print()
    print("2. Inspect data structure:")
    print("   python3 -c \"import pandas as pd; df = pd.read_parquet('data/raw/liquidations/BTC-USDT_liquidations_2024-01.parquet'); print(df.head()); print(df.columns)\"")
    print()
    print("3. Integrate into Layer TBD:")
    print("   - Update layer_tbd_method.py to load liquidation data")
    print("   - Enhance _analyze_levels() with liquidation proximity scoring")
    print("   - Add funding rate bias to session analysis")
    print("   - Use open interest for trend strength validation")
    print()
    print("Documentation:")
    print("  - See docs/Layer_TBD/TBD_Data_Requirements_Analysis.md")
    print("  - See scripts/data_download/README_LIQUIDATIONS.md (will be created)")
    print()

if __name__ == "__main__":
    main()
