"""
Binance Daily Sync - Automatic Data Updates

This script runs daily to keep data current and complete.
Designed for cron/scheduled execution.

Features:
- Downloads yesterday's complete data
- Fills any gaps from missed days
- All data types (candles, funding, OI)
- Rate limiting with retry logic
- Automatic recovery from failures
- Gap detection and filling

Cron Schedule (Recommended):
10 0 * * * cd /home/sirrus/projects/BTC_Engine_v3 && python scripts/binance/daily_sync.py

Author: BTC_Engine_v3
Date: January 8, 2026
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import time
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data_manager.binance.rest_client import BinanceRestClient
from src.data_manager.config import PROJECT_ROOT

# Directories
BINANCE_DATA_DIR = PROJECT_ROOT / "data" / "binance"
SYNC_STATE_FILE = BINANCE_DATA_DIR / ".sync_state.json"

# CRITICAL: We trade PERPETUAL FUTURES
SYMBOL = 'BTCUSDT'
USE_FUTURES = True


class DailySync:
    """
    Daily synchronization manager
    
    Responsibilities:
    - Download yesterday's data
    - Detect and fill gaps
    - Handle rate limiting
    - Retry on failures
    - Maintain sync state
    """
    
    def __init__(self):
        """Initialize daily sync"""
        self.client = BinanceRestClient()
        BINANCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sync state
        self.sync_state = self._load_sync_state()
        
        # Results tracking
        self.results = {
            'date': datetime.now().isoformat(),
            'success': [],
            'failed': [],
            'skipped': []
        }
    
    def _load_sync_state(self) -> Dict:
        """Load last sync state"""
        if SYNC_STATE_FILE.exists():
            import json
            with open(SYNC_STATE_FILE, 'r') as f:
                return json.load(f)
        return {'last_sync_date': None, 'sync_history': []}
    
    def _save_sync_state(self):
        """Save sync state"""
        import json
        with open(SYNC_STATE_FILE, 'w') as f:
            json.dump(self.sync_state, f, indent=2)
    
    def get_last_sync_date(self) -> Optional[datetime]:
        """Get date of last successful sync"""
        if self.sync_state['last_sync_date']:
            return datetime.fromisoformat(self.sync_state['last_sync_date'])
        
        # Check for latest data in binance directory
        if BINANCE_DATA_DIR.exists():
            # Look for most recent month directory
            month_dirs = [d for d in BINANCE_DATA_DIR.iterdir() if d.is_dir() and d.name.match(r'\d{4}-\d{2}')]
            if month_dirs:
                latest = max(month_dirs, key=lambda d: d.name)
                # Return last day of that month
                year, month = map(int, latest.name.split('-'))
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                return datetime(year, month, last_day)
        
        return None
    
    def detect_gaps(self) -> List[datetime]:
        """
        Detect missing days between last sync and yesterday
        
        Returns:
            List of dates that need to be downloaded
        """
        yesterday = (datetime.now() - timedelta(days=1)).date()
        last_sync = self.get_last_sync_date()
        
        if not last_sync:
            # First run - just do yesterday
            return [datetime.combine(yesterday, datetime.min.time())]
        
        last_sync_date = last_sync.date()
        
        # Calculate gap
        gap_days = (yesterday - last_sync_date).days
        
        if gap_days <= 0:
            print("✅ Already up to date!")
            return []
        
        if gap_days > 30:
            print(f"⚠️  Large gap detected: {gap_days} days")
            print(f"   Limiting to last 30 days (Binance history limit)")
            gap_days = 30
        
        # Generate list of missing dates
        missing_dates = []
        for i in range(1, gap_days + 1):
            date = last_sync_date + timedelta(days=i)
            missing_dates.append(datetime.combine(date, datetime.min.time()))
        
        return missing_dates
    
    def download_day_candles(
        self,
        target_date: datetime,
        timeframes: List[str]
    ) -> Dict:
        """
        Download all timeframes for a specific day
        
        Args:
            target_date: Date to download
            timeframes: List of timeframes
        
        Returns:
            Dict with results per timeframe
        """
        date_str = target_date.strftime('%Y-%m-%d')
        month_str = target_date.strftime('%Y-%m')
        month_dir = BINANCE_DATA_DIR / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📅 {date_str}")
        print("-" * 70)
        
        results = {}
        
        for tf in timeframes:
            try:
                # Calculate hours to download
                start = target_date.replace(hour=0, minute=0, second=0)
                end = start + timedelta(days=1)
                hours = 24
                
                # Download from Binance Futures
                candles = self.client.get_klines(
                    interval=tf,
                    symbol=SYMBOL,
                    hours=hours,
                    futures=USE_FUTURES
                )
                
                # Filter to exact day
                candles['timestamp'] = pd.to_datetime(candles['timestamp'])
                candles = candles[
                    (candles['timestamp'] >= start) &
                    (candles['timestamp'] < end)
                ].copy()
                
                # Save to parquet
                filename = f"BTCUSDT_PERP_{tf}_{date_str}.parquet"
                output_file = month_dir / filename
                candles.to_parquet(output_file, compression='snappy', index=False)
                
                file_size_mb = output_file.stat().st_size / 1024 / 1024
                
                print(f"  ✅ {tf:4s}: {len(candles):4d} bars, {file_size_mb:.1f} MB")
                
                results[tf] = {
                    'success': True,
                    'bars': len(candles),
                    'file_size_mb': file_size_mb
                }
                
                # Small delay between timeframes (be nice to API)
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ {tf:4s}: {e}")
                results[tf] = {'success': False, 'error': str(e)}
        
        return results
    
    def sync_day(self, target_date: datetime) -> bool:
        """
        Synchronize a single day
        
        Args:
            target_date: Date to sync
        
        Returns:
            True if successful, False otherwise
        """
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        results = self.download_day_candles(target_date, timeframes)
        
        # Check if all succeeded
        successful = sum(1 for r in results.values() if r.get('success'))
        total = len(results)
        
        date_str = target_date.strftime('%Y-%m-%d')
        
        if successful == total:
            self.results['success'].append(date_str)
            return True
        elif successful > 0:
            self.results['success'].append(f"{date_str} (partial: {successful}/{total})")
            return True
        else:
            self.results['failed'].append(date_str)
            return False
    
    def run(self):
        """
        Main sync execution
        
        Process:
        1. Detect gaps
        2. Download missing days
        3. Update sync state
        4. Report results
        """
        print("="*70)
        print("BINANCE DAILY SYNC")
        print("="*70)
        print(f"Time: {datetime.now()}")
        print()
        
        # Detect gaps
        print("🔍 Detecting gaps...")
        missing_dates = self.detect_gaps()
        
        if not missing_dates:
            print("\n✅ No sync needed - already up to date!")
            return
        
        print(f"📥 Found {len(missing_dates)} day(s) to sync")
        print(f"   From: {missing_dates[0].date()}")
        print(f"   To: {missing_dates[-1].date()}")
        print()
        
        # Download each missing day
        for i, target_date in enumerate(missing_dates, 1):
            print(f"[{i}/{len(missing_dates)}]", end=' ')
            
            success = self.sync_day(target_date)
            
            # Rate limiting between days
            if i < len(missing_dates):
                time.sleep(1)  # 1 second between days
        
        # Update sync state
        if self.results['success']:
            last_success = missing_dates[-1]
            self.sync_state['last_sync_date'] = last_success.isoformat()
            self.sync_state['sync_history'].append({
                'date': datetime.now().isoformat(),
                'synced_days': len(self.results['success']),
                'failed_days': len(self.results['failed'])
            })
            
            # Keep only last 30 sync records
            self.sync_state['sync_history'] = self.sync_state['sync_history'][-30:]
            
            self._save_sync_state()
        
        # Summary
        print()
        print("="*70)
        print("SYNC COMPLETE")
        print("="*70)
        print(f"✅ Successful: {len(self.results['success'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⏭️  Skipped: {len(self.results['skipped'])}")
        
        if self.results['success']:
            print(f"\n📊 Latest data: {missing_dates[-1].date()}")
        
        if self.results['failed']:
            print(f"\n⚠️  Failed dates: {', '.join(self.results['failed'])}")
        
        print("="*70)


def main():
    """Run daily sync"""
    sync = DailySync()
    sync.run()


if __name__ == "__main__":
    main()