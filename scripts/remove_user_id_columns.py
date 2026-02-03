#!/usr/bin/env python3
"""
Remove user_id columns from company-scoped tables
Makes data fully company-scoped instead of user-scoped
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def main():
    """Remove user_id columns from tables"""
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("Removing user_id Columns from Company-Scoped Tables")
        print("=" * 70)
        print()
        
        tables_to_update = [
            'api_tokens',
            'alerts',
            'blocked_ips',
            'whitelisted_ips'
        ]
        
        for table in tables_to_update:
            print(f"Processing table: {table}")
            try:
                # Check if user_id column exists
                result = db.session.execute(text(f"PRAGMA table_info({table})"))
                columns = [row[1] for row in result]
                
                if 'user_id' in columns:
                    print(f"  - Found user_id column")
                    
                    # SQLite doesn't support DROP COLUMN directly
                    # We need to recreate the table without the column
                    
                    # Step 1: Get the CREATE TABLE statement
                    result = db.session.execute(text(
                        f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'"
                    ))
                    create_sql = result.fetchone()[0]
                    
                    # Step 2: Create a temporary table
                    print(f"  - Creating temporary table...")
                    db.session.execute(text(f"ALTER TABLE {table} RENAME TO {table}_old"))
                    
                    # Step 3: Get column names (excluding user_id)
                    non_user_columns = [col for col in columns if col != 'user_id']
                    columns_str = ', '.join(non_user_columns)
                    
                    # Step 4: Create new table without user_id
                    # We'll recreate with a simplified schema
                    print(f"  - Recreating table without user_id...")
                    
                    if table == 'api_tokens':
                        db.session.execute(text(f"""
                            CREATE TABLE {table} (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                token_hash VARCHAR(255) UNIQUE NOT NULL,
                                token_prefix VARCHAR(20) NOT NULL,
                                name VARCHAR(100),
                                is_active BOOLEAN DEFAULT 1,
                                requests_today INTEGER DEFAULT 0,
                                last_used_at DATETIME,
                                created_at DATETIME,
                                expires_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                            )
                        """))
                    elif table == 'alerts':
                        db.session.execute(text(f"""
                            CREATE TABLE {table} (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                source_ip VARCHAR(45) NOT NULL,
                                source_port INTEGER,
                                destination_ip VARCHAR(45),
                                destination_port INTEGER,
                                protocol VARCHAR(10),
                                attack_type VARCHAR(100) NOT NULL,
                                severity VARCHAR(20) NOT NULL,
                                confidence FLOAT NOT NULL,
                                raw_features TEXT,
                                created_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                            )
                        """))
                    elif table == 'blocked_ips':
                        db.session.execute(text(f"""
                            CREATE TABLE {table} (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                ip_address VARCHAR(45) NOT NULL,
                                reason VARCHAR(255),
                                related_alert_id INTEGER,
                                block_type VARCHAR(20) DEFAULT 'manual',
                                is_active BOOLEAN DEFAULT 1,
                                expires_at DATETIME,
                                ufw_rule_number INTEGER,
                                snort_rule_id VARCHAR(100),
                                created_at DATETIME,
                                deactivated_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                FOREIGN KEY (related_alert_id) REFERENCES alerts(id)
                            )
                        """))
                    elif table == 'whitelisted_ips':
                        db.session.execute(text(f"""
                            CREATE TABLE {table} (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                ip_address VARCHAR(45) NOT NULL,
                                description VARCHAR(255),
                                is_active BOOLEAN DEFAULT 1,
                                created_at DATETIME,
                                created_by INTEGER,
                                expires_at DATETIME,
                                deactivated_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                FOREIGN KEY (created_by) REFERENCES users(id)
                            )
                        """))
                    
                    # Step 5: Copy data
                    print(f"  - Copying data...")
                    db.session.execute(text(
                        f"INSERT INTO {table} ({columns_str}) SELECT {columns_str} FROM {table}_old"
                    ))
                    
                    # Step 6: Drop old table
                    print(f"  - Dropping old table...")
                    db.session.execute(text(f"DROP TABLE {table}_old"))
                    
                    # Step 7: Recreate indexes
                    print(f"  - Recreating indexes...")
                    if table == 'api_tokens':
                        db.session.execute(text(f"CREATE INDEX ix_{table}_company_id ON {table}(company_id)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_token_hash ON {table}(token_hash)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_is_active ON {table}(is_active)"))
                    elif table == 'alerts':
                        db.session.execute(text(f"CREATE INDEX ix_{table}_company_id ON {table}(company_id)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_source_ip ON {table}(source_ip)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_attack_type ON {table}(attack_type)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_severity ON {table}(severity)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_created_at ON {table}(created_at)"))
                    elif table == 'blocked_ips':
                        db.session.execute(text(f"CREATE INDEX ix_{table}_company_id ON {table}(company_id)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_ip_address ON {table}(ip_address)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_is_active ON {table}(is_active)"))
                    elif table == 'whitelisted_ips':
                        db.session.execute(text(f"CREATE INDEX ix_{table}_company_id ON {table}(company_id)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_ip_address ON {table}(ip_address)"))
                        db.session.execute(text(f"CREATE INDEX ix_{table}_is_active ON {table}(is_active)"))
                    
                    db.session.commit()
                    print(f"  ✓ Successfully removed user_id from {table}")
                else:
                    print(f"  ✓ user_id column not found (already removed)")
                
                print()
                
            except Exception as e:
                print(f"  ✗ Error processing {table}: {e}")
                db.session.rollback()
                return
        
        # Verify changes
        print("=" * 70)
        print("Verification")
        print("=" * 70)
        print()
        
        for table in tables_to_update:
            result = db.session.execute(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in result]
            
            has_company_id = 'company_id' in columns
            has_user_id = 'user_id' in columns
            
            status = "✓" if has_company_id and not has_user_id else "✗"
            print(f"{status} {table}:")
            print(f"    company_id: {'✓' if has_company_id else '✗'}")
            print(f"    user_id: {'✗ (removed)' if not has_user_id else '✓ (ERROR: still exists)'}")
        
        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)
        print("\nAll tables are now fully company-scoped.")

if __name__ == '__main__':
    main()
