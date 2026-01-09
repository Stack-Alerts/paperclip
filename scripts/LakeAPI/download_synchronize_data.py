#!/usr/bin/env python3
"""
Download and Synchronize Data - Main Script
Institutional-grade data acquisition with 300GB limit enforcement

Usage:
    # Sync trades from Nov 2024 to now
    python scripts/LakeAPI/download_synchronize_data.py --data-type trades --start-date 2024-11-01
    
    # Sync all data types from Nov 2024
    python scripts/LakeAPI/download_synchronize_data.py --all --start-date 2024-11-01
    
    # Update current month only
    python scripts/LakeAPI/download_synchronize_data.py --update-current
    
    # Check sync status
    python scripts/LakeAPI/download_synchronize_data.py --status

Security:
    - Credentials loaded from .env file only
    - Never logs sensitive information
    - Enforces 300GB/month limit

Critical:
    - Real money at risk (data costs)
    - Always preview changes before confirming
    - Usage tracking is MANDATORY
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data_manager.download import DataSynchronizer, UsageTracker, LakeAPIClient
from src.data_manager.config import DATA_TYPES


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download and synchronize crypto market data from LakeAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Data selection
    parser.add_argument(
        '--data-type',
        choices=DATA_TYPES,
        help='Specific data type to sync'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Sync all data types'
    )
    
    # Date range
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD format, default: today)'
    )
    
    # Options
    parser.add_argument(
        '--update-current',
        action='store_true',
        help='Update current month data only'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download existing files'
    )
    
    parser.add_argument(
        '--no-current-month-update',
        action='store_true',
        help='Skip updating current month'
    )
    
    # Information commands
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show synchronization status'
    )
    
    parser.add_argument(
        '--usage',
        action='store_true',
        help='Show LakeAPI usage statistics'
    )
    
    parser.add_argument(
        '--check-freshness',
        action='store_true',
        help='Check if data is fresh'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.data_type, args.all, args.status, args.usage, args.update_current, args.check_freshness]):
        parser.print_help()
        sys.exit(1)
    
    # Initialize components
    print("\n" + "="*60)
    print("LAKEAPI DATA SYNCHRONIZATION")
    print("="*60 + "\n")
    
    try:
        tracker = UsageTracker()
        synchronizer = DataSynchronizer()
        
        # Show usage status
        if args.usage:
            print(tracker.get_usage_summary())
            warning = tracker.get_warning_message()
            if warning:
                print(f"\n{warning}")
            return 0
        
        # Show sync status
        if args.status:
            print("Current Synchronization Status:\n")
            status = synchronizer.get_sync_status()
            
            for data_type, info in status.items():
                icon = "✅" if info['is_current'] else "⚠️"
                print(f"{icon} {data_type:15}")
                print(f"   Months: {info['total_months']}")
                
                if info['first_month']:
                    print(f"   Range: {info['first_month']} to {info['last_month']}")
                else:
                    print(f"   Range: No data")
                
                if info['last_sync']:
                    print(f"   Last sync: {info['last_sync'][:19]}")
                print()
            
            print(tracker.get_usage_summary())
            return 0
        
        # Check freshness
        if args.check_freshness:
            print("Checking data freshness...\n")
            freshness = synchronizer.check_data_freshness(max_age_hours=24.0)
            
            stale_count = sum(1 for fresh in freshness.values() if not fresh)
            
            for data_type, is_fresh in freshness.items():
                icon = "✅" if is_fresh else "🔄"
                status = "Fresh" if is_fresh else "Stale (>24h)"
                print(f"{icon} {data_type:15} - {status}")
            
            if stale_count > 0:
                print(f"\n⚠️  {stale_count} data type(s) need updating")
                
                response = input("\nUpdate stale data now? (y/n): ")
                if response.lower() == 'y':
                    synchronizer.update_stale_data(max_age_hours=24.0)
            else:
                print("\n✅ All data is fresh")
            
            return 0
        
        # Update current month only
        if args.update_current:
            print("Updating current month data...\n")
            synchronizer.update_stale_data(max_age_hours=0.0)  # Force update
            return 0
        
        # Sync specific data type
        if args.data_type:
            if not args.start_date:
                print("❌ --start-date is required for data synchronization")
                return 1
            
            results = synchronizer.sync_data_type(
                args.data_type,
                args.start_date,
                args.end_date,
                force_redownload=args.force,
                update_current_month=not args.no_current_month_update
            )
            
            if results['status'] in ['success', 'up_to_date']:
                print("\n✅ Synchronization successful")
                return 0
            else:
                print("\n⚠️  Synchronization completed with errors")
                return 1
        
        # Sync all data types
        if args.all:
            if not args.start_date:
                print("❌ --start-date is required for data synchronization")
                return 1
            
            results = synchronizer.sync_all_data_types(
                args.start_date,
                args.end_date,
                update_current_month=not args.no_current_month_update
            )
            
            total_failed = sum(r['failed'] for r in results.values())
            
            if total_failed == 0:
                print("\n✅ All synchronizations successful")
                return 0
            else:
                print(f"\n⚠️  Completed with {total_failed} failed download(s)")
                return 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())