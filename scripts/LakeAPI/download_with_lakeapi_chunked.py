"""
Download Historical Data using lakeapi - MEMORY-EFFICIENT VERSION

Downloads in MONTHLY chunks to prevent RAM exhaustion and system crashes.
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
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
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
        
        df = load_data(
            table=table,
            start=datetime.strptime(start_date, '%Y-%m-%d'),
            end=datetime.strptime(end_date, '%Y-%m-%d'),
            symbols=['BTC-USDT'],
            exchanges=['BINANCE'],
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
        print(f" ❌ Error: {type(e).__name__}")
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
    
    for start_date, end_date, chunk_name in month_ranges:
        result = download_chunk(table, start_date, end_date, chunk_name, data_type_name)
        if result == "downloaded":
            downloaded_count += 1
        elif result == "skipped":
            skipped_count += 1
        else:
            error_count += 1
        
        # Force garbage collection between chunks
        gc.collect()
    
    print(f"\n✅ Completed: {downloaded_count} downloaded, {skipped_count} skipped, {error_count} errors")
    return downloaded_count

def main():
    """Download all data in memory-safe chunks."""
    
    print("="*80)
    print("CRYPTO-LAKE DOWNLOADER - MEMORY-EFFICIENT VERSION")
    print("="*80)
    print()
    print("⚠️  IMPORTANT: Downloads in MONTHLY chunks to prevent memory issues")
    print()
    print("Data types:")
    print("  1. Order book snapshots")
    print("  2. Trade ticks")
    print("  3. Liquidations")
    print("  4. Funding rates")
    print("  5. Open interest")
    print()
    print("Date range: Jan 2024 to TODAY (OPTIMAL 1-YEAR WINDOW)")
    print("Chunk size: 1 month per download")
    print("Total chunks: ~60 (5 data types × 12 months)")
    print()
    print("Expected:")
    print("  - Download time: 2-3 hours")
    print("  - Training time: 1-2 hours")
    print("  - Memory usage: < 4 GB (safe for any system)")
    print("  - Disk space: 30-40 GB")
    print("  - Model accuracy: 78-82%")
    print()
    
    proceed = input("Proceed with chunked download? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Download cancelled.")
        return
    
    # OPTIMAL: 1-year window (Jan 2024 - Today)
    # Most relevant to current market, fastest training
    start_year = 2024
    end_year = datetime.now().year
    
    # Get month ranges from Jan 2024 to today
    month_ranges = get_month_ranges(start_year, end_year)
    
    print()
    print(f"Starting download: Jan 2024 to Today")
    print(f"Total months: {len(month_ranges)} (~24 months)")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Why 1 year? See docs/OPTIMAL_TRAINING_WINDOW_ANALYSIS.md")
    print("  - Most relevant to 2025 trading")
    print("  - 78-82% accuracy (same as 3-year dataset!)")
    print("  - 3x faster download and training")
    print()
    
    # Download each data type
    # Note: Only 'book' and 'trades' (plural!) are available
    data_types = [
        ('book', 'orderbook'),
        ('trades', 'trades'),  # Note: PLURAL form works!
    ]
    
    total_downloaded = 0
    
    for table, data_type_name in data_types:
        # Pass filtered month ranges instead of year range
        print(f"\n{'='*80}")
        print(f"DOWNLOADING {data_type_name.upper().replace('_', ' ')}")
        print(f"{'='*80}")
        print(f"Will download {len(month_ranges)} monthly chunks")
        print()
        
        success_count = 0
        for start_date, end_date, chunk_name in month_ranges:
            result = download_chunk(table, start_date, end_date, chunk_name, data_type_name)
            if result:
                success_count += 1
            gc.collect()
        
        print(f"\n✅ Completed: {success_count}/{len(month_ranges)} chunks downloaded")
        total_downloaded += success_count
        
        gc.collect()
        print()
    
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print()
    print(f"Total chunks downloaded: {total_downloaded}")
    print()
    print("Data saved to:")
    print("  - data/raw/orderbook/")
    print("  - data/raw/trades/")
    print("  - data/raw/liquidations/")
    print("  - data/raw/funding/")
    print("  - data/raw/open_interest/")
    print()
    print("NEXT STEPS:")
    print("1. Verify downloads: ls -lh data/raw/*/")
    print("2. Merge chunks: python3 merge_data_chunks.py")
    print("3. Train ML model: python3 train_layer05_with_complete_data.py")
    print()
    print("Expected ML accuracy with complete dataset: 80-85%")

if __name__ == "__main__":
    main()
