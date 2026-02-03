"""
Create Admin User Script
Creates the default admin user for system administration
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.company import Company
from app.models.user_company_role import UserCompanyRole
from config import Config


def create_admin_user():
    """Create the default admin user"""
    print("Creating Admin User...")
    
    app = create_app('development')
    
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email=Config.DEFAULT_ADMIN_EMAIL).first()
        
        if admin:
            print(f"Admin user already exists: {Config.DEFAULT_ADMIN_EMAIL}")
            return
        
        # Create company (1 company account == 1 customer boundary)
        company = Company(
            public_id=Company.generate_public_id(),
            name='SecureCore Admin'
        )
        db.session.add(company)
        db.session.flush()

        # Create admin user
        admin = User(
            company_id=company.id,
            email=Config.DEFAULT_ADMIN_EMAIL,
            name='Administrator',
            role='admin',
            is_active=True,
            email_verified=True
        )
        admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
        
        db.session.add(admin)
        db.session.flush()

        # Ensure PBAC role mapping exists
        db.session.add(UserCompanyRole(user_id=admin.id, company_id=company.id, role='admin'))
        db.session.commit()
        
        print(f"✅ Admin user created successfully!")
        print(f"Email: {Config.DEFAULT_ADMIN_EMAIL}")
        print(f"Password: {Config.DEFAULT_ADMIN_PASSWORD}")
        print(f"\n⚠️  IMPORTANT: Change the admin password immediately!")


def ensure_admin_has_company():
    app = create_app('development')
    with app.app_context():
        admin = User.query.filter_by(email=Config.DEFAULT_ADMIN_EMAIL).first()
        if not admin:
            return
        if admin.company_id:
            return

        company = Company(
            public_id=Company.generate_public_id(),
            name='SecureCore Admin'
        )
        db.session.add(company)
        db.session.flush()
        admin.company_id = company.id
        db.session.flush()

        exists = UserCompanyRole.query.filter_by(user_id=admin.id, company_id=company.id).first()
        if not exists:
            db.session.add(UserCompanyRole(user_id=admin.id, company_id=company.id, role='admin'))
        db.session.commit()


if __name__ == '__main__':
    create_admin_user()
    ensure_admin_has_company()
