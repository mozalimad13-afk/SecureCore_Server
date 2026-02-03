#!/usr/bin/env python3
"""Add company_id column to locations and adjust unique constraints (SQLite)."""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'locations' not in tables:
            print('⚠️  locations table not found; skipping')
            return

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                cols = {col['name'] for col in inspector.get_columns('locations')}
                if 'company_id' not in cols:
                    print('🔄 Adding company_id column to locations')
                    conn.execute(text('ALTER TABLE locations ADD COLUMN company_id INTEGER'))
                else:
                    print('ℹ️  company_id already present on locations')

                # SQLite cannot drop/add unique constraints easily post-hoc; rely on application-level constraints.
                trans.commit()
                print('✅ Migration complete')
            except Exception as exc:
                trans.rollback()
                print(f'❌ Migration failed: {exc}')
                raise


if __name__ == '__main__':
    main()
