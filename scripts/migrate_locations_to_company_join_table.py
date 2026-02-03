#!/usr/bin/env python3
"""Migrate location scoping from `locations.company_id` to `companies_countries`.

What it does:
- Creates `companies_countries` join table if missing.
- Backfills mappings from existing `locations.company_id` values.
- Drops old constraints/indexes that reference `company_id` (best-effort).
- Rebuilds `locations` table without `company_id` (SQLite-safe).

Notes:
- Designed for SQLite dev DB.
- Makes a timestamped backup before changing the DB.

Run from `server/`:
    PYTHONPATH=$PWD:$PYTHONPATH python scripts/migrate_locations_to_company_join_table.py

Optional DB override:
    DATABASE_URL=sqlite:////abs/path/securecore.db PYTHONPATH=$PWD:$PYTHONPATH python scripts/migrate_locations_to_company_join_table.py
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

from sqlalchemy import text


def _db_path_from_uri(uri: str) -> str | None:
    if uri.startswith("sqlite:///"):
        return uri.replace("sqlite:///", "", 1)
    return None


def main() -> None:
    from app import create_app
    from app.extensions import db

    app = create_app("development")
    uri = app.config.get("SQLALCHEMY_DATABASE_URI")

    db_path = _db_path_from_uri(uri) if isinstance(uri, str) else None
    if db_path and os.path.exists(db_path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.bak.locations_m2m.{ts}"
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")

    with app.app_context():
        engine = db.engine

        with engine.begin() as conn:
            # 1) Create join table if missing
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS companies_countries (
                  company_id INTEGER NOT NULL,
                  location_id INTEGER NOT NULL,
                  PRIMARY KEY (company_id, location_id),
                  CONSTRAINT fk_cc_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                  CONSTRAINT fk_cc_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
                )
                """
            )

            # 2) Backfill mappings from locations.company_id
            # If locations has no company_id (already migrated), this will fail gracefully.
            try:
                res = conn.exec_driver_sql(
                    """
                    INSERT OR IGNORE INTO companies_countries(company_id, location_id)
                    SELECT company_id, id
                    FROM locations
                    WHERE company_id IS NOT NULL
                    """
                )
                print(f"Backfilled companies_countries rows: {res.rowcount}")
            except Exception as e:
                print(f"Backfill skipped (likely already migrated): {e}")

            # 3) Rebuild locations table without company_id (SQLite)
            cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(locations)").fetchall()]
            if "company_id" not in cols:
                print("locations.company_id not present; nothing to drop.")
                return

            # SQLite can't drop columns, so: create new table, copy, swap.
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS locations_new (
                  id INTEGER PRIMARY KEY,
                  code VARCHAR(2) NOT NULL,
                  name VARCHAR(100) NOT NULL
                )
                """
            )

            conn.exec_driver_sql(
                """
                INSERT INTO locations_new(id, code, name)
                SELECT id, code, name
                FROM locations
                """
            )

            conn.exec_driver_sql("DROP TABLE locations")
            conn.exec_driver_sql("ALTER TABLE locations_new RENAME TO locations")

            # Recreate uniqueness constraints
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_location_code ON locations(code)")
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_location_name ON locations(name)")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_locations_code ON locations(code)")

            print("Migration complete: dropped locations.company_id, created companies_countries.")


if __name__ == "__main__":
    main()
