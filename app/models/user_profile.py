"""
User Profile Model
Stores user-specific preferences and profile information
"""
from datetime import datetime

from app.extensions import db


class UserProfile(db.Model):
    """User Profile model for personal preferences"""
    
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    # Profile Information
    display_name = db.Column(db.String(255))
    profile_picture = db.Column(db.String(500))  # URL or path to profile picture
    bio = db.Column(db.Text)
    
    # Preferences
    timezone = db.Column(db.String(50), default='UTC')
    language = db.Column(db.String(10), default='en')
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    
    # Security Settings
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255))  # Encrypted 2FA secret
    
    # Notification Preferences (user-specific)
    email_on_mention = db.Column(db.Boolean, default=True)
    email_on_alert = db.Column(db.Boolean, default=True)
    push_notifications = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='profile')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'displayName': self.display_name,
            'profilePicture': self.profile_picture,
            'bio': self.bio,
            'timezone': self.timezone,
            'language': self.language,
            'theme': self.theme,
            'twoFactorEnabled': self.two_factor_enabled,
            'emailOnMention': self.email_on_mention,
            'emailOnAlert': self.email_on_alert,
            'pushNotifications': self.push_notifications,
        }
    
    def __repr__(self):
        return f'<UserProfile user_id={self.user_id}>'
