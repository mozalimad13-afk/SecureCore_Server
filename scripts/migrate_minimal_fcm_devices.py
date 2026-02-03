"""SQLite migration: minimize fcm_devices columns.

Goal:
- Mobile login should require only: email/password/device_id.
- Store device_id encrypted-at-rest, plus a hash for lookup.
- Keep optional `device_token_encrypted` for push notifications.

This migration rebuilds the `fcm_devices` table to a minimal schema:
  id, tenant_id, user_id,
  device_id_hash, device_id_encrypted, device_token_encrypted,
  last_seen_at, is_active, last_notified_at,
  created_at, updated_at

It preserves existing data for these columns.

Usage:
  python scripts/migrate_minimal_fcm_devices.py

Notes:
- Designed for SQLite.
- Safe/idempotent: if the table is already minimal, it exits.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Allow running this script from any working directory.
SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config import Config


MINIMAL_COLS = [
    'id',
    'tenant_id',
    'user_id',
    'device_id_hash',
    'device_id_encrypted',
    'device_token_encrypted',
    'last_seen_at',
    'is_active',
    'last_notified_at',
    'created_at',
    'updated_at',
]


def _sqlite_path_from_uri(uri: str) -> Path:
    if not uri.startswith('sqlite:///'):
        raise RuntimeError(f'Only sqlite URIs supported, got: {uri}')
    return Path(uri.replace('sqlite:///', ''))


def main() -> None:
    db_path = _sqlite_path_from_uri(Config.SQLALCHEMY_DATABASE_URI)
    if not db_path.exists():
        raise FileNotFoundError(f'Database not found: {db_path}')

    con = sqlite3.connect(db_path)
    con.execute('PRAGMA foreign_keys=OFF')

    try:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fcm_devices'")
        if cur.fetchone() is None:
            print('No fcm_devices table found; nothing to migrate.')
            return

        cur.execute('PRAGMA table_info(fcm_devices)')
        existing_cols = [row[1] for row in cur.fetchall()]

        # If already minimal (or a subset that includes all minimal), we can skip.
        if all(c in existing_cols for c in MINIMAL_COLS) and not any(
            c for c in existing_cols if c not in MINIMAL_COLS
        ):
            print('fcm_devices already minimal; nothing to do.')
            return

        print('Migrating fcm_devices -> minimal schema...')

        # Create new minimal table
        con.execute('''
            CREATE TABLE fcm_devices_new (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                user_id INTEGER NOT NULL,
                device_id_hash VARCHAR(64),
                device_id_encrypted BLOB,
                device_token_encrypted BLOB,
                last_seen_at DATETIME,
                is_active BOOLEAN,
                last_notified_at DATETIME,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')

        # Copy over compatible columns
        copy_cols = [c for c in MINIMAL_COLS if c in existing_cols]
        if not copy_cols:
            raise RuntimeError('Unexpected schema: no overlapping columns to copy')

        cols_csv = ', '.join(copy_cols)
        con.execute(f'INSERT INTO fcm_devices_new ({cols_csv}) SELECT {cols_csv} FROM fcm_devices')

        # Swap tables
        con.execute('ALTER TABLE fcm_devices RENAME TO fcm_devices_old')
        con.execute('ALTER TABLE fcm_devices_new RENAME TO fcm_devices')

        # Recreate indexes (best-effort)
        con.execute('CREATE INDEX IF NOT EXISTS ix_fcm_devices_user_id ON fcm_devices(user_id)')
        con.execute('CREATE INDEX IF NOT EXISTS ix_fcm_devices_tenant_id ON fcm_devices(tenant_id)')
        con.execute('CREATE INDEX IF NOT EXISTS ix_fcm_devices_device_id_hash ON fcm_devices(device_id_hash)')
        con.execute('CREATE INDEX IF NOT EXISTS ix_fcm_devices_is_active ON fcm_devices(is_active)')

        # Drop old table
        con.execute('DROP TABLE fcm_devices_old')

        con.commit()
        print('✅ Migration complete.')
    finally:
        con.execute('PRAGMA foreign_keys=ON')
        con.close()


if __name__ == '__main__':
    main()
