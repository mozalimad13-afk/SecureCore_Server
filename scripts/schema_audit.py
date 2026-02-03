"""Non-destructive database schema audit.

Compares the live database (SQLite) to SQLAlchemy model metadata.

Usage:
  cd server
  source finalProjectCS4/bin/activate
  python scripts/schema_audit.py

Notes:
- This script does NOT modify the database.
- For now it focuses on table/column presence and basic mismatches.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Allow running as `python scripts/schema_audit.py` from `server/`.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool


def _sqlite_table_info(conn, table: str) -> dict[str, ColumnInfo]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    out: dict[str, ColumnInfo] = {}
    for _cid, name, ctype, notnull, _dflt, _pk in cur.fetchall():
        out[name] = ColumnInfo(name=name, type=str(ctype), nullable=(notnull == 0))
    return out


def main() -> int:
    app = create_app(os.getenv('FLASK_ENV', 'development'))

    from app.extensions import db

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != 'sqlite':
            print(f"schema_audit: only SQLite is supported right now (got {engine.dialect.name!r}).")
            return 2

        db_path = str(engine.url.database)
        print('DB:', db_path)

        import sqlite3

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        live_tables = {r[0] for r in cur.fetchall()}

        model_tables = set(db.metadata.tables.keys())

        missing_in_db = sorted(model_tables - live_tables)
        extra_in_db = sorted(live_tables - model_tables)

        if missing_in_db:
            print('\nTables missing in DB (exist in models):')
            for t in missing_in_db:
                print('  -', t)

        if extra_in_db:
            print('\nTables present in DB (missing in models):')
            for t in extra_in_db:
                print('  -', t)

        # Column comparison
        mismatches = []
        for tname in sorted(model_tables & live_tables):
            model_cols = {c.name for c in db.metadata.tables[tname].columns}
            live_cols = set(_sqlite_table_info(conn, tname).keys())

            miss_cols = sorted(model_cols - live_cols)
            extra_cols = sorted(live_cols - model_cols)
            if miss_cols or extra_cols:
                mismatches.append((tname, miss_cols, extra_cols))

        if mismatches:
            print('\nColumn mismatches:')
            for tname, miss_cols, extra_cols in mismatches:
                print(f"\n== {tname}")
                if miss_cols:
                    print('  missing:', ', '.join(miss_cols))
                if extra_cols:
                    print('  extra:  ', ', '.join(extra_cols))

        ok = (not missing_in_db) and (not mismatches)
        print('\nResult:', 'OK' if ok else 'NEEDS ATTENTION')
        return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
