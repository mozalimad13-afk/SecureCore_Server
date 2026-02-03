"""
Admin Broadcast Model
Tracks notifications sent by admins to multiple users
"""
from datetime import datetime
from app.extensions import db

class AdminBroadcast(db.Model):
    """Model for tracking admin-sent broadcast notifications"""
    
    __tablename__ = 'admin_broadcasts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(50), nullable=False)  # 'all', 'selected', 'single'
    recipient_count = db.Column(db.Integer, default=0)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        from app.utils.security import sanitize_html
        if 'title' in kwargs:
            kwargs['title'] = sanitize_html(kwargs['title'])
        if 'message' in kwargs:
            kwargs['message'] = sanitize_html(kwargs['message'])
        super(AdminBroadcast, self).__init__(**kwargs)
    
    # Relationship to sender
    sender = db.relationship('User', foreign_keys=[sender_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'target': self.target_type,
            'recipients_display': self.target_type,
            'recipient_count': self.recipient_count,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M'),
            'status': 'delivered'
        }

    # Backward compatibility
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value
