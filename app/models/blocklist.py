"""
Blocked IP Model
Manages IP addresses blocked by firewall
"""
from datetime import datetime

from app.extensions import db
from app.utils.frontend_helpers import get_relative_time


class BlockedIP(db.Model):
    """Blocked IP model for firewall management"""
    
    __tablename__ = 'blocked_ips'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    reason = db.Column(db.String(255))
    related_alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'))
    block_type = db.Column(db.String(20), default='manual')  # 'manual', 'automatic', 'temporary'
    is_active = db.Column(db.Boolean, default=True, index=True)
    expires_at = db.Column(db.DateTime)  # NULL for permanent
    ufw_rule_number = db.Column(db.Integer)  # UFW rule tracking
    snort_rule_id = db.Column(db.String(100))  # Snort rule tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deactivated_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        from app.utils.security import sanitize_html
        if 'reason' in kwargs:
            kwargs['reason'] = sanitize_html(kwargs['reason'])
        super(BlockedIP, self).__init__(**kwargs)
    
    def to_dict(self, include_relative_time: bool = True):
        """Convert to frontend-compatible dictionary"""
        data = {
            'id': self.id,
            'ip': self.ip_address,  # Frontend expects 'ip'
            'ip_address': self.ip_address,
            'reason': self.reason or 'No reason provided',
            'block_type': self.block_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
        
        # Add relative time and timestamp for frontend
        if include_relative_time and self.created_at:
            data['time'] = get_relative_time(self.created_at)
            data['timestamp'] = self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        return data
    
    def __repr__(self):
        return f'<BlockedIP {self.ip_address}>'

    # Backward compatibility
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value
