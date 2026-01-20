"""
Download RECENT Liquidation Data from Binance Futures API (Real-Time Source)

PURPOSE:
- Use for PAPER TRADING and LIVE TRADING (fast, real-time data)
- Use Crypto-Lake for BACKTEST and WALKFORWARD (historical archive)

DATA SOURCE:
- Binance Futures Public API (last ~30 days only)
- No API key required
- Fast real-time updates

USE CASES:
- Paper trading: Recent market context
- Live trading: Real-time liquidation clusters
- Real-time monitoring: Active liquidation levels

LIMITATIONS:
- Only provides last ~30 days of data
- Cannot retrieve historical data (>30 days old)
- For historical analysis, use Crypto-Lake downloader

Author: BTC_Engine_LLM Team
Date: December 26, 2025
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import json
from typing import List, Dict, Optional

# Get project root directory (two levels up from this script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class BinanceLiquidationDownloader:
    """
    Download liquidation data from Binance Futures API
    
    API Documentation:
    https://binance-docs.github.io/apidocs/futures/en/#liquidation-order-streams
    """
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def get_all_liquidation_orders(
        self,
        symbol: str = "BTCUSDT",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Get historical liquidation orders
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            limit: Number of records (max 1000)
        
        Returns:
            DataFrame with liquidation events
        """
        endpoint = f"{self.base_url}/fapi/v1/allForceOrders"
        
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Convert timestamp to datetime
            if 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching liquidation orders: {e}")
            return pd.DataFrame()
    
    def download_liquidations_chunked(
        self,
        symbol: str = "BTCUSDT",
        start_date: datetime = None,
        end_date: datetime = None,
        chunk_hours: int = 6
    ) -> pd.DataFrame:
        """
        Download liquidations in time chunks to handle API limits
        
        Binance limits to 1000 records per request. We chunk by time
        to ensure we get all liquidations.
        
        Args:
            symbol: Trading pair
            start_date: Start datetime
            end_date: End datetime
            chunk_hours: Hours per chunk (default 6)
        
        Returns:
            Combined DataFrame of all liquidations
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        all_liquidations = []
        current_start = start_date
        
        print(f"Downloading liquidations from {start_date} to {end_date}")
        print(f"Chunk size: {chunk_hours} hours")
        print()
        
        chunk_count = 0
        total_records = 0
        
        while current_start < end_date:
            current_end = min(current_start + timedelta(hours=chunk_hours), end_date)
            
            start_ms = int(current_start.timestamp() * 1000)
            end_ms = int(current_end.timestamp() * 1000)
            
            print(f"  Chunk {chunk_count + 1}: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end='')
            
            df = self.get_all_liquidation_orders(
                symbol=symbol,
                start_time=start_ms,
                end_time=end_ms,
                limit=1000
            )
            
            if not df.empty:
                all_liquidations.append(df)
                total_records += len(df)
                print(f" {len(df):,} liquidations")
            else:
                print(" No data")
            
            current_start = current_end
            chunk_count += 1
            
            # Rate limiting: 20 requests per second
            time.sleep(0.1)
        
        print()
        print(f"Downloaded {total_records:,} liquidation events in {chunk_count} chunks")
        
        if all_liquidations:
            combined = pd.concat(all_liquidations, ignore_index=True)
            # Remove duplicates
            combined = combined.drop_duplicates(subset=['orderId'])
            return combined
        else:
            return pd.DataFrame()
    
    def download_monthly_liquidations(
        self,
        symbol: str = "BTCUSDT",
        year: int = 2024,
        month: int = 1
    ) -> pd.DataFrame:
        """
        Download liquidations for a specific month
        
        Args:
            symbol: Trading pair
            year: Year
            month: Month (1-12)
        
        Returns:
            DataFrame of liquidations for that month
        """
        start_date = datetime(year, month, 1)
        
        # Calculate end date (last day of month)
        if month == 12:
            end_date = datetime(year, 12, 31, 23, 59, 59)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Don't go past today
        if end_date > datetime.now():
            end_date = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING LIQUIDATIONS FOR {year}-{month:02d}")
        print(f"{'='*80}")
        print()
        
        df = self.download_liquidations_chunked(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            chunk_hours=6
        )
        
        return df
    
    def save_liquidations(
        self,
        df: pd.DataFrame,
        output_path: str,
        format: str = 'parquet'
    ):
        """
        Save liquidations to disk
        
        Args:
            df: DataFrame to save
            output_path: Output file path
            format: 'parquet' or 'csv'
        """
        if df.empty:
            print(f"No data to save")
            return
        
        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'parquet':
            df.to_parquet(output_path, compression='gzip')
        else:
            df.to_csv(output_path, index=False)
        
        file_size_mb = Path(output_path).stat().st_size / 1024 / 1024
        print(f"Saved {len(df):,} records to {output_path} ({file_size_mb:.1f} MB)")
    
    def get_liquidation_summary(self, df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for liquidations
        
        Args:
            df: Liquidations DataFrame
        
        Returns:
            Dictionary with summary stats
        """
        if df.empty:
            return {}
        
        summary = {
            'total_liquidations': len(df),
            'total_volume': df['origQty'].astype(float).sum() if 'origQty' in df.columns else 0,
            'long_liquidations': len(df[df['side'] == 'SELL']) if 'side' in df.columns else 0,
            'short_liquidations': len(df[df['side'] == 'BUY']) if 'side' in df.columns else 0,
            'avg_price': df['price'].astype(float).mean() if 'price' in df.columns else 0,
            'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}" if 'timestamp' in df.columns else "N/A"
        }
        
        return summary

def main():
    """Download historical liquidations from Binance"""
    
    print("="*80)
    print("BINANCE LIQUIDATION DOWNLOADER - BACKUP DATA SOURCE")
    print("="*80)
    print()
    print("This downloads liquidation order data from Binance Futures API.")
    print()
    print("Data includes:")
    print("  - Liquidation time and price")
    print("  - Order ID and side (LONG/SHORT liquidation)")
    print("  - Original quantity and filled quantity")
    print("  - Average price and status")
    print()
    print("Use case:")
    print("  - Backup if Crypto-Lake liquidation data is incomplete")
    print("  - Real-time liquidation monitoring")
    print("  - Historical liquidation analysis")
    print()
    print("API Limits:")
    print("  - 1000 records per request")
    print("  - 2400 requests per minute (weight-based)")
    print("  - No API key required")
    print()
    
    # Configuration
    symbol = "BTCUSDT"
    
    # Binance only keeps ~30 days of liquidation history
    # Use this for LIVE/PAPER trading (real-time data)
    # Use Crypto-Lake for BACKTEST/WALKFORWARD (historical data)
    days_back = 30
    start_date = datetime.now() - timedelta(days=days_back)
    end_date = datetime.now()
    
    print(f"⚠️  NOTE: Binance API only provides recent liquidations (~30 days)")
    print(f"   Historical data (>30 days): Use Crypto-Lake")
    print(f"   Recent data (last 30 days): Use Binance (faster, real-time)")
    print()
    print(f"This script will download: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()
    
    proceed = input(f"Download recent liquidations for {symbol}? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Download cancelled.")
        return
    
    downloader = BinanceLiquidationDownloader()
    
    # Download recent liquidations (last 30 days)
    print(f"\n{'='*80}")
    print(f"DOWNLOADING RECENT LIQUIDATIONS")
    print(f"{'='*80}")
    print()
    
    df = downloader.download_liquidations_chunked(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        chunk_hours=6
    )
    
    if not df.empty:
        # Save to file (use absolute path from project root)
        output_filename = f"BTC-USDT_liquidations_recent_{datetime.now().strftime('%Y%m%d')}.parquet"
        output_path = PROJECT_ROOT / "data" / "raw" / "liquidations_binance" / output_filename
        downloader.save_liquidations(df, str(output_path), format='parquet')
        
        # Generate summary
        summary = downloader.get_liquidation_summary(df)
        
        print()
        print(f"Summary for last {days_back} days:")
        print(f"  Total liquidations: {summary['total_liquidations']:,}")
        print(f"  Long liquidations: {summary['long_liquidations']:,}")
        print(f"  Short liquidations: {summary['short_liquidations']:,}")
        print(f"  Total volume: {summary['total_volume']:,.2f} BTC")
        print(f"  Average price: ${summary['avg_price']:,.2f}")
        print(f"  Date range: {summary['date_range']}")
        print()
        
        # Save summary (use absolute path from project root)
        summary_df = pd.DataFrame([summary])
        summary_path = PROJECT_ROOT / "data" / "raw" / "liquidations_binance" / "SUMMARY_RECENT.csv"
        summary_df.to_csv(str(summary_path), index=False)
        print(f"Summary saved to {summary_path}")
    else:
        print("\n⚠️  No liquidation data retrieved.")
        print("This may be due to:")
        print("  - No liquidations occurred in the time period")
        print("  - API rate limiting")
        print("  - Network issues")
    
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print()
    print("Data saved to: data/raw/liquidations_binance/")
    print()
    print("NEXT STEPS:")
    print("1. Compare with Crypto-Lake liquidations:")
    print("   python3 -c \"import pandas as pd; lake = pd.read_parquet('data/raw/liquidations/BTC-USDT_liquidations_2024-01.parquet'); binance = pd.read_parquet('data/raw/liquidations_binance/BTC-USDT_liquidations_2024-01.parquet'); print(f'Lake: {len(lake)}, Binance: {len(binance)}')\"")
    print()
    print("2. Choose best data source:")
    print("   - Use Crypto-Lake if comprehensive (preferred)")
    print("   - Use Binance if Lake data is incomplete")
    print("   - Merge both if needed for completeness")
    print()
    print("3. Integrate into Layer TBD")
    print()

if __name__ == "__main__":
    main()
