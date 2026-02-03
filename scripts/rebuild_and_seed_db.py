"""Rebuild the dev SQLite DB and seed minimal company-scoped data.

This is intended for local development/testing only.

What it does:
- Creates a timestamped backup of `server/data/securecore.db` (if it exists)
- Drops & recreates all tables using SQLAlchemy models
- Ensures a default company exists
- Ensures `admin@securecore.com` exists with password `admin123`
- Ensures PBAC mapping `user_company_roles` has `admin` for that company
- Creates an active subscription for the admin user

Usage:
  PYTHONPATH=$PWD:$PYTHONPATH python scripts/rebuild_and_seed_db.py

Optional:
  DATABASE_URL=sqlite:////absolute/path/to/db PYTHONPATH=$PWD:$PYTHONPATH python scripts/rebuild_and_seed_db.py

"""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.company import Company
from app.models.subscription import Subscription
from app.models.user import User
from app.models.user_company_role import UserCompanyRole
from config import Config


def _backup_sqlite_db() -> Path | None:
    uri = Config.SQLALCHEMY_DATABASE_URI
    if not uri.startswith("sqlite:///"):
        return None
    db_path = Path(uri.replace("sqlite:///", "", 1))
    if not db_path.exists():
        return None

    backup = db_path.with_suffix(db_path.suffix + f".bak.{date.today().strftime('%Y%m%d')}")
    # Make unique if repeated in same day
    i = 1
    out = backup
    while out.exists():
        out = db_path.with_suffix(db_path.suffix + f".bak.{date.today().strftime('%Y%m%d')}.{i}")
        i += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, out)
    return out


def rebuild_and_seed():
    print("Rebuilding SecureCore IDS database (dev)...")
    app = create_app("development")

    with app.app_context():
        backup = _backup_sqlite_db()
        if backup:
            print(f"Backup created: {backup}")

        print("Dropping all tables...")
        db.drop_all()

        print("Creating tables...")
        db.create_all()

        # Company
        company = Company.query.filter_by(name="SecureCore Admin").first()
        if not company:
            company = Company(public_id=Company.generate_public_id(), name="SecureCore Admin")
            db.session.add(company)
            db.session.flush()

        # Admin user
        admin = User.query.filter_by(email=Config.DEFAULT_ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                company_id=company.id,
                email=Config.DEFAULT_ADMIN_EMAIL,
                name="Administrator",
                role="admin",
                is_active=True,
                email_verified=True,
            )
            admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.flush()
        else:
            # Ensure correct linkage and password
            admin.company_id = company.id
            admin.role = "admin"
            admin.is_active = True
            admin.email_verified = True
            admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
            db.session.flush()

        # PBAC mapping
        ucr = UserCompanyRole.query.filter_by(user_id=admin.id, company_id=company.id).first()
        if not ucr:
            db.session.add(UserCompanyRole(user_id=admin.id, company_id=company.id, role="admin"))
        else:
            ucr.role = "admin"

        # Subscription (active)
        sub = Subscription.query.filter_by(user_id=admin.id).first()
        if not sub:
            sub = Subscription(
                company_id=company.id,
                user_id=admin.id,
                plan_name="Small Companies",
                plan_price=49.00,
                status="active",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                next_billing_date=date.today() + timedelta(days=30),
                max_requests_per_minute=1000,
                max_requests_per_month=1_000_000,
            )
            db.session.add(sub)
        else:
            sub.company_id = company.id
            sub.status = "active"

        db.session.commit()

        print("Done.")
        print(f"Company: id={company.id} name={company.name}")
        print(f"Admin: {admin.email} / {Config.DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    rebuild_and_seed()
