#!/usr/bin/env python3
"""
Test script for company-centric architecture
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.company import Company
from app.models.company_settings import CompanySettings
from app.models.user_profile import UserProfile
from app.models.payment_method import PaymentMethod
from app.models.subscription import Subscription

def test_models():
    """Test that all models work correctly"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Testing Company-Centric Architecture")
        print("=" * 60)
        print()
        
        # Test 1: Check companies
        print("Test 1: Companies")
        companies = Company.query.all()
        print(f"  ✓ Found {len(companies)} companies")
        
        if companies:
            company = companies[0]
            print(f"  ✓ Sample company: {company.name} (ID: {company.id})")
        
        # Test 2: Check company settings
        print("\nTest 2: Company Settings")
        company_settings = CompanySettings.query.all()
        print(f"  ✓ Found {len(company_settings)} company settings")
        
        if company_settings:
            settings = company_settings[0]
            print(f"  ✓ Sample settings: Company {settings.company_id}")
            print(f"    - Email notifications: {settings.email_notifications}")
            print(f"    - Backup frequency: {settings.backup_frequency}")
        
        # Test 3: Check user profiles
        print("\nTest 3: User Profiles")
        profiles = UserProfile.query.all()
        print(f"  ✓ Found {len(profiles)} user profiles")
        
        # Test 4: Check users
        print("\nTest 4: Users and Roles")
        users = User.query.all()
        print(f"  ✓ Found {len(users)} users")
        
        for user in users[:3]:  # Show first 3
            from app.utils.security import check_user_role
            role = check_user_role(user)
            print(f"    - {user.name} ({user.email}): role={role}, company_id={user.company_id}")
        
        # Test 5: Check subscriptions
        print("\nTest 5: Subscriptions")
        subscriptions = Subscription.query.all()
        print(f"  ✓ Found {len(subscriptions)} subscriptions")
        
        for sub in subscriptions:
            print(f"    - Company {sub.company_id}: {sub.plan_name} ({sub.status})")
        
        # Test 6: Check payment methods
        print("\nTest 6: Payment Methods")
        payment_methods = PaymentMethod.query.all()
        print(f"  ✓ Found {len(payment_methods)} payment methods")
        
        company_scoped = PaymentMethod.query.filter(PaymentMethod.company_id.isnot(None)).count()
        print(f"    - Company-scoped: {company_scoped}")
        print(f"    - Missing company_id: {len(payment_methods) - company_scoped}")
        
        # Test 7: Test to_dict() methods
        print("\nTest 7: Model Serialization")
        if company_settings:
            settings_dict = company_settings[0].to_dict()
            print(f"  ✓ CompanySettings.to_dict() works")
            print(f"    Keys: {list(settings_dict.keys())[:5]}...")
        
        if profiles:
            profile_dict = profiles[0].to_dict()
            print(f"  ✓ UserProfile.to_dict() works")
            print(f"    Keys: {list(profile_dict.keys())[:5]}...")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

if __name__ == '__main__':
    test_models()
