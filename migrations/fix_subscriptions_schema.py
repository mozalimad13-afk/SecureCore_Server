"""
Fix Subscriptions Table in the CORRECT database (data/securecore.db)
Removes user_id column and keeps only company_id
"""
import sqlite3
import os
from datetime import datetime

# Correct database path - data/securecore.db (not instance/)
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'securecore.db')

def fix_subscriptions_table():
    """Recreate subscriptions table without user_id column"""
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        row_count = cursor.fetchone()[0]
        print(f"Found {row_count} existing subscription records")
        
        # Backup existing data
        if row_count > 0:
            cursor.execute("SELECT id, company_id, plan_name, plan_price, status, start_date, end_date, next_billing_date, max_requests_per_minute, max_requests_per_month, created_at, updated_at FROM subscriptions")
            backup_data = cursor.fetchall()
            print(f"Backed up {len(backup_data)} records")
        else:
            backup_data = []
        
        # Drop old table
        print("Dropping old subscriptions table...")
        cursor.execute("DROP TABLE IF EXISTS subscriptions")
        
        # Create new table WITHOUT user_id
        print("Creating new subscriptions table (company_id only, no user_id)...")
        cursor.execute("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                plan_name VARCHAR(100) NOT NULL,
                plan_price NUMERIC(10, 2) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'trial',
                start_date DATE NOT NULL DEFAULT (DATE('now')),
                end_date DATE,
                next_billing_date DATE,
                max_requests_per_minute INTEGER DEFAULT 1000,
                max_requests_per_month INTEGER DEFAULT 1000000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX ix_subscriptions_company_id ON subscriptions (company_id)")
        cursor.execute("CREATE INDEX ix_subscriptions_status ON subscriptions (status)")
        
        # Restore data (if any)
        if backup_data:
            print(f"Restoring {len(backup_data)} records...")
            cursor.executemany("""
                INSERT INTO subscriptions (
                    id, company_id, plan_name, plan_price, status,
                    start_date, end_date, next_billing_date,
                    max_requests_per_minute, max_requests_per_month,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, backup_data)
            print(f"Restored {cursor.rowcount} records")
        
        conn.commit()
        print("\n✅ Subscriptions table fixed successfully!")
        
        # Verify new structure
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = cursor.fetchall()
        print("\nNew table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}){' NOT NULL' if col[3] else ''}")
        
        # Verify no user_id column
        has_user_id = any(col[1] == 'user_id' for col in columns)
        if has_user_id:
            print("\n❌ ERROR: user_id column still exists!")
        else:
            print("\n✅ Confirmed: user_id column removed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    fix_subscriptions_table()
