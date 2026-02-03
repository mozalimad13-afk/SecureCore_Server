"""Migration: introduce `roles` + `users_roles` and backfill from `user_company_roles`.

This keeps `users.role` as a global app-level role (should normally be 'user').
Company permissions move to users_roles.

Usage:
  PYTHONPATH=$PWD:$PYTHONPATH python scripts/migrate_user_roles_to_roles_table.py

Safe to run multiple times.
"""

from datetime import datetime

from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.user_company_role import UserCompanyRole


DEFAULT_ROLE_NAMES = ["admin", "fully", "limited"]


def ensure_tables_exist() -> None:
    Role.__table__.create(db.engine, checkfirst=True)
    UserRole.__table__.create(db.engine, checkfirst=True)


def ensure_roles_seeded() -> dict[str, Role]:
    existing = {r.name: r for r in Role.query.all()}
    for name in DEFAULT_ROLE_NAMES:
        if name not in existing:
            role = Role(name=name)
            db.session.add(role)
            db.session.flush()
            existing[name] = role
    return existing


def backfill_users_roles(roles_by_name: dict[str, Role]) -> int:
    inserted = 0
    for mapping in UserCompanyRole.query.all():
        role_name = (mapping.role or "").strip().lower()
        if role_name not in roles_by_name:
            # Ignore unknown roles instead of failing the migration.
            continue

        exists = UserRole.query.filter_by(
            user_id=mapping.user_id,
            company_id=mapping.company_id,
            role_id=roles_by_name[role_name].id,
        ).first()
        if exists is not None:
            continue

        db.session.add(
            UserRole(
                user_id=mapping.user_id,
                company_id=mapping.company_id,
                role_id=roles_by_name[role_name].id,
            )
        )
        inserted += 1

    return inserted


def report_schema() -> None:
    insp = inspect(db.engine)
    tables = set(insp.get_table_names())
    print("[schema] roles:", "roles" in tables)
    print("[schema] users_roles:", "users_roles" in tables)
    print("[schema] user_company_roles:", "user_company_roles" in tables)


def main() -> None:
    app = create_app()
    with app.app_context():
        print("[start]", datetime.utcnow().isoformat())
        ensure_tables_exist()
        roles_by_name = ensure_roles_seeded()
        inserted = backfill_users_roles(roles_by_name)
        db.session.commit()
        report_schema()
        print(f"[done] backfilled users_roles rows inserted: {inserted}")


if __name__ == "__main__":
    main()
