"""
WebSocket Session Model
Tracks active WebSocket connections and their statistics
"""
from datetime import datetime

from app.extensions import db


class WebSocketSession(db.Model):
    """WebSocket Session model for tracking connections"""
    
    __tablename__ = 'websocket_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    api_token_id = db.Column(db.Integer, db.ForeignKey('api_tokens.id', ondelete='CASCADE'), nullable=False)
    connection_ip = db.Column(db.String(45))
    is_active = db.Column(db.Boolean, default=True, index=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    disconnected_at = db.Column(db.DateTime)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow)
    inference_count = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<WebSocketSession {self.session_id}>'
