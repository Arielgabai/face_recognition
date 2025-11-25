#!/usr/bin/env python3
"""
Migration script to add show_in_general column to photos table.
This column controls which photos appear in the "Général" tab.

- NULL (default): Use fallback behavior (show all photos)
- TRUE: Explicitly show in "Général" tab
- FALSE: Explicitly hide from "Général" tab

Usage:
    python migrate_add_show_in_general.py
"""
import sys
import os
from sqlalchemy import text
from database import engine, SessionLocal

def migrate():
    """Add show_in_general column to photos table"""
    print("Starting migration: Adding show_in_general column to photos table...")
    print(f"Database URL: {os.getenv('DATABASE_URL', 'Not set (using default)')}")
    
    try:
        with engine.connect() as conn:
            # Check if column already exists (PostgreSQL)
            print("Checking if column already exists...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='photos' AND column_name='show_in_general'
            """))
            
            if result.fetchone():
                print("✓ Column show_in_general already exists. Skipping migration.")
                return True
            
            # Add the column (default NULL for fallback behavior)
            print("Adding show_in_general column to photos table...")
            conn.execute(text("""
                ALTER TABLE photos 
                ADD COLUMN show_in_general BOOLEAN DEFAULT NULL
            """))
            conn.commit()
            
            print("✓ Migration completed successfully!")
            print("  - Column show_in_general added to photos table")
            print("  - Default value: NULL (fallback to showing all photos)")
            print("  - Photographers can now select which photos appear in 'Général' tab")
            print("\nℹ️  Redémarrez votre application pour que les changements prennent effet.")
            return True
            
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

