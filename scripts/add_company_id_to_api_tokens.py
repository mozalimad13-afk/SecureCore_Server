#!/usr/bin/env python3
"""
Adds company_id column to api_tokens and backfills from users.company_id.
Safe to run multiple times.
Requires SQLite >= 3.35 for DROP COLUMN if rollback needed, but only ADD COLUMN is used.
"""

from app import create_app
from app.extensions import db


def table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def add_column(conn, inspector, table: str, column_def: str, name: str):
    if not table_exists(inspector, table):
        print(f"ℹ️  Skip {table}.{name}: table missing")
        return False
    if has_column(inspector, table, name):
        print(f"ℹ️  {table} already has column {name}")
        return False
    print(f"➕ Adding column {table}.{name}")
    conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
    return True


def backfill_company(conn):
    print("🔄 Backfilling api_tokens.company_id from users.company_id")
    conn.execute(db.text(
        """
        UPDATE api_tokens
        SET company_id = (
            SELECT users.company_id FROM users WHERE users.id = api_tokens.user_id
        )
        WHERE company_id IS NULL
        """
    ))


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                added = add_column(conn, inspector, 'api_tokens', 'company_id INTEGER REFERENCES companies(id)', 'company_id')
                if added:
                    backfill_company(conn)
                trans.commit()
                print("✅ api_tokens company_id ensured")
            except Exception as exc:
                trans.rollback()
                print(f"❌ Migration failed: {exc}")
                raise


if __name__ == '__main__':
    main()
