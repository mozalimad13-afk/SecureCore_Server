"""
CSRF Token Model
Manages CSRF tokens for security protection
"""
from datetime import datetime

from app.extensions import db


class CSRFToken(db.Model):
    """CSRF Token model for request protection"""
    
    __tablename__ = 'csrf_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.String(255))
    is_used = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    
    def __repr__(self):
        return f'<CSRFToken {self.id}>'
