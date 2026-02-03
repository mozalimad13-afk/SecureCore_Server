from app import create_app
from app.extensions import db
import os


def sync_db():
    # Import models package so SQLAlchemy models are registered
    import app.models  # noqa: F401

    app = create_app()
    with app.app_context():
        db.create_all()

        # --- SQLite schema fixes (lightweight migrations) ---
        # Ensure `payment_methods` is company-owned by removing legacy `user_id`.
        try:
            engine_name = str(db.engine.url.drivername)
            if engine_name.startswith('sqlite'):
                res = db.session.execute(db.text("PRAGMA table_info(payment_methods)"))
                cols = [r[1] for r in res.fetchall()]
                if 'user_id' in cols:
                    db.session.execute(db.text("""
                        CREATE TABLE IF NOT EXISTS payment_methods_new (
                            id INTEGER NOT NULL,
                            company_id INTEGER NOT NULL,
                            card_last4 VARCHAR(4) NOT NULL,
                            card_brand VARCHAR(20),
                            card_holder_name VARCHAR(100) NOT NULL,
                            expiry_month VARCHAR(2) NOT NULL,
                            expiry_year VARCHAR(2) NOT NULL,
                            billing_address VARCHAR(255),
                            city VARCHAR(100),
                            zip_code VARCHAR(20),
                            is_default BOOLEAN NOT NULL,
                            is_active BOOLEAN NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            PRIMARY KEY (id),
                            FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
                        )
                    """))
                    db.session.execute(db.text("""
                        INSERT INTO payment_methods_new (
                            id, company_id, card_last4, card_brand, card_holder_name,
                            expiry_month, expiry_year, billing_address, city, zip_code,
                            is_default, is_active, created_at, updated_at
                        )
                        SELECT
                            pm.id,
                            COALESCE(pm.company_id, u.company_id) AS company_id,
                            pm.card_last4, pm.card_brand, pm.card_holder_name,
                            pm.expiry_month, pm.expiry_year, pm.billing_address, pm.city, pm.zip_code,
                            pm.is_default, pm.is_active, pm.created_at, pm.updated_at
                        FROM payment_methods pm
                        LEFT JOIN users u ON u.id = pm.user_id
                        WHERE COALESCE(pm.company_id, u.company_id) IS NOT NULL
                    """))
                    db.session.execute(db.text("DROP TABLE payment_methods"))
                    db.session.execute(db.text("ALTER TABLE payment_methods_new RENAME TO payment_methods"))
                    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS ix_payment_methods_company_id ON payment_methods (company_id)"))
                    db.session.commit()
        except Exception:
            db.session.rollback()

        # Optional: minimize fcm_devices schema for mobile-only deployments.
        if os.getenv('MIGRATE_MINIMAL_FCM_DEVICES', '').strip() in {'1', 'true', 'TRUE', 'yes', 'YES'}:
            try:
                from scripts.migrate_minimal_fcm_devices import main as migrate_minimal_fcm_devices
                migrate_minimal_fcm_devices()
            except Exception as e:
                print(f"FCM devices migration skipped/failed: {e}")

        # Backfill tenant_id for existing installations (idempotent)
        try:
            from scripts.migrate_add_tenants import main as migrate_add_tenants
            migrate_add_tenants()
        except Exception as e:
            print(f"Tenant migration skipped/failed: {e}")

        print("Database synced successfully. All missing tables (including 'backups') should be created.")


if __name__ == '__main__':
    sync_db()
