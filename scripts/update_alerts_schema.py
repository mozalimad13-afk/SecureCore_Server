#!/usr/bin/env python3
"""
Update alerts database schema and insert test data
"""
from app import create_app
from app.extensions import db
from app.models.alert import Alert
from app.models.user import User
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    print("📊 Updating database schema...")
    
    # Update alerts table schema
    with db.engine.connect() as conn:
        try:
            # Add new columns
            conn.execute(db.text('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source_port INTEGER'))
            conn.execute(db.text('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS destination_port INTEGER'))
            conn.execute(db.text('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS protocol VARCHAR(10)'))
            print("✅ Added: source_port, destination_port, protocol")
            
            # Remove old columns (SQLite doesn't support DROP COLUMN easily, so we'll skip for safety)
            # Note: The columns still exist in DB but won't be used by the model
            print("ℹ️  Old columns kept in DB (model ignores them)")
            
            conn.commit()
        except Exception as e:
            print(f"⚠️  Schema update note: {e}")
    
    print("\n🗑️  Deleting all old alerts...")
    Alert.query.delete()
    db.session.commit()
    print("✅ Old alerts deleted")
    
    print("\n📝 Inserting new test alerts for user2@test.com...")
    user = User.query.filter_by(email='user2@test.com').first()
    
    if not user:
        print("❌ user2@test.com not found!")
        exit(1)
    
    print(f"   Found user: {user.email} (ID: {user.id})")
    
    templates = [
        {'source_ip': '192.168.1.105', 'source_port': 45678, 'destination_ip': '10.0.0.1', 'destination_port': 443, 'protocol': 'TCP', 'severity': 'High', 'attack_type': 'Port Scan'},
        {'source_ip': '10.0.0.45', 'source_port': 52341, 'destination_ip': '192.168.1.1', 'destination_port': 22, 'protocol': 'TCP', 'severity': 'Critical', 'attack_type': 'SSH Brute Force'},
        {'source_ip': '172.16.0.88', 'source_port': 33456, 'destination_ip': '10.0.0.5', 'destination_port': 80, 'protocol': 'TCP', 'severity': 'Medium', 'attack_type': 'SQL Injection'},
        {'source_ip': '192.168.2.201', 'source_port': 48923, 'destination_ip': '172.16.0.1', 'destination_port': 3389, 'protocol': 'TCP', 'severity': 'High', 'attack_type': 'RDP Attack'},
        {'source_ip': '10.0.1.33', 'source_port': 51234, 'destination_ip': '192.168.1.50', 'destination_port': 8080, 'protocol': 'TCP', 'severity': 'Low', 'attack_type': 'Suspicious Traffic'},
        {'source_ip': '172.16.1.45', 'source_port': 39876, 'destination_ip': '192.168.2.1', 'destination_port': 53, 'protocol': 'UDP', 'severity': 'Medium', 'attack_type': 'DNS Query'},
        {'source_ip': '10.0.2.67', 'source_port': 47123, 'destination_ip': '172.16.0.50', 'destination_port': 445, 'protocol': 'TCP', 'severity': 'Critical', 'attack_type': 'SMB Exploit'},
        {'source_ip': '192.168.5.12', 'source_port': 62345, 'destination_ip': '10.0.0.20', 'destination_port': 3306, 'protocol': 'TCP', 'severity': 'High', 'attack_type': 'MySQL Attack'},
    ]
    
    now = datetime.utcnow()
    for i in range(30):
        t = templates[i % len(templates)]
        hours = random.randint(0, 23)
        mins = random.randint(0, 59)
        created = now - timedelta(hours=hours, minutes=mins)
        
        alert = Alert(
            user_id=user.id,
            source_ip=t['source_ip'],
            source_port=t['source_port'],
            destination_ip=t['destination_ip'],
            destination_port=t['destination_port'],
            protocol=t['protocol'],
            attack_type=t['attack_type'],
            severity=t['severity'],
            confidence=0.85 + random.random() * 0.15
        )
        alert.created_at = created
        db.session.add(alert)
    
    db.session.commit()
    
    count = Alert.query.filter_by(user_id=user.id).count()
    print(f"✅ Inserted {count} alerts with ports and protocols!")
    print("\n🎉 Database update complete!")
    print(f"   • user2@test.com has {count} test alerts")
    print("   • All alerts include: source_port, destination_port, protocol")
    print("   • Severities: Low, Medium, High, Critical")
    print("   • Time range: Last 24 hours")
