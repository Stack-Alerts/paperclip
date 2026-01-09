"""Data Synchronizer - Incremental download orchestration"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from ..config import RAW_DATA_DIR, DATA_TYPES
from ..utils.date_utils import generate_month_range, get_current_month, is_current_month
from .lake_api_client import LakeAPIClient
from .usage_tracker import UsageTracker


class DataSynchronizer:
    """
    Orchestrate incremental data downloads
    
    Key Features:
    - Only downloads missing months
    - Tracks last download date
    - Supports partial month updates (current month)
    - Prevents re-downloading existing data
    - Respects 300GB usage limit
    
    Example:
        >>> sync = DataSynchronizer()
        >>> sync.sync_data_type('trades', start_date='2024-11-01')
        # Downloads Nov, Dec, Jan (only missing months)
    """
    
    def __init__(self, client: Optional[LakeAPIClient] = None):
        """
        Initialize data synchronizer
        
        Args:
            client: LakeAPI client (creates new if None)
        """
        self.tracker = UsageTracker()
        self.client = client or LakeAPIClient(usage_tracker=self.tracker)
        
        # Sync state file
        self.state_file = RAW_DATA_DIR / ".sync_state.json"
        self.sync_state = self._load_sync_state()
    
    def _load_sync_state(self) -> Dict:
        """Load synchronization state"""
        if not self.state_file.exists():
            return self._initialize_sync_state()
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading sync state: {e}")
            return self._initialize_sync_state()
    
    def _initialize_sync_state(self) -> Dict:
        """Initialize new sync state"""
        state = {
            'created': datetime.now().isoformat(),
            'last_sync': {},
            'data_types': {}
        }
        
        for data_type in DATA_TYPES:
            state['data_types'][data_type] = {
                'last_sync_month': None,
                'total_months': 0,
                'last_update': None
            }
        
        self._save_sync_state(state)
        return state
    
    def _save_sync_state(self, state: Optional[Dict] = None):
        """Save synchronization state"""
        if state is None:
            state = self.sync_state
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving sync state: {e}")
    
    def get_missing_months(
        self,
        data_type: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> List[tuple]:
        """
        Get list of months that need to be downloaded
        
        Args:
            data_type: Data type to check
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (default: today)
        
        Returns:
            List of (year, month) tuples that are missing
        
        Example:
            >>> sync.get_missing_months('trades', '2024-11-01')
            [(2024, 11), (2024, 12), (2025, 1)]  # Missing months
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Generate all months in range
        all_months = generate_month_range(start_date, end_date)
        
        # Get currently downloaded months
        available_months = set(self.client.get_available_months(data_type))
        
        # Find missing months
        missing_months = [
            (year, month) for year, month in all_months
            if (year, month) not in available_months
        ]
        
        return missing_months
    
    def sync_data_type(
        self,
        data_type: str,
        start_date: str,
        end_date: Optional[str] = None,
        force_redownload: bool = False,
        update_current_month: bool = True
    ) -> Dict[str, any]:
        """
        Synchronize one data type (incremental download)
        
        Args:
            data_type: Data type to sync ('trades', 'liquidations', etc.)
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (default: today)
            force_redownload: Force re-download all months
            update_current_month: Re-download current month for updates
        
        Returns:
            Dictionary with sync results
        
        Example:
            >>> results = sync.sync_data_type('trades', '2024-11-01')
            >>> results['downloaded']
            3  # Downloaded 3 months
        
        Note:
            This is the key method for incremental synchronization
        """
        print(f"\n{'='*60}")
        print(f"SYNCHRONIZING: {data_type.upper()}")
        print(f"{'='*60}")
        print(f"Start date: {start_date}")
        print(f"End date: {end_date or 'today'}")
        print(f"Force redownload: {force_redownload}")
        print(f"Update current month: {update_current_month}")
        print()
        
        # Get missing months
        if force_redownload:
            # Download all months in range
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            months_to_download = generate_month_range(start_date, end_date)
            print(f"🔄 Force redownload: {len(months_to_download)} months")
        else:
            # Only download missing months
            months_to_download = self.get_missing_months(data_type, start_date, end_date)
            
            # Check for incomplete previous month (partial month that should be complete)
            # If we're in January 2026, December 2025 should be complete but might be partial
            now = datetime.now()
            if now.day < 15:  # Early in month, previous month might be partial
                prev_month = now.month - 1 if now.month > 1 else 12
                prev_year = now.year if now.month > 1 else now.year - 1
                
                # Check if previous month file exists but might be incomplete
                file_path = self.client._get_file_path(data_type, prev_year, prev_month)
                if file_path.exists():
                    # Previous month exists but might be partial - add to redownload
                    if (prev_year, prev_month) not in months_to_download:
                        print(f"🔄 Re-downloading previous month {prev_year}-{prev_month:02d} (may be incomplete)")
                        months_to_download.append((prev_year, prev_month))
                        months_to_download.sort()
            
            if not months_to_download:
                print(f"✅ All months already downloaded for {data_type}")
                
                # Check if we should update current month
                if update_current_month:
                    current_year = datetime.now().year
                    current_month = datetime.now().month
                    
                    if is_current_month(current_year, current_month):
                        print(f"🔄 Updating current month: {current_year}-{current_month:02d}")
                        months_to_download = [(current_year, current_month)]
            else:
                print(f"📥 {len(months_to_download)} missing months to download")
        
        if not months_to_download:
            return {
                'data_type': data_type,
                'downloaded': 0,
                'skipped': 0,
                'failed': 0,
                'status': 'up_to_date'
            }
        
        # Download missing months
        results = self.client.download_multiple_months(
            data_type,
            months_to_download,
            force_redownload=force_redownload,
            stop_on_error=False
        )
        
        # Count results
        downloaded = sum(1 for v in results.values() if v is not None and isinstance(v, object))
        skipped = sum(1 for v in results.values() if v is None)
        failed = len(results) - downloaded - skipped
        
        # Update sync state
        if months_to_download:
            last_month = months_to_download[-1]
            self.sync_state['data_types'][data_type]['last_sync_month'] = f"{last_month[0]}-{last_month[1]:02d}"
            self.sync_state['data_types'][data_type]['total_months'] = len(self.client.get_available_months(data_type))
            self.sync_state['data_types'][data_type]['last_update'] = datetime.now().isoformat()
            self._save_sync_state()
        
        return {
            'data_type': data_type,
            'downloaded': downloaded,
            'skipped': skipped,
            'failed': failed,
            'status': 'success' if failed == 0 else 'partial'
        }
    
    def sync_all_data_types(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        data_types: Optional[List[str]] = None,
        update_current_month: bool = True
    ) -> Dict[str, Dict]:
        """
        Synchronize all data types
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (default: today)
            data_types: List of data types to sync (default: all)
            update_current_month: Re-download current month for updates
        
        Returns:
            Dictionary mapping data_type to sync results
        
        Example:
            >>> results = sync.sync_all_data_types('2024-11-01')
            >>> results['trades']['downloaded']
            3  # Downloaded 3 months of trades
        """
        if data_types is None:
            data_types = DATA_TYPES
        
        print(f"\n{'='*60}")
        print(f"FULL SYNCHRONIZATION")
        print(f"{'='*60}")
        print(f"Data types: {', '.join(data_types)}")
        print(f"Period: {start_date} to {end_date or 'today'}")
        print(f"{self.tracker.get_usage_summary()}\n")
        
        all_results = {}
        
        for data_type in data_types:
            try:
                results = self.sync_data_type(
                    data_type,
                    start_date,
                    end_date,
                    update_current_month=update_current_month
                )
                all_results[data_type] = results
                
            except Exception as e:
                print(f"❌ Error syncing {data_type}: {e}")
                all_results[data_type] = {
                    'data_type': data_type,
                    'downloaded': 0,
                    'skipped': 0,
                    'failed': 1,
                    'status': 'error',
                    'error': str(e)
                }
        
        # Print final summary
        self._print_sync_summary(all_results)
        
        return all_results
    
    def _print_sync_summary(self, results: Dict[str, Dict]):
        """Print synchronization summary"""
        print(f"\n{'='*60}")
        print(f"SYNCHRONIZATION COMPLETE")
        print(f"{'='*60}\n")
        
        total_downloaded = sum(r['downloaded'] for r in results.values())
        total_skipped = sum(r['skipped'] for r in results.values())
        total_failed = sum(r['failed'] for r in results.values())
        
        print(f"Summary:")
        print(f"  Total downloaded: {total_downloaded}")
        print(f"  Total skipped: {total_skipped}")
        print(f"  Total failed: {total_failed}")
        print()
        
        # Per data type breakdown
        print(f"By Data Type:")
        for data_type, result in results.items():
            status_icon = "✅" if result['status'] in ['success', 'up_to_date'] else "⚠️"
            print(f"  {status_icon} {data_type:15} - Downloaded: {result['downloaded']}, Skipped: {result['skipped']}, Failed: {result['failed']}")
        
        print()
        print(f"{self.tracker.get_usage_summary()}")
        print(f"{'='*60}\n")
    
    def get_sync_status(self) -> Dict:
        """
        Get current synchronization status
        
        Returns:
            Dictionary with sync status for all data types
        
        Example:
            >>> status = sync.get_sync_status()
            >>> status['trades']['total_months']
            15  # Have 15 months of trades data
        """
        status = {}
        
        for data_type in DATA_TYPES:
            available_months = self.client.get_available_months(data_type)
            state = self.sync_state['data_types'].get(data_type, {})
            
            status[data_type] = {
                'total_months': len(available_months),
                'first_month': f"{available_months[0][0]}-{available_months[0][1]:02d}" if available_months else None,
                'last_month': f"{available_months[-1][0]}-{available_months[-1][1]:02d}" if available_months else None,
                'last_sync': state.get('last_update'),
                'is_current': available_months[-1] == (datetime.now().year, datetime.now().month) if available_months else False
            }
        
        return status
    
    def check_data_freshness(self, max_age_hours: float = 24.0) -> Dict[str, bool]:
        """
        Check if current month data is fresh
        
        Args:
            max_age_hours: Maximum age in hours before data is considered stale
        
        Returns:
            Dictionary mapping data_type to is_fresh boolean
        
        Example:
            >>> freshness = sync.check_data_freshness(max_age_hours=24.0)
            >>> freshness['trades']
            False  # Trades data is stale
        """
        from ..utils.date_utils import is_file_stale
        
        freshness = {}
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        for data_type in DATA_TYPES:
            file_path = self.client._get_file_path(data_type, current_year, current_month)
            
            if not file_path.exists():
                freshness[data_type] = False
            else:
                freshness[data_type] = not is_file_stale(file_path, max_age_hours)
        
        return freshness
    
    def update_stale_data(self, max_age_hours: float = 24.0) -> Dict[str, any]:
        """
        Update any stale current month data
        
        Args:
            max_age_hours: Maximum age before data is considered stale
        
        Returns:
            Dictionary with update results
        
        Example:
            >>> results = sync.update_stale_data(max_age_hours=24.0)
            # Re-downloads stale current month data
        """
        freshness = self.check_data_freshness(max_age_hours)
        stale_types = [dt for dt, fresh in freshness.items() if not fresh]
        
        if not stale_types:
            print("✅ All current month data is fresh")
            return {'status': 'fresh', 'updated': 0}
        
        print(f"🔄 Updating {len(stale_types)} stale data types...")
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        months = [(current_year, current_month)]
        
        results = {}
        for data_type in stale_types:
            result = self.client.download_multiple_months(
                data_type,
                months,
                force_redownload=True
            )
            results[data_type] = result
        
        return {
            'status': 'updated',
            'updated': len(stale_types),
            'data_types': stale_types
        }