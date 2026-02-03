"""
Notification Model
In-app notifications for users
"""
from datetime import datetime

from app.extensions import db
from app.utils.frontend_helpers import get_relative_time
from app.utils.security import sanitize_html


class Notification(db.Model):
    """Notification model for in-app notifications"""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'alert', 'info', 'warning', 'success'
    priority = db.Column(db.String(20), default='medium')
    is_read = db.Column(db.Boolean, default=False, index=True)
    related_alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'))
    related_type = db.Column(db.String(50))  # 'alert', 'report', etc.
    related_id = db.Column(db.Integer)
    link = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)

    def __init__(self, **kwargs):
        if 'title' in kwargs:
            kwargs['title'] = sanitize_html(kwargs['title'])
        if 'message' in kwargs:
            kwargs['message'] = sanitize_html(kwargs['message'])
        super(Notification, self).__init__(**kwargs)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def to_dict(self, include_relative_time: bool = True):
        """Convert to frontend-compatible dictionary"""
        data = {
            'id': str(self.id),  # Frontend expects string ID
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'priority': self.priority,
            'read': self.is_read,  # Frontend expects 'read'
            'is_read': self.is_read,
            'related_type': self.related_type,
            'related_id': self.related_id,
            'link': self.link,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }
        
        # Add relative time for frontend
        if include_relative_time and self.created_at:
            data['time'] = get_relative_time(self.created_at)
        
        return data
    
    def __repr__(self):
        return f'<Notification {self.id} {self.type}>'

    # Backward compatibility
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value
