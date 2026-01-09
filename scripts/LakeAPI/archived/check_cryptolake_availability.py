"""
Check what data is actually available from Crypto-lake
"""

import boto3
from datetime import datetime

AWS_ACCESS_KEY = "REDACTED_AWS_KEY"
AWS_SECRET_KEY = "REDACTED_AWS_SECRET_ACCESS_KEY"
BUCKET_NAME = "crypto-lake"

def check_availability():
    """Check what's actually available."""
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    print("Checking Crypto-lake data availability...")
    print()
    
    # Check order book
    print("ORDER BOOK (book_1m):")
    prefix = "BINANCE_FUTURES/book_1m/BTC-USDT/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=100
        )
        
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
            dates = sorted([f.split('/')[-1].replace('.csv.gz', '') for f in files if f.endswith('.csv.gz')])
            
            if dates:
                print(f"  First date: {dates[0]}")
                print(f"  Last date: {dates[-1]}")
                print(f"  Sample: {dates[:5]}")
            else:
                print("  No data found!")
        else:
            print("  No data found!")
    except Exception as e:
        print(f"  Error: {e}")
    
    print()
    
    # Check liquidations
    print("LIQUIDATIONS:")
    prefix = "BINANCE_FUTURES/liquidations/BTC-USDT/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=100
        )
        
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
            dates = sorted([f.split('/')[-1].replace('.csv.gz', '') for f in files if f.endswith('.csv.gz')])
            
            if dates:
                print(f"  First date: {dates[0]}")
                print(f"  Last date: {dates[-1]}")
            else:
                print("  No data found!")
        else:
            print("  No data found!")
    except Exception as e:
        print(f"  Error: {e}")
    
    print()
    
    # Check funding
    print("FUNDING RATES:")
    prefix = "BINANCE_FUTURES/funding/BTC-USDT/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=100
        )
        
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
            dates = sorted([f.split('/')[-1].replace('.csv.gz', '') for f in files if f.endswith('.csv.gz')])
            
            if dates:
                print(f"  First date: {dates[0]}")
                print(f"  Last date: {dates[-1]}")
            else:
                print("  No data found!")
        else:
            print("  No data found!")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    check_availability()
