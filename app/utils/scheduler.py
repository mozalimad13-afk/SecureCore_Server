"""
Background Scheduler
Handles periodic tasks like system health checks and automated backups
"""
import threading
import time
import logging
from datetime import datetime, timedelta
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification
from app.utils.health import get_system_health
from app.models.company_settings import CompanySettings
from app.models.alert import Alert
from app.models.blocklist import BlockedIP
from app.models.whitelist import WhitelistedIP
from app.utils.security import get_user_company_role
import json
import os
import sqlite3

logger = logging.getLogger(__name__)

def check_system_health_task(app):
    """Periodic task to check system health and notify admins"""
    with app.app_context():
        logger.info("Running periodic system health check notification task")
        try:
            health = get_system_health()
            status = health.get('overall_status', 'unknown')
            
            # Form message based on status
            if status == 'healthy':
                logger.info("System is healthy, skipping notification")
                return
            
            # Check for existing recent notification to avoid spam
                # Do not globally dedupe across tenants; dedupe per-admin below.

            title = f"System Health: {status.capitalize()}"
            message = f"System health is currently {status}. Please check the system health dashboard."
            msg_type = "warning" if status == "degraded" else "alert"
                
            # Notify ONLY service provider admins (users.role == 'admin')
            # NOT company users
            admins = User.query.filter(User.role == 'admin').all()
            for admin in admins:
                    existing_notification = Notification.query.filter_by(
                        company_id=admin.company_id,
                        user_id=admin.id,
                        related_type='system_health',
                        is_read=False
                    ).first()
                    if not existing_notification:
                        notification = Notification(
                            company_id=admin.company_id,
                            user_id=admin.id,
                            title=title,
                            message=message,
                            type=msg_type,
                            related_type='system_health',
                            link='/admin/system',
                            created_at=datetime.utcnow()
                        )
                        db.session.add(notification)
            db.session.commit()
            logger.info("System health notifications sent to service provider admins")
        except Exception as e:
            logger.error(f"Health check task error: {str(e)}")
            db.session.rollback()

def run_backups_task(app):
    """Periodic task to run automated backups for companies"""
    with app.app_context():
        logger.info("Running automated company backups task")
        try:
            now = datetime.utcnow()
            settings_to_backup = CompanySettings.query.filter(CompanySettings.next_backup <= now).all()
            
            for settings in settings_to_backup:
                company_id = settings.company_id
                logger.info(f"Running automated backup for company {company_id}")
                
                # Collect company data
                from app.models.company import Company
                company = Company.query.get(company_id)
                company_users = User.query.filter_by(company_id=company_id).all()
                alerts = Alert.query.filter_by(company_id=company_id).all()
                blocks = BlockedIP.query.filter_by(company_id=company_id).all()
                whitelists = WhitelistedIP.query.filter_by(company_id=company_id).all()
                
                backup_data = {
                    'company': {
                        'id': company_id,
                        'name': company.name if company else 'Unknown'
                    },
                    'users': [{'name': u.name, 'email': u.email, 'role': u.role} for u in company_users],
                    'settings': settings.to_dict(),
                    'alerts': [a.to_dict() for a in alerts],
                    'blocked_ips': [b.to_dict() for b in blocks],
                    'whitelisted_ips': [w.to_dict() for w in whitelists]
                }
                
                # Save backup to consolidated SQLite file
                backup_dir = app.config['BACKUP_DIR']
                backup_file = os.path.join(backup_dir, "all_backups.db")
                
                # Create/Update SQLite file with indexed table
                conn = sqlite3.connect(backup_file)
                c = conn.cursor()
                c.execute('CREATE TABLE IF NOT EXISTS backup_data (company_id INTEGER PRIMARY KEY, payload TEXT, created_at TEXT)')
                
                # Replace existing backup for this company in the consolidated file
                c.execute(
                    'INSERT OR REPLACE INTO backup_data (company_id, payload, created_at) VALUES (?, ?, ?)',
                    (company_id, json.dumps(backup_data), now.isoformat()),
                )
                conn.commit()
                conn.close()
                
                # Update timestamps
                settings.last_backup = now
                freq = settings.backup_frequency
                if freq == 'hourly': settings.next_backup = now + timedelta(hours=1)
                elif freq == 'daily': settings.next_backup = now + timedelta(days=1)
                elif freq == 'weekly': settings.next_backup = now + timedelta(weeks=1)
                elif freq == 'monthly': settings.next_backup = now + timedelta(days=30)
                else: settings.next_backup = None
                
            db.session.commit()
            if settings_to_backup:
                logger.info(f"Automated backups completed for {len(settings_to_backup)} companies")
        except Exception as e:
            logger.error(f"Backup task error: {str(e)}")
            db.session.rollback()

# Global flag to track if scheduler is running
scheduler_started = False

def run_scheduler(app, interval_seconds=18000): # 18000s = 5 hours
    """Run the scheduler in a background thread"""
    global scheduler_started
    if scheduler_started:
        return
        
    scheduler_started = True

    def scheduler_loop():
        # Wait a bit for the app to fully start
        time.sleep(30)
        while True:
            try:
                check_system_health_task(app)
                run_backups_task(app)
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            time.sleep(interval_seconds)
            
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    logger.info(f"Background scheduler started with interval {interval_seconds}s")
