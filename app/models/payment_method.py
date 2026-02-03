"""
Payment Method Model
Stores user payment information (last 4 digits only for security)
"""
from app.extensions import db
from datetime import datetime


class PaymentMethod(db.Model):
    """Payment method model for storing user payment information"""
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Card info (ONLY last 4 digits for security - never store full card number)
    card_last4 = db.Column(db.String(4), nullable=False)
    card_brand = db.Column(db.String(20))  # Visa, Mastercard, Amex, etc.
    card_holder_name = db.Column(db.String(100), nullable=False)
    expiry_month = db.Column(db.String(2), nullable=False)
    expiry_year = db.Column(db.String(2), nullable=False)
    
    # Billing address
    billing_address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    
    # Status
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    company = db.relationship('Company', backref=db.backref('payment_methods', lazy=True))
    
    def to_dict(self):
        """Convert payment method to dictionary"""
        return {
            'id': self.id,
            'card_last4': self.card_last4,
            'card_brand': self.card_brand,
            'card_holder_name': self.card_holder_name,
            'expiry': f"{self.expiry_month}/{self.expiry_year}",
            'expiry_month': self.expiry_month,
            'expiry_year': self.expiry_year,
            'billing_address': self.billing_address,
            'city': self.city,
            'zip_code': self.zip_code,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<PaymentMethod {self.id} - •••• {self.card_last4}>'
