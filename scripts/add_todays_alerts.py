"""
Add alerts for TODAY to show on dashboard
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.alert import Alert
from app.models.user import User

def add_todays_alerts():
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email='user2@test.com').first()
        if not user:
            print("Error: user2@test.com not found")
            return
        
        print(f"Adding TODAY's alerts for user: {user.email}")
        
        attack_types = ['SQL Injection', 'XSS Attack', 'DDoS Attack', 'Port Scan', 'Brute Force']
        severities = ['critical', 'high', 'medium', 'low']
        protocols = ['TCP', 'UDP', 'HTTP', 'HTTPS']
        
        # Add 15 alerts for TODAY
        now = datetime.utcnow()
        today_alerts = []
        
        for i in range(15):
            # Random time today (within last 12 hours)
            hours_ago = random.randint(0, 12)
            minutes_ago = random.randint(0, 59)
            alert_time = now - timedelta(hours=hours_ago, minutes=minutes_ago)
            
            source_ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            
            alert = Alert(
                user_id=user.id,
                source_ip=source_ip,
                source_port=random.randint(1024, 65535),
                destination_ip=f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
                destination_port=random.choice([80, 443, 22, 3306]),
                protocol=random.choice(protocols),
                attack_type=random.choice(attack_types),
                severity=random.choice(severities),
                confidence=random.uniform(0.6, 0.95),
                created_at=alert_time
            )
            today_alerts.append(alert)
        
        db.session.bulk_save_objects(today_alerts)
        db.session.commit()
        
        print(f"✅ Added {len(today_alerts)} alerts for TODAY")
        print(f"📅 Date: {now.strftime('%Y-%m-%d')}")
        print(f"⏰ Time range: Last 12 hours")

if __name__ == '__main__':
    add_todays_alerts()
