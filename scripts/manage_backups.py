#!/usr/bin/env python3
"""
Database Backup Management Script
Task 0.7: Backup/Restore CLI Tool

Simplifies database backup and restore operations with safety checks.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.database.backup import get_backup_manager


def create_backup(args):
    """Create a new database backup"""
    backup_mgr = get_backup_manager()
    
    print(f"\n📦 Creating database backup...")
    print(f"   Target: {backup_mgr.db_config['database']}")
    print(f"   Compression: {'enabled' if args.compress else 'disabled'}\n")
    
    try:
        backup_file = backup_mgr.create_backup(
            backup_name=args.name,
            compress=args.compress
        )
        
        print(f"\n✅ Backup created successfully!")
        print(f"   File: {backup_file}")
        print(f"   Size: {backup_file.stat().st_size:,} bytes")
        
    except Exception as e:
        print(f"\n❌ Backup failed: {str(e)}")
        sys.exit(1)


def restore_backup(args):
    """Restore database from backup"""
    backup_mgr = get_backup_manager()
    backup_file = Path(args.file)
    
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)
    
    print(f"\n⚠️  WARNING: Database Restore Operation")
    print(f"   Database: {backup_mgr.db_config['database']}")
    print(f"   Backup: {backup_file}")
    print(f"   Drop existing: {'YES' if args.drop else 'NO'}")
    
    if not args.yes:
        response = input("\n   Proceed with restore? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Restore cancelled")
            return
    
    try:
        backup_mgr.restore_backup(backup_file, drop_existing=args.drop)
        print("\n✅ Database restored successfully!")
        
    except Exception as e:
        print(f"\n❌ Restore failed: {str(e)}")
        sys.exit(1)


def list_backups(args):
    """List all available backups"""
    backup_mgr = get_backup_manager()
    
    backups = backup_mgr.list_backups()
    
    if not backups:
        print("\nNo backups found")
        return
    
    print(f"\n📋 Available Backups ({len(backups)}):\n")
    
    for backup in backups:
        compressed = "📦" if backup['compressed'] else "📄"
        print(f"   {compressed} {backup['name']}")
        print(f"      Size: {backup['size_mb']:.2f} MB")
        print(f"      Created: {backup['created']}")
        print()


def cleanup_backups(args):
    """Cleanup old backups"""
    backup_mgr = get_backup_manager()
    
    retention_days = args.retention if args.retention else backup_mgr.backup_config['retention_days']
    
    print(f"\n🗑️  Cleaning up backups older than {retention_days} days...")
    
    if not args.yes:
        response = input("   Proceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cleanup cancelled")
            return
    
    try:
        deleted_files = backup_mgr.cleanup_old_backups(retention_days=retention_days)
        
        if deleted_files:
            print(f"\n✅ Deleted {len(deleted_files)} backup(s):")
            for file in deleted_files:
                print(f"   - {file.name}")
        else:
            print("\n✅ No old backups to delete")
            
    except Exception as e:
        print(f"\n❌ Cleanup failed: {str(e)}")
        sys.exit(1)


def backup_stats(args):
    """Show backup statistics"""
    backup_mgr = get_backup_manager()
    
    stats = backup_mgr.get_backup_stats()
    
    print("\n📊 Backup Statistics:\n")
    print(f"   Total backups: {stats['total_backups']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")
    print(f"   Compressed: {stats['compressed_backups']}")
    print(f"   Uncompressed: {stats['uncompressed_backups']}")
    
    if stats['oldest_backup']:
        print(f"   Oldest: {stats['oldest_backup']}")
    if stats['newest_backup']:
        print(f"   Newest: {stats['newest_backup']}")
    
    print(f"\n   Backup directory: {stats['backup_directory']}")
    print(f"   Retention policy: {stats['retention_days']} days")


def verify_backup(args):
    """Verify backup integrity"""
    backup_mgr = get_backup_manager()
    backup_file = Path(args.file)
    
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)
    
    print(f"\n🔍 Verifying backup: {backup_file.name}...")
    
    if backup_mgr.verify_backup(backup_file):
        print("✅ Backup is valid")
    else:
        print("❌ Backup verification failed")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage database backups for Optimizer V3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create backup
  python scripts/manage_backups.py create
  
  # Create compressed backup with custom name
  python scripts/manage_backups.py create --name my_backup --compress
  
  # List all backups
  python scripts/manage_backups.py list
  
  # Restore from backup
  python scripts/manage_backups.py restore backup_file.sql.gz
  
  # Restore with drop-create
  python scripts/manage_backups.py restore backup_file.sql.gz --drop --yes
  
  # Cleanup old backups (uses retention from config)
  python scripts/manage_backups.py cleanup
  
  # Cleanup backups older than 7 days
  python scripts/manage_backups.py cleanup --retention 7 --yes
  
  # Show backup statistics
  python scripts/manage_backups.py stats
  
  # Verify backup integrity
  python scripts/manage_backups.py verify backup_file.sql.gz
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create backup
    create_parser = subparsers.add_parser('create', help='Create new backup')
    create_parser.add_argument('--name', help='Custom backup name')
    create_parser.add_argument('--compress', action='store_true', help='Compress backup')
    create_parser.set_defaults(func=create_backup)
    
    # Restore backup
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('file', help='Backup file path')
    restore_parser.add_argument('--drop', action='store_true', 
                               help='Drop existing database first')
    restore_parser.add_argument('--yes', action='store_true', 
                               help='Skip confirmation prompt')
    restore_parser.set_defaults(func=restore_backup)
    
    # List backups
    list_parser = subparsers.add_parser('list', help='List all backups')
    list_parser.set_defaults(func=list_backups)
    
    # Cleanup backups
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old backups')
    cleanup_parser.add_argument('--retention', type=int, 
                               help='Retention days (default: from config)')
    cleanup_parser.add_argument('--yes', action='store_true', 
                               help='Skip confirmation prompt')
    cleanup_parser.set_defaults(func=cleanup_backups)
    
    # Backup statistics
    stats_parser = subparsers.add_parser('stats', help='Show backup statistics')
    stats_parser.set_defaults(func=backup_stats)
    
    # Verify backup
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('file', help='Backup file path')
    verify_parser.set_defaults(func=verify_backup)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute the command
    args.func(args)


if __name__ == '__main__':
    main()
