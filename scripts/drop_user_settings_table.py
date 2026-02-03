#!/usr/bin/env python3
"""
Drop user_settings table and verify the database is clean
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def main():
    """Drop user_settings table"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Dropping user_settings table")
        print("=" * 60)
        print()
        
        try:
            # Drop the user_settings table
            print("Dropping user_settings table...")
            db.session.execute(text("DROP TABLE IF EXISTS user_settings"))
            db.session.commit()
            print("✓ user_settings table dropped successfully")
            
            # Verify tables
            print("\nVerifying database tables...")
            result = db.session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """))
            tables = [row[0] for row in result]
            
            print(f"\nExisting tables ({len(tables)}):")
            for table in tables:
                prefix = "  ✓ " if table != "user_settings" else "  ✗ "
                print(f"{prefix}{table}")
            
            # Check for our new tables
            print("\nVerifying new tables:")
            if 'company_settings' in tables:
                print("  ✓ company_settings exists")
            else:
                print("  ✗ company_settings NOT found")
            
            if 'user_profiles' in tables:
                print("  ✓ user_profiles exists")
            else:
                print("  ✗ user_profiles NOT found")
            
            if 'user_settings' in tables:
                print("  ⚠ user_settings still exists (should be dropped)")
            else:
                print("  ✓ user_settings successfully removed")
            
            print("\n" + "=" * 60)
            print("Database cleanup complete!")
            print("=" * 60)
            
        except Exception as e:
            print(f"✗ Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    main()
