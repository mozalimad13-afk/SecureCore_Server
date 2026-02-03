"""
Company Settings Model
Stores company-wide preferences and configuration
"""
from datetime import datetime

from app.extensions import db


class CompanySettings(db.Model):
    """Company Settings model for company-wide preferences"""
    
    __tablename__ = 'company_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    # Notification Settings
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    webhook_notifications = db.Column(db.Boolean, default=False)
    webhook_url = db.Column(db.String(500))
    
    # Digest Settings
    daily_digest = db.Column(db.Boolean, default=False)
    weekly_report = db.Column(db.Boolean, default=True)
    digest_time = db.Column(db.String(10), default='09:00')
    
    # Backup Settings
    backup_frequency = db.Column(db.String(20), default='monthly')
    last_backup = db.Column(db.DateTime)
    next_backup = db.Column(db.DateTime)
    
    # Reminder Settings
    alert_reminder_enabled = db.Column(db.Boolean, default=True)
    alert_reminder_interval = db.Column(db.Integer, default=24)  # hours
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', foreign_keys=[company_id], backref='settings')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'emailNotifications': self.email_notifications,
            'smsNotifications': self.sms_notifications,
            'webhookNotifications': self.webhook_notifications,
            'webhookUrl': self.webhook_url or '',
            'dailyDigest': self.daily_digest,
            'weeklyReport': self.weekly_report,
            'digestTime': self.digest_time,
            'backupFrequency': self.backup_frequency,
            'lastBackup': self.last_backup.isoformat() if self.last_backup else None,
            'nextBackup': self.next_backup.isoformat() if self.next_backup else None,
            'alertReminderEnabled': self.alert_reminder_enabled,
            'alertReminderInterval': self.alert_reminder_interval,
        }
    
    def __repr__(self):
        return f'<CompanySettings company_id={self.company_id}>'
