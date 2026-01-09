"""
Test script to check available Crypto-Lake data tables and proper naming.
"""

from lakeapi import load_data
from datetime import datetime
import boto3

# Create boto3 session
session = boto3.Session(
    aws_access_key_id='REDACTED_AWS_KEY',
    aws_secret_access_key='REDACTED_AWS_SECRET_ACCESS_KEY',
    region_name='eu-west-1'
)

# Test each table type
tables_to_test = [
    ('book', 'Order Book'),
    ('trade', 'Trades'),
    ('trades', 'Trades (plural)'),
    ('liquidation', 'Liquidations'),
    ('liquidations', 'Liquidations (plural)'),
    ('funding_rate', 'Funding Rate'),
    ('funding', 'Funding'),
    ('open_interest', 'Open Interest'),
    ('oi', 'OI'),
]

print("Testing Crypto-Lake API table names...")
print("="*80)
print()

# Test with a small date range (Jan 1-2, 2024)
test_start = datetime(2024, 1, 1)
test_end = datetime(2024, 1, 2)

for table_name, description in tables_to_test:
    try:
        print(f"Testing '{table_name}' ({description})...", end=' ', flush=True)
        
        df = load_data(
            table=table_name,
            start=test_start,
            end=test_end,
            symbols=['BTC-USDT'],
            exchanges=['BINANCE'],
            boto3_session=session
        )
        
        if df is not None and not df.empty:
            print(f"✅ WORKS! ({len(df)} rows)")
            print(f"   Columns: {list(df.columns)[:5]}...")
        else:
            print("⚠️  Returns empty DataFrame")
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if 'NoFilesFound' in error_msg or 'NoFilesFound' in error_type:
            print(f"❌ NoFilesFound - table doesn't exist or no data")
        else:
            print(f"❌ {error_type}: {error_msg[:50]}")

print()
print("="*80)
print("Test complete!")
