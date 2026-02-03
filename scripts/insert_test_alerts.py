"""
Insert test alerts with random dates for user2@test.com
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.alert import Alert
from app.models.user import User

def insert_test_alerts():
    app = create_app()
    
    with app.app_context():
        # Get user2
        user = User.query.filter_by(email='user2@test.com').first()
        if not user:
            print("Error: user2@test.com not found")
            return
        
        print(f"Adding alerts for user: {user.email}")
        
        # Delete existing alerts for user2
        Alert.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        print("Deleted existing alerts")
        
        # Alert configurations
        attack_types = [
            'SQL Injection', 'XSS Attack', 'DDoS Attack', 'Port Scan',
            'Brute Force', 'Malware Detection', 'Phishing Attempt',
            'Command Injection', 'Directory Traversal', 'CSRF Attack'
        ]
        
        severities = ['critical', 'high', 'medium', 'low']
        severity_weights = [0.1, 0.2, 0.4, 0.3]  # Distribution
        
        protocols = ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS']
        
        # Generate 100 alerts over the last 60 days
        alerts_to_add = []
        now = datetime.utcnow()
        
        for i in range(100):
            # Random date within last 60 days
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            alert_time = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Random IP addresses
            source_ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            dest_ip = f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}"
            
            # Random ports
            source_port = random.randint(1024, 65535)
            dest_port = random.choice([80, 443, 22, 21, 3306, 5432, 8080, 3389])
            
            # Select severity
            severity = random.choices(severities, weights=severity_weights)[0]
            
            # Confidence based on severity
            if severity == 'critical':
                confidence = random.uniform(0.85, 0.99)
            elif severity == 'high':
                confidence = random.uniform(0.70, 0.90)
            elif severity == 'medium':
                confidence = random.uniform(0.50, 0.75)
            else:
                confidence = random.uniform(0.30, 0.60)
            
            alert = Alert(
                user_id=user.id,
                source_ip=source_ip,
                source_port=source_port,
                destination_ip=dest_ip,
                destination_port=dest_port,
                protocol=random.choice(protocols),
                attack_type=random.choice(attack_types),
                severity=severity,
                confidence=confidence,
                created_at=alert_time
            )
            
            alerts_to_add.append(alert)
        
        # Bulk insert
        db.session.bulk_save_objects(alerts_to_add)
        db.session.commit()
        
        print(f"✅ Successfully added {len(alerts_to_add)} alerts")
        
        # Show distribution
        print("\n📊 Distribution by severity:")
        for severity in severities:
            count = sum(1 for a in alerts_to_add if a.severity == severity)
            print(f"  {severity.capitalize()}: {count}")
        
        print("\n📅 Date range:")
        dates = sorted([a.created_at for a in alerts_to_add])
        print(f"  Oldest: {dates[0].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Newest: {dates[-1].strftime('%Y-%m-%d %H:%M')}")
        
        print("\n🔢 Alerts by time period:")
        last_7_days = sum(1 for a in alerts_to_add if (now - a.created_at).days <= 7)
        last_30_days = sum(1 for a in alerts_to_add if (now - a.created_at).days <= 30)
        last_90_days = sum(1 for a in alerts_to_add if (now - a.created_at).days <= 90)
        
        print(f"  Last 7 days: {last_7_days}")
        print(f"  Last 30 days: {last_30_days}")
        print(f"  Last 90 days (quarter): {last_90_days}")

if __name__ == '__main__':
    insert_test_alerts()
