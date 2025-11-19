#!/usr/bin/env python3
"""
Database Inspector
Quick script to check what conversations are stored in the database.
"""

import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')
load_dotenv()

def check_database():
    """Check the contents of the conversation database."""
    # If DATABASE_URL is set (PostgreSQL, e.g., Supabase), use SQLAlchemy path instead of sqlite3 direct
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("✅ DATABASE_URL detected. Use scripts/setup_database.py --verify for a comprehensive check.")
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        stats = db.get_statistics()
        print("\nDatabase Status: ✓ OK (remote)")
        print("Current Statistics:")
        print(f"  Total Participants: {stats['total_participants']}")
        print(f"  Completed Conversations: {stats['completed_conversations']}")
        print(f"  Total Messages: {stats['total_messages']}")
        print(f"  Crisis Flags: {stats['crisis_flags']}")
        print("\nUse the admin dashboard to explore data interactively.")
        print("=" * 60)
        return
    
    db_path = "data/database/conversations.db"
    if not Path(db_path).exists():
        print(f"❌ Database not found at: {db_path}")
        return
    print(f"✅ Database found at: {db_path}")
    print("=" * 80)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"📋 Tables in database: {len(tables)}")
    for table in tables:
        print(f"   - {table[0]}")
    print()
    
    # Check participants
    try:
        cursor.execute("SELECT COUNT(*) FROM participants")
        participant_count = cursor.fetchone()[0]
        print(f"👥 Total participants: {participant_count}")
        
        if participant_count > 0:
            cursor.execute("""
                SELECT id, bot_type, total_messages, completed, 
                       datetime(start_time, 'localtime') as start_time,
                       datetime(end_time, 'localtime') as end_time
                FROM participants 
                ORDER BY start_time DESC 
                LIMIT 10
            """)
            participants = cursor.fetchall()
            
            print("\n📊 Recent Participants:")
            print("ID".ljust(12) + "Bot Type".ljust(15) + "Messages".ljust(10) + "Complete".ljust(10) + "Started")
            print("-" * 70)
            for p in participants:
                pid, bot_type, total_msg, completed, start_time, end_time = p
                completed_str = "✅ Yes" if completed else "⏳ No"
                start_str = start_time[:16] if start_time else "Unknown"
                print(f"{pid[:11].ljust(12)}{bot_type.ljust(15)}{str(total_msg).ljust(10)}{completed_str.ljust(10)}{start_str}")
    
    except sqlite3.OperationalError:
        print("❌ Participants table not found or empty")
    
    # Check messages
    try:
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        print(f"\n💬 Total messages: {message_count}")
        
        if message_count > 0:
            cursor.execute("""
                SELECT participant_id, message_num, sender, 
                       substr(content, 1, 50) as content_preview,
                       datetime(timestamp, 'localtime') as timestamp
                FROM messages 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            messages = cursor.fetchall()
            
            print("\n📝 Recent Messages:")
            print("Participant".ljust(12) + "Msg#".ljust(6) + "Sender".ljust(8) + "Content Preview".ljust(52) + "Time")
            print("-" * 90)
            for m in messages:
                pid, msg_num, sender, content, timestamp = m
                content_clean = content.replace('\n', ' ').strip()
                time_str = timestamp[:16] if timestamp else "Unknown"
                print(f"{pid[:11].ljust(12)}{str(msg_num).ljust(6)}{sender.ljust(8)}{content_clean[:50].ljust(52)}{time_str}")
    
    except sqlite3.OperationalError:
        print("❌ Messages table not found or empty")
    
    # Check crisis flags
    try:
        cursor.execute("SELECT COUNT(*) FROM crisis_flags")
        crisis_count = cursor.fetchone()[0]
        print(f"\n🚨 Crisis flags: {crisis_count}")
        
        if crisis_count > 0:
            cursor.execute("""
                SELECT cf.participant_id, cf.keyword_matched,
                       datetime(cf.flagged_at, 'localtime') as flagged_at
                FROM crisis_flags cf
                ORDER BY cf.flagged_at DESC
                LIMIT 5
            """)
            flags = cursor.fetchall()
            
            print("\n🚨 Recent Crisis Flags:")
            for flag in flags:
                print(f"   - {flag[0]}: '{flag[1]}' at {flag[2][:16]}")
    
    except sqlite3.OperationalError:
        print("❌ Crisis flags table not found or empty")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Database check complete!")

if __name__ == "__main__":
    check_database()