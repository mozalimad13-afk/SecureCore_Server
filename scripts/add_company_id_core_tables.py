#!/usr/bin/env python3
"""Add company_id columns to core tables (alerts, blocked_ips, whitelisted_ips, notifications, subscriptions)."""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def ensure_column(conn, inspector, table: str, column: str):
    cols = {col['name'] for col in inspector.get_columns(table)}
    if column in cols:
        print(f"ℹ️  {table}.{column} already exists")
        return
    print(f"🔄 Adding {column} to {table}")
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER"))


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        target_tables = ['alerts', 'blocked_ips', 'whitelisted_ips', 'notifications', 'subscriptions']

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                for table in target_tables:
                    if table not in tables:
                        print(f"⚠️  {table} missing; skipping")
                        continue
                    ensure_column(conn, inspector, table, 'company_id')
                trans.commit()
                print('✅ Migration complete')
            except Exception as exc:
                trans.rollback()
                print(f'❌ Migration failed: {exc}')
                raise


if __name__ == '__main__':
    main()
