#!/usr/bin/env python3
"""Create user_company_roles table and backfill admin roles for existing users.

Idempotent: skips if table exists; only inserts missing (user, company) pairs.
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.user_company_role import UserCompanyRole


def main():
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        table_names = inspector.get_table_names()

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                if 'user_company_roles' not in table_names:
                    print('🔨 Creating table user_company_roles')
                    conn.execute(text(
                        """
                        CREATE TABLE user_company_roles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            company_id INTEGER NOT NULL,
                            role VARCHAR(32) NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            CONSTRAINT uq_user_company_role UNIQUE (user_id, company_id),
                            CONSTRAINT fk_ucr_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                            CONSTRAINT fk_ucr_company FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
                        );
                        """
                    ))
                else:
                    print('ℹ️  user_company_roles table already exists')

                trans.commit()
            except Exception as exc:
                trans.rollback()
                print(f'❌ Failed creating table: {exc}')
                raise

        # Backfill admin role for existing users with company_id
        created = 0
        for user in User.query.filter(User.company_id.isnot(None)).all():
            exists = UserCompanyRole.query.filter_by(user_id=user.id, company_id=user.company_id).first()
            if exists:
                continue
            role = user.role or 'admin'
            db.session.add(UserCompanyRole(user_id=user.id, company_id=user.company_id, role=role))
            created += 1
        if created:
            db.session.commit()
        print(f'✅ Backfill complete; added {created} role rows')


if __name__ == '__main__':
    main()
