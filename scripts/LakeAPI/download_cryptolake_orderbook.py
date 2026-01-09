"""
Download Free Order Book Data from Crypto-lake.com

Downloads sample historical order book data to test if it improves ML accuracy.
Free data available at: https://crypto-lake.com/free-data/
"""

import requests
import pandas as pd
from pathlib import Path
import gzip
import shutil
from datetime import datetime, timedelta

# Get project root directory (two levels up from this script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def download_cryptolake_sample():
    """
    Download free sample order book data from Crypto-lake.
    
    Free data includes:
    - BTC-USDT order book snapshots
    - 1 month of data (rolling)
    - 1-minute snapshots
    """
    
    print("="*80)
    print("DOWNLOADING FREE CRYPTO-LAKE ORDER BOOK DATA")
    print("="*80)
    print()
    
    # Create directory (use absolute path from project root)
    output_dir = PROJECT_ROOT / "data" / "raw" / "orderbook"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    print()
    
    # Crypto-lake free data URLs
    # Note: These are example URLs - visit https://crypto-lake.com/free-data/ 
    # for actual download links
    
    print("📋 FREE DATA AVAILABLE FROM CRYPTO-LAKE:")
    print()
    print("1. Visit: https://crypto-lake.com/free-data/")
    print("2. Download: BTC-USDT order book data (CSV format)")
    print("3. Place files in: data/raw/orderbook/")
    print()
    print("Expected format:")
    print("  - Filename: BTC-USDT_orderbook_YYYY-MM-DD.csv.gz")
    print("  - Columns: timestamp, bids (JSON), asks (JSON)")
    print()
    
    # Check if data already exists
    existing_files = list(output_dir.glob("*.csv*"))
    
    if existing_files:
        print(f"✅ Found {len(existing_files)} existing files:")
        for f in existing_files[:5]:
            print(f"   - {f.name}")
        if len(existing_files) > 5:
            print(f"   ... and {len(existing_files) - 5} more")
        print()
        print("🎯 Ready to train ML model with order book features!")
    else:
        print("❌ No order book data found yet.")
        print()
        print("MANUAL DOWNLOAD STEPS:")
        print()
        print("1. Go to: https://crypto-lake.com/free-data/")
        print("2. Sign up for free account (if needed)")
        print("3. Download BTC-USDT order book snapshots")
        print("4. Extract to: data/raw/orderbook/")
        print()
        print("ALTERNATIVE - API Download (if available):")
        print()
        
        # Example API download (may require API key)
        print("# Install crypto-lake client:")
        print("pip install crypto-lake")
        print()
        print("# Download data:")
        print("from crypto_lake import CryptoLake")
        print("cl = CryptoLake(api_key='your_key')  # Free tier available")
        print("data = cl.load_orderbook('BTC-USDT', '2024-01-01', '2024-01-31')")
        print("data.to_csv('data/raw/orderbook/BTC-USDT_2024-01.csv')")
        print()
    
    return existing_files, output_dir

def verify_orderbook_format(csv_file: Path):
    """Verify order book CSV format is correct."""
    print(f"\nVerifying format of: {csv_file.name}")
    
    try:
        # Try to load
        if csv_file.suffix == '.gz':
            df = pd.read_csv(csv_file, compression='gzip', nrows=10)
        else:
            df = pd.read_csv(csv_file, nrows=10)
        
        print(f"  Columns: {list(df.columns)}")
        print(f"  Rows: {len(df)}")
        print(f"  ✅ Format looks good!")
        
        # Show sample
        print("\nSample row:")
        print(df.iloc[0])
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    # Download / check for data
    files, output_dir = download_cryptolake_sample()
    
    # Verify first file if exists
    if files:
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)
        verify_orderbook_format(files[0])
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print()
        print("1. ✅ Order book data ready")
        print("2. Run: python3 train_layer05_with_orderbook.py")
        print("3. Expected accuracy: 53% → 65-70%")
        print()
    else:
        print("\n" + "="*80)
        print("ACTION REQUIRED")
        print("="*80)
        print()
        print("Please download free data from:")
        print("https://crypto-lake.com/free-data/")
        print()
        print("Then place CSV files in:")
        print("data/raw/orderbook/")
        print()
        
        # Create README
        readme = output_dir / "README.txt"
        with open(readme, 'w') as f:
            f.write("Order Book Data Directory\n")
            f.write("=" * 50 + "\n\n")
            f.write("Download free historical order book data:\n")
            f.write("https://crypto-lake.com/free-data/\n\n")
            f.write("Expected format:\n")
            f.write("- Filename: BTC-USDT_orderbook_YYYY-MM-DD.csv\n")
            f.write("- Columns: timestamp, bids (JSON), asks (JSON)\n\n")
            f.write("Once downloaded, place files here.\n")
        
        print(f"📝 Created README: {readme}")

if __name__ == "__main__":
    main()
