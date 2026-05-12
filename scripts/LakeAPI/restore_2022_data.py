"""
Restore 2022 data that was accidentally deleted
"""

from lakeapi import load_data
import pandas as pd
from pathlib import Path
from datetime import datetime
import boto3
import gc

# Create boto3 session with Crypto-Lake credentials
import os
session = boto3.Session(
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name='eu-west-1'
)

def download_month(table, year, month, data_type_name):
    """Download a specific month of data."""
    chunk_name = f"{year}-{month:02d}"
    output_dir = Path(f"data/raw/{data_type_name}")
    output_file = output_dir / f"BTC-USDT_{data_type_name}_{chunk_name}.parquet"
    
    if output_file.exists():
        print(f"✅ {chunk_name} already exists, skipping")
        return True
    
    print(f"📥 Downloading {data_type_name} {chunk_name}...", end='', flush=True)
    
    try:
        # Calculate start and end dates
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year, 12, 31)
        else:
            from datetime import timedelta
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        df = load_data(
            table=table,
            start=start_date,
            end=end_date,
            symbols=['BTC-USDT'],
            exchanges=['BINANCE'],
            boto3_session=session
        )
        
        if df is not None and not df.empty:
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_file, compression='gzip')
            
            file_size_mb = output_file.stat().st_size / 1024 / 1024
            row_count = len(df)
            
            print(f" ✅ {row_count:,} rows, {file_size_mb:.1f} MB")
            
            del df
            gc.collect()
            return True
        else:
            print(f" ⚠️  No data")
            return False
            
    except Exception as e:
        print(f" ❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("RESTORING 2022 DATA")
    print("="*80)
    print()
    
    # Restore orderbook 2022-11
    print("Restoring orderbook data...")
    download_month('book', 2022, 11, 'orderbook')
    
    print("\nRestoring trades data...")
    # Restore trades 2022-03 through 2022-11
    for month in range(3, 12):
        download_month('trades', 2022, month, 'trades')
        gc.collect()
    
    print("\n" + "="*80)
    print("RESTORE COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
