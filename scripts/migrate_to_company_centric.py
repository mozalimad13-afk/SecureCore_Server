#!/usr/bin/env python3
"""
Database Migration Script
Migrates from user-centric to company-centric architecture
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.company import Company
from app.models.user_settings import UserSettings
from app.models.company_settings import CompanySettings
from app.models.user_profile import UserProfile
from app.models.payment_method import PaymentMethod
from app.models.subscription import Subscription
from sqlalchemy import text

def main():
    """Run database migration"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Database Migration: User-Centric → Company-Centric")
        print("=" * 60)
        print()
        
        # Step 1: Create new tables
        print("Step 1: Creating new tables...")
        try:
            db.create_all()
            print("✓ Tables created successfully")
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            return
        
        # Step 2: Migrate user settings to company settings
        print("\nStep 2: Migrating user settings to company settings...")
        migrate_user_settings_to_company()
        
        # Step 3: Create default user profiles
        print("\nStep 3: Creating default user profiles...")
        create_default_user_profiles()
        
        # Step 4: Update payment methods (if needed)
        print("\nStep 4: Checking payment methods...")
        check_payment_methods()
        
        # Step 5: Update subscriptions (if needed)
        print("\nStep 5: Checking subscriptions...")
        check_subscriptions()
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test the application")
        print("2. Verify all endpoints work correctly")
        print("3. Check role-based permissions")


def migrate_user_settings_to_company():
    """Migrate user settings to company settings"""
    try:
        # Get all user settings
        user_settings = UserSettings.query.all()
        
        if not user_settings:
            print("  No user settings to migrate")
            return
        
        # Group by company
        company_settings_map = {}
        
        for settings in user_settings:
            user = User.query.get(settings.user_id)
            if not user or not user.company_id:
                print(f"  ⚠ Skipping settings for user {settings.user_id} (no company)")
                continue
            
            company_id = user.company_id
            
            # If we haven't created settings for this company yet
            if company_id not in company_settings_map:
                # Check if company settings already exist
                existing = CompanySettings.query.filter_by(company_id=company_id).first()
                
                if existing:
                    company_settings_map[company_id] = existing
                    print(f"  ✓ Company {company_id} already has settings")
                else:
                    # Create new company settings from this user's settings
                    company_settings = CompanySettings(
                        company_id=company_id,
                        email_notifications=settings.email_notifications,
                        sms_notifications=settings.sms_notifications,
                        webhook_notifications=settings.webhook_notifications,
                        webhook_url=settings.webhook_url,
                        daily_digest=settings.daily_digest,
                        weekly_report=settings.weekly_report,
                        digest_time=settings.digest_time,
                        backup_frequency=settings.backup_frequency,
                        last_backup=settings.last_backup,
                        next_backup=settings.next_backup,
                        alert_reminder_enabled=True,
                        alert_reminder_interval=24
                    )
                    db.session.add(company_settings)
                    company_settings_map[company_id] = company_settings
                    print(f"  ✓ Created company settings for company {company_id}")
        
        db.session.commit()
        print(f"  ✓ Migrated settings for {len(company_settings_map)} companies")
        
    except Exception as e:
        print(f"  ✗ Error migrating user settings: {e}")
        db.session.rollback()


def create_default_user_profiles():
    """Create default user profiles for all users"""
    try:
        users = User.query.all()
        created = 0
        
        for user in users:
            # Check if profile already exists
            existing = UserProfile.query.filter_by(user_id=user.id).first()
            if existing:
                continue
            
            # Create default profile
            profile = UserProfile(
                user_id=user.id,
                timezone='UTC',
                language='en',
                theme='light',
                two_factor_enabled=False,
                email_on_mention=True,
                email_on_alert=True,
                push_notifications=True
            )
            db.session.add(profile)
            created += 1
        
        db.session.commit()
        print(f"  ✓ Created {created} user profiles")
        
    except Exception as e:
        print(f"  ✗ Error creating user profiles: {e}")
        db.session.rollback()


def check_payment_methods():
    """Check and report on payment methods"""
    try:
        total = PaymentMethod.query.count()
        without_company = PaymentMethod.query.filter_by(company_id=None).count()
        
        print(f"  ℹ Total payment methods: {total}")
        
        if without_company > 0:
            print(f"  ⚠ Found {without_company} payment methods without company_id")
            print("    These may need manual review")
        else:
            print("  ✓ All payment methods have company_id")
        
    except Exception as e:
        print(f"  ✗ Error checking payment methods: {e}")


def check_subscriptions():
    """Check and report on subscriptions"""
    try:
        total = Subscription.query.count()
        without_company = Subscription.query.filter_by(company_id=None).count()
        
        print(f"  ℹ Total subscriptions: {total}")
        
        if without_company > 0:
            print(f"  ⚠ Found {without_company} subscriptions without company_id")
            print("    These may need manual review")
        else:
            print("  ✓ All subscriptions have company_id")
        
    except Exception as e:
        print(f"  ✗ Error checking subscriptions: {e}")


if __name__ == '__main__':
    main()
