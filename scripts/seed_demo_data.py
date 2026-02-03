"""Seed demo data (2 admins + 2 users + lots of records across dates).

This script is designed for local/dev testing only.

What it does:
- Runs sqlite migration to ensure tenant columns exist.
- Ensures specific credentials exist:
  - admin@securecore.com / admin123
  - admin2@securecore.com / admin123
  - user1@test.com / password123
  - user2@test.com / password123
- Creates one tenant per user (company==account) if missing.
- Creates realistic junk data for today and prior days:
  alerts, blocked_ips, whitelisted_ips, notifications, subscription, settings.

Run:
  cd server
  source finalProjectCS4/bin/activate
  python scripts/seed_demo_data.py

Optional: override DB path
  SECURECORE_DB_PATH=/abs/path/to/securecore.db python scripts/seed_demo_data.py
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import sys

# Allow running as `python scripts/seed_demo_data.py` from `server/`
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models.alert import Alert
from app.models.blocklist import BlockedIP
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.whitelist import WhitelistedIP
from app.models.fcm_device import FCMDevice
from app.utils.encryption import encrypt_fcm_token


ATTACK_TYPES = [
    'Port Scan',
    'DDoS',
    'Brute Force',
    'SQL Injection',
    'XSS',
    'Malware Traffic',
    'Suspicious Activity',
]

SEVERITIES = ['low', 'medium', 'high', 'critical']
PROTOCOLS = ['TCP', 'UDP', 'HTTP', 'HTTPS']


@dataclass(frozen=True)
class SeedUser:
    email: str
    password: str
    name: str
    role: str  # 'admin' | 'user'


SEED_USERS = [
    SeedUser('admin@securecore.com', 'admin123', 'Administrator', 'admin'),
    SeedUser('admin2@securecore.com', 'admin123', 'Administrator Two', 'admin'),
    SeedUser('user1@test.com', 'password123', 'Test User 1', 'user'),
    SeedUser('user2@test.com', 'password123', 'Test User 2', 'user'),
]


def _ensure_user_with_tenant(su: SeedUser) -> User:
    user = User.query.filter_by(email=su.email).first()
    if user is None:
        tenant = Tenant(public_id=Tenant.generate_public_id(), name=su.name)
        db.session.add(tenant)
        db.session.flush()
        user = User(
            tenant_id=tenant.id,
            email=su.email,
            name=su.name,
            role=su.role,
            is_active=True,
            email_verified=True,
        )
        user.set_password(su.password)
        user.created_at = datetime.utcnow() - timedelta(days=30)
        user.last_login = datetime.utcnow() - timedelta(hours=1)
        db.session.add(user)
        db.session.flush()
        return user

    # Ensure tenant exists
    if not user.tenant_id:
        tenant = Tenant(public_id=Tenant.generate_public_id(), name=su.name)
        db.session.add(tenant)
        db.session.flush()
        user.tenant_id = tenant.id

    # Ensure role + active
    user.role = su.role
    user.is_active = True
    user.email_verified = True

    # Reset password to known value (dev/demo only)
    user.set_password(su.password)

    return user


def _ensure_settings(user: User) -> None:
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    if settings is None:
        settings = UserSettings(user_id=user.id, tenant_id=user.tenant_id)
        db.session.add(settings)

    settings.email_notifications = True
    settings.weekly_report = True
    settings.daily_digest = True
    settings.backup_frequency = 'daily'
    settings.last_backup = datetime.utcnow() - timedelta(hours=4)
    settings.next_backup = datetime.utcnow() + timedelta(hours=20)


def _ensure_subscription(user: User) -> None:
    sub = Subscription.query.filter_by(user_id=user.id).first()
    if sub is None:
        sub = Subscription(user_id=user.id, tenant_id=user.tenant_id)
        db.session.add(sub)

    # Basic active plan
    sub.plan_name = 'Small Companies' if user.role == 'user' else 'Enterprise'
    sub.plan_price = 44.00 if user.role == 'user' else 299.00
    sub.status = 'active'
    sub.start_date = (datetime.utcnow() - timedelta(days=10)).date()
    sub.next_billing_date = (datetime.utcnow() + timedelta(days=20)).date()
    sub.max_requests_per_minute = 1000
    sub.max_requests_per_month = 1000000


def _rand_ip() -> str:
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def _seed_alerts(user: User, days: int = 14, per_day: int = 12) -> None:
    now = datetime.utcnow()
    for day_offset in range(days):
        day = now - timedelta(days=day_offset)
        for _ in range(per_day):
            created_at = day.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=0,
            )
            alert = Alert(
                tenant_id=user.tenant_id,
                user_id=user.id,
                source_ip=_rand_ip(),
                source_port=random.randint(1024, 65535),
                destination_ip=f"192.168.{random.randint(0, 10)}.{random.randint(1, 254)}",
                destination_port=random.choice([80, 443, 22, 3306]),
                protocol=random.choice(PROTOCOLS),
                attack_type=random.choice(ATTACK_TYPES),
                severity=random.choice(SEVERITIES),
                confidence=round(random.uniform(0.60, 0.99), 2),
                created_at=created_at,
            )
            db.session.add(alert)


def _seed_blocklist(user: User, count: int = 40) -> None:
    reasons = [
        'Multiple brute force attempts',
        'Port scanning activity',
        'DDoS source',
        'Malware distribution',
        'Suspicious activity',
    ]
    for _ in range(count):
        ip = BlockedIP(
            tenant_id=user.tenant_id,
            user_id=user.id,
            ip_address=_rand_ip(),
            reason=random.choice(reasons),
            block_type=random.choice(['manual', 'automatic']),
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
        )
        db.session.add(ip)


def _seed_whitelist(user: User, count: int = 20) -> None:
    descriptions = [
        'Office gateway',
        'VPN subnet',
        'Monitoring server',
        'Database server',
    ]
    for _ in range(count):
        ip = WhitelistedIP(
            tenant_id=user.tenant_id,
            user_id=user.id,
            ip_address=f"10.0.{random.randint(0, 10)}.{random.randint(1, 254)}",
            description=random.choice(descriptions),
            is_active=True,
            created_by=user.id,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 60)),
        )
        db.session.add(ip)


def _seed_notifications(user: User, count: int = 30) -> None:
    templates = [
        ('Critical Alert', 'Potential intrusion detected from {}', 'alert'),
        ('Weekly Report Ready', 'Your weekly security report is now available', 'info'),
        ('New Login Detected', 'Login from {}', 'warning'),
        ('Threat Blocked', 'Blocked {} malicious requests', 'alert'),
    ]

    for _ in range(count):
        title, msg_template, notif_type = random.choice(templates)
        message = msg_template.format(_rand_ip()) if '{}' in msg_template else msg_template

        created_at = datetime.utcnow() - timedelta(hours=random.randint(0, 96))
        notif = Notification(
            tenant_id=user.tenant_id,
            user_id=user.id,
            title=title,
            message=message,
            type=notif_type,
            priority='high' if notif_type == 'alert' else 'normal',
            is_read=random.random() > 0.4,
            created_at=created_at,
        )
        if notif.is_read:
            notif.read_at = created_at + timedelta(minutes=random.randint(5, 120))
        db.session.add(notif)


def _seed_devices(user: User, count: int = 2) -> None:
    """Seed per-device identifiers for a user (no FCM token required)."""
    for i in range(count):
        device_id = f"device-{user.id}-{i}-demo"
        device_id_hash = __import__('hashlib').sha256(device_id.encode('utf-8')).hexdigest()

        existing = FCMDevice.query.filter_by(
            tenant_id=user.tenant_id,
            user_id=user.id,
            device_id_hash=device_id_hash,
        ).first()

        if existing is None:
            existing = FCMDevice(
                tenant_id=user.tenant_id,
                user_id=user.id,
                device_id_hash=device_id_hash,
                device_id_encrypted=encrypt_fcm_token(device_id),
                device_type='android' if i % 2 == 0 else 'ios',
                device_name=f"{user.name} Phone {i+1}",
                device_platform='mobile',
                app_version='1.0.0',
                is_active=True,
                last_seen_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
            )
            db.session.add(existing)


def main() -> int:
    app = create_app('development')
    with app.app_context():
        # Ensure schema current (migrations are handled externally by scripts/migrate_add_tenants.py).
        # Here we only ensure tables exist if the DB was empty.
        db.create_all()

        users: list[User] = []
        for su in SEED_USERS:
            users.append(_ensure_user_with_tenant(su))

        db.session.commit()

        # Clear tenant-owned data for seeded users to keep reruns deterministic
        seeded_user_ids = [u.id for u in users]
        Notification.query.filter(Notification.user_id.in_(seeded_user_ids)).delete(synchronize_session=False)
        Alert.query.filter(Alert.user_id.in_(seeded_user_ids)).delete(synchronize_session=False)
        BlockedIP.query.filter(BlockedIP.user_id.in_(seeded_user_ids)).delete(synchronize_session=False)
        WhitelistedIP.query.filter(WhitelistedIP.user_id.in_(seeded_user_ids)).delete(synchronize_session=False)
        FCMDevice.query.filter(FCMDevice.user_id.in_(seeded_user_ids)).delete(synchronize_session=False)

        db.session.commit()

        for u in users:
            _ensure_settings(u)
            _ensure_subscription(u)
            _seed_alerts(u, days=14, per_day=(18 if u.role == 'user' else 10))
            _seed_blocklist(u, count=30 if u.role == 'user' else 10)
            _seed_whitelist(u, count=20 if u.role == 'user' else 10)
            _seed_notifications(u, count=35 if u.role == 'user' else 10)
            _seed_devices(u, count=(3 if u.role == 'user' else 1))

        db.session.commit()

        print('✅ Seeded demo data successfully')
        print('\nCredentials:')
        for su in SEED_USERS:
            print(f"- {su.email}:{su.password} ({su.role})")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
