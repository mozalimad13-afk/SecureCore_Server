#!/usr/bin/env python3
"""
Creates audit_logs table if missing.
"""

from app import create_app
from app.extensions import db


def table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        if table_exists(inspector, 'audit_logs'):
            print('ℹ️  audit_logs already exists; skipping')
            return

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(db.text(
                    """
                    CREATE TABLE audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                        action VARCHAR(100) NOT NULL,
                        resource_type VARCHAR(100) NOT NULL,
                        resource_id INTEGER,
                        details JSON,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT idx_audit_company_id_created_at UNIQUE (id)
                    )
                    """
                ))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_company_id ON audit_logs (company_id)"))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id)"))
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)"))
                trans.commit()
                print('✅ audit_logs table created')
            except Exception as exc:
                trans.rollback()
                print(f'❌ Failed to create audit_logs: {exc}')
                raise


if __name__ == '__main__':
    main()
