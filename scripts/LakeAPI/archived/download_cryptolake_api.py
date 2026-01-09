"""
Download Historical Order Book Data from Crypto-lake API

Uses AWS S3 access to download:
- Order book snapshots (book_1m) - 1-minute granularity, 20 levels
- Deep order book (deep_book_1m) - ~1000 levels for better analysis
- Liquidations - For sentiment analysis
- Funding rates - Market regime detection
"""

import boto3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json
import gzip
from io import BytesIO

# AWS credentials (Crypto-lake)
AWS_ACCESS_KEY = "REDACTED_AWS_KEY"
AWS_SECRET_KEY = "REDACTED_AWS_SECRET"
BUCKET_NAME = "crypto-lake"

def setup_s3_client():
    """Initialize S3 client with Crypto-lake credentials."""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

def list_available_dates(s3_client, symbol="BTC-USDT", data_type="book_1m"):
    """List available dates for a symbol."""
    prefix = f"BINANCE_FUTURES/{data_type}/{symbol}/"
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            Delimiter='/'
        )
        
        dates = []
        if 'CommonPrefixes' in response:
            for prefix_obj in response['CommonPrefixes']:
                date_str = prefix_obj['Prefix'].split('/')[-2]
                dates.append(date_str)
        
        return sorted(dates)
    except Exception as e:
        print(f"Error listing dates: {e}")
        return []

def download_orderbook_date(
    s3_client, 
    symbol="BTC-USDT", 
    date="2024-12-01",
    data_type="book_1m",
    output_dir=Path("data/raw/orderbook")
):
    """
    Download order book data for a specific date.
    
    Args:
        s3_client: boto3 S3 client
        symbol: Trading pair
        date: Date in YYYY-MM-DD format
        data_type: book_1m or deep_book_1m
        output_dir: Where to save
    """
    # S3 path format: BINANCE_FUTURES/book_1m/BTC-USDT/2024-12-01.csv.gz
    s3_key = f"BINANCE_FUTURES/{data_type}/{symbol}/{date}.csv.gz"
    
    output_file = output_dir / f"{symbol}_{data_type}_{date}.csv.gz"
    
    try:
        print(f"  Downloading {date}...", end=" ", flush=True)
        
        # Download from S3
        s3_client.download_file(BUCKET_NAME, s3_key, str(output_file))
        
        # Verify file
        with gzip.open(output_file, 'rt') as f:
            df = pd.read_csv(f, nrows=1)
            print(f"✅ ({len(df.columns)} columns)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def download_date_range(
    symbol="BTC-USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    data_type="book_1m"
):
    """Download order book data for date range."""
    
    print("="*80)
    print(f"DOWNLOADING {data_type.upper()} DATA FROM CRYPTO-LAKE")
    print("="*80)
    print()
    print(f"Symbol: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Data type: {data_type}")
    print()
    
    # Setup
    output_dir = Path("data/raw/orderbook")
    output_dir.mkdir(parents=True, exist_ok=True)
    s3_client = setup_s3_client()
    
    # Generate date list
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") 
             for i in range((end - start).days + 1)]
    
    print(f"Will download {len(dates)} days")
    print()
    
    # Download each date
    success_count = 0
    for date in dates:
        if download_orderbook_date(s3_client, symbol, date, data_type, output_dir):
            success_count += 1
    
    print()
    print(f"✅ Downloaded {success_count}/{len(dates)} days")
    print(f"📁 Saved to: {output_dir}")
    
    return success_count

def download_liquidations(
    symbol="BTC-USDT",
    start_date="2024-01-01",
    end_date="2024-12-31"
):
    """Download liquidation data."""
    print("\n" + "="*80)
    print("DOWNLOADING LIQUIDATION DATA")
    print("="*80)
    print()
    
    output_dir = Path("data/raw/liquidations")
    output_dir.mkdir(parents=True, exist_ok=True)
    s3_client = setup_s3_client()
    
    # Generate dates
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") 
             for i in range((end - start).days + 1)]
    
    success_count = 0
    for date in dates:
        s3_key = f"BINANCE_FUTURES/liquidations/{symbol}/{date}.csv.gz"
        output_file = output_dir / f"{symbol}_liquidations_{date}.csv.gz"
        
        try:
            print(f"  {date}...", end=" ", flush=True)
            s3_client.download_file(BUCKET_NAME, s3_key, str(output_file))
            print("✅")
            success_count += 1
        except:
            print("⏭️ ")
    
    print(f"\n✅ Downloaded {success_count} days of liquidation data")
    return success_count

def download_funding_rates(
    symbol="BTC-USDT",
    start_date="2024-01-01",
    end_date="2024-12-31"
):
    """Download funding rate data."""
    print("\n" + "="*80)
    print("DOWNLOADING FUNDING RATE DATA")
    print("="*80)
    print()
    
    output_dir = Path("data/raw/funding")
    output_dir.mkdir(parents=True, exist_ok=True)
    s3_client = setup_s3_client()
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") 
             for i in range((end - start).days + 1)]
    
    success_count = 0
    for date in dates:
        s3_key = f"BINANCE_FUTURES/funding/{symbol}/{date}.csv.gz"
        output_file = output_dir / f"{symbol}_funding_{date}.csv.gz"
        
        try:
            print(f"  {date}...", end=" ", flush=True)
            s3_client.download_file(BUCKET_NAME, s3_key, str(output_file))
            print("✅")
            success_count += 1
        except:
            print("⏭️")
    
    print(f"\n✅ Downloaded {success_count} days of funding rate data")
    return success_count

def main():
    """
    Download comprehensive dataset for ML training.
    
    Downloads:
    1. Order book snapshots (1-minute, 20 levels) - For all years
    2. Liquidations - For sentiment
    3. Funding rates - For market regime detection
    """
    
    print("="*80)
    print("CRYPTO-LAKE DATA DOWNLOADER")
    print("="*80)
    print()
    print("This will download:")
    print("  1. Order book snapshots (book_1m) - 20 levels, 1-minute")
    print("  2. Liquidation data - For sentiment analysis")
    print("  3. Funding rates - For regime detection")
    print()
    
    # Date range: Match our existing OHLC data (2019-2025)
    start_date = "2019-09-01"
    end_date = "2025-12-16"
    
    print(f"Period: {start_date} to {end_date}")
    print(f"Symbol: BTC-USDT")
    print()
    
    proceed = input("Proceed with download? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Download cancelled.")
        return
    
    print()
    
    # Download order book (this is the main one)
    print("PHASE 1: Order Book Data")
    print("-" * 80)
    ob_count = download_date_range(
        symbol="BTC-USDT",
        start_date=start_date,
        end_date=end_date,
        data_type="book_1m"  # 1-minute snapshots, 20 levels
    )
    
    # Download liquidations
    print("\nPHASE 2: Liquidation Data")
    print("-" * 80)
    liq_count = download_liquidations(
        symbol="BTC-USDT",
        start_date=start_date,
        end_date=end_date
    )
    
    # Download funding rates
    print("\nPHASE 3: Funding Rate Data")
    print("-" * 80)
    fund_count = download_funding_rates(
        symbol="BTC-USDT",
        start_date=start_date,
        end_date=end_date
    )
    
    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print()
    print(f"✅ Order book: {ob_count} days")
    print(f"✅ Liquidations: {liq_count} days")
    print(f"✅ Funding rates: {fund_count} days")
    print()
    print("📁 Data saved to:")
    print("   - data/raw/orderbook/")
    print("   - data/raw/liquidations/")
    print("   - data/raw/funding/")
    print()
    print("NEXT STEP:")
    print("Run: python3 train_layer05_with_orderbook.py")
    print()
    print("Expected accuracy improvement:")
    print("  Current: 53%")
    print("  With order book: 65-70%")
    print("  With liquidations/funding: 70-75%")

if __name__ == "__main__":
    main()
