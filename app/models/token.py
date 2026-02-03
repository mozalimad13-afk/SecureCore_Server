"""
API Token Model
Manages API authentication tokens with usage tracking
"""
from datetime import datetime, timedelta
import secrets
import hashlib

from app.extensions import db
from app.utils.frontend_helpers import get_relative_time
from config import Config


class APIToken(db.Model):
    """API Token model for WebSocket and API authentication"""
    
    __tablename__ = 'api_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    token_prefix = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, index=True)
    requests_today = db.Column(db.Integer, default=0)
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        from app.utils.security import sanitize_html
        if 'name' in kwargs:
            kwargs['name'] = sanitize_html(kwargs['name'])
        super(APIToken, self).__init__(**kwargs)
    
    # Relationships
    company = db.relationship('Company', backref='api_tokens')
    
    @staticmethod
    def generate_token():
        """
        Generate a new API token
        
        Returns:
            tuple: (token_string, token_hash, token_prefix)
        """
        # Generate random token
        random_part = secrets.token_urlsafe(Config.API_TOKEN_LENGTH)
        token_string = f"{Config.API_TOKEN_PREFIX}{random_part}"
        
        # Create hash for storage
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        
        # Extract prefix for display
        token_prefix = token_string[:20]
        
        return token_string, token_hash, token_prefix
    
    @staticmethod
    def find_by_token(token_string):
        """
        Find token by token string
        
        Args:
            token_string: Full token string
        
        Returns:
            APIToken or None
        """
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        return APIToken.query.filter_by(
            token_hash=token_hash,
            is_active=True
        ).first()
    
    def update_usage(self):
        """Update token usage statistics"""
        self.requests_today += 1
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_relative_time: bool = True):
        """Convert to frontend-compatible dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'token_prefix': self.token_prefix,
            'is_active': self.is_active,
            'requests_today': self.requests_today,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
        
        # Add relative time for frontend
        if include_relative_time:
            if self.created_at:
                data['created_relative'] = get_relative_time(self.created_at)
            if self.last_used_at:
                data['last_used_relative'] = get_relative_time(self.last_used_at)
        
        return data
    
    def __repr__(self):
        return f'<APIToken {self.token_prefix}...>'
