"""User-company role mapping for PBAC."""

from datetime import datetime

from app.extensions import db


class UserCompanyRole(db.Model):
    __tablename__ = 'user_company_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'company_id', name='uq_user_company_role'),
    )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'company_id': self.company_id,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
