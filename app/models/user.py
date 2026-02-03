"""
User Model
Represents system users with authentication and role management
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.utils.frontend_helpers import get_relative_time


class User(db.Model):
    """User model for authentication and authorization"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user', index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    # Profile
    country = db.Column(db.String(100))
    
    def __init__(self, **kwargs):
        from app.utils.security import sanitize_html
        if 'name' in kwargs:
            kwargs['name'] = sanitize_html(kwargs['name'])
        super(User, self).__init__(**kwargs)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    company = db.relationship('Company', back_populates='users')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    fcm_devices = db.relationship('FCMDevice', back_populates='user', cascade='all, delete-orphan')
    user_profile = db.relationship('UserProfile', backref='owner', cascade='all, delete-orphan', uselist=False)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_relative_time: bool = False):
        """Convert to frontend-compatible dictionary"""
        # Get company role if user is part of a company
        company_role = None
        if self.company_id:
            from app.utils.security import get_user_company_role
            company_role = get_user_company_role(self, self.company_id)
        
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'company_role': company_role,  # Add company role for RBAC
            'is_active': self.is_active,
            'country': self.country,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        # Add relative time for frontend (optional)
        if include_relative_time:
            if self.created_at:
                data['member_since'] = get_relative_time(self.created_at)
            if self.last_login:
                data['last_login_relative'] = get_relative_time(self.last_login)
        
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'

    # Backward compatibility aliases
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value

    @property
    def tenant(self):
        return self.company

    @tenant.setter
    def tenant(self, value):
        self.company = value
