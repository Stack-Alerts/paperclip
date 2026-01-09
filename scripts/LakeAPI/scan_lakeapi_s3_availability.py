y"""
Scan LakeAPI S3 Bucket - Discover what data is actually available

This script directly queries the LakeAPI S3 bucket to list all available files
for December 2025 across all data types, providing ground truth about data availability.
"""

import boto3
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

# Load credentials
load_dotenv()

# Create boto3 S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('LAKEAPI_KEY'),
    aws_secret_access_key=os.getenv('LAKEAPI_SECRET'),
    region_name='eu-west-1'
)

# LakeAPI S3 bucket
BUCKET = 'qnt.data'

# Data types and their S3 paths
DATA_TYPES = {
    'trades': 'market-data/cryptofeed/trades',
    'liquidations': 'market-data/cryptofeed/liquidations',
    'funding': 'market-data/cryptofeed/funding',
    'open_interest': 'market-data/cryptofeed/open-interest',
    'orderbook': 'market-data/cryptofeed/book'
}

def list_s3_files(prefix, max_keys=1000):
    """List files in S3 bucket with prefix"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=BUCKET,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        if 'Contents' not in response:
            return []
        
        files = []
        for obj in response['Contents']:
            files.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified']
            })
        
        return files
    except Exception as e:
        print(f"Error listing {prefix}: {e}")
        return []

def scan_december_2025():
    """Scan S3 for December 2025 data across all types"""
    
    print("="*80)
    print("LAKEAPI S3 AVAILABILITY SCAN - DECEMBER 2025")
    print("="*80)
    print()
    print("Scanning S3 bucket: s3://qnt.data/")
    print()
    
    for data_type, s3_path in DATA_TYPES.items():
        print("="*80)
        print(f"{data_type.upper()}")
        print("="*80)
        print(f"S3 Path: s3://{BUCKET}/{s3_path}/")
        print()
        
        # Scan for December 2025 files
        # Files are typically organized like: .../BINANCE/BTC-USDT/2025/12/XX/...
        prefix = f"{s3_path}/BINANCE/BTC-USDT/2025/12"
        
        print(f"Scanning: {prefix}/")
        files = list_s3_files(prefix, max_keys=10000)
        
        if not files:
            print(f"⚠️  NO FILES FOUND for December 2025")
            print()
            
            # Try to see if ANY files exist for this data type
            general_prefix = f"{s3_path}/BINANCE/BTC-USDT/2025"
            general_files = list_s3_files(general_prefix, max_keys=100)
            
            if general_files:
                print(f"   But found {len(general_files)} files for 2025 (other months)")
                # Show first few
                for f in general_files[:3]:
                    print(f"   - {f['key']}")
            else:
                print(f"   No 2025 files found at all for {data_type}")
        else:
            print(f"✅ Found {len(files)} files")
            print()
            
            # Analyze by day
            days_found = set()
            total_size = 0
            
            for f in files:
                # Parse day from path
                parts = f['key'].split('/')
                if len(parts) >= 7:  # .../BINANCE/BTC-USDT/2025/12/DD/...
                    day = parts[6]
                    days_found.add(day)
                total_size += f['size']
            
            days_sorted = sorted(days_found)
            
            print(f"   Days available: {len(days_sorted)}/31")
            print(f"   Days: {', '.join(days_sorted)}")
            print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
            print()
            
            # Check for missing days
            all_days = set(f"{d:02d}" for d in range(1, 32))
            missing_days = sorted(all_days - days_found)
            
            if missing_days:
                print(f"   ⚠️  Missing days: {', '.join(missing_days)}")
            else:
                print(f"   ✅ Complete month (all 31 days present)")
            
            # Show sample files
            print()
            print(f"   Sample files:")
            for f in files[:3]:
                size_mb = f['size'] / 1024 / 1024
                print(f"   - {f['key'].split('/')[-1]} ({size_mb:.2f} MB)")
        
        print()

def compare_with_local():
    """Compare S3 availability with local files"""
    print("="*80)
    print("COMPARISON: S3 vs LOCAL DATA")
    print("="*80)
    print()
    
    local_data_dir = Path('data/raw')
    
    for data_type in DATA_TYPES.keys():
        local_file = local_data_dir / data_type / 'BTC-USDT_' / f'{data_type}_2025-12.parquet'
        
        if local_file.exists():
            size_mb = local_file.stat().st_size / 1024 / 1024
            print(f"✅ {data_type}: Have local file ({size_mb:.1f} MB)")
        else:
            print(f"❌ {data_type}: No local file")
    
    print()

def main():
    """Main function"""
    
    print()
    print("Starting S3 scan...")
    print()
    
    # Scan December 2025
    scan_december_2025()
    
    # Compare with local
    # compare_with_local()
    
    print("="*80)
    print("SCAN COMPLETE")
    print("="*80)
    print()
    print("This shows EXACTLY what files LakeAPI has available on S3.")
    print("If days are missing from S3, they cannot be downloaded.")
    print()

if __name__ == "__main__":
    main()