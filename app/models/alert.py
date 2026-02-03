"""
Alert Model
Stores detected security alerts from ML inference
"""
from datetime import datetime
import json

from app.extensions import db
from app.utils.frontend_helpers import get_relative_time


class Alert(db.Model):
    """Alert model for storing detected attacks"""
    
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    source_ip = db.Column(db.String(45), nullable=False, index=True)
    source_port = db.Column(db.Integer)
    destination_ip = db.Column(db.String(45))
    destination_port = db.Column(db.Integer)
    protocol = db.Column(db.String(10))  # TCP, UDP, ICMP, etc.
    attack_type = db.Column(db.String(100), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    raw_features = db.Column(db.Text)  # JSON - features used for ML inference
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    company = db.relationship('Company', backref='alerts')
    
    def get_features(self):
        """Get raw features as list"""
        if self.raw_features:
            return json.loads(self.raw_features)
        return []
    

    def to_dict(self, include_relative_time: bool = True):
        """Convert to frontend-compatible dictionary"""
        data = {
            'id': self.id,
            # Field aliases for frontend compatibility
            'ip': self.source_ip,  # Frontend expects 'ip'
            'source_ip': self.source_ip,
            'source_port': self.source_port,
            'destination_ip': self.destination_ip,
            'destination_port': self.destination_port,
            'protocol': self.protocol,
            'type': self.attack_type,  # Frontend expects 'type'
            'attack_type': self.attack_type,
            'severity': self.severity,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        # Add relative time for frontend
        if include_relative_time and self.created_at:
            data['time'] = get_relative_time(self.created_at)
            data['timestamp'] = self.created_at.isoformat()
        
        return data
    
    def __repr__(self):
        return f'<Alert {self.id} {self.attack_type} {self.severity}>'

    # Backward compatibility
    @property
    def tenant_id(self):
        return self.company_id

    @tenant_id.setter
    def tenant_id(self, value):
        self.company_id = value
