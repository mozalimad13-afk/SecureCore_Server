"""
Subscription Model
Manages user subscription plans and limits
"""
from datetime import datetime, date

from app.extensions import db


class Subscription(db.Model):
    """Subscription model for user plans"""
    
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_name = db.Column(db.String(100), nullable=False)
    plan_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='trial', index=True)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date)
    next_billing_date = db.Column(db.Date)
    max_requests_per_minute = db.Column(db.Integer, default=1000)
    max_requests_per_month = db.Column(db.Integer, default=1000000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref=db.backref('subscription', uselist=False))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_name': self.plan_name,
            'plan_price': float(self.plan_price),
            'status': self.status,
            'max_requests_per_minute': self.max_requests_per_minute,
            'max_requests_per_month': self.max_requests_per_month,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None
        }
    
    def __repr__(self):
        return f'<Subscription {self.id} {self.plan_name}>'
