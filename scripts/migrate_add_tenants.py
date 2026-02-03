"""SQLite migration: add tenants + tenant_id backfill.

This script is intentionally SQLite-safe and idempotent.

What it does:
- Ensures `tenants` table exists.
- Ensures `users.tenant_id` exists.
- Creates one tenant per existing user (company account == user) if missing.
- Adds `tenant_id` columns to tenant-owned tables if missing.
- Backfills `tenant_id` based on owning user's tenant_id.

Run:
  python server/scripts/migrate_add_tenants.py

NOTE:
- This does NOT enforce NOT NULL at the SQLite schema level.
  Enforcement is done at the application layer and via backfill.
"""

from __future__ import annotations

import os
import sqlite3
import secrets
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "server"
DEFAULT_DB_PATH = SERVER_DIR / "data" / "securecore.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in cur.fetchall())


def _add_column(conn: sqlite3.Connection, table: str, column_sql: str) -> None:
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def _indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA index_list({table})")
    return {r["name"] for r in cur.fetchall()}


def _create_index(conn: sqlite3.Connection, table: str, index_name: str, cols: str) -> None:
    conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({cols})")


def _ensure_tenants_table(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "tenants"):
        return

    conn.execute(
        """
        CREATE TABLE tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    _create_index(conn, "tenants", "ix_tenants_public_id", "public_id")


def _ensure_users_tenant_id(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "users"):
        raise RuntimeError("users table does not exist; run your app db init first")

    if not _column_exists(conn, "users", "tenant_id"):
        _add_column(conn, "users", "tenant_id INTEGER")
        _create_index(conn, "users", "ix_users_tenant_id", "tenant_id")


def _generate_public_id() -> str:
    return secrets.token_hex(16)


def _ensure_user_tenants(conn: sqlite3.Connection) -> None:
    """Create one tenant per user when users.tenant_id is null."""
    users = conn.execute("SELECT id, name, tenant_id FROM users").fetchall()

    for u in users:
        if u["tenant_id"] is not None:
            continue

        public_id = _generate_public_id()
        name = u["name"] or f"Tenant {u['id']}"
        conn.execute(
            "INSERT INTO tenants (public_id, name, created_at) VALUES (?, ?, datetime('now'))",
            (public_id, name),
        )
        tenant_row = conn.execute("SELECT last_insert_rowid() as id").fetchone()
        tenant_id = int(tenant_row["id"])
        conn.execute("UPDATE users SET tenant_id=? WHERE id=?", (tenant_id, u["id"]))


def _ensure_tenant_id_columns(conn: sqlite3.Connection) -> None:
    """Ensure tenant_id columns exist on tenant-owned tables."""
    # table -> (fk_owner_col)
    tables: dict[str, str] = {
        "alerts": "user_id",
        "api_tokens": "user_id",
        "subscriptions": "user_id",
        "notifications": "user_id",
        "admin_broadcasts": "sender_id",
        "websocket_sessions": "user_id",
        "blocked_ips": "user_id",
        "whitelisted_ips": "user_id",
        "user_settings": "user_id",
        "fcm_devices": "user_id",
        "payment_methods": "user_id",
        "csrf_tokens": "user_id",
    }

    for table in tables.keys():
        if not _table_exists(conn, table):
            continue
        if not _column_exists(conn, table, "tenant_id"):
            _add_column(conn, table, "tenant_id INTEGER")
            _create_index(conn, table, f"ix_{table}_tenant_id", "tenant_id")


def _backfill_table_tenant_id(conn: sqlite3.Connection, table: str, owner_col: str) -> None:
    if not _table_exists(conn, table):
        return
    if not _column_exists(conn, table, "tenant_id"):
        return

    # Only backfill rows where tenant_id is NULL
    conn.execute(
        f"""
        UPDATE {table}
        SET tenant_id = (
            SELECT u.tenant_id FROM users u WHERE u.id = {table}.{owner_col}
        )
        WHERE tenant_id IS NULL
        """
    )


def _backfill_all(conn: sqlite3.Connection) -> None:
    tables: dict[str, str] = {
        "alerts": "user_id",
        "api_tokens": "user_id",
        "subscriptions": "user_id",
        "notifications": "user_id",
        "admin_broadcasts": "sender_id",
        "websocket_sessions": "user_id",
        "blocked_ips": "user_id",
        "whitelisted_ips": "user_id",
        "user_settings": "user_id",
        "fcm_devices": "user_id",
        "payment_methods": "user_id",
        "csrf_tokens": "user_id",
    }

    for table, owner_col in tables.items():
        _backfill_table_tenant_id(conn, table, owner_col)


def main() -> int:
    db_path = Path(os.getenv("SECURECORE_DB_PATH", str(DEFAULT_DB_PATH))).resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found at {db_path}")

    conn = _connect(db_path)
    try:
        conn.execute("BEGIN")
        _ensure_tenants_table(conn)
        _ensure_users_tenant_id(conn)
        _ensure_user_tenants(conn)
        _ensure_tenant_id_columns(conn)
        _backfill_all(conn)
        conn.commit()
        print("Migration completed successfully")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
