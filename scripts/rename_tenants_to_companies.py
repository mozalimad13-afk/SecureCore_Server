#!/usr/bin/env python3
"""
One-time migration: rename tenants -> companies and tenant_id -> company_id.

Safe to run multiple times; skips operations that are already applied.
Works with SQLite (requires SQLite 3.25+ for column rename).
"""

from app import create_app
from app.extensions import db


def table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col['name'] == column_name for col in inspector.get_columns(table_name))


def rename_column(conn, inspector, table_name: str, old: str, new: str):
    if not table_exists(inspector, table_name):
        print(f"ℹ️  Skip {table_name}.{old} -> {new}: table missing")
        return
    if not has_column(inspector, table_name, old):
        print(f"ℹ️  Skip {table_name}.{old} -> {new}: column missing")
        return
    if has_column(inspector, table_name, new):
        print(f"ℹ️  {table_name} already has column {new}; skipping rename")
        return
    print(f"🔄 Renaming {table_name}.{old} -> {new}")
    conn.execute(db.text(f'ALTER TABLE {table_name} RENAME COLUMN {old} TO {new}'))


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Rename tenants table to companies
                if table_exists(inspector, 'companies'):
                    print('ℹ️  companies table already exists; skipping table rename')
                elif table_exists(inspector, 'tenants'):
                    print('🔄 Renaming table tenants -> companies')
                    conn.execute(db.text('ALTER TABLE tenants RENAME TO companies'))
                else:
                    print('⚠️  tenants table not found; nothing to rename')

                # Refresh inspector after possible table rename
                inspector = db.inspect(db.engine)

                # Rename tenant_id columns to company_id
                rename_column(conn, inspector, 'users', 'tenant_id', 'company_id')
                rename_column(conn, inspector, 'fcm_devices', 'tenant_id', 'company_id')
                rename_column(conn, inspector, 'admin_broadcasts', 'tenant_id', 'company_id')
                rename_column(conn, inspector, 'payment_methods', 'tenant_id', 'company_id')

                trans.commit()
                print('✅ Migration complete')
            except Exception as exc:
                trans.rollback()
                print(f'❌ Migration failed: {exc}')
                raise


if __name__ == '__main__':
    main()
