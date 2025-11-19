"""
Database Setup Script
Initialize or reset the database for the research platform.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager
load_dotenv()
from src.database.models import Base


def setup_database(reset: bool = False, force: bool = False):
    """
    Setup or reset the database.
    
    Args:
        reset: If True, delete existing database and create fresh one
    """
    db_path = project_root / "data" / "database" / "conversations.db"
    
    print("=" * 60)
    print("DATABASE SETUP")
    print("=" * 60)
    print()
    
    # If using DATABASE_URL (Postgres, etc.), we skip local file checks
    using_url = bool(os.getenv("DATABASE_URL"))

    # Check if local SQLite database exists when not using external URL
    if not using_url and db_path.exists():
        if reset:
            print(f"⚠️  Database exists at: {db_path}")
            if not force:
                confirm = input("Delete existing database and create new one? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Aborted. No changes made.")
                    return
            else:
                print("--yes provided: proceeding without interactive confirmation")
            
            # Delete existing database
            db_path.unlink()
            print("✓ Deleted existing database")
        else:
            print(f"Database already exists at: {db_path}")
            print("Use --reset flag to delete and recreate.")
            return
    
    # Create database directory if needed (SQLite only)
    if not using_url:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database (DatabaseManager will honor DATABASE_URL if set; for Supabase, include sslmode=require)
    if using_url:
        print("Using DATABASE_URL to initialize remote Postgres (tables will be created if missing)...")
    else:
        print(f"Creating database at: {db_path}")
    db_manager = DatabaseManager(str(db_path))

    # For remote DBs, apply reset by dropping/recreating tables
    if using_url and reset:
        print("\nRemote reset requested.")
        if not force:
            confirm = input("This will DROP and RECREATE all tables on the remote DB. Type 'yes' to confirm: ")
            if confirm.lower() != 'yes':
                print("Aborted. No changes made.")
                return
        else:
            print("--yes provided: proceeding without interactive confirmation")

        try:
            print("Dropping all tables...")
            Base.metadata.drop_all(db_manager.engine)
            print("Recreating tables...")
            Base.metadata.create_all(db_manager.engine)
            print("✓ Remote database reset complete")
        except Exception as e:
            print(f"✗ Failed to reset remote database: {e}")
            raise
    
    print()
    print("✓ Database created successfully!")
    print()
    print("Database includes the following tables:")
    print("  - participants (participant information)")
    print("  - messages (conversation messages)")
    print("  - crisis_flags (safety monitoring)")
    print("  - export_logs (export tracking)")
    print()
    print("Database is ready for use.")
    print("=" * 60)


def verify_database():
    """Verify database structure and display statistics."""
    db_path = project_root / "data" / "database" / "conversations.db"
    
    if not db_path.exists():
        print("No database found. Run setup first.")
        return
    
    print("=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)
    print()
    
    db_manager = DatabaseManager(str(db_path))
    stats = db_manager.get_statistics()
    
    print("Database Status: ✓ OK")
    print(f"Location: {db_path}")
    print()
    print("Current Statistics:")
    print(f"  Total Participants: {stats['total_participants']}")
    print(f"  Completed Conversations: {stats['completed_conversations']}")
    print(f"  Total Messages: {stats['total_messages']}")
    print(f"  Crisis Flags: {stats['crisis_flags']}")
    print()
    print("Bot Distribution:")
    for bot_type, count in stats['bot_distribution'].items():
        print(f"  {bot_type.capitalize()}: {count}")
    print()
    print("=" * 60)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database setup utility")
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Delete existing database and create new one'
    )
    parser.add_argument(
        '--yes', '--force',
        dest='yes',
        action='store_true',
        help='Proceed without interactive confirmation prompts'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify database and show statistics'
    )
    
    args = parser.parse_args()
    
    if args.verify:
        verify_database()
    else:
        setup_database(reset=args.reset, force=args.yes)


if __name__ == "__main__":
    main()