#!/usr/bin/env python3
"""
Hard-delete legacy tenant artifacts after the company cutover.

- Drops the `tenants` table if it still exists.
- Drops any `tenant_id` column that may remain on tables (post-rename/migration).

Safe to run multiple times; skips work that's already done.
Requires SQLite >= 3.35 for `ALTER TABLE DROP COLUMN` (or any DB that supports it).
"""

from app import create_app
from app.extensions import db


def table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def sqlite_supports_drop_column(conn) -> bool:
    if "sqlite" not in conn.engine.name:
        return True
    version_str = conn.exec_driver_sql("select sqlite_version() as v").scalar() or "0"
    parts = version_str.split(".")
    major, minor, patch = (int(x) for x in (parts + [0, 0, 0])[:3])
    return (major, minor, patch) >= (3, 35, 0)


def drop_column(conn, inspector, table_name: str, column_name: str):
    if not table_exists(inspector, table_name):
        print(f"ℹ️  Skip {table_name}.{column_name}: table missing")
        return
    if not has_column(inspector, table_name, column_name):
        print(f"ℹ️  Skip {table_name}.{column_name}: column missing")
        return
    if not sqlite_supports_drop_column(conn):
        raise RuntimeError(
            "SQLite version too old for DROP COLUMN (need >= 3.35). "
            f"Found {conn.exec_driver_sql('select sqlite_version()').scalar()}"
        )
    # Drop indexes that reference the column before dropping it
    for idx in inspector.get_indexes(table_name):
        cols = idx.get("column_names") or []
        if column_name in cols:
            idx_name = idx.get("name")
            print(f"🗑️  Dropping index {idx_name} on {table_name} (references {column_name})")
            conn.execute(db.text(f"DROP INDEX IF EXISTS {idx_name}"))
    print(f"🗑️  Dropping column {table_name}.{column_name}")
    conn.execute(db.text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))


def drop_tenants_table(conn, inspector):
    if table_exists(inspector, "tenants"):
        print("🗑️  Dropping tenants table")
        conn.execute(db.text("DROP TABLE tenants"))
    else:
        print("ℹ️  tenants table already removed")


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                drop_tenants_table(conn, inspector)

                # Refresh inspector after possible table drop
                inspector = db.inspect(db.engine)

                # Drop any remaining tenant_id columns across all tables
                tables = inspector.get_table_names()
                for table in tables:
                    drop_column(conn, inspector, table, "tenant_id")

                trans.commit()
                print("✅ Tenant artifacts removed")
            except Exception as exc:
                trans.rollback()
                print(f"❌ Failed to remove tenant artifacts: {exc}")
                raise


if __name__ == "__main__":
    main()
