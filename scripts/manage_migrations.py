#!/usr/bin/env python3
"""
Database Migration Management Script
Task 0.5: Alembic Migration Helper

Simplifies common Alembic migration operations with validation and safety checks.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.database.config import get_db_config


def run_command(cmd: list, check=True) -> subprocess.CompletedProcess:
    """Run command and return result"""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def create_migration(message: str, autogenerate: bool = True):
    """Create a new database migration"""
    print(f"\n📝 Creating migration: {message}\n")
    
    cmd = ["alembic", "revision"]
    if autogenerate:
        cmd.append("--autogenerate")
    cmd.extend(["-m", message])
    
    try:
        result = run_command(cmd)
        print(result.stdout)
        print("\n✅ Migration created successfully")
        print("⚠️  Please review the generated migration file before applying!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to create migration: {e.stderr}")
        sys.exit(1)


def apply_migrations(revision: str = "head"):
    """Apply database migrations"""
    print(f"\n⬆️  Applying migrations to: {revision}\n")
    
    # Verify database configuration
    try:
        config = get_db_config()
        print(f"Target database: {config['host']}:{config['port']}/{config['database']}")
        
        response = input("\n⚠️  Proceed with migration? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Migration cancelled")
            return
    except Exception as e:
        print(f"❌ Failed to load database configuration: {e}")
        sys.exit(1)
    
    cmd = ["alembic", "upgrade", revision]
    
    try:
        result = run_command(cmd)
        print(result.stdout)
        print("\n✅ Migrations applied successfully")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to apply migrations: {e.stderr}")
        sys.exit(1)


def rollback_migrations(steps: int = 1):
    """Rollback database migrations"""
    print(f"\n⬇️  Rolling back {steps} migration(s)\n")
    
    # Verify database configuration
    try:
        config = get_db_config()
        print(f"Target database: {config['host']}:{config['port']}/{config['database']}")
        
        response = input("\n⚠️  Proceed with rollback? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Rollback cancelled")
            return
    except Exception as e:
        print(f"❌ Failed to load database configuration: {e}")
        sys.exit(1)
    
    cmd = ["alembic", "downgrade", f"-{steps}"]
    
    try:
        result = run_command(cmd)
        print(result.stdout)
        print(f"\n✅ Rolled back {steps} migration(s) successfully")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to rollback migrations: {e.stderr}")
        sys.exit(1)


def show_current():
    """Show current migration version"""
    print("\n📊 Current migration version:\n")
    
    cmd = ["alembic", "current"]
    
    try:
        result = run_command(cmd)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get current version: {e.stderr}")
        sys.exit(1)


def show_history():
    """Show migration history"""
    print("\n📜 Migration history:\n")
    
    cmd = ["alembic", "history", "--verbose"]
    
    try:
        result = run_command(cmd)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get history: {e.stderr}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage database migrations for Optimizer V3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new migration
  python scripts/manage_migrations.py create "Add user preferences table"
  
  # Apply all pending migrations
  python scripts/manage_migrations.py upgrade
  
  # Rollback last migration
  python scripts/manage_migrations.py downgrade
  
  # Show current version
  python scripts/manage_migrations.py current
  
  # Show migration history
  python scripts/manage_migrations.py history
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create migration
    create_parser = subparsers.add_parser('create', help='Create a new migration')
    create_parser.add_argument('message', help='Migration description')
    create_parser.add_argument('--no-autogenerate', action='store_true',
                              help='Create empty migration (no autogenerate)')
    
    # Apply migrations
    upgrade_parser = subparsers.add_parser('upgrade', help='Apply migrations')
    upgrade_parser.add_argument('revision', nargs='?', default='head',
                               help='Target revision (default: head)')
    
    # Rollback migrations
    downgrade_parser = subparsers.add_parser('downgrade', help='Rollback migrations')
    downgrade_parser.add_argument('steps', nargs='?', type=int, default=1,
                                 help='Number of migrations to rollback (default: 1)')
    
    # Show current version
    subparsers.add_parser('current', help='Show current migration version')
    
    # Show history
    subparsers.add_parser('history', help='Show migration history')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'create':
        create_migration(args.message, autogenerate=not args.no_autogenerate)
    elif args.command == 'upgrade':
        apply_migrations(args.revision)
    elif args.command == 'downgrade':
        rollback_migrations(args.steps)
    elif args.command == 'current':
        show_current()
    elif args.command == 'history':
        show_history()


if __name__ == '__main__':
    main()
