"""Company model.

Represents an isolated customer/account boundary (multi-company).
"""

from datetime import datetime
import secrets

from app.extensions import db


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    phone_number = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    users = db.relationship('User', back_populates='company')

    # Countries allowed/available for this company (optional scoping).
    # Uses `companies_countries` join table defined in `app.models.location`.
    locations = db.relationship(
        'Location',
        secondary='companies_countries',
        lazy='select',
    )

    @staticmethod
    def generate_public_id() -> str:
        return secrets.token_hex(16)

    def to_dict(self):
        return {
            'id': self.id,
            'public_id': self.public_id,
            'name': self.name,
            'company': self.company,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
