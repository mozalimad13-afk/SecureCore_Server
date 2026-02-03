"""
FCM Device Model
Stores encrypted per-device identifiers (and optional FCM tokens).
"""
from datetime import datetime

from app.extensions import db


class FCMDevice(db.Model):
    """Per-user device record.

    Mobile login sends only `device_id` (encrypted at rest) to bind a device.
    If/when the app obtains an FCM token, it can be stored encrypted as well.
    """
    
    __tablename__ = 'fcm_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    # Per-device stable identifier: store encrypted value + hash for lookup.
    # We use a hash because encrypted bytes include a random IV and won't match across inserts.
    device_id_hash = db.Column(db.String(64), nullable=True, index=True)
    device_id_encrypted = db.Column(db.LargeBinary, nullable=True)
    # Optional: mobile may not have FCM set up.
    device_token_encrypted = db.Column(db.LargeBinary, nullable=True)  # AES encrypted FCM token
    # Optional metadata fields may exist in some DBs; they are not required by the mobile login flow.
    device_name = db.Column(db.String(255), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)  # 'android', 'ios', 'web'
    device_platform = db.Column(db.String(50), nullable=True)  # legacy/optional extra label
    app_version = db.Column(db.String(50), nullable=True)
    last_seen_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_notified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='fcm_devices')
    
    def to_dict(self):
        """Convert to dictionary (without exposing encrypted token)"""
        return {
            'id': self.id,
            'is_active': self.is_active,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'last_notified_at': self.last_notified_at.isoformat() if self.last_notified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<FCMDevice {self.id} user_id={self.user_id}>'

    # Backward compatibility
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value
