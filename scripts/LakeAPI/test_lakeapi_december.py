"""
Test LakeAPI Data Availability for December 2025

This script queries LakeAPI directly to verify what data actually exists
for December 2025, bypassing our local cache.
"""

from lakeapi import load_data
import pandas as pd
from datetime import datetime
import boto3
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

# Create boto3 session
session = boto3.Session(
    aws_access_key_id=os.getenv('LAKEAPI_KEY'),
    aws_secret_access_key=os.getenv('LAKEAPI_SECRET'),
    region_name='eu-west-1'
)

print("="*80)
print("TESTING LAKEAPI DATA AVAILABILITY - DECEMBER 2025")
print("="*80)
print()
print("Querying LakeAPI directly (not using local cache)...")
print()

# Query December 2025
start_date = datetime(2025, 12, 1)
end_date = datetime(2025, 12, 31, 23, 59, 59)

print(f"Requesting: {start_date.date()} to {end_date.date()}")
print()

try:
    # Download from LakeAPI
    print("Downloading from LakeAPI...", end='', flush=True)
    df = load_data(
        table='trades',
        start=start_date,
        end=end_date,
        symbols=['BTC-USDT'],
        exchanges=['BINANCE'],
        boto3_session=session
    )
    print(" Done!")
    print()
    
    if df is None or df.empty:
        print("❌ No data returned from LakeAPI")
    else:
        # Analyze what we got
        df['dt'] = pd.to_datetime(df['origin_time'])
        
        print("="*80)
        print("LAKEAPI RESPONSE ANALYSIS")
        print("="*80)
        print()
        print(f"Total rows: {len(df):,}")
        print(f"First trade: {df['dt'].min()}")
        print(f"Last trade: {df['dt'].max()}")
        print()
        
        # Calculate days
        days_span = (df['dt'].max() - df['dt'].min()).days
        first_day = df['dt'].min().day
        last_day = df['dt'].max().day
        
        print(f"First day of month: December {first_day}")
        print(f"Last day of month: December {last_day}")
        print(f"Days span: {days_span} days")
        print()
        
        # Check each day
        print("="*80)
        print("DAY-BY-DAY BREAKDOWN")
        print("="*80)
        print()
        
        trades_by_day = df.groupby(df['dt'].dt.day).size()
        
        for day in range(1, 32):
            if day in trades_by_day:
                count = trades_by_day[day]
                print(f"✅ Dec {day:02d}: {count:,} trades")
            else:
                print(f"❌ Dec {day:02d}: NO DATA")
        
        print()
        print("="*80)
        print("CONCLUSION")
        print("="*80)
        print()
        
        missing_days = []
        for day in range(1, 32):
            if day not in trades_by_day:
                missing_days.append(day)
        
        if missing_days:
            print(f"⚠️  Missing {len(missing_days)} days from LakeAPI:")
            print(f"   Days: {', '.join(f'Dec {d}' for d in missing_days)}")
            print()
            print("This confirms LakeAPI does not have complete December 2025 data.")
        else:
            print("✅ LakeAPI has complete December 2025 data (all 31 days)")
        
        print()

except Exception as e:
    print(f" ❌ Error")
    print()
    print(f"Error: {e}")
    print()
    print("This might indicate:")
    print("- LakeAPI connection issue")
    print("- Invalid credentials")
    print("- Data not available for this period")

print("="*80)