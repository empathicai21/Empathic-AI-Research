#!/usr/bin/env python3
"""
Data Migration Script: Neon → Supabase
Run this script to migrate your data from Neon to Supabase
"""

import os
import sys
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_data():
    """Migrate data from Neon to Supabase"""
    
    # Original Neon connection (from your backup)
    neon_url = "postgresql://neondb_owner:npg_YXGeo09Jbitm@ep-frosty-sea-afgjjeq0-pooler.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    # Get Supabase URL from environment (user needs to set their password)
    supabase_url = os.getenv("DATABASE_URL")
    
    if not supabase_url or "YOUR_PASSWORD" in supabase_url:
        print("❌ Error: Please update DATABASE_URL in .env file with your actual Supabase password")
        print("Replace 'YOUR_PASSWORD' with your real Supabase database password")
        return False
    
    print("🔄 Starting data migration from Neon to Supabase...")
    
    try:
        # Connect to both databases
        print("📡 Connecting to Neon database...")
        neon_engine = create_engine(neon_url, echo=False)
        
        print("📡 Connecting to Supabase database...")
        supabase_engine = create_engine(supabase_url, echo=False)
        
        # Test connections
        with neon_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✅ Neon connection successful")
            
        with supabase_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("✅ Supabase connection successful")
            
        # Get table list from Neon
        with neon_engine.connect() as neon_conn:
            tables_result = neon_conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """))
            tables = [row[0] for row in tables_result]
            
        print(f"📋 Found {len(tables)} tables to migrate: {', '.join(tables)}")
        
        # Migrate each table
        for table in tables:
            print(f"🔄 Migrating table: {table}")
            
            # Get data from Neon
            with neon_engine.connect() as neon_conn:
                data_result = neon_conn.execute(text(f"SELECT * FROM {table}"))
                rows = data_result.fetchall()
                columns = data_result.keys()
                
            print(f"  📊 Found {len(rows)} rows in {table}")
            
            if len(rows) > 0:
                # Insert data into Supabase
                with supabase_engine.connect() as supabase_conn:
                    # Clear existing data (optional - comment out if you want to keep existing data)
                    supabase_conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                    
                    # Insert data
                    for row in rows:
                        placeholders = ', '.join([f':{col}' for col in columns])
                        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                        
                        # Convert row to dict
                        row_dict = dict(zip(columns, row))
                        supabase_conn.execute(text(query), row_dict)
                    
                    supabase_conn.commit()
                    
            print(f"  ✅ Migrated {len(rows)} rows to {table}")
            
        print("🎉 Data migration completed successfully!")
        
        # Verify migration
        print("\n📊 Verification Summary:")
        with supabase_engine.connect() as supabase_conn:
            for table in tables:
                count_result = supabase_conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.fetchone()[0]
                print(f"  {table}: {count} rows")
                
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    
    finally:
        # Close connections
        try:
            neon_engine.dispose()
            supabase_engine.dispose()
        except:
            pass

if __name__ == "__main__":
    print("🚀 Neon → Supabase Data Migration Tool")
    print("=" * 50)
    
    success = migrate_data()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("🔧 Next steps:")
        print("1. Test your application with the new Supabase connection")
        print("2. Update Streamlit Cloud secrets with new DATABASE_URL")
        print("3. Deploy and verify everything works")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)