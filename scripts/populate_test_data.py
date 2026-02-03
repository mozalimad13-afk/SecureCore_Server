"""
Database Test Data Generator
Populates database with realistic test data for frontend integration testing
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    User, Alert, APIToken, BlockedIP, WhitelistedIP,
    Notification, Subscription, UserSettings, PaymentMethod
)


# Test data generators
ATTACK_TYPES = [
    'Port Scan', 'DDoS', 'Brute Force', 'SQL Injection',
    'XSS', 'Malware Traffic', 'Suspicious Activity', 'UNKNOWN'
]

SEVERITIES = ['Low', 'Medium', 'High', 'Critical']

TEST_IPS = [
    '192.168.1.105', '10.0.0.45', '172.16.0.88', '192.168.2.201',
    '10.0.1.33', '203.0.113.50', '198.51.100.23', '192.0.2.100',
    '10.0.2.55', '172.16.1.88', '192.168.3.101', '10.0.3.77'
]

COMPANIES = [
    'TechCorp', 'DataFlow', 'SecureNet', 'CloudGuard',
    'StartupIO', 'Enterprise Inc', 'SecurityNet', 'Protect.io',
    'CyberGuard', 'InfoSec'
]


def create_test_users(count=10):
    """Create test users"""
    print(f"\n📝 Creating {count} test users...")
    
    users = []
    for i in range(count):
        user = User(
            email=f'user{i+1}@test.com',
            name=f'Test User {i+1}',
            role='user' if i > 0 else 'admin',
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))
        )
        user.set_password('password123')
        
        if random.random() > 0.3:  # 70% have logged in recently
            user.last_login = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
        
        users.append(user)
        db.session.add(user)
    
    db.session.commit()
    print(f"✅ Created {len(users)} users")
    return users


def create_test_alerts(users, count=50):
    """Create test alerts"""
    print(f"\n📝 Creating {count} test alerts...")
    
    alerts = []
    for i in range(count):
        user = random.choice(users)
        
        alert = Alert(
            user_id=user.id,
            source_ip=random.choice(TEST_IPS),
            destination_ip=f'10.0.0.{random.randint(1, 255)}',
            attack_type=random.choice(ATTACK_TYPES),
            severity=random.choice(SEVERITIES),
            confidence=round(random.uniform(0.7, 0.99), 2),
            model_name='binary_classifier_v1',
            model_version='1.0.0',
            created_at=datetime.utcnow() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        )
        
        alerts.append(alert)
        db.session.add(alert)
    
    db.session.commit()
    print(f"✅ Created {len(alerts)} alerts")
    return alerts


def create_test_blocked_ips(users, count=15):
    """Create blocked IPs"""
    print(f"\n📝 Creating {count} blocked IPs...")
    
    blocked = []
    reasons = [
        'Multiple brute force attempts',
        'Port scanning activity',
        'DDoS source',
        'Malware distribution',
        'Suspicious activity',
        'Spam bot detected',
        'SQL injection attempts'
    ]
    
    for i in range(count):
        user = random.choice(users)
        
        ip = BlockedIP(
            user_id=user.id,
            ip_address=random.choice(TEST_IPS),
            reason=random.choice(reasons),
            block_type='automatic' if random.random() > 0.3 else 'manual',
            is_active=random.random() > 0.2,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        
        blocked.append(ip)
        db.session.add(ip)
    
    db.session.commit()
    print(f"✅ Created {len(blocked)} blocked IPs")
    return blocked


def create_test_whitelisted_ips(users, count=12):
    """Create whitelisted IPs"""
    print(f"\n📝 Creating {count} whitelisted IPs...")
    
    whitelisted = []
    descriptions = [
        'Main office gateway',
        'Internal network subnet',
        'Backup server',
        'Development server',
        'Branch office router',
        'Monitoring server',
        'Database server',
        'VPN gateway',
        'DNS server',
        'Mail server'
    ]
    
    for i in range(count):
        user = random.choice(users)
        
        ip = WhitelistedIP(
            user_id=user.id,
            ip_address=f'10.0.{random.randint(0, 5)}.{random.randint(1, 255)}',
            description=random.choice(descriptions),
            is_active=True,
            created_by=user.id,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 60))
        )
        
        whitelisted.append(ip)
        db.session.add(ip)
    
    db.session.commit()
    print(f"✅ Created {len(whitelisted)} whitelisted IPs")
    return whitelisted


def create_test_notifications(users, count=25):
    """Create notifications"""
    print(f"\n📝 Creating {count} notifications...")
    
    notifications = []
    templates = [
        ('Critical Alert', 'Potential intrusion detected from {}', 'alert'),
        ('Weekly Report Ready', 'Your weekly security report is now available', 'info'),
        ('New Login Detected', 'Login from {} in {}', 'warning'),
        ('System Update', 'Scheduled maintenance tonight at 2 AM', 'info'),
        ('Threat Blocked', 'Blocked {} malicious requests', 'alert'),
    ]
    
    cities = ['San Francisco', 'New York', 'London', 'Tokyo', 'Berlin']
    
    for i in range(count):
        user = random.choice(users)
        title, msg_template, notif_type = random.choice(templates)
        
        # Format message based on type
        if '{}' in msg_template:
            if 'from' in msg_template:
                message = msg_template.format(random.choice(TEST_IPS), random.choice(cities))
            elif 'requests' in msg_template:
                message = msg_template.format(random.randint(10, 100))
            else:
                message = msg_template.format(random.choice(TEST_IPS))
        else:
            message = msg_template
        
        notif = Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=notif_type,
            priority='high' if notif_type == 'alert' else 'normal',
            is_read=random.random() > 0.4,
            created_at=datetime.utcnow() - timedelta(
                hours=random.randint(0, 72),
                minutes=random.randint(0, 59)
            )
        )
        
        if notif.is_read:
            notif.read_at = notif.created_at + timedelta(minutes=random.randint(5, 120))
        
        notifications.append(notif)
        db.session.add(notif)
    
    db.session.commit()
    print(f"✅ Created {len(notifications)} notifications")
    return notifications


def create_test_subscriptions(users):
    """Create subscriptions for users"""
    print(f"\n📝 Creating subscriptions...")
    
    plans = [
        ('Free Trial', 0.00, 'trial'),
        ('Small Companies', 44.00, 'active'),
        ('Professional', 99.00, 'active'),
        ('Enterprise', 299.00, 'active')
    ]
    
    subscriptions = []
    for user in users:
        plan_name, price, status = random.choice(plans)
        
        # Randomly set some as cancelled or expired
        if random.random() > 0.85:
            status = 'cancelled'
        elif random.random() > 0.95:
            status = 'expired'
        
        sub = Subscription(
            user_id=user.id,
            plan_name=plan_name,
            plan_price=price,
            status=status,
            start_date=user.created_at.date() if user.created_at else date.today(),
            next_billing_date=(datetime.utcnow() + timedelta(days=30)).date() if price > 0 and status == 'active' else None,
            max_requests_per_minute=100 if price == 0 else 1000,
            max_requests_per_month=10000 if price == 0 else 1000000
        )
        
        subscriptions.append(sub)
        db.session.add(sub)
    
    db.session.commit()
    print(f"✅ Created {len(subscriptions)} subscriptions")
    return subscriptions


def create_test_settings(users):
    """Create user settings"""
    print(f"\n📝 Creating user settings...")
    
    settings_list = []
    for user in users:
        settings = UserSettings(
            user_id=user.id,
            email_notifications=random.random() > 0.3,
            sms_notifications=random.random() > 0.7,
            webhook_notifications=random.random() > 0.5,
            webhook_url='https://api.example.com/webhook' if random.random() > 0.5 else None,
            daily_digest=random.random() > 0.5,
            weekly_report=random.random() > 0.3,
            digest_time=random.choice(['06:00', '09:00', '12:00', '18:00']),
            backup_frequency=random.choice(['hourly', 'daily', 'weekly', 'monthly']),
            last_backup=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            next_backup=datetime.utcnow() + timedelta(hours=random.randint(1, 24))
        )
        
        settings_list.append(settings)
        db.session.add(settings)
    
    db.session.commit()
    print(f"✅ Created {len(settings_list)} user settings")
    return settings_list


def create_test_payment_methods(users):
    """Create payment methods for users"""
    print(f"\n📝 Creating payment methods...")
    
    card_brands = ['Visa', 'Mastercard', 'Amex']
    cities = ['San Francisco', 'New York', 'Los Angeles', 'Chicago', 'Boston', 'Seattle']
    countries = ['USA', 'Canada', 'UK']
    
    payment_methods = []
    for user in users:
        # 60% of users have payment methods
        if random.random() > 0.4:
            # Some users have multiple cards (20%)
            num_cards = 2 if random.random() > 0.8 else 1
            
            for card_num in range(num_cards):
                pm = PaymentMethod(
                    user_id=user.id,
                    card_last4=str(random.randint(1000, 9999)),
                    card_brand=random.choice(card_brands),
                    card_holder_name=user.name,
                    expiry_month=str(random.randint(1, 12)).zfill(2),
                    expiry_year=str(random.randint(25, 30)),
                    billing_address=f"{random.randint(100, 9999)} Main Street",
                    city=random.choice(cities),
                    zip_code=str(random.randint(10000, 99999)),
                    country=random.choice(countries),
                    is_default=(card_num == 0),  # First card is default
                    is_active=True,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 90))
                )
                
                payment_methods.append(pm)
                db.session.add(pm)
    
    db.session.commit()
    print(f"✅ Created {len(payment_methods)} payment methods")
    return payment_methods


def main():
    """Main function to populate database"""
    print("=" * 60)
    print("Database Test Data Generator")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        print("\n🗑️  Clearing existing data...")
        
        # Clear existing test data (keep admin)
        Notification.query.delete()
        Alert.query.delete()
        BlockedIP.query.delete()
        WhitelistedIP.query.delete()
        UserSettings.query.delete()
        Subscription.query.delete()
        PaymentMethod.query.delete()
        APIToken.query.delete()
        User.query.filter(User.email != 'admin@securecore.com').delete()
        
        db.session.commit()
        print("✅ Cleared existing test data")
        
        # Create new test data with LOTS of records for pagination testing
        users = create_test_users(50)  # 50 users for admin page pagination
        alerts = create_test_alerts(users, 300)  # 300 alerts for alerts page pagination
        blocked = create_test_blocked_ips(users, 100)  # 100 blocked IPs for blocklist pagination
        whitelisted = create_test_whitelisted_ips(users, 80)  # 80 whitelisted IPs
        notifications = create_test_notifications(users, 150)  # 150 notifications
        subscriptions = create_test_subscriptions(users)
        settings = create_test_settings(users)
        payment_methods = create_test_payment_methods(users)  # Payment methods for 60% of users
        
        print("\n" + "=" * 60)
        print("✅ DATABASE POPULATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Users: {len(users)}")
        print(f"   Alerts: {len(alerts)}")
        print(f"   Blocked IPs: {len(blocked)}")
        print(f"   Whitelisted IPs: {len(whitelisted)}")
        print(f"   Notifications: {len(notifications)}")
        print(f"   Subscriptions: {len(subscriptions)}")
        print(f"   Settings: {len(settings)}")
        print(f"   Payment Methods: {len(payment_methods)}")
        print(f"\n🚀 Backend ready for frontend integration!")
        print("\n💡 Test credentials:")
        print("   Admin: admin@securecore.com / admin123")
        print("   User1: user1@test.com / password123")
        print("   User2: user2@test.com / password123")


if __name__ == '__main__':
    main()
